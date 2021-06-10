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
"""Tests for storage."""

import datetime
import tempfile
import time
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from data_store import assignment_monitor
from data_store import data_store as data_store_module
from data_store import file_system as data_store_file_system
from learner import storage as storage_module
from learner import test_data

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import data_store_pb2


class StorageTest(parameterized.TestCase):

  def setUp(self):
    super().setUp()
    self.tmp_dir = tempfile.TemporaryDirectory()
    self.data_store_file_system = data_store_file_system.FileSystem(
        self.tmp_dir.name)
    self.data_store = data_store_module.DataStore(self.data_store_file_system)
    with mock.patch.object(assignment_monitor, 'AssignmentMonitor') as (
        mock_assignment_monitor):
      self.storage = storage_module.Storage(self.data_store,
                                            self.data_store_file_system)
      # Verify assignment monitor is constructed with the correct arguments.
      mock_assignment_monitor.assert_called_with(
          self.data_store_file_system, self.storage._enqueue_pending_assignment,
          self.storage._episode_chunk_notification)

    self.project = test_data.project()
    self.brain = test_data.brain()
    self.session = test_data.session()
    self.assignment = test_data.assignment()

  def tearDown(self):
    self.tmp_dir.cleanup()
    super().tearDown()

  def populate_datastore(self):
    self.data_store.write(self.project)
    self.data_store.write(self.brain)
    self.data_store.write(self.session)
    self.data_store.write(self.assignment)

  def test_get_brain_spec(self):
    """Tests reading a BrainSpec."""
    self.populate_datastore()
    brain_spec = self.storage.get_brain_spec(test_data.PROJECT_ID,
                                             test_data.BRAIN_ID)

    self.assertEqual(brain_spec, test_data.brain_spec())

  def test_get_brain_spec_empty(self):
    """Tests reading a non-existent BrainSpec."""
    with self.assertRaises(storage_module.NotFoundError):
      self.storage.get_brain_spec(test_data.PROJECT_ID, test_data.BRAIN_ID)

  def test_record_new_model(self):
    """Add a new model to the DB."""
    self.populate_datastore()
    model_id = self.storage.record_new_model(
        self.assignment, '1020', 5, 10, 100, 0,
        '/path/to/model', '/path/to/model.zip')

    model = self.data_store.read_by_proto_ids(
        project_id=test_data.PROJECT_ID,
        brain_id=test_data.BRAIN_ID,
        session_id=test_data.SESSION_ID,
        model_id=model_id)

    self.assertEqual(model.model_id, model_id)
    self.assertEqual(model.model_path, '/path/to/model')
    self.assertEqual(model.compressed_model_path, '/path/to/model.zip')
    self.assertEqual(model.assignment, self.assignment.assignment_id)
    self.assertEqual(model.episode, '1020')
    self.assertEqual(model.episode_chunk, 5)

  def test_record_assignment_error(self):
    """Test recording assignment error."""
    self.populate_datastore()
    self.storage.record_assignment_error(
        self.assignment, Exception('Test exception'))

    got_assignment = self.storage.get_assignment(
        self.assignment.project_id,
        self.assignment.brain_id,
        self.assignment.session_id,
        self.assignment.assignment_id)

    self.assertEqual(
        got_assignment.status.message,
        'Test exception')

  def test_record_session_error(self):
    """Test recording session error."""
    self.populate_datastore()
    self.storage.record_session_error(self.assignment, 'Test exception')

    got_session = self.data_store.read_by_proto_ids(
        project_id=self.session.project_id,
        brain_id=self.session.brain_id,
        session_id=self.session.session_id)

    self.assertEqual('Test exception', got_session.status.message)

  def test_handle_assignment_error(self):
    """Test handling an assignment error."""
    self.populate_datastore()
    self.storage.handle_assignment_error(
        self.assignment, Exception('Test exception'))

    got_assignment = self.storage.get_assignment(
        self.assignment.project_id,
        self.assignment.brain_id,
        self.assignment.session_id,
        self.assignment.assignment_id)
    self.assertEqual(got_assignment.status.message, 'Test exception')

    got_session = self.data_store.read_by_proto_ids(
        project_id=self.assignment.project_id,
        brain_id=self.assignment.brain_id,
        session_id=self.assignment.session_id)
    self.assertEqual(got_session.status.message, 'Test exception')

  def test_get_session_state(self):
    """Tests querying SessionState."""
    self.populate_datastore()
    # Test NEW
    s1 = data_store_pb2.Session(
        project_id=test_data.PROJECT_ID,
        brain_id=test_data.BRAIN_ID,
        session_id='_S1')
    self.data_store.write(s1)
    self.assertEqual(
        self.storage.get_session_state(
            s1.project_id, s1.brain_id, s1.session_id),
        storage_module.SessionState.NEW)

    # Test IN_PROGRESS
    s1.last_data_received_micros = int(time.time() * 1_000_000)
    self.data_store.write(s1)
    self.assertEqual(
        self.storage.get_session_state(
            s1.project_id, s1.brain_id, s1.session_id),
        storage_module.SessionState.IN_PROGRESS)

    # Test STALE
    tomorrow = (
        datetime.datetime.now(datetime.timezone.utc) +
        datetime.timedelta(hours=24))
    self.assertEqual(
        self.storage.get_session_state(
            s1.project_id, s1.brain_id, s1.session_id,
            as_of_datetime=tomorrow),
        storage_module.SessionState.STALE)

    # Test ENDED
    s1.ended_micros = int(time.time() * 1_000_000)
    self.data_store.write(s1)
    self.assertEqual(
        self.storage.get_session_state(
            s1.project_id, s1.brain_id, s1.session_id),
        storage_module.SessionState.ENDED)

  def test_record_evaluations(self):
    self.populate_datastore()
    model_id = self.storage.record_new_model(
        self.assignment, '123', 4, 10, 100, 0,
        '/path/to/model',
        '/path/to/model.zip')
    evaluations = [(0, 0.0), (1, 2.0), (2, 4.0)]
    self.storage.record_evaluations(self.assignment, model_id, evaluations)

    eval_rid_glob = self.data_store.resource_id_from_proto_ids(
        project_id=self.assignment.project_id,
        brain_id=self.assignment.brain_id,
        session_id=self.assignment.session_id,
        model_id=model_id,
        offline_evaluation_id='*')

    rids = self.data_store.list(eval_rid_glob)[0]
    scores = [self.data_store.read(rid).score for rid in rids]
    self.assertEqual(
        scores,
        [0.0, 2.0, 4.0])

    evaluations = [(0, 2.0), (1, 4.0), (2, 8.0), (3, 16.0)]
    self.storage.record_evaluations(self.assignment, model_id, evaluations)

    rids = self.data_store.list(eval_rid_glob)[0]
    scores = [self.data_store.read(rid).score for rid in rids]
    self.assertEqual(
        scores,
        [2.0, 4.0, 8.0, 16])

  def test_get_ancestor_session_ids(self):
    self.populate_datastore()
    self.session.starting_snapshots.extend(['snap0', 'snap1'])
    self.data_store.write(self.session)
    self.data_store.write(
        data_store_pb2.Snapshot(
            project_id=self.session.project_id,
            brain_id=self.session.brain_id,
            snapshot_id='snap0',
            session='as0',
            ancestor_snapshots=[
                data_store_pb2.SnapshotParents(
                    snapshot='snap0',
                    parent_snapshots=['snap2', 'snap3'],
                ),
                data_store_pb2.SnapshotParents(
                    snapshot='snap2',
                    parent_snapshots=['snap4']),
            ]))
    self.data_store.write(
        data_store_pb2.Snapshot(
            project_id=self.session.project_id,
            brain_id=self.session.brain_id,
            snapshot_id='snap1',
            session='as1',
            ancestor_snapshots=[
                data_store_pb2.SnapshotParents(
                    snapshot='snap1',
                    parent_snapshots=['snap5'],
                ),
            ]))
    for snap_num in range(2, 6):
      self.data_store.write(
          data_store_pb2.Snapshot(
              project_id=self.session.project_id,
              brain_id=self.session.brain_id,
              snapshot_id=f'snap{snap_num}',
              session=f'as{snap_num}'))

    ancestor_session_ids = self.storage.get_ancestor_session_ids(
        self.session.project_id,
        self.session.brain_id,
        self.session.session_id)

    self.assertCountEqual(
        ['as0', 'as1', 'as2', 'as3', 'as4', 'as5'],
        ancestor_session_ids)

  def test_get_episode_chunks(self):
    self.populate_datastore()
    for session_id in ['s2', 's3', 's4']:
      self.session.session_id = session_id
      self.data_store.write(self.session)

    def _write_chunk(session_id, episode_id, chunk_id, created_micros):
      self.data_store.write(
          data_store_pb2.EpisodeChunk(
              project_id=self.session.project_id,
              brain_id=self.session.brain_id,
              session_id=session_id,
              episode_id=episode_id,
              chunk_id=chunk_id,
              created_micros=created_micros))

    _write_chunk('s2', 'e0', 0, 1)
    _write_chunk('s2', 'e0', 1, 2)
    _write_chunk('s2', 'e0', 2, 3)
    _write_chunk('s3', 'e1', 0, 2)
    _write_chunk('s3', 'e1', 1, 3)
    _write_chunk('s3', 'e1', 2, 4)
    _write_chunk('s4', 'e1', 0, 2)
    _write_chunk('s4', 'e1', 1, 3)
    _write_chunk('s4', 'e1', 2, 4)

    chunks = self.storage.get_episode_chunks(
        self.session.project_id, self.session.brain_id,
        ['s2', 's4'], 3)

    chunk_keys = [(c.session_id, c.episode_id, c.chunk_id) for c in chunks]

    self.assertCountEqual(
        [('s2', 'e0', 2), ('s4', 'e1', 1), ('s4', 'e1', 2)],
        chunk_keys)

  @staticmethod
  def _fake_time_callable(increment):
    """Generate a time.time() callable that generates incremental timestamps.

    Args:
      increment: Increment between each timestamp starting at 0.

    Returns:
      Callable that generates timestamps from 0 at each specified increment.
    """
    timestamp = 0
    def get_next_timestamp():
      """Returns a timestamp in one second increments."""
      nonlocal timestamp
      timestamp += increment
      return timestamp
    return get_next_timestamp

  def test_receive_assignment_from_empty_queue(self):
    """Try pulling an assignment from an empty queue."""
    self.assertIsNone(self.storage.receive_assignment(timeout=0))

  @parameterized.named_parameters(
      ('No Timeout', None, [mock.call(timeout=None)]),
      ('Poll', 0, [mock.call(timeout=0)]),
      # We're emulating 1 second per queue query so receive_assignment() should
      # try to pull three items from the queue.
      ('Timeout', 2, [mock.call(timeout=2),
                      mock.call(timeout=1),
                      mock.call(timeout=0)]))
  def test_receive_assignment_with_timeout(self, timeout, expected_calls):
    """Test receiving an enqueued assignment with no timeout."""
    with mock.patch.object(time, 'time') as mock_time:
      mock_time.side_effect = self._fake_time_callable(1)
      mock_pending_assignment_ids = mock.Mock()
      mock_pending_assignment_ids.get.return_value = None
      self.storage._pending_assignment_ids = mock_pending_assignment_ids

      self.assertIsNone(self.storage.receive_assignment(timeout=timeout))
      mock_pending_assignment_ids.get.assert_has_calls(expected_calls)

  @parameterized.named_parameters(
      ('Already Acquired', False),
      ('Acquired', True))
  def test_receive_assignment_acquire_and_read(self, can_acquire_assignment):
    """Receive an enqueue assignment that can't be acquired."""
    self.populate_datastore()
    with mock.patch.object(time, 'time') as mock_time:
      mock_time.side_effect = self._fake_time_callable(1)
      test_assignment_id = self.data_store.to_resource_id(self.assignment)
      self.storage._enqueue_pending_assignment(test_assignment_id)
      mock_monitor = self.storage._assignment_monitor
      mock_monitor.acquire_assignment.return_value = can_acquire_assignment
      expected_assignment = self.assignment if can_acquire_assignment else None

      self.assertEqual(self.storage.receive_assignment(timeout=0.5),
                       expected_assignment)
      mock_monitor.acquire_assignment.assert_called_once_with(
          test_assignment_id)
      # Requesting the assignment again should yield the same result without
      # waiting.
      if expected_assignment:
        self.assertEqual(self.storage.receive_assignment(), expected_assignment)

  def test_number_of_pending_assignments(self):
    """Get the number of pending / enqueued assignments."""
    self.assertEqual(self.storage._number_of_pending_assignments, 0)
    self.populate_datastore()
    another_assignment = test_data.assignment(
        assignment_id=test_data.create_assignment_id(
            {'another_param': True}))
    self.data_store.write(another_assignment)

    self.storage._enqueue_pending_assignment(
        self.data_store.to_resource_id(self.assignment))
    self.assertEqual(self.storage._number_of_pending_assignments, 1)

    self.storage._enqueue_pending_assignment(self.data_store.to_resource_id(
        another_assignment))
    self.assertEqual(self.storage._number_of_pending_assignments, 2)

    self.storage.receive_assignment()
    self.assertEqual(self.storage._number_of_pending_assignments, 2)
    self.storage.record_assignment_done()
    self.assertEqual(self.storage._number_of_pending_assignments, 1)
    self.storage.receive_assignment()
    self.assertEqual(self.storage._number_of_pending_assignments, 1)
    self.storage.record_assignment_done()
    self.assertEqual(self.storage._number_of_pending_assignments, 0)

  def test_record_assignment_done_no_received_assignment(self):
    """Check for an when a non-pending assignment is marked complete."""
    with self.assertRaises(AssertionError):
      self.storage.record_assignment_done()

  def test_record_assignment_done(self):
    """Mark the currently acquired assignment as complete."""
    mock_monitor = self.storage._assignment_monitor
    self.populate_datastore()
    self.storage._enqueue_pending_assignment(
        self.data_store.to_resource_id(self.assignment))
    self.storage.receive_assignment()
    self.storage.record_assignment_done()
    mock_monitor.release_assignment.assert_called_once()

  def test_create_session_and_assignment(self):
    """Ensure a session and assignment proto are stored in the datastore."""
    assignment = self.storage.create_session_and_assignment(
        test_data.PROJECT_ID, test_data.BRAIN_ID, test_data.SESSION_ID,
        test_data.ASSIGNMENT_ID)
    self.assertIsNotNone(self.data_store.read_by_proto_ids(
        project_id=test_data.PROJECT_ID, brain_id=test_data.BRAIN_ID,
        session_id=test_data.SESSION_ID))
    self.assertEqual(assignment, self.data_store.read_by_proto_ids(
        project_id=test_data.PROJECT_ID, brain_id=test_data.BRAIN_ID,
        session_id=test_data.SESSION_ID, assignment_id=test_data.ASSIGNMENT_ID))

  def test_record_assignment_progress(self):
    """Ensure the assignment is updated in record_assignment_progress."""
    assignment = test_data.assignment()
    assignment_res_id = self.data_store.write(assignment)

    self.storage._enqueue_pending_assignment(
        self.data_store.to_resource_id(self.assignment))
    self.storage.receive_assignment()
    self.storage.record_assignment_progress(assignment, 0.5, 123_456_789)

    got = self.data_store.read(assignment_res_id)
    want_progress = data_store_pb2.AssignmentProgress(
        training_progress=0.5,
        most_recent_demo_time_micros=123_456_789)
    self.assertEqual(got.progress, want_progress)


if __name__ == '__main__':
  absltest.main()
