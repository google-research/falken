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

import tempfile
import threading
from unittest import mock

from absl.testing import absltest

from data_store import assignment_monitor
from data_store import file_system
from data_store import resource_id


class AssignmentMonitorTest(absltest.TestCase):

  def setUp(self):
    """Create a datastore object that uses a temporary directory."""
    super().setUp()
    self._temporary_directory = tempfile.TemporaryDirectory()
    self._fs = file_system.FileSystem(self._temporary_directory.name)
    self._monitor = assignment_monitor.AssignmentMonitor(
        self._fs, 'notif', lambda x: None, lambda x, y: None)

  def tearDown(self):
    """Clean up the temporary directory and datastore."""
    super().tearDown()
    self._monitor = None
    self._fs = None
    self._temporary_directory.cleanup()

  def test_acquire_release(self):
    """Tests acquiring is exclusive."""
    self._second_monitor = assignment_monitor.AssignmentMonitor(
        self._fs, 'notif', lambda x: None, lambda x, y: None)

    assignment_id = resource_id.FalkenResourceId(
        project='p0', brain='b0', session='s0', assignment='a0')
    self.assertTrue(self._monitor.acquire_assignment(assignment_id))
    self.assertFalse(self._second_monitor.acquire_assignment(assignment_id))
    self._monitor.release_assignment()
    self.assertTrue(self._second_monitor.acquire_assignment(assignment_id))

    self._monitor._metronome.stop()
    self._second_monitor._metronome.stop()

  @mock.patch.object(
      assignment_monitor, '_Metronome', new=assignment_monitor._FakeMetronome)
  def test_callbacks(self):
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

    self._monitor._metronome.stop()
    self._monitor = assignment_monitor.AssignmentMonitor(
        self._fs, 'notif', assignment_callback, chunk_callback)
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
    self._monitor.trigger_assignment_notification(assignment_id, chunk_id)

    metronome.force_tick()
    self.assertTrue(callback_called.wait(3))
    assignment_callback.assert_called_once_with(assignment_id)
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

    metronome.stop()
    assignment_callback.assert_not_called()
    chunk_callback.assert_not_called()


if __name__ == '__main__':
  absltest.main()
