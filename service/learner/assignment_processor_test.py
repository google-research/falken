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
"""Tests for assignment_processor."""
import os
import tempfile
import time
from unittest import mock

from absl import flags
from absl.testing import absltest
from absl.testing import parameterized

from data_store import data_store as data_store_module
from data_store import file_system as data_store_file_system
from learner import assignment_processor
from learner import storage
from learner import test_data
from learner.brains import brain_cache
from learner.brains import continuous_imitation_brain

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import data_store_pb2 as falken_schema_pb2


class AssignmentProcessorTest(parameterized.TestCase):

  def setUp(self):
    super().setUp()
    self._assignment = test_data.assignment()
    write_assignment = test_data.assignment()
    write_assignment.session_id = 'write_session'
    self._write_assignment = write_assignment
    self._mock_storage = mock.Mock()
    self._mock_storage.get_brain_spec.return_value = falken_schema_pb2.Brain()
    self._mock_storage.get_assignment.return_value = self._assignment
    self._mock_fs = mock.Mock()

  @mock.patch.object(continuous_imitation_brain, 'ContinuousImitationBrain',
                     autospec=True)
  def test_process_already_closed(self, mock_continuous_imitation_brain):
    with assignment_processor.AssignmentProcessor(
        self._assignment,
        self._mock_fs,
        self._mock_storage,
        brain_cache.BrainCache(
            assignment_processor.populate_hparams_with_defaults_and_validate),
        get_session_state=(lambda: storage.SessionState.ENDED),
        write_assignment=self._write_assignment,
        always_block_when_fetching=False) as proc:
      mock_brain = mock.Mock()
      mock_continuous_imitation_brain.return_value = mock_brain
      self.assertEmpty(list(proc.process()))

  @mock.patch.object(continuous_imitation_brain, 'ContinuousImitationBrain',
                     autospec=True)
  def test_process_exceeded_max_work_time(
      self, mock_continuous_imitation_brain):
    with assignment_processor.AssignmentProcessor(
        self._assignment,
        self._mock_fs,
        self._mock_storage,
        brain_cache.BrainCache(
            assignment_processor.populate_hparams_with_defaults_and_validate),
        get_session_state=(lambda: storage.SessionState.NEW),
        write_assignment=self._write_assignment,
        always_block_when_fetching=False) as proc:
      mock_brain = mock.Mock()
      mock_hparams = mock.PropertyMock(return_value={})
      type(mock_brain).hparams = mock_hparams
      mock_continuous_imitation_brain.return_value = mock_brain

      try:
        old_val = assignment_processor._MAX_ASSIGNMENT_WORK_TIME_SECS
        assignment_processor._MAX_ASSIGNMENT_WORK_TIME_SECS = 0
        with self.assertRaises(assignment_processor.ExceededMaxWorkTimeError):
          list(proc.process())
      finally:
        assignment_processor._MAX_ASSIGNMENT_WORK_TIME_SECS = old_val

  @parameterized.parameters(True, False)
  @mock.patch.object(continuous_imitation_brain, 'ContinuousImitationBrain',
                     autospec=True)
  def test_process(self, synchronous_export, mock_continuous_imitation_brain):
    episode_chunks = test_data.episode_chunks(
        [10] * 3, 'episode_id')

    def get_episode_chunks(*unused_args):
      """Return episode_chunks once."""
      returned_episode_chunks = list(episode_chunks)
      episode_chunks.clear()
      return returned_episode_chunks

    self._mock_storage.get_episode_chunks.side_effect = get_episode_chunks
    with assignment_processor.AssignmentProcessor(
        self._assignment,
        self._mock_fs,
        self._mock_storage,
        brain_cache.BrainCache(
            assignment_processor.populate_hparams_with_defaults_and_validate),
        get_session_state=(lambda: storage.SessionState.NEW),
        write_assignment=self._write_assignment,
        always_block_when_fetching=False) as proc:

      mock_brain = mock.Mock()
      mock_brain.num_train_frames = 10
      mock_brain.num_eval_frames = 10
      mock_brain.global_step = 20
      # Evals follow the format of (eval_version, eval_score)
      eval_tuples = [(0, 2.3), (1, 2.34), (2, 2.11), (3, 1.0)]
      mock_brain.compute_full_evaluation.return_value = iter(eval_tuples)
      mock_hparams = mock.PropertyMock(
          return_value={'synchronous_export': synchronous_export,
                        'save_interval_batches': 5,
                        'batch_size': 10})
      type(mock_brain).hparams = mock_hparams
      mock_continuous_imitation_brain.return_value = mock_brain

      tmp_checkpoint_path = (
          tempfile.TemporaryDirectory(
              prefix=os.path.join(
                  flags.FLAGS.test_tmpdir, 'checkpoint')).name)
      tmp_model_path = tmp_checkpoint_path.replace('checkpoint', 'saved_model')
      self._mock_fs.create_tmp_checkpoint_path.return_value = (
          tmp_checkpoint_path)
      self._mock_fs.extract_tmp_model_path_from_checkpoint_path.return_value = (
          tmp_model_path)
      os.makedirs(tmp_checkpoint_path)

      process_assignment_generator = proc.process()

      # First yield in process_assignment_generator should be for fetching data.
      status, metadata = next(process_assignment_generator)
      self.assertEqual(
          status, assignment_processor.ProcessAssignmentStatus.WILL_FETCH_DATA)
      self.assertIsNone(metadata)

      # Eventually, enters the training/saving model flow.
      for s, m in process_assignment_generator:
        status, metadata = s, m
        if status == assignment_processor.ProcessAssignmentStatus.SAVED_MODEL:
          break

      # Force training completion by mocking out ModelManager.should_stop() to
      # True
      mock_model_manager = mock.Mock()
      mock_model_manager.should_stop.return_value = True
      proc._model_manager = mock_model_manager

      # Wait until model exporting completed.
      while not self._mock_storage.record_evaluations.called:
        time.sleep(0.1)

      # Verify save model/eval operations were called.
      self.assertEqual(self._mock_fs.copy_to_model_directory.call_count, 1)
      self.assertEqual(self._mock_fs.compress_model_directory.call_count, 1)
      self.assertEqual(self._mock_storage.record_new_model.call_count, 1)
      self.assertEqual(self._mock_storage.record_evaluations.call_count, 1)
      self.assertIsNotNone(metadata)  # Returns model_id of saved model.

      # Last state for when main loop is complete and the step has been
      # processed.
      status, metadata = list(process_assignment_generator)[-1]
      self.assertEqual(
          status, assignment_processor.ProcessAssignmentStatus.PROCESSED_STEP)
      self.assertIsNone(metadata)
      self.assertGreater(self._mock_fs.wipe_checkpoints.call_count, 0)

  def test_chunk_generator(self):
    """Test fetching episode chunks."""
    temporary_file_system = data_store_file_system.FileSystem(
        self.create_tempdir())
    data_store = data_store_module.DataStore(temporary_file_system)
    with assignment_processor.AssignmentProcessor(
        self._assignment,
        self._mock_fs,
        storage.Storage(data_store, temporary_file_system),
        brain_cache.BrainCache(
            assignment_processor.populate_hparams_with_defaults_and_validate),
        get_session_state=(lambda: storage.SessionState.ENDED),
        write_assignment=self._write_assignment,
        always_block_when_fetching=False) as proc:

      _, episode_chunk_resource_ids = test_data.populate_data_store(
          data_store, episode_ids=['episode_0', 'episode_1'],
          steps_per_episode_chunk=[3] * 2)

      # Should return the current set of chunks.
      chunk_generator = proc._chunk_generator()
      chunks = next(iter(chunk_generator))
      read_resource_ids = [data_store.to_resource_id(c) for c in chunks]
      self.assertCountEqual(episode_chunk_resource_ids, read_resource_ids)
      # Add and fetch more chunks.
      _, episode_chunk_resource_ids = test_data.populate_data_store(
          data_store, episode_ids=['episode_2', 'episode_3', 'episode_4'],
          steps_per_episode_chunk=[4] * 3)
      chunks = next(iter(chunk_generator))
      read_resource_ids = [data_store.to_resource_id(c) for c in chunks]
      self.assertCountEqual(episode_chunk_resource_ids, read_resource_ids)
      # No more chunks.
      self.assertIsNone(next(iter(chunk_generator)))


if __name__ == '__main__':
  absltest.main()
