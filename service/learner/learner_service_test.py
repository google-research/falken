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

"""Unit test the learner service entrypoint."""

import os
import tempfile
from unittest import mock

from absl.testing import absltest
from data_store import data_store as data_store_module
from data_store import file_system as data_store_file_system
from learner import learner
from learner import learner_service
from learner import storage


class LearnerServiceTest(absltest.TestCase):

  def setUp(self):
    """Reset flags."""
    super().setUp()
    learner_service.FLAGS.root_dir = ''
    learner_service.FLAGS.tmp_models_dir = None
    learner_service.FLAGS.models_dir = None
    learner_service.FLAGS.checkpoints_dir = None
    learner_service.FLAGS.summaries_dir = None

  def test_get_permanent_storage_dir_when_flag_set(self):
    """Get the permanent storage dir from its' flag."""
    learner_service.FLAGS.models_dir = 'foo'
    self.assertEqual(
        learner_service._get_permanent_storage_dir('models_dir'),
        os.path.abspath('foo'))

  def test_get_permanent_storage_dir_when_flag_not_set(self):
    """Derive a permanent storage dir from the root dir and the flag name."""
    learner_service.FLAGS.root_dir = os.sep + os.path.join('a', 'root')
    self.assertEqual(
        learner_service._get_permanent_storage_dir('summaries_dir'),
        os.path.abspath(os.path.join(learner_service.FLAGS.root_dir,
                                     'summaries_dir')))

  @mock.patch.object(learner, 'Learner')
  def test_get_temporary_storage_dir_when_flag_set(self, unused_mock_learner):
    """Get a temporary directory when a flag is set."""
    with tempfile.TemporaryDirectory() as test_dir:
      learner_service.FLAGS.tmp_models_dir = test_dir
      service = learner_service.LearnerService(None)
      temporary_dir = service._get_temporary_storage_dir('tmp_models_dir')
      self.assertEqual(temporary_dir.split(os.path.sep)[:-1],
                       test_dir.split(os.path.sep))

  @mock.patch.object(learner, 'Learner')
  def test_get_temporary_storage_dir_when_flag_not_set(self,
                                                       unused_mock_learner):
    """Get a temporary directory when a flag is not set."""
    temporary_dir = ''
    service = learner_service.LearnerService(None)
    try:
      temporary_dir = service._get_temporary_storage_dir('tmp_models_dir')
      self.assertTrue(os.path.exists(temporary_dir))
    finally:
      if os.path.exists(temporary_dir):
        os.rmdir(temporary_dir)

  @mock.patch.object(learner, 'Learner')
  def test_cleanup_temporary_dirs(self, unused_mock_learner):
    """Create and cleanup temporary directories."""
    service = learner_service.LearnerService(None)
    with tempfile.TemporaryDirectory() as test_dir:
      learner_service.FLAGS.tmp_models_dir = test_dir
      temporary_dir = service._get_temporary_storage_dir('tmp_models_dir')
      service._cleanup_temporary_dirs()
      self.assertFalse(os.path.exists(temporary_dir))

  @mock.patch.object(storage, 'Storage', autospec=True)
  @mock.patch.object(data_store_module, 'DataStore', autospec=True)
  @mock.patch.object(data_store_file_system, 'FileSystem', autospec=True)
  @mock.patch.object(learner, 'Learner', autospec=True)
  def test_construct(self, mock_learner_class, mock_file_system_class,
                     mock_data_store_class, mock_storage_class):
    """Test constructing a learner from module flags."""
    with tempfile.TemporaryDirectory() as test_dir:
      learner_service.FLAGS.root_dir = os.path.abspath('root_dir')
      learner_service.FLAGS.tmp_models_dir = test_dir
      learner_service.FLAGS.models_dir = os.path.abspath('models')
      learner_service.FLAGS.checkpoints_dir = os.path.abspath('checkpoints')
      learner_service.FLAGS.summaries_dir = os.path.abspath('summaries')
      mock_file_system = mock_file_system_class.return_value
      mock_data_store = mock_data_store_class.return_value
      mock_storage = mock_storage_class.return_value
      _ = learner_service.LearnerService('an/assignment/path')

      class StartsWith(str):
        """Checks whether another string starts with this one."""

        def __eq__(self, other):
          return other.startswith(self)

      mock_file_system_class.assert_called_once_with(
          learner_service.FLAGS.root_dir)
      mock_data_store_class.assert_called_once_with(mock_file_system)
      mock_storage_class.assert_called_once_with(mock_data_store,
                                                 mock_file_system)
      mock_learner_class.assert_called_once_with(
          StartsWith(test_dir),
          learner_service.FLAGS.models_dir,
          learner_service.FLAGS.checkpoints_dir,
          learner_service.FLAGS.summaries_dir, mock_storage,
          assignment_path='an/assignment/path')

  @mock.patch.object(learner, 'Learner', autospec=True)
  def test_run_limited_iterations(self, mock_learner_class):
    """Test processing learner assignments."""
    mock_learner = mock_learner_class.return_value
    service = learner_service.LearnerService(None)
    service.run(3)
    mock_learner.process_assignment.assert_has_calls([mock.call()] * 3)

  @mock.patch.object(learner, 'Learner', autospec=True)
  def test_run_until_interrupt(self, mock_learner_class):
    """Test processing learner assignments until a keyboard interrupt."""
    iteration = 0
    expected_iterations = 10

    def raise_keyboard_interrupt():
      """Raise a keyboard interrupt after expected_iterations."""
      nonlocal iteration
      iteration += 1
      if iteration >= expected_iterations:
        raise KeyboardInterrupt()

    mock_learner = mock_learner_class.return_value
    mock_learner.process_assignment.side_effect = raise_keyboard_interrupt
    service = learner_service.LearnerService(None)
    service.run(-1)
    mock_learner.process_assignment.assert_has_calls([mock.call()] *
                                                     expected_iterations)

  @mock.patch.object(learner, 'Learner', autospec=True)
  def test_stop(self, mock_learner_class):
    """Test stopping the learner."""
    mock_learner = mock_learner_class.return_value
    service = learner_service.LearnerService(None)
    service.stop()
    mock_learner.stop_process_assignment.assert_called_once()

  @mock.patch.object(learner, 'Learner', autospec=True)
  def test_shutdown(self, mock_learner_class):
    """Test shutting down the learner."""
    mock_learner = mock_learner_class.return_value
    service = learner_service.LearnerService(None)
    with mock.patch.object(service, '_cleanup_temporary_dirs') as mock_cleanup:
      service.shutdown()
      mock_learner.shutdown.assert_called_once()
      mock_cleanup.assert_called_once()

  @mock.patch.object(learner_service, 'LearnerService', autospec=True)
  def test_main(self, mock_service_class):
    """Test the entry point of the service module."""
    mock_service = mock_service_class.return_value

    learner_service.main([], assignment_path='a/assignment', iterations=2)
    mock_service_class.assert_called_once_with('a/assignment')
    mock_service.run.assert_called_once_with(2)
    mock_service.shutdown.assert_called_once()


if __name__ == '__main__':
  absltest.main()
