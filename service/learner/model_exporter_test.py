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
"""Tests for google3.research.kernel.falken.service.learner.model_exporter."""
import os
import tempfile
import time
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized

from data_store import data_store
from data_store import file_system as data_store_file_system
from learner import file_system
from learner import model_exporter
from learner import model_manager
from learner import stats_collector
from learner import storage
from learner import test_data
from learner.brains import continuous_imitation_brain
from learner.brains import demonstration_buffer


class ModelExporterTest(parameterized.TestCase):

  _STEPS_PER_EPISODE = 10
  _EPISODES_TO_RUN = 100
  _ENVIRONMENT_ID = 0

  def setUp(self):
    super(ModelExporterTest, self).setUp()

    self._tmp_data_store_root = tempfile.TemporaryDirectory()
    temp_file_system = data_store_file_system.FileSystem(
        self._tmp_data_store_root.name)
    self._data_store = data_store.DataStore(temp_file_system)

    test_data.populate_data_store(self._data_store)

    self._assignment = test_data.assignment()
    self._storage = storage.Storage(self._data_store, temp_file_system)

    self._tmp_export_path = tempfile.TemporaryDirectory()

    self.checkpoints_path = os.path.join(
        self._tmp_export_path.name, 'checkpoints')
    self.summaries_path = os.path.join(
        self._tmp_export_path.name, 'summaries')
    self.tmp_models_path = os.path.join(
        self._tmp_export_path.name, 'tmp_models')
    self.models_path = os.path.join(
        self._tmp_export_path.name, 'models')

    self._fs = file_system.FileSystem(self.tmp_models_path, self.models_path,
                                      self.checkpoints_path,
                                      self.summaries_path)
    self._model_manager = model_manager.ModelManager()

    self._hparams = continuous_imitation_brain.BCAgent.default_hparams()
    self._hparams['training_examples'] = 1

    self._eval_tuples = [(0, 2.3), (1, 2.34), (2, 2.11), (3, 1.0)]
    self._stats = stats_collector.StatsCollector(self._assignment.project_id,
                                                 self._assignment.brain_id,
                                                 self._assignment.session_id,
                                                 self._assignment.assignment_id)

  def initialize_and_start_model_exporter(self, synchronous):
    self._hparams['synchronous_export'] = synchronous
    self._model_exporter = model_exporter.ModelExporter(self._assignment,
                                                        self._storage, self._fs,
                                                        self._model_manager,
                                                        self._hparams)
    self._model_exporter.start()

  def tearDown(self):
    del self._tmp_data_store_root
    del self._tmp_export_path
    super(ModelExporterTest, self).tearDown()

  def setup_valid_checkpoint(self, checkpoint_path):
    """Sets up everything in a checkpoint path that had been saved."""
    brain = continuous_imitation_brain.ContinuousImitationBrain(
        brain_id=self._assignment.brain_id,
        spec_pb=self._storage.get_brain_spec(self._assignment.project_id,
                                             self._assignment.brain_id),
        checkpoint_path=self.checkpoints_path,
        hparams=self._hparams)

    observation_data = test_data.observation_data(50.0, (10, 15, 20))
    action_data = test_data.action_data(1, 0.3)
    reward = 0

    total_frames = self._STEPS_PER_EPISODE * self._EPISODES_TO_RUN
    for i in range(total_frames):
      phase = demonstration_buffer.StepPhase.IN_PROGRESS
      if i % self._STEPS_PER_EPISODE == 0:
        phase = demonstration_buffer.StepPhase.START
      elif i % self._STEPS_PER_EPISODE == self._STEPS_PER_EPISODE - 1:
        phase = demonstration_buffer.StepPhase.SUCCESS
      brain.record_step(observation_data, reward, phase, self._ENVIRONMENT_ID,
                        action_data, i)

    brain.train()

    os.makedirs(checkpoint_path)
    brain.save_checkpoint(checkpoint_path)

  @parameterized.parameters(True, False)
  def test_stop_error(self, synchronous_export):
    self.initialize_and_start_model_exporter(synchronous_export)
    self._model_exporter._error_queue.put((ValueError(), 'stack_trace'))
    with self.assertRaises(ValueError):
      self._model_exporter.stop()

  @parameterized.parameters(True, False)
  def test_export_empty_eval(self, synchronous_export):
    self.initialize_and_start_model_exporter(synchronous_export)
    with self.assertRaises(ValueError):
      self._model_exporter.export_model(
          '', [], self._stats, 'model_id', 'episode_id', 0,
          training_examples_completed=10, max_training_examples=100,
          most_recent_demo_time_micros=0)
    self._model_exporter.stop()

  @parameterized.parameters(True, False)
  @mock.patch.object(
      model_exporter.ModelExporter, '_export_model', autospec=True)
  def test_export_queue_processing(self, synchronous_export, mock_export_model):
    self.initialize_and_start_model_exporter(synchronous_export)
    self._model_exporter.export_model(
        'test_checkpoint_queue_process', self._eval_tuples, self._stats,
        'model_id', 'episode_id', 0, training_examples_completed=10,
        max_training_examples=100, most_recent_demo_time_micros=0)
    # Wait for mock_export_model to be called in a BG thread.
    while not mock_export_model.called:
      time.sleep(0.1)

    self.assertEqual(mock_export_model.call_count, 1)
    call_args = mock_export_model.call_args[0]
    self.assertLen(call_args, 2)
    self.assertEqual(call_args[0], self._model_exporter)
    called_task = call_args[1]
    self.assertEqual(
        called_task, model_exporter._ModelExportTask(
            checkpoint_path='test_checkpoint_queue_process',
            eval_list=self._eval_tuples, stats=mock.ANY,
            model_id='model_id', episode_id='episode_id', episode_chunk_id=0,
            training_examples_completed=10, max_training_examples=100,
            most_recent_demo_time_micros=0))

  def test_export_invalid_checkpoint(self):
    self.initialize_and_start_model_exporter(True)
    invalid_checkpoint_path = os.path.join(self.tmp_models_path,
                                           'invalid/checkpoint/')
    with self.assertRaises(ValueError):
      self._model_exporter.export_model(
          invalid_checkpoint_path, self._eval_tuples, self._stats, 'model_id',
          'episode_id', 0, training_examples_completed=10,
          max_training_examples=100, most_recent_demo_time_micros=0)

  @parameterized.parameters(True, False)
  def test_export_model(self, synchronous_export):
    self.initialize_and_start_model_exporter(synchronous_export)

    checkpoint_path_0 = os.path.join(self.tmp_models_path, '0/checkpoint')
    self.setup_valid_checkpoint(checkpoint_path_0)

    self._model_exporter.export_model(
        checkpoint_path_0, self._eval_tuples, self._stats, 'model_id_0',
        'episode_id', 0, training_examples_completed=10,
        max_training_examples=100, most_recent_demo_time_micros=0)
    self.assertTrue(self._model_exporter._export_model_thread.is_alive())

    checkpoint_path_1 = os.path.join(self.tmp_models_path, '1/checkpoint')
    self.setup_valid_checkpoint(checkpoint_path_1)
    model_1_eval_tuples = [(4, 0.9), (5, 0.1)]
    self._model_exporter.export_model(
        checkpoint_path_1, model_1_eval_tuples, self._stats, 'model_id_1',
        'episode_id', 0, training_examples_completed=10,
        max_training_examples=100, most_recent_demo_time_micros=0)
    self.assertTrue(self._model_exporter._export_model_thread.is_alive())

    self._model_exporter.stop()
    self.assertFalse(self._model_exporter._export_model_thread.is_alive())

    model_res_ids, _ = self._data_store.list_by_proto_ids(
        project_id='*',
        brain_id='*',
        session_id='*',
        model_id='*')

    model_paths = [self._data_store.read(m).model_path for m in model_res_ids]
    self.assertEqual(model_paths, [
        os.path.join(self.models_path, '0'),
        os.path.join(self.models_path, '1')
    ])

    compressed_model_paths = [
        self._data_store.read(m).compressed_model_path for m in model_res_ids]
    self.assertEqual(compressed_model_paths, [
        os.path.join(self.models_path, '0.zip'),
        os.path.join(self.models_path, '1.zip')
    ])

    offline_eval_res_ids, _ = self._data_store.list_by_proto_ids(
        project_id='*', brain_id='*', session_id='*',
        model_id='*', offline_evaluation_id='*')
    offline_evals = [
        self._data_store.read(r) for r in offline_eval_res_ids]
    evals_results = {}
    for offline_eval in offline_evals:
      evals_results[offline_eval.model_id] = offline_eval.offline_evaluation_id
    self.assertEqual(evals_results, {'model_id_0': 3, 'model_id_1': 5})

  @parameterized.parameters(True, False)
  @mock.patch.object(
      model_exporter.ModelExporter, '_export_model', autospec=True)
  def test_export_model_error(self, synchronous_export, mock_export_model):
    self.initialize_and_start_model_exporter(synchronous_export)
    mock_export_model.side_effect = ValueError()

    checkpoint_path = os.path.join(self.tmp_models_path, '0/checkpoint/')
    self.setup_valid_checkpoint(checkpoint_path)
    with self.assertRaises(ValueError):
      self._model_exporter.export_model(
          checkpoint_path, self._eval_tuples, self._stats, 'model_id',
          'episode_id', 0, training_examples_completed=10,
          max_training_examples=100, most_recent_demo_time_micros=0)
      self._model_exporter.stop()

  @parameterized.parameters(True, False)
  def test_dont_export_model(self, synchronous_export):
    self.initialize_and_start_model_exporter(synchronous_export)
    self.assertTrue(self._model_exporter._export_model_thread.is_alive())
    self._model_exporter.stop()
    self.assertFalse(self._model_exporter._export_model_thread.is_alive())

  @parameterized.parameters(True, False)
  def test_stopped_model_exporter(self, synchronous_export):
    self.initialize_and_start_model_exporter(synchronous_export)
    self._model_exporter.stop()
    with self.assertRaises(model_exporter.InactiveExporterError):
      self._model_exporter.export_model(
          'test_checkpoint_path', self._eval_tuples, self._stats, 'model_id',
          'episode_id', 0, training_examples_completed=10,
          max_training_examples=100, most_recent_demo_time_micros=0)


if __name__ == '__main__':
  absltest.main()
