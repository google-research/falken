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

"""Tests for AssignmentMonitor."""

import os.path
import tempfile
import threading
import types
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized

from data_store import assignment_monitor
from data_store import file_system
from data_store import resource_id


def patch_file_system(fs, time_increment):
  """Patches self._fs to have control of file modification times.

  This will modify get_modification_time to simulate that every file was
  written exactly time_increment milliseconds apart from the next.

  Args:
    fs: A FileSystem object to patch.
    time_increment: By how much to increment the milliseconds counter every
      time a file is written.
  """
  fs._current_time = 0
  fs._file_times = {}

  def new_write_file(self, path, data):
    self._file_times[file_system.posix_path(path)] = self._current_time
    self._current_time += time_increment
    self._original_write_file(path, data)

  def new_get_modification_time(self, path):
    return self._file_times[file_system.posix_path(path)]

  fs._original_write_file = fs.write_file
  fs.write_file = types.MethodType(new_write_file, fs)
  fs.get_modification_time = types.MethodType(new_get_modification_time, fs)


class AssignmentMonitorTest(parameterized.TestCase):

  def setUp(self):
    """Create a datastore object that uses a temporary directory."""
    super().setUp()
    self._temporary_directory = tempfile.TemporaryDirectory()
    self._fs = file_system.FileSystem(self._temporary_directory.name)
    self._monitor = assignment_monitor.AssignmentMonitor(
        self._fs, lambda x: None, lambda x, y: None)
    self._notifier = assignment_monitor.AssignmentNotifier(self._fs)

  def tearDown(self):
    """Clean up the temporary directory and datastore."""
    super().tearDown()
    if self._monitor:
      self._monitor.shutdown()
    self._monitor = None
    self._fs = None
    self._temporary_directory.cleanup()

  def test_acquire_release(self):
    """Tests acquiring is exclusive."""
    self._second_monitor = assignment_monitor.AssignmentMonitor(
        self._fs, lambda x: None, lambda x, y: None)

    assignment_id = resource_id.FalkenResourceId(
        project='p0', brain='b0', session='s0', assignment='a0')
    self.assertTrue(self._monitor.acquire_assignment(assignment_id))
    self.assertFalse(self._second_monitor.acquire_assignment(assignment_id))
    self._monitor.release_assignment()
    self.assertTrue(self._second_monitor.acquire_assignment(assignment_id))

    self._second_monitor.shutdown()

  def test_trigger_assignment_notification_bad_resource_id(self):
    """Test triggering assignment notification with a bad resource ID."""
    with self.assertRaises(AssertionError):
      self._notifier.trigger_assignment_notification(
          resource_id.FalkenResourceId(
              project='project_0', brain='brain_0', session='session_0',
              assignment='assignment_0'),
          resource_id.FalkenResourceId(
              project='project_0', brain='brain_0', session='session_0',
              episode='episode_0',
              chunk=0))

  @parameterized.named_parameters([
      ('Files written at the same time', 0),
      ('Files written at different times', 10_000)])
  @mock.patch.object(
      assignment_monitor, '_Metronome', new=assignment_monitor._FakeMetronome)
  def test_callbacks(self, time_increment):
    """Tests callbacks."""
    callback_called = threading.Event()
    def side_effect(*unused_args):
      callback_called.set()

    assignment_callback = mock.Mock(side_effect=side_effect)
    chunk_callback = mock.Mock(side_effect=side_effect)

    def reset_callbacks():
      assignment_callback.reset_mock()
      chunk_callback.reset_mock()
      callback_called.clear()

    self._monitor.shutdown()
    patch_file_system(self._fs, time_increment)
    self._monitor = assignment_monitor.AssignmentMonitor(
        self._fs, assignment_callback, chunk_callback)
    metronome = self._monitor._metronome

    metronome.force_tick()
    assignment_callback.assert_not_called()
    chunk_callback.assert_not_called()
    reset_callbacks()

    assignment_id = resource_id.FalkenResourceId(
        project='p0', brain='b0', session='s0', assignment='a0')
    chunk_id = resource_id.FalkenResourceId(
        project='p0', brain='b0', session='s0', episode='e0',
        chunk=0)
    assignment_id_2 = resource_id.FalkenResourceId(
        project='p0', brain='b0', session='s1', assignment='a1')
    chunk_id_2 = resource_id.FalkenResourceId(
        project='p0', brain='b0', session='s1', episode='e0',
        chunk=0)

    self._notifier.trigger_assignment_notification(assignment_id, chunk_id)
    metronome.force_tick()
    self.assertTrue(callback_called.wait(3))
    assignment_callback.assert_called_once_with(assignment_id)
    chunk_callback.assert_not_called()
    reset_callbacks()

    self._notifier.trigger_assignment_notification(assignment_id_2, chunk_id_2)
    metronome.force_tick()
    self.assertTrue(callback_called.wait(3))
    assignment_callback.assert_called_once_with(assignment_id_2)
    chunk_callback.assert_not_called()
    reset_callbacks()

    metronome.force_tick()
    assignment_callback.assert_not_called()
    chunk_callback.assert_not_called()
    reset_callbacks()

    self.assertTrue(self._monitor.acquire_assignment(assignment_id))
    metronome.force_tick()
    self.assertTrue(callback_called.wait(3))
    assignment_callback.assert_not_called()
    chunk_callback.assert_called_once_with(assignment_id, [chunk_id])
    reset_callbacks()

    metronome.force_tick()
    assignment_callback.assert_not_called()
    chunk_callback.assert_not_called()
    reset_callbacks()

    self._monitor.release_assignment()
    self.assertTrue(self._monitor.acquire_assignment(assignment_id_2))
    metronome.force_tick()
    self.assertTrue(callback_called.wait(3))
    assignment_callback.assert_not_called()
    chunk_callback.assert_called_once_with(assignment_id_2, [chunk_id_2])
    reset_callbacks()

    self._monitor.shutdown()
    self._monitor = None
    assignment_callback.assert_not_called()
    chunk_callback.assert_not_called()

  @mock.patch.object(
      assignment_monitor, '_Metronome', new=assignment_monitor._FakeMetronome)
  def test_release_assignment_removes_files(self):
    """Verifies that chunks are removed when releasing an assignment."""
    callback_called = threading.Event()
    def callback(*unused_args):
      callback_called.set()

    self._monitor.shutdown()
    self._monitor = assignment_monitor.AssignmentMonitor(
        self._fs, lambda x: None, callback)
    metronome = self._monitor._metronome

    assignment_id = resource_id.FalkenResourceId(
        project='p0', brain='b0', session='s0', assignment='a0')
    chunk_id = resource_id.FalkenResourceId(
        project='p0', brain='b0', session='s0', episode='e0',
        chunk=0)

    self._notifier.trigger_assignment_notification(assignment_id, chunk_id)
    self.assertTrue(self._monitor.acquire_assignment(assignment_id))
    metronome.force_tick()
    self.assertTrue(callback_called.wait(3))

    chunk_path = os.path.join(
        self._monitor._get_assignment_directory(assignment_id), 'chunk_e0_0')
    self.assertTrue(self._fs.exists(chunk_path))

    self._monitor.release_assignment()
    self.assertFalse(self._fs.exists(chunk_path))

  @mock.patch.object(
      assignment_monitor, '_Metronome', new=assignment_monitor._FakeMetronome)
  def test_lock_refresh(self):
    """Test that assignment lock is refreshed in every poll."""
    refresh_called = threading.Event()
    def refresh_lock_side_effect(*unused_args):
      refresh_called.set()

    self._monitor.shutdown()
    self._monitor = assignment_monitor.AssignmentMonitor(
        self._fs, lambda x: None, lambda x: None)

    metronome = self._monitor._metronome
    self._fs.refresh_lock = mock.Mock(side_effect=refresh_lock_side_effect)

    assignment_id = resource_id.FalkenResourceId(
        project='p0', brain='b0', session='s0', assignment='a0')
    self.assertTrue(self._monitor.acquire_assignment(assignment_id))
    lock = self._monitor._acquired_assignment_lock_file

    self._fs.refresh_lock.assert_not_called()
    for _ in range(3):
      metronome.force_tick()
      self.assertTrue(refresh_called.wait(3))
      self._fs.refresh_lock.assert_called_once_with(
          lock, assignment_monitor._ASSIGNMENT_EXPIRATION_SECONDS)
      refresh_called.clear()
      self._fs.refresh_lock.reset_mock()

    self._monitor.shutdown()
    self._monitor = None
    self._fs.refresh_lock.assert_not_called()

  def test_cleanup_cleans_stale(self):
    notifier = assignment_monitor.AssignmentNotifier(self._fs)
    notifier.trigger_assignment_notification(
        resource_id.FalkenResourceId(
            'projects/p0/brains/b0/sessions/s0/assignments/1234'),
        resource_id.FalkenResourceId(
            'projects/p0/brains/b0/sessions/s0/episodes/e0/chunks/0'))

    self.assertTrue(self._fs.exists(
        os.path.join(
            notifier._notification_dir,
            'projects/p0/brains/b0/sessions/s0/')))

    with mock.patch.object(self._fs, 'get_staleness') as staleness_mock:
      # Always return a stale result.
      staleness_mock.return_value = (
          assignment_monitor._NOTIFICATION_MAX_STALENESS_SECONDS * 1000 + 1)
      assignment_monitor.AssignmentMonitor(
          self._fs, lambda x: None, lambda x: None)

    # Check that session was deleted.
    self.assertFalse(self._fs.exists(
        os.path.join(
            notifier._notification_dir,
            'projects/p0/brains/b0/sessions/s0/')))

    # Check that brain was not deleted.
    self.assertTrue(self._fs.exists(
        os.path.join(
            notifier._notification_dir,
            'projects/p0/brains/b0')))

  def test_cleanup_doesnt_clean_fresh(self):
    notifier = assignment_monitor.AssignmentNotifier(self._fs)
    assignment_resource_id = resource_id.FalkenResourceId(
        'projects/p0/brains/b0/sessions/s0/assignments/1234')
    notifier.trigger_assignment_notification(
        assignment_resource_id,
        resource_id.FalkenResourceId(
            'projects/p0/brains/b0/sessions/s0/episodes/e0/chunks/0'))

    self.assertTrue(self._fs.exists(
        notifier._get_assignment_directory(assignment_resource_id)))

    # Trigger cleanup by instantiating monitor.
    self._monitor.shutdown()
    self._monitor = assignment_monitor.AssignmentMonitor(
        self._fs, lambda x: None, lambda x: None)

    self.assertTrue(self._fs.exists(
        notifier._get_assignment_directory(assignment_resource_id)))


if __name__ == '__main__':
  absltest.main()
