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
"""Monitors creation of assignments.

The assignment monitor allows for two kinds of monitoring:

* Monitoring on acquired assignments: A process that acquires an assignment,
  will only receive notifications for episode chunks that have been added to
  that assignment.

  Strong guarantees apply in this case: This is a producer-consumer scheme
  in which there's only one consumer at a time (acquiring an assignment is
  exclusive). All new chunks will be consumed by the consumer process,
  and in the transition from one consumer process to another, each chunk
  will be sent to either process, but no chunk will be sent to both.

  The notifications on acquired assignments can be taken to mean "this
  assignment has new training data available", and since acquiring is
  exclusive, the process can start training on that data right away knowing
  no other process will do the same.

* Monitoring on all assignments: A process that hasn't acquired an
  assignment will receive notifications for all assignments with
  new episode chunks (excluding assignments that are already acquired by other
  processes).

  This kind of monitoring is like a broadcasting system for multiple
  listeners. It provides very weak guarantees: A process that
  received a notification of this kind can't tell for sure another process
  won't train on the new data before it does.

  So a client that receives a notification of this kind can try to acquire
  the corresponding assignment. If that succeeds, they must wait for
  notifications of new chunks; such a notification would confirm that there's
  new data that hasn't been used for training before, and that the client
  has a lock that allows it to train on the data.

Monitoring is implemented as files and locks that are accumulated on the
notification directory. Monitoring on all assignments only reads these files,
and keeps track of state internally (hence the lack of guarantees). Monitoring
on acquired assignments locks assignments for writing, which allows is to
clean up the notification files and provide stronger guarantees.
"""

import hashlib
import os.path
import queue
import threading
import time

from data_store import file_system


class _Metronome(object):
  """Yields values with a maximum frequency."""

  def __init__(self, frequency):
    """Initializes the metronome.

    Args:
      frequency: Maximum frequency for the metronome ticks.
    """
    if frequency <= 0:
      raise ValueError(
          f'Metronome frequency must be positive, but is {frequency}.')
    self._sleep_time = 1 / frequency
    self._stop = False

  def wait_for_tick(self):
    """Generator that yields with the maximum requested frequency."""
    while not self._stop:
      yield
      time.sleep(self._sleep_time)

  def stop(self):
    """Makes wait_for_tick stop yielding ticks."""
    self._stop = True


class _FakeMetronome(object):
  """Simulates Metronome ticks when it is requested to do so."""
  _STOP_STRING = 'stop'

  def __init__(self, unused_frequency):
    """Initializes the fake metronome.

    Args:
      unused_frequency: Used only to be consistent with the _Metronome
        constructor.
    """
    self._ticks = queue.Queue()

  def wait_for_tick(self):
    """Generator that yields every time force_tick() is called."""
    while True:
      # Block until force_tick has been called at least once.
      tick = self._ticks.get()
      self._ticks.task_done()
      if tick == self._STOP_STRING:
        return

      yield

  def force_tick(self):
    """Make wait_for_tick tick."""
    self._ticks.put('tick!')

  def stop(self):
    """Makes wait_for_tick stop yielding ticks."""
    self._ticks.put(self._STOP_STRING)
    self._ticks.join()


class AssignmentMonitor(threading.Thread):
  """Monitors creation of assignments."""

  def __init__(self, fs, notification_dir, assignment_callback, chunk_callback,
               notification_frequency=5):
    """Initializes an assignment monitor.

    Args:
      fs: A FileSystem object.
      notification_dir: Directory path where the files used to handle
        chunk notifications are stored.
      assignment_callback: A callback function with a single argument,
        the resource id for the assignment. This callback function will be
        called to notify every time any assignment has received a new episode
        chunk (but only when no assignment has been acquired with
        acquire_assignment).
      chunk_callback: A callback function with two arguments:
        - assignment_id: Resource id for an assignment that has at least one
          new chunk.
        - chunks: A list of chunk resource ids.
        This callback function will be called to notify every time at least one
        episode chunk has been added to the acquired assignment. It is
        responsibility of the client to find which episode chunks were created
        before the first callback call.
      notification_frequency: Maximum amount of times per second to poll.
    """
    if not assignment_callback or not chunk_callback:
      raise ValueError('All callbacks must be set.')

    self._fs = fs
    self._metronome = _Metronome(notification_frequency)
    self._notification_dir = notification_dir

    # Information about the currently acquired assignment.
    self._acquired_assignment_id = None
    self._acquired_assignment_lock = None

    # Set callbacks.
    self._assignment_callback = assignment_callback
    self._chunk_callback = chunk_callback

    # Start polling.
    self._thread = threading.Thread(
        target=self._poll_assignments_and_episode_chunks, daemon=True)
    self._thread.start()

    super().__init__()

  def acquire_assignment(self, assignment_id):
    """Acquires an assignment.

    A process can only acquired a single assignment at a time. An assignment
    cannot be acquired by more than one process.

    Args:
      assignment_id: The resource id for the assignment to acquire.
    Returns:
      A boolean telling whether the assignment was correctly acquired or not.
    """
    if self._acquired_assignment_id:
      raise ValueError(
          f'Cannot acquire assignment {assignment_id} as assignment '
          f'{self._acquired_assignment_id} is already acquired.')

    lock_path = os.path.join(self._notification_dir, str(assignment_id))
    try:
      self._acquired_assignment_lock = self._fs.lock_file(lock_path)
    except file_system.UnableToLockFileError:
      self._acquired_assignment_lock = None
      return False

    self._acquired_assignment_id = assignment_id
    return True

  def release_assignment(self):
    """Releases the currently acquired assignment."""
    if not self._acquired_assignment_lock:
      raise ValueError(
          'Attempted to release an assignment, but none has been acquired yet.')

    self._fs.unlock_file(self._acquired_assignment_lock)
    self._acquired_assignment_id = None
    self._acquired_assignment_lock = None

  def trigger_assignment_notification(self, assignment_id, episode_chunk_id):
    """Triggers a notification for a given assignment.

    This will create files in the corresponding directory that make the polling
    method of another process run the callbacks.

    Args:
      assignment_id: Resource id of the assignment to trigger notifications for.
      episode_chunk_id: Resource id of a newly created chunk that's the reason
        why the assignment should be triggered.
    """
    # There's no need to lock for this.
    chunk_hash = hashlib.sha256(
        episode_chunk_id.episode_chunk.encode('utf-8')).hexdigest()
    path = os.path.join(
        self._notification_dir, str(assignment_id),
        f'chunk_{time.time()}_{chunk_hash}')
    self._fs.write_file(
        path, f'{str(assignment_id)}\n{str(episode_chunk_id)}')

  def _poll_assignments_and_episode_chunks(self):
    """Polls the notification dir using the metronome to dictate frequency."""
    # TODO(b/185940506): Use threading.Lock() for using object variables that
    # can be modified by main thread.
    for _ in self._metronome.wait_for_tick():
      if self._acquired_assignment_id:
        # TODO(b/185940506): List new chunks for self._acquired_assignment_id.
        self._chunk_callback(self._acquired_assignment_id, ['test'])
      else:
        # TODO(b/185940506): List chunks for all assignments that aren't
        # acquired by any other processes.
        self._assignment_callback('test')
