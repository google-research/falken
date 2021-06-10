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
"""Tests for google3.research.kernel.falken.service.learner.learner."""

import collections
import os
import threading
import time
from unittest import mock

from absl import flags
from absl.testing import absltest
from absl.testing import parameterized

from data_store import assignment_monitor
from data_store import data_store as data_store_module
from data_store import file_system as data_store_file_system
from learner import assignment_processor
from learner import learner as learner_module
from learner import model_manager
from learner import storage
from learner import test_data
from learner.brains import brain_cache
from log import falken_logging


ASSIGNMENT_PROCESSING_TIMEOUT = 600
MICROSECONDS_PER_SECOND = 1_000_000
FLAGS = flags.FLAGS

flags.DEFINE_string(
    'training_output_dir', None,
    'Directory to write the results of training from each test case. If '
    'specified, tests will write to this directory rather than a temporary '
    'directory.')


def wait_until_equal(name, func, expected, timeout=6):
  """Waits for timeout seconds until func() == expected."""
  deadline = time.time() + timeout
  value = None
  while time.time() < deadline:
    value = func()
    if value == expected:
      return
    time.sleep(0.1)
  raise Exception(f'Timed out while waiting for {name} == {expected}; '
                  f'currently it\'s {value}.')


class LearnerTest(parameterized.TestCase):

  def setUp(self):
    """Create a DataStore instance."""
    super().setUp()
    self._data_store_dir = self.create_tempdir()
    self._data_store_file_system = data_store_file_system.FileSystem(
        self._data_store_dir.full_path)
    self.assignment_notifier = assignment_monitor.AssignmentNotifier(
        self._data_store_file_system)
    self.data_store = data_store_module.DataStore(self._data_store_file_system)
    self.storage = storage.Storage(
        self.data_store, self._data_store_file_system,
        stale_seconds=assignment_processor._MAX_ASSIGNMENT_WORK_TIME_SECS)

  def tearDown(self):
    """Clean up the DataStore instance."""
    self.storage = None
    self.data_store = None
    self.assignment_notifier = None
    self._data_store_file_system = None
    super().tearDown()

  def end_session(self, project_id=test_data.PROJECT_ID,
                  brain_id=test_data.BRAIN_ID, session_id=test_data.SESSION_ID):
    """Ends the specified session.

    Args:
      project_id: ID of the session's project.
      brain_id: ID of the session's brain.
      session_id: ID of the session to end.
    """
    self.data_store.write_stopped_session(
        self.data_store.read(self.data_store.resource_id_from_proto_ids(
            project_id=project_id, brain_id=brain_id, session_id=session_id)))

  def touch_session(self, project_id=test_data.PROJECT_ID,
                    brain_id=test_data.BRAIN_ID,
                    session_id=test_data.SESSION_ID):
    """Ensure session doesn't go stale.

    Args:
      project_id: ID of the session's project.
      brain_id: ID of the session's brain.
      session_id: ID of the session to end.
    """
    resource = self.data_store.resource_id_from_proto_ids(
        project_id=project_id, brain_id=brain_id, session_id=session_id)
    falken_logging.info(f'Touching session {resource}.')
    session = self.data_store.read(resource)
    session.last_data_received_micros = int(time.time() *
                                            MICROSECONDS_PER_SECOND)
    self.data_store.write(session)

  @staticmethod
  def wait_for_assignment_count(learner, expected_count, timeout=60):
    """Wait for enqeueud assignments.

    Args:
      learner: Learner to query.
      expected_count: Number of assignments to wait for.
      timeout: How long to wait in seconds.
    """
    wait_until_equal(
        'assignment_queue_size',
        lambda: learner._storage._number_of_pending_assignments,
        expected_count, timeout)

  def get_learner(self, output_dir=None, **kwargs):
    """Construct a learner.

    Args:
      output_dir: Optional location to store training results.
      **kwargs: Additional arguments for the learner.

    Returns:
      Learner instance.
    """
    if output_dir:
      output_path = os.path.join(output_dir, self.id())
    else:
      output_path = self.create_tempdir().full_path

    self.checkpoints_path = os.path.join(output_path, 'checkpoints')
    self.summaries_path = os.path.join(output_path, 'summaries')
    self.tmp_models_path = os.path.join(output_path, 'tmp_models')
    self.models_path = os.path.join(output_path, 'models')
    learner = learner_module.Learner(
        self.tmp_models_path,
        self.models_path,
        self.checkpoints_path,
        self.summaries_path,
        self.storage,
        always_block_when_fetching=True,
        **kwargs)
    return learner

  def test_process_assignment_until_stop(self):
    """Test processing an assignment until stop_process_assignment is called."""

    class LearnerThreadContext:
      """Thread context that runs process_assignment_until() indefinitely."""

      def __init__(self, learner, started_event):
        """Initialize with a learner and mock the assignment generator.

        Args:
          learner: Learner to patch with a mock assignment generator.
          started_event: Event that is signaled when processing has started.
        """
        self.learner = learner
        self.learner._process_assignment_generator = (
            self.mock_process_assignment())
        self.run = True
        self.started_event = started_event

      def mock_process_assignment(self):
        """Yields assignment status until run is False."""
        while self.run:
          yield (assignment_processor.ProcessAssignmentStatus.PROCESSED_STEP,
                 None)
          started_event.set()

      def run_process_assignment(self):
        """Process an assignment indefinitely."""
        self.learner.process_assignment_until(None)
        self.run = False

    learner = self.get_learner()
    started_event = threading.Event()
    learner_context = LearnerThreadContext(learner, started_event)
    learner_thread = threading.Thread(
        target=learner_context.run_process_assignment)
    learner_thread.start()
    self.assertTrue(started_event.wait(timeout=10))
    learner.stop_process_assignment()
    learner_thread.join(timeout=10)
    self.assertFalse(learner_context.run)
    learner_context.run = False

  def get_episode_chunk_resource_ids(self, project_id=test_data.PROJECT_ID,
                                     brain_id=test_data.BRAIN_ID,
                                     session_id=test_data.SESSION_ID):
    """Get episode chunk IDs in the specified session.

    Args:
      project_id: ID of the session's project.
      brain_id: ID of the session's brain.
      session_id: ID of the session to query.

    Returns:
      List of episode chunk ResourceId instances in the session.
    """
    episode_chunk_ids, _ = self.data_store.list_by_proto_ids(
        project_id=project_id, brain_id=brain_id, session_id=session_id,
        episode_id='*', chunk_id='*')
    return episode_chunk_ids

  def wait_for_chunk_count(self, expected_count, timeout=6):
    """Wait for the specified number of episode chunks to be available.

    Args:
      expected_count: Number of episode chunks to wait for.
      timeout: Time to wait in seconds.
    """
    wait_until_equal(
        'episode_chunk_count',
        lambda: len(self.get_episode_chunk_resource_ids()),
        expected_count, timeout)

  def get_model_resource_ids(self, project_id=test_data.PROJECT_ID,
                             brain_id=test_data.BRAIN_ID,
                             session_id=test_data.SESSION_ID):
    """Get model IDs trained in a session.

    Args:
      project_id: ID of the session's project.
      brain_id: ID of the session's brain.
      session_id: ID of the session to query.

    Returns:
      List of model ResourceId instances in the session.
    """
    model_ids, _ = self.data_store.list_by_proto_ids(
        project_id=project_id, brain_id=brain_id, session_id=session_id,
        model_id='*')
    return model_ids

  def test_learner_with_manual_assignment(self):
    """Test the learner fetching a manually specified assignment."""
    chunk_count = 3
    test_data.populate_data_store(self.data_store,
                                  steps_per_episode_chunk=[10] * chunk_count)

    # This test is used to generate models for SDK testing. We set the
    # assignment to produce noisy policies to help test the tflite ops that
    # rely on them.
    assignment_id = test_data.create_assignment_id(dict(policy_type='noisy'))
    learner = self.get_learner(
        output_dir=FLAGS.training_output_dir,
        assignment_path='/'.join([
            test_data.PROJECT_ID, test_data.BRAIN_ID, test_data.SESSION_ID,
            assignment_id
        ]))
    self.wait_for_chunk_count(chunk_count)

    learner.setup_process_assignment(timeout=ASSIGNMENT_PROCESSING_TIMEOUT)
    learner.process_assignment_until(
        assignment_processor.ProcessAssignmentStatus.SAVED_MODEL)

    # The yield inside AssignmentProcess._ProcessStep() doesn't run
    # ModelExporter.__exit__() which joins on the export thread, so wait
    # up to a few seconds for model export to complete.
    # We're waiting for data from any session as a new session is created by the
    # learner when training from a manually specified assignment.
    wait_until_equal('get_number_of_models',
                     lambda: len(self.get_model_resource_ids(session_id='*')),
                     1, timeout=60)

  def get_offline_evaluations(self, project_id=test_data.PROJECT_ID,
                              brain_id=test_data.BRAIN_ID,
                              session_id=test_data.SESSION_ID):
    """Get offline evaluations for the all models in the specified session.

    Args:
      project_id: ID of the session's project.
      brain_id: ID of the session's brain.
      session_id: ID of the session to query.

    Returns:
      Dictionary of lists of offline evaluation IDs by model IDs.
    """
    offline_evaluation_resource_ids, _ = self.data_store.list_by_proto_ids(
        project_id=project_id, brain_id=brain_id,
        session_id=session_id, model_id='*', offline_evaluation_id='*')
    result = collections.defaultdict(list)
    for resource in offline_evaluation_resource_ids:
      result[resource.model].append(resource.offline_evaluation)
    return result

  def trigger_assignment_notifications(self, assignment_resource_id,
                                       episode_chunk_resource_ids):
    """Trigger notifications for the assignment and each episode chunk.

    Args:
      assignment_resource_id: Assignment resource_id.ResourceId instance.
      episode_chunk_resource_ids: List of episode chunk resource_id.ResourceId
        instances.
    """
    for episode_chunk_resource_id in episode_chunk_resource_ids:
      self.assignment_notifier.trigger_assignment_notification(
          assignment_resource_id, episode_chunk_resource_id)

  @parameterized.parameters('stale', 'ended')
  def test_learner_trains(self, end_condition):
    """Test that learner correctly trains until session end."""
    number_of_episodes = 20
    steps_per_episode_chunk = [0, 10]
    expected_episode_ids = [f'ep{i}' for i in range(number_of_episodes)]
    chunk_count = number_of_episodes * len(steps_per_episode_chunk)

    assignment_resource_id, episode_chunk_resource_ids = (
        test_data.populate_data_store(
            self.data_store, episode_ids=expected_episode_ids,
            steps_per_episode_chunk=steps_per_episode_chunk))

    self.trigger_assignment_notifications(assignment_resource_id,
                                          episode_chunk_resource_ids)

    learner = self.get_learner()

    self.wait_for_assignment_count(learner, 1)
    self.wait_for_chunk_count(chunk_count)

    # Should train for a number of steps and then return.
    learner.setup_process_assignment(timeout=ASSIGNMENT_PROCESSING_TIMEOUT)
    learner.process_assignment_until(
        assignment_processor.ProcessAssignmentStatus.SAVED_MODEL)
    learner.process_assignment_until(
        assignment_processor.ProcessAssignmentStatus.SAVED_MODEL)

    if end_condition == 'ended':
      # Cleanly end the session.
      self.end_session()
    else:
      # Force a timeout.
      learner._storage._stale_seconds = 0

    last_state, stats = learner.process_assignment_until(None)
    learner.stop_process_assignment()
    assignment_stats, model_stats = stats

    # Check that assignment was processed.
    self.assertEqual(last_state,
                     assignment_processor.ProcessAssignmentStatus.FINISHED)
    self.wait_for_assignment_count(learner, 0)
    # Check that we have models in the DB.
    model_ids = self.get_model_resource_ids()
    num_models = len(model_ids)

    self.assertGreater(num_models, 0)
    self.assertGreater(assignment_stats.queries_completed, 1)
    self.assertGreater(assignment_stats.brain_train_steps, 0)
    self.assertEqual(model_stats.training_steps, 1)
    self.assertEqual(model_stats.batch_size, 500)
    self.assertGreater(model_stats.demonstration_frames, 0)
    self.assertGreater(model_stats.evaluation_frames, 0)
    evals = self.get_offline_evaluations()
    self.assertLen(evals.keys(), num_models)
    self.assertLen(list(evals.values())[0], number_of_episodes)
    max_evals = max(len(v) for v in evals.values())
    self.assertGreater(max_evals, 1)

    for proto in [self.data_store.read(model_id) for model_id in model_ids]:
      # Check that the paths contain permanent path.
      self.assertStartsWith(proto.model_path, self.models_path)
      # Check that the compressed paths contain permanent path and end with zip.
      self.assertStartsWith(proto.compressed_model_path, self.models_path)
      self.assertEndsWith(proto.compressed_model_path, '.zip')
      # Check that models reference the episodes used to train them.
      self.assertIn(proto.episode, expected_episode_ids)
      self.assertGreaterEqual(int(proto.episode_chunk), 0)
      self.assertLess(int(proto.episode_chunk), 20)

  def test_non_continuous(self):
    """Test that hyperparam continuous = False is processed correctly."""
    batch_size = 500
    train_steps = 5
    assignment_id = test_data.create_assignment_id({
        'continuous': False,
        'max_train_examples': batch_size * train_steps
    })

    assignment_resource_id, _ = test_data.populate_data_store(
        self.data_store, assignment_id=assignment_id, episode_ids=[])

    episode_count = 0

    def add_chunks():
      nonlocal episode_count
      episode_id = f'ep{episode_count}'
      episode_chunk_resource_ids = [
          self.data_store.write(chunk)
          for chunk in test_data.episode_chunks([10], episode_id)]
      self.trigger_assignment_notifications(assignment_resource_id,
                                            episode_chunk_resource_ids)
      episode_count += 1
      self.wait_for_chunk_count(episode_count)

    add_chunks()

    learner = self.get_learner()

    self.wait_for_assignment_count(learner, 1)

    # Should train for a number of steps and then return. Let it wait for
    # longer as it needs to train multiple times.
    learner.setup_process_assignment(timeout=ASSIGNMENT_PROCESSING_TIMEOUT)
    # Add chunks at increments.
    for _ in range(train_steps):
      learner.process_assignment_until(
          assignment_processor.ProcessAssignmentStatus.WILL_FETCH_DATA)
      add_chunks()

    # Stop processing assignments.
    _, metadata = learner.process_assignment_until(None)
    learner.stop_process_assignment()

    assignment_stats, stats = metadata

    # Sanity check on test to check that batch size is set correctly.
    self.assertEqual(stats.batch_size, batch_size)

    # Check that we restarted
    self.assertGreater(assignment_stats.num_restarts, 0)

    # Brain train steps should have been called more than 5 times due to
    # restarting.
    self.assertGreater(assignment_stats.brain_train_steps, 5)

    # Global step should be exactly what is required to train to completion.
    self.assertEqual(assignment_stats.brain_global_step, train_steps)
    # Ensure that total number of steps trained is greater than the steps
    # required to train to completion once, since we restarted.
    self.assertGreater(assignment_stats.brain_train_steps, train_steps)

    # Check that we have models in the DB.
    num_models = len(self.get_model_resource_ids())
    self.assertGreater(num_models, 1)  # 1 restart == at least 2 models.

  @mock.patch.object(learner_module.Learner, '_notify_error_listeners')
  def test_persistent_error_handling(self, mock_notify_error_listeners):
    """Test that persistent error on learner gets off of queue."""
    chunk_count = 11
    assignment_resource_id, episode_chunk_resource_ids = (
        test_data.populate_data_store(
            self.data_store, steps_per_episode_chunk=[1] * chunk_count))

    self.trigger_assignment_notifications(assignment_resource_id,
                                          episode_chunk_resource_ids)

    learner = self.get_learner()

    self.wait_for_assignment_count(learner, 1)
    self.wait_for_chunk_count(chunk_count)

    # Override class level variable with member.
    old_val = assignment_processor._MAX_ASSIGNMENT_WORK_TIME_SECS
    assignment_processor._MAX_ASSIGNMENT_WORK_TIME_SECS = 0.5
    try:
      # Make sure the session doesn't go stale.
      self.touch_session()
      with self.assertRaises(assignment_processor.ExceededMaxWorkTimeError):
        learner.process_assignment()
    finally:
      assignment_processor._MAX_ASSIGNMENT_WORK_TIME_SECS = old_val

    # Check that listeners were notified of the error.
    mock_notify_error_listeners.assert_called_with(
        test_data.PROJECT_ID, test_data.BRAIN_ID,
        test_data.SESSION_ID, test_data.ASSIGNMENT_ID)

    status = self.data_store.read_by_proto_ids(
        project_id=test_data.PROJECT_ID, brain_id=test_data.BRAIN_ID,
        session_id=test_data.SESSION_ID,
        assignment_id=test_data.ASSIGNMENT_ID).status
    self.assertStartsWith(status.message, 'Assignment took too long.')
    status = self.data_store.read_by_proto_ids(
        project_id=test_data.PROJECT_ID, brain_id=test_data.BRAIN_ID,
        session_id=test_data.SESSION_ID).status
    self.assertStartsWith(status.message, 'Assignment took too long.')

  def test_error_handling(self):
    """Test that the receiver handles learner errors properly."""
    chunk_count = 11
    assignment_resource_id, episode_chunk_resource_ids = (
        test_data.populate_data_store(
            self.data_store, steps_per_episode_chunk=[1] * chunk_count))
    self.trigger_assignment_notifications(assignment_resource_id,
                                          episode_chunk_resource_ids)

    learner = self.get_learner()

    self.wait_for_assignment_count(learner, 1)
    self.wait_for_chunk_count(chunk_count)

    # Mock assignment completion method to determine whether it's called.
    with mock.patch.object(learner._storage, 'record_assignment_done') as (
        mock_record_assignment_done):

      with self.assertRaises(assignment_processor.ExceededMaxWorkTimeError):
        # Trigger a failing run by reducing max_time to half a second.
        old_val = assignment_processor._MAX_ASSIGNMENT_WORK_TIME_SECS
        try:
          # Override class level variable with member.
          assignment_processor._MAX_ASSIGNMENT_WORK_TIME_SECS = 0.5
          learner.process_assignment(timeout=1)
        finally:
          # Delete member to restore access to class level variable.
          assignment_processor._MAX_ASSIGNMENT_WORK_TIME_SECS = old_val

      status = self.data_store.read_by_proto_ids(
          project_id=test_data.PROJECT_ID, brain_id=test_data.BRAIN_ID,
          session_id=test_data.SESSION_ID,
          assignment_id=test_data.ASSIGNMENT_ID).status
      self.assertStartsWith(status.message, 'Assignment took too long.')

      # Check that the assignment is still pending completion.
      mock_record_assignment_done.assert_not_called()

    # Now process the assignment without failing.
    learner.setup_process_assignment(timeout=ASSIGNMENT_PROCESSING_TIMEOUT)
    learner.process_assignment_until(
        assignment_processor.ProcessAssignmentStatus.SAVED_MODEL)
    self.end_session()
    learner.process_assignment_until(None)
    learner.stop_process_assignment()

    # Check that assignment was processed.
    self.wait_for_assignment_count(learner, 0)
    # Check that we have models in the DB.
    num_models = len(self.get_model_resource_ids())
    self.assertGreater(num_models, 0)

  def test_send_empty_chunks(self):
    # Add two empty chunks to the first episode of the assignment.
    assignment_resource_id, episode_chunk_resource_ids = (
        test_data.populate_data_store(self.data_store,
                                      steps_per_episode_chunk=[0, 0]))

    self.trigger_assignment_notifications(assignment_resource_id,
                                          episode_chunk_resource_ids)

    learner = self.get_learner()
    learner.process_assignment(timeout=ASSIGNMENT_PROCESSING_TIMEOUT)
    self.wait_for_assignment_count(learner, 0)

  @mock.patch.object(model_manager, 'ModelManager')
  def test_early_stopping(self, mock_manager):
    # ModelManagerMock stops after 2 models.
    mock_manager.side_effect = _ModelManagerMock
    chunk_count = 3
    assignment_resource_id, episode_chunk_resource_ids = (
        test_data.populate_data_store(
            self.data_store, steps_per_episode_chunk=[10] * chunk_count))
    self.trigger_assignment_notifications(assignment_resource_id,
                                          episode_chunk_resource_ids)

    learner = self.get_learner()
    self.touch_session()
    learner.process_assignment(timeout=ASSIGNMENT_PROCESSING_TIMEOUT)

    # Assignment should be completed and two models trained.
    self.wait_for_assignment_count(learner, 0)
    self.wait_for_chunk_count(chunk_count)
    num_models = len(self.get_model_resource_ids())
    self.assertEqual(num_models, 2)

  @mock.patch.object(model_manager, 'ModelManager')
  def test_min_train_examples(self, mock_manager):
    # ModelManagerMock stops after 2 models.
    mock_manager.side_effect = _ModelManagerMock

    # Generate enough chunks so trajectories get placed in the demo buffer.
    assignment_resource_id, episode_chunk_resource_ids = (
        test_data.populate_data_store(
            self.data_store,
            assignment_id=test_data.create_assignment_id({
                'min_train_examples': 2000000,
                'batch_size': 500,
                'training_examples': 500,
                'save_interval_batches': 5
            }),
            steps_per_episode_chunk=[10] * 10))
    self.trigger_assignment_notifications(assignment_resource_id,
                                          episode_chunk_resource_ids)

    learner = self.get_learner()
    self.touch_session()
    learner.setup_process_assignment(timeout=ASSIGNMENT_PROCESSING_TIMEOUT)

    # The model manager requests to stop after two models, so we verify that
    # this request is ignored if min_train_examples is very high. No need to
    # assert anything, as process_assignment_until would raise an exception
    # if this didn't work.
    for _ in range(3):
      learner.process_assignment_until(
          assignment_processor.ProcessAssignmentStatus.SAVED_MODEL)
    learner.stop_process_assignment()

  def test_max_train_examples(self):
    # Generate enough chunks so trajectories get placed in the demo buffer.
    assignment_resource_id, episode_chunk_resource_ids = (
        test_data.populate_data_store(
            self.data_store,
            assignment_id=test_data.create_assignment_id({
                'max_train_examples': 1000,
                'batch_size': 500,
                'training_examples': 500,
                'save_interval_batches': None
            }),
            steps_per_episode_chunk=[10] * 10))
    self.trigger_assignment_notifications(assignment_resource_id,
                                          episode_chunk_resource_ids)

    learner = self.get_learner()
    assignment_stats, _ = learner.process_assignment(
        timeout=ASSIGNMENT_PROCESSING_TIMEOUT)

    # We should stop processing after:
    #    2 brain.train steps
    # == 2 tf_agents.train steps
    # == 1000 training examples (2 batches)
    # See brains.continous_imitation_brain.BCAgent.update_derived_hparams()
    # for the derivation of training steps from examples and batch size.
    self.assertEqual(assignment_stats.brain_train_steps, 2)

  def test_save_interval_null(self):
    # Generate enough chunks so trajectories get placed in the demo buffer.
    assignment_resource_id, episode_chunk_resource_ids = (
        test_data.populate_data_store(
            self.data_store,
            assignment_id=test_data.create_assignment_id({
                'save_interval_batches': None,
                'max_train_examples': 1000
            }),
            steps_per_episode_chunk=[10] * 10))
    self.trigger_assignment_notifications(assignment_resource_id,
                                          episode_chunk_resource_ids)

    learner = self.get_learner()

    learner.setup_process_assignment(timeout=ASSIGNMENT_PROCESSING_TIMEOUT)

    # Run until max_train_examples
    learner.process_assignment_until(None)

    # Only one model should be saved.
    num_models = len(self.get_model_resource_ids())
    self.assertEqual(num_models, 1)

  def test_create_brain(self):
    temp_path = self.create_tempdir().full_path
    brain_spec = test_data.brain_spec()
    cache = brain_cache.BrainCache(
        assignment_processor.populate_hparams_with_defaults_and_validate)
    with self.assertRaises(assignment_processor.HParamError):
      brain, _ = cache.GetOrCreateBrain({'unknown_hparam': 'crazyjuice'},
                                        brain_spec,
                                        os.path.join(temp_path, 'model'),
                                        os.path.join(temp_path, 'summary'))
    brain, _ = cache.GetOrCreateBrain({'learning_rate': 20.0}, brain_spec,
                                      os.path.join(temp_path, 'model'),
                                      os.path.join(temp_path, 'summary'))
    self.assertEqual(brain._hparams['learning_rate'], 20.0)
    self.assertIn('dropout', brain._hparams)

  def test_register_and_notify_error_listeners(self):
    """Register error listeners and notify them."""
    mock_listeners = [mock.Mock(), mock.Mock()]
    try:
      learner_module.Learner.register_error_listener(mock_listeners[0])
      learner_module.Learner.register_error_listener(mock_listeners[1])

      assignment_resource = ('project', 'brain', 'session', 'assignment')
      learner_module.Learner._notify_error_listeners(*assignment_resource)
      mock_listeners[0].assert_called_with(*assignment_resource)
      mock_listeners[1].assert_called_with(*assignment_resource)
    finally:
      learner_module.Learner._error_listeners.clear()


class _ModelManagerMock(model_manager.ModelManager):

  def should_stop(self):
    falken_logging.info(f'Mock learner has {self._models_recorded} models.')
    if self._models_recorded >= 2:
      return 'Mock learner has >= 2 models.'
    return None


if __name__ == '__main__':
  absltest.main()
