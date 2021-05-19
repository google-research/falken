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
"""Handles interactions with the storage layer."""

import datetime
import queue
import time
from typing import List, Optional
import uuid

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
from data_store import assignment_monitor
from data_store import data_store as data_store_module
from data_store import file_system as data_store_file_system
from data_store import resource_id
import data_store_pb2
from google.rpc import code_pb2
from log import falken_logging


_DEFAULT_STALE_SECONDS = 600


class NotFoundError(Exception):
  """Returned if a requested object is not found in storage."""
  pass


def wrap_data_store_exception(fun):
  """Annotation to reraise data_store.NotFoundErrors as NotFoundErrors."""
  def wrapped_fun(*args, **kwargs):
    """Executes fun and reraises data_store.NotFoundErrors as native errors."""
    try:
      return fun(*args, **kwargs)
    except data_store_module.NotFoundError as e:
      raise NotFoundError(e)
  return wrapped_fun


class SessionState:
  NEW = 1          # No data submitted yet.
  IN_PROGRESS = 2  # Data submitted recently.
  STALE = 3         # No recent data submitted.
  ENDED = 4        # Session marked as ended.

  @classmethod
  def as_string(cls, session_state):
    return {
        1: 'NEW',
        2: 'IN_PROGRESS',
        3: 'STALE',
        4: 'ENDED',
    }[session_state]


class Storage:
  """Helper class for accessing storage for the learner."""

  def __init__(self,
               data_store: data_store_module.DataStore,
               file_system: data_store_file_system.FileSystem,
               stale_seconds=_DEFAULT_STALE_SECONDS):
    """Create a new Storage instance.

    Args:
      data_store: A DataStore object to access the storage layer.
      file_system: FileSystem instance to use to monitor assignments.
      stale_seconds: How many seconds need to elapse for an event on a session
        before it is considered stale.
    """
    self._data_store = data_store
    self._assignment_monitor = assignment_monitor.AssignmentMonitor(
        file_system, self._enqueue_pending_assignment,
        self._episode_chunk_notification)
    self._pending_assignments = queue.Queue()
    self._stale_seconds = stale_seconds

  @wrap_data_store_exception
  def record_session_error(
      self,
      assignment: data_store_pb2.Assignment,
      error: Exception):
    """Record error during assignment in session."""
    session = self._data_store.read_by_proto_ids(
        project_id=assignment.project_id,
        brain_id=assignment.brain_id,
        session_id=assignment.session_id)

    session.status.code = code_pb2.UNKNOWN
    session.status.message = str(error)
    self._data_store.write(session)

  @wrap_data_store_exception
  def record_assignment_error(
      self,
      assignment: data_store_pb2.Assignment,
      error: Exception):
    """Record error during assignment in assignment."""
    assignment.status.code = code_pb2.UNKNOWN
    assignment.status.message = str(error)
    self._data_store.write(assignment)

  def record_evaluations(self,
                         assignment,
                         model_id,
                         version_evals,
                         eval_latency_proto=None):
    """Record evaluations of a given model in the database.

    Args:
      assignment: The assignment that created the model.
      model_id: The ID of the model.
      version_evals: An iterable of pairs (version, score) where version is a
        version_id string and score is a float.
      eval_latency_proto: Latency stats associated with this eval.
    """
    offline_eval = data_store_pb2.OfflineEvaluation(
        project_id=assignment.project_id,
        brain_id=assignment.brain_id,
        session_id=assignment.session_id,
        model_id=model_id)
    timestamp = int(time.time() * 1e6)

    for eval_set_version, eval_score in version_evals:
      offline_eval.commit_timestamp = timestamp
      offline_eval.offline_evaluation_id = eval_set_version
      offline_eval.score = eval_score
      if eval_latency_proto:
        offline_eval.latency_stats.CopyFrom(eval_latency_proto)
      self._data_store.write(offline_eval)

  def record_new_model(self,
                       assignment,
                       episode_id,
                       episode_chunk_id,
                       training_examples_completed,
                       max_training_examples,
                       most_recent_demo_time_micros,
                       model_path,
                       compressed_model_path,
                       model_id=None,
                       model_latency_proto=None):
    """Record that a new model was written to storage.

    Will check in a transaction whether the session is still open.

    Args:
      assignment: The assignment associated with the model.
      episode_id: ID of the episode containing data used to train the model.
      episode_chunk_id: Integer ID of the episode chunk containing data used to
        train the model.
      training_examples_completed: Amount of steps * batches completed at
        the time of saving.
      max_training_examples: Maximum step * batch count allowed for training
        this model.
      most_recent_demo_time_micros: Time for the most recent human demostration
        used to train this model (the most recent chunk that doesn't contain
        human data).
      model_path: The path where the SavedModel is stored.
      compressed_model_path: The path where the compressed SavedModel is stored.
      model_id: Optional model_id. Will be autocreated if missing.
      model_latency_proto: Optional proto containing latency stats for creating
        and recording the model. Will be empty if missing.

    Returns:
      ModelID of the new model.
    """
    assert model_path
    model_id = model_id or str(uuid.uuid4())
    m = data_store_pb2.Model(
        project_id=assignment.project_id,
        brain_id=assignment.brain_id,
        session_id=assignment.session_id,
        model_id=model_id,
        model_path=model_path,
        compressed_model_path=compressed_model_path,
        assignment=assignment.assignment_id,
        episode=episode_id,
        episode_chunk=episode_chunk_id,
        latency_stats=model_latency_proto,
        training_examples_completed=training_examples_completed,
        max_training_examples=max_training_examples,
        most_recent_demo_time_micros=most_recent_demo_time_micros)
    falken_logging.info(
        'Recording new model.',
        project_id=assignment.project_id,
        brain_id=assignment.brain_id,
        session_id=assignment.session_id,
        assignment_id=assignment.assignment_id,
        model_path=model_path,
        episode_id=episode_id,
        episode_chunk_id=episode_chunk_id)

    session_state = self.get_session_state(
        assignment.project_id, assignment.brain_id, assignment.session_id)

    if session_state != SessionState.ENDED:
      self._data_store.write(m)
    else:
      falken_logging.info('Skipping model write to DB for closed session.',
                          project_id=assignment.project_id,
                          brain_id=assignment.brain_id,
                          session_id=assignment.session_id,
                          assignment_id=assignment.assignment_id)

    return m.model_id

  @wrap_data_store_exception
  def get_brain_spec(self, project_id, brain_id):
    """Get the spec for a given brain.

    Args:
      project_id: ProjectId to get episode chunks for.
      brain_id: BrainId to get episode chunks for.

    Returns:
      A BrainSpec, or None if no spec was found.
    """
    return self._data_store.read_by_proto_ids(
        project_id=project_id,
        brain_id=brain_id).brain_spec

  @wrap_data_store_exception
  def get_session_state(
      self,
      project_id,
      brain_id,
      session_id,
      as_of_datetime=None):
    """Returns a SessionState object describing the session."""
    session = self._data_store.read_by_proto_ids(
        project_id=project_id,
        brain_id=brain_id,
        session_id=session_id)

    # If an end time is set: ENDED
    if session.ended_micros:
      falken_logging.info(f'Session ended at {session.ended_micros}.',
                          project_id=project_id, brain_id=brain_id,
                          session_id=session_id)
      return SessionState.ENDED

    # If too much time elapsed since last activity: STALE
    last_activity_micros = (
        session.last_data_received_micros or session.created_micros)

    now = as_of_datetime or datetime.datetime.now()
    delta_micros = now.timestamp() * 1e6 - last_activity_micros
    if delta_micros / 1e6 > self._stale_seconds:
      falken_logging.warn('Session is stale. This should not happen.',
                          project_id=project_id, brain_id=brain_id,
                          session_id=session_id)
      return SessionState.STALE

    # If data was submitted recently: IN_PROGRESS
    if session.last_data_received_micros:
      return SessionState.IN_PROGRESS

    # If no data was submitted and session was started recently: NEW
    return SessionState.NEW

  @wrap_data_store_exception
  def get_assignment(self, project_id, brain_id, session_id, assignment_id):
    """Return assignment proto."""
    return self._data_store.read_by_proto_ids(
        project_id=project_id,
        brain_id=brain_id,
        session_id=session_id,
        assignment_id=assignment_id)

  @wrap_data_store_exception
  def get_ancestor_session_ids(
      self, project_id, brain_id, session_id):
    """Return set of all ancestor session IDs of the provided session."""
    session = self._data_store.read_by_proto_ids(
        project_id=project_id,
        brain_id=brain_id,
        session_id=session_id)
    ancestor_snapshot_ids = set(session.starting_snapshots)
    for snapshot_id in session.starting_snapshots:
      snapshot = self._data_store.read_by_proto_ids(
          project_id=project_id,
          brain_id=brain_id,
          snapshot_id=snapshot_id)

      for snapshot_parents in snapshot.ancestor_snapshots:
        ancestor_snapshot_ids.add(snapshot_parents.snapshot)
        ancestor_snapshot_ids.update(snapshot_parents.parent_snapshots)

    ancestor_session_ids = []
    for snapshot_id in ancestor_snapshot_ids:
      snapshot = self._data_store.read_by_proto_ids(
          project_id=project_id,
          brain_id=brain_id,
          snapshot_id=snapshot_id)
      ancestor_session_ids.append(snapshot.session)

    return set(ancestor_session_ids)

  @wrap_data_store_exception
  def get_episode_chunks(
      self, project_id, brain_id,
      session_ids, min_timestamp_micros=None):
    """Get all unprocessed episode chunks for a given assignment.

    Args:
      project_id: ProjectId to get episode chunks for.
      brain_id: BrainId to get episode chunks for.
      session_ids: Either a string SessionId or a list of SessionIds.
      min_timestamp_micros: GetEpisodeChunks will only read EpisodeChunks that
        have a creation timestamp higher or equal than min_timestamp_micros.
        If None, grab all chunks. Uses microsecond resolution.

    Returns:
      A list of EpisodeChunks.
    """
    if min_timestamp_micros is None:
      min_timestamp_micros = 0
    assert isinstance(min_timestamp_micros, int)
    if isinstance(session_ids, str):
      session_ids = [session_ids]

    assert session_ids
    if len(session_ids) == 1:
      (session_id_glob,) = session_ids
    else:
      session_id_glob = '{' + ','.join(session_ids) + '}'

    res_id_glob = self._data_store.resource_id_from_proto_ids(
        project_id=project_id,
        brain_id=brain_id,
        session_id=session_id_glob,
        episode_id='*',
        chunk_id='*')

    res_ids, _ = self._data_store.list(
        res_id_glob, min_timestamp_micros=min_timestamp_micros)

    return [self._data_store.read(res_id) for res_id in res_ids]

  def _enqueue_pending_assignment(
      self, assignment: resource_id.ResourceId):
    """Called when a new assignment is available.

    Args:
      assignment: ResourceId instance that references an assignment.
    """
    self._pending_assignments.put(assignment)

  def _episode_chunk_notification(
      self, assignment: resource_id.ResourceId,
      episode_chunks: List[resource_id.ResourceId]):
    """Called when a new episode chunk is available for an assignment.

    Args:
      assignment: ResourceId instance that references an assignment.
      episode_chunks: ResourceId instances that reference the new chunks in the
        assignment.
    """
    pass  # TODO(lph): Integrate with get_episode_chunks().

  @wrap_data_store_exception
  def receive_assignment(self, timeout: float = None) -> (
      Optional[data_store_pb2.Assignment]):
    """Retrieves the last unprocessed Assignment from the Assignments queue.

    Args:
      timeout: If a positive number, max amount of seconds to wait for an
        Assignment. If <=0, return immediately. If None, allow for infinite
        waiting time.

    Returns:
      Assignment proto, or None if there are no unprocessed assignments.
      The returned assignment is locked by this process and should be released
      when complete using record_assignment_done().
    """
    assignment = None
    deadline = time.time()
    if timeout is None:
      remaining = None
    elif timeout <= 0:
      remaining = 0
    else:
      deadline += timeout
      remaining = timeout

    while remaining is None or remaining >= 0:
      try:
        assignment_resource_id = self._pending_assignments.get(
            timeout=remaining)
      except queue.Empty:
        assignment_resource_id = None

      if (assignment_resource_id and
          self._assignment_monitor.acquire_assignment(assignment_resource_id)):
        assignment = self._data_store.read(assignment_resource_id)
        break
      elif remaining is None:
        break
      remaining = deadline - time.time()
    return assignment

  def handle_assignment_error(self, assignment: data_store_pb2.Assignment,
                              error: Exception):
    """Handle assignment that has errored.

    Args:
      assignment: Assignment proto instance for the assignment that experienced
        the error.
      error: Exception that occurred while processing the assignment.
    """
    # If we wanted to support retries we could retry training the assignment
    # and only abort the session after a number of retries. For the moment,
    # if an error occurs abort the session.
    # Log the source assignment.
    self.record_assignment_error(assignment, error)
    # Abort the session.
    self.record_session_error(assignment, error)

  @wrap_data_store_exception
  def record_assignment_done(self):
    """Mark the currently acquired assignment as done / complete."""
    falken_logging.info('Recording assignment done.')
    self._assignment_monitor.release_assignment()
    falken_logging.info('Recorded assignment done.')

  def create_session_and_assignment(self, project_id: str, brain_id: str,
                                    session_id: str, assignment_id: str) -> (
                                        data_store_pb2.Assignment):
    """Create a new session and assignment.

    Args:
      project_id: Project to create the new session and assignment in.
      brain_id: Brain to create a new session and assignment in.
      session_id: New Session ID to create.
      assignment_id: Assignment to create.

    Returns:
      New assignment proto.
    """
    assignment = data_store_pb2.Assignment(project_id=project_id,
                                           brain_id=brain_id,
                                           session_id=session_id,
                                           assignment_id=assignment_id)
    session = data_store_pb2.Session(project_id=project_id, brain_id=brain_id,
                                     session_id=session_id)
    falken_logging.info('Recording new session and assignment',
                        project_id=assignment.project_id,
                        brain_id=assignment.brain_id,
                        session_id=assignment.session_id,
                        assignment_id=assignment.assignment_id)
    self._data_store.write(session)
    self._data_store.write(assignment)
    return assignment
