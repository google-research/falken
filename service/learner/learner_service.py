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
"""Module to start the learner service."""

import os
import signal
import tempfile
import traceback
from typing import Optional

from absl import app
from absl import flags
from data_store import data_store as data_store_module
from data_store import file_system as data_store_file_system
from learner import learner as learner_module
from learner import storage
from log import falken_logging

flags.DEFINE_string('root_dir', '',
                    'Directory where the Falken service will store data.')
flags.DEFINE_string('tmp_models_dir', None,
                    'Temporary parent directory for models.')
flags.DEFINE_string('models_dir', None,
                    'Permanent parent directory that contains all models.')
flags.DEFINE_string('checkpoints_dir', None,
                    'Parent directory that contains all checkpoints.')
flags.DEFINE_string('summaries_dir', None,
                    'Parent directory that contains all summaries.')
FLAGS = flags.FLAGS


def _get_permanent_storage_dir(dir_property_name: str) -> str:
  """Get a path to the specified directory.

  Args:
    dir_property_name: Name of the directory property to fetch, e.g
      summaries_dir.

  Returns:
    Absolute path of the directory.
  """
  directory = getattr(FLAGS, dir_property_name)
  if not directory:
    directory = os.path.join(FLAGS.root_dir, dir_property_name)
  return os.path.abspath(directory)


class LearnerService:
  """Creates a Learner based upon the module's flags."""

  def __init__(self, assignment_path: Optional[str]):
    """Create a learner instance from the module's flags."""
    falken_logging.info(
        f'Creating Learner that uses data store {FLAGS.root_dir}')
    # TemporaryDirectory objects.
    self._temporary_directories = []
    fs = data_store_file_system.FileSystem(FLAGS.root_dir)
    self._learner = learner_module.Learner(
        self._get_temporary_storage_dir('tmp_models_dir'),
        _get_permanent_storage_dir('models_dir'),
        _get_permanent_storage_dir('checkpoints_dir'),
        _get_permanent_storage_dir('summaries_dir'),
        storage.Storage(data_store_module.DataStore(fs), fs),
        assignment_path=assignment_path)

  def _get_temporary_storage_dir(self, dir_property_name: str) -> str:
    """Get a path to a temporary directory to store models.

    Args:
      dir_property_name: Name of the directory property to fetch, e.g
        tmp_models_dir.

    Returns:
      Absolute path of the temporary directory.
    """
    directory = getattr(FLAGS, dir_property_name)
    if directory:
      os.makedirs(directory, exist_ok=True)
      temp_dir = tempfile.TemporaryDirectory(prefix=dir_property_name,
                                             dir=directory)
    else:
      temp_dir = tempfile.TemporaryDirectory(prefix=dir_property_name)
    self._temporary_directories.append(temp_dir)
    return os.path.abspath(temp_dir.name)

  def _cleanup_temporary_dirs(self):
    """Clean up temporary directories."""
    for temp_dir in self._temporary_directories:
      temp_dir.cleanup()
    self._temporary_directories = []

  def run(self, iterations: int):
    """Process assignments.

    Processes assignments until the number of iterations is reached or a
    keyboard interrupt (sigint) occurs.

    Args:
      iterations: Number of attempts to process assignments.
    """
    falken_logging.info('Started Falken Learner service; '
                        'waiting for assignments...')
    while iterations != 0:
      if iterations > 0: iterations -= 1
      try:
        self._learner.process_assignment()
      except KeyboardInterrupt as e:  # Handle SIGINT.
        return
      except Exception as e:  # pylint: disable=broad-except
        falken_logging.error(
            f'Exception found when processing assignment: {e}\n'
            f'{traceback.format_exc()}')
        raise e

  def stop(self):
    """Stop processing assignments. This can be called from another thread."""
    self._learner.stop_process_assignment()

  def shutdown(self):
    """Stop processing assignments and cleanup."""
    self._learner.shutdown()
    self._cleanup_temporary_dirs()


def main(unused_argv, assignment_path=None, iterations=-1):
  """Start a learner from the module's flags."""
  service = LearnerService(assignment_path)
  # Gracefully shut down when handling SIGTERM.
  signal.signal(signal.SIGTERM,
                lambda unused_signnum, unused_frame: service.stop())
  try:
    service.run(iterations)
  except KeyboardInterrupt:
    pass

  falken_logging.info('Shutting down learner...')
  service.shutdown()
  falken_logging.info('Shutdown complete.')


if __name__ == '__main__':
  app.run(main)
