# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Lint as: python3
"""Launches Falken services."""
import os
import platform
import signal
import subprocess
import sys

# pylint: disable=unused-import,g-bad-import-order
# NOTE: All non-standard libraries must be included after pip_installer
import common.pip_installer
import common.generate_protos

from absl import app
from absl import flags
from absl import logging

from api import api_keys
from data_store import data_store
from data_store import file_system


FLAGS = flags.FLAGS

flags.DEFINE_integer('port', 50051,
                     'Port for the Falken service to accept RPCs.')
flags.DEFINE_string('ssl_dir',
                    os.path.dirname(os.path.abspath(__file__)),
                    'Path containing the SSL cert and key.')
flags.DEFINE_string('root_dir', os.getcwd(),
                    'Directory where the Falken service will store data.')
flags.DEFINE_bool('clean_up_protos', False,
                  'Clean up generated protos at stop.')
flags.DEFINE_multi_string(
    'project_ids', [],
    'Project IDs to create API keys for and use with Falken.')
flags.DEFINE_bool(
    'generate_sdk_config', False,
    'Auto-generate SDK config using default settings. Requires that exactly '
    'one project_id is specified via --project_ids')
flags.DEFINE_multi_string(
    'hyperparameters',
    r'{"fc_layers":[64], "learning_rate":1e-4, "continuous":false, '
    r'"min_train_examples":100000, "max_train_examples":30000000, '
    r'"activation_fn":"tanh"}',
    'Hyperparameters to train the models on.')


def check_ssl():
  """Check if the SSL cert and key exists and request them if they are not.

  Raises:
    FileNotFoundError: when at the end of the operation the key or cert are not
      found.
  """
  key_file = os.path.join(FLAGS.ssl_dir, 'key.pem')
  cert_file = os.path.join(FLAGS.ssl_dir, 'cert.pem')
  if os.path.isfile(key_file) and os.path.isfile(cert_file):
    return

  logging.debug(
      'Cannot find %s and %s, so requesting certificates using openssl.',
      key_file, cert_file)
  try:
    subprocess.run(
        ['openssl', 'req', '-x509', '-newkey', 'rsa:4096', '-keyout', key_file,
         '-out', cert_file, '-days', '365', '-nodes', '-subj',
         '/CN=localhost'], check=True)
  except (subprocess.CalledProcessError, FileNotFoundError) as e:
    logging.error('Please install openssl at openssl.org.')
    raise e

  if not os.path.isfile(key_file):
    raise FileNotFoundError('Key was not created.')
  if not os.path.isfile(cert_file):
    raise FileNotFoundError('Cert were not created.')


def run_api(current_path: str):
  """Start the API in a subprocess.

  Args:
    current_path: The path of the file being executed. Passed as the cwd of the
      subprocess.

  Returns:
    Popen instance where the API service is running.
  """
  args = [
      sys.executable, '-m', 'api.falken_service', '--root_dir', FLAGS.root_dir,
      '--port', str(FLAGS.port), '--ssl_dir', FLAGS.ssl_dir,
      '--verbosity', str(FLAGS.verbosity), '--alsologtostderr',
      '--log_dir', FLAGS.log_dir,
  ]
  for hyperparameters in FLAGS.hyperparameters:
    args.extend(['--hyperparameters', hyperparameters])
  for project_id in FLAGS.project_ids:
    args.append('--project_ids')
    args.append(project_id)
  return subprocess.Popen(args, env=os.environ, cwd=current_path)


def run_learner(current_path: str):
  """Start the learner in a subprocess.

  Args:
    current_path: The path of the file being executed. Passed as the cwd of the
      subprocess.

  Returns:
    Popen instance where the learner service is running.
  """
  return subprocess.Popen(
      [sys.executable, '-m', 'learner.learner_service',
       '--root_dir', FLAGS.root_dir, '--verbosity', str(FLAGS.verbosity),
       '--alsologtostderr', '--log_dir', FLAGS.log_dir],
      env=os.environ, cwd=current_path)


def run_generate_sdk_configuration(
    current_path: str, project_id: str, api_key: str):
  """Run script to generate the JSON config file for the SDK."""
  logging.info('Writing config for project %s, api_key %s', project_id, api_key)
  subprocess.run(
      [sys.executable, '-m', 'tools.generate_sdk_configuration',
       '--project_id', project_id, '--api_key', api_key, '--ssl_dir',
       FLAGS.ssl_dir],
      check=True, cwd=current_path)


def main(argv):
  if len(argv) > 1:
    logging.error('Non-flag parameters are not allowed.')

  logging.get_absl_handler().use_absl_log_file()
  check_ssl()

  file_dir = os.path.dirname(os.path.abspath(__file__))
  if FLAGS.generate_sdk_config:
    if len(FLAGS.project_ids) != 1:
      raise ValueError('--generate_sdk_config flag requires that exactly '
                       'one project ID is specified via --project_ids')
    (project_id,) = FLAGS.project_ids
    api_key = api_keys.get_or_create_api_key(
        data_store.DataStore(file_system.FileSystem(FLAGS.root_dir)),
        project_id)
    run_generate_sdk_configuration(file_dir, project_id, api_key)

  logging.debug('Starting Falken services. Press ctrl-c to exit.')
  api_process = run_api(file_dir)
  learner_process = run_learner(file_dir)
  while True:
    try:
      _ = sys.stdin.readline()  # Wait for keyboard input.
    except KeyboardInterrupt:
      logging.debug('Cleaning up...')
      if FLAGS.clean_up_protos:
        common.generate_protos.clean_up()
      signal_to_send = (
          signal.CTRL_C_EVENT
          if platform.system().lower() == 'windows' else signal.SIGINT)
      api_process.send_signal(signal_to_send)
      learner_process.send_signal(signal_to_send)
      break


if __name__ == '__main__':
  app.run(main)
