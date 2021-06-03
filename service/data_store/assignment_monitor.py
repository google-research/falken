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

import collections
import os.path
import queue
import threading
import time

from data_store import file_system
from data_store import resource_id


# Seconds before an assignment acquisition expires.
_ASSIGNMENT_EXPIRATION_SECONDS = 5 * 60  # Five minutes.


class _Metronome:
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


class _FakeMetronome:
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


# A path for a file, with its corresponding timestamp in milliseconds since
# the epoch.
TimestampedPath = collections.namedtuple(
    'TimestampedPath', ['path', 'timestamp'])


class _AssignmentMonitorBase:
  """Common functionality for AssignmentNotifier and AssignmentMonitor."""

  def __init__(self, fs):
    """Initialize the instance.

    Args:
      fs: A FileSystem object used for queue storage.
    """
    super().__init__()
    self._fs = fs
    self._notification_dir = 'notifications'

  def _get_assignment_directory(self, assignment_resource_id):
    """Gives the directory given the resource id of an assignment."""
    return os.path.join(self._notification_dir, str(assignment_resource_id))


class AssignmentNotifier(_AssignmentMonitorBase):
  """Sends assignment notifications."""

  def trigger_assignment_notification(self, assignment_id, episode_chunk_id):
    """Triggers a notification for a given assignment.

    This will create files in the corresponding directory that make the polling
    method of another process run the callbacks.

    Args:
      assignment_id: Resource ID of the assignment to trigger notifications for.
      episode_chunk_id: Resource ID of a newly created chunk that's the reason
        why the assignment should be triggered. The episode component of
        the resource ID must not contain underscores.
    """
    # Underscores are used to separate metadata components in the chunk
    # filename so make sure encoded fields do not contain underscores.
    assert '_' not in episode_chunk_id.episode
    # There's no need to lock for this.
    path = os.path.join(
        self._get_assignment_directory(assignment_id),
        f'chunk_{episode_chunk_id.episode}_{episode_chunk_id.chunk}')
    self._fs.write_file(path, b'')


class AssignmentMonitor(_AssignmentMonitorBase):
  """Monitors creation of assignments."""

  def __init__(self, fs, assignment_callback, chunk_callback,
               notification_frequency=5):
    """Initializes an assignment monitor.

    Args:
      fs: A FileSystem object.
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
    super().__init__(fs)

    if not assignment_callback or not chunk_callback:
      raise ValueError('All callbacks must be set.')

    self._metronome = _Metronome(notification_frequency)

    # Information about the currently acquired assignment.
    self._acquired_assignment_id = None
    # Lock file used to make assignment acquisition exclusive across processes.
    self._acquired_assignment_lock_file = None
    # threading.Lock object to protect access to _acquired_assignment_id and
    # _acquired_assignment_lock_file variables across threads of the same
    # process.
    self._acquired_assignment_in_process_lock = threading.Lock()

    # Set callbacks.
    self._assignment_callback = assignment_callback
    self._chunk_callback = chunk_callback

    # Keys are assignment dir paths, and each value is a pair
    # (timestamp, chunks), with:
    # - timestamp: Last timestamp seen for that assignment.
    # - chunks: Set of chunk files seen with that timestamp. This allows
    #   detecting new chunks that happen to have the same timestamp than a
    #   previous one.
    self._last_timestamp = {}

    # Start polling.
    self._thread = threading.Thread(
        target=self._poll_assignments_and_episode_chunks, daemon=True)
    self._thread.start()

  def acquire_assignment(self, assignment_id):
    """Acquires an assignment.

    A process can only acquired a single assignment at a time. An assignment
    cannot be acquired by more than one process.

    Args:
      assignment_id: The resource id for the assignment to acquire.
    Returns:
      A boolean telling whether the assignment was correctly acquired or not.
    """
    with self._acquired_assignment_in_process_lock:
      if self._acquired_assignment_id:
        raise ValueError(
            f'Cannot acquire assignment {assignment_id} as assignment '
            f'{self._acquired_assignment_id} is already acquired.')

      lock_path = self._get_assignment_directory(assignment_id)
      try:
        self._acquired_assignment_lock_file = self._fs.lock_file(
            lock_path, _ASSIGNMENT_EXPIRATION_SECONDS)
      except file_system.UnableToLockFileError:
        self._acquired_assignment_lock_file = None
        return False

      self._acquired_assignment_id = assignment_id
      return True

  def release_assignment(self):
    """Releases the currently acquired assignment."""
    with self._acquired_assignment_in_process_lock:
      if not self._acquired_assignment_lock_file:
        raise ValueError(
            'Attempted to release an assignment, but none has been acquired '
            'yet.')

      self._fs.unlock_file(self._acquired_assignment_lock_file)
      self._acquired_assignment_id = None
      self._acquired_assignment_lock_file = None

  def _poll_assignments_and_episode_chunks(self):
    """Polls the notification dir using the metronome to dictate frequency."""
    for _ in self._metronome.wait_for_tick():
      callback = None

      with self._acquired_assignment_in_process_lock:
        if self._acquired_assignment_id:
          self._fs.refresh_lock(
              self._acquired_assignment_lock_file,
              _ASSIGNMENT_EXPIRATION_SECONDS)

          chunks = self._pop_episode_chunks(self._acquired_assignment_id)

          if chunks:
            callback = lambda: self._chunk_callback(  # pylint: disable=g-long-lambda
                self._acquired_assignment_id, chunks)  # pylint: disable=cell-var-from-loop
        else:
          # TODO(b/185940506): List chunks for all assignments that aren't
          # acquired by any other processes.
          callback = lambda: [  # pylint: disable=g-long-lambda
              self._assignment_callback(a)
              for a in self._get_assignments_with_changes()]

      if callback:
        callback()

  def _pop_episode_chunks(self, assignment_id):
    """Get and remove all new episode chunks for a given assignment id.

    Args:
      assignment_id: Resource id for the assignment to pop episode chunks for.
    Returns:
      A list of resource ids for each episode chunk found.
    """
    assert self._acquired_assignment_id == assignment_id

    chunks = []
    files = self._fs.glob(os.path.join(
        self._get_assignment_directory(assignment_id), 'chunk_*'))
    for f in files:
      id_parts = os.path.basename(f).split('_')
      if len(id_parts) != 3 or id_parts[0] != 'chunk':
        raise ValueError(f'Invalid chunk file {f}.')
      episode_id, chunk_id = id_parts[1:]

      try:
        chunk_id = int(chunk_id)
      except ValueError:
        raise ValueError(f'Failed to parse {chunk_id} as an int, for file {f}.')

      chunks.append(resource_id.FalkenResourceId(
          project=assignment_id.project,
          brain=assignment_id.brain,
          session=assignment_id.session,
          episode=episode_id,
          chunk=int(chunk_id)))

      self._fs.remove_file(f)

    return chunks

  def _get_assignments_with_changes(self):
    """Gives a list of assignments that had additions to their chunks list.

    This allows for monitoring on all assignments; see comment at top of
    this file for more details.

    Additions are considered since last time this method was called in the
    current process. This listing method can be slower than _pop_episode_chunks,
    as learners spend more time training for specific assignments than waiting
    for a new assignment.

    Modifies the self._last_timestamp cache as a side-effect.

    Returns:
      List of resource ids for the assignments that have changed.
    """
    assert self._acquired_assignment_id is None

    assignment_dirs = self._fs.glob(os.path.join(
        self._notification_dir,
        str(resource_id.FalkenResourceId(
            project='*', brain='*', session='*', assignment='*'))) + os.sep)

    assignment_ids_with_changes = []
    for assignment_dir in assignment_dirs:
      # Process only assignment dirs for assignments that haven't been acquired
      # by another process.
      locked = True
      try:
        with self._fs.lock_file_context(assignment_dir):
          locked = False
      except file_system.UnableToLockFileError:
        pass

      if locked:
        continue

      # Ignore chunk data we've already seen.
      chunks = [TimestampedPath(c, self._fs.get_modification_time(c))
                for c in self._fs.glob(os.path.join(assignment_dir, '*'))]

      last_timestamp = 0
      last_chunks = set()
      if assignment_dir in self._last_timestamp:
        last_timestamp, last_chunks = self._last_timestamp[assignment_dir]

      max_last_timestamp = last_timestamp
      new_chunks = []
      new_chunks_by_timestamp = collections.defaultdict(set)
      new_chunks_by_timestamp[last_timestamp] = last_chunks
      for chunk in chunks:
        if (chunk.timestamp >= last_timestamp and
            chunk.path not in last_chunks):
          new_chunks.append(chunk)
          new_chunks_by_timestamp[chunk.timestamp].add(chunk.path)
          max_last_timestamp = max(max_last_timestamp, chunk.timestamp)
      self._last_timestamp[assignment_dir] = (
          max_last_timestamp, new_chunks_by_timestamp[max_last_timestamp])
      chunks = new_chunks

      if chunks:
        assignment_ids_with_changes.append(
            resource_id.FalkenResourceId(
                os.path.relpath(assignment_dir, self._notification_dir)))

    return assignment_ids_with_changes
