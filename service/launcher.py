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
import signal
import subprocess
import sys

from absl import app
from absl import flags
from absl import logging
import common.generate_protos  # pylint: disable=unused-import
import common.pip_installer  # pylint: disable=unused-import

FLAGS = flags.FLAGS

flags.DEFINE_string('port', '[::]:50051',
                    'Port for the Falken service to accept RPCs.')
flags.DEFINE_string('ssl_dir', None, 'Path containing the SSL cert and key.')
flags.DEFINE_bool('clean_up_protos', False,
                  'Clean up generated protos at stop.')


def run_api(current_path):
  """Start the API in a subprocess.

  Args:
    current_path: The path of the file being executed. Used to retrieve the
      falken_service.py path.

  Returns:
    Popen instance where the API service is running.
  """
  return subprocess.Popen(
      [sys.executable, '-m', 'api.falken_service', '--port', FLAGS.port,
       '--ssl_dir', FLAGS.ssl_dir], env=os.environ, cwd=current_path)


def main(argv):
  if len(argv) > 1:
    logging.error('Non-flag parameters are not allowed.')

  logging.debug('Starting Falken services. Press ctrl-c to exit.')
  file_dir = os.path.dirname(os.path.abspath(__file__))
  api_process = run_api(file_dir)
  while True:
    try:
      _ = sys.stdin.readline()  # Wait for keyboard input.
    except KeyboardInterrupt:
      logging.debug('Cleaning up...')
      if FLAGS.clean_up_protos:
        common.generate_protos.clean_up()
      api_process.send_signal(signal.SIGINT)
      break


if __name__ == '__main__':
  app.run(main)
