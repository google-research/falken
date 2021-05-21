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
"""Main methods for Learner process of Falken service.."""

import traceback
import uuid

from learner import assignment_processor
from learner import file_system
from learner import storage
from learner.brains import brain_cache
from log import falken_logging

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import data_store_pb2 as falken_schema_pb2

# Default number of seconds to wait to process an assignment.
_DEFAULT_ASSIGNMENT_PROCESSING_TIMEOUT = 120


class Learner:
  """Receives assignments from queue and processes them."""
  # Max time to work on assignment before erroring out and triggering a retry.

  # See register_error_listener().
  _error_listeners = set()

  def __init__(self,
               tmp_models_directory,
               models_directory,
               checkpoints_directory,
               summaries_directory,
               learner_storage,
               assignment_path=None,
               always_block_when_fetching=False):
    """Initialize this instance.

    Args:
      tmp_models_directory: Location to write models before copying to
        models_directory.
      models_directory: Location to permanently store models.
      checkpoints_directory: Location to store checkpoints.
      summaries_directory: Location to store summaries.
      learner_storage: Storage object to use to gather experience and save
        training results.
      assignment_path: Path to the assignment to process in the form
        'project_id/brain_id/session_id/assignment_id'. If this is None
        the learner will process assignments from the storage module.
      always_block_when_fetching: If True, always block during fetching. Useful
        for removing racing conditions in tests.
    """
    self.queries_completed = 0
    self._brain_cache = brain_cache.BrainCache(
        assignment_processor.populate_hparams_with_defaults_and_validate)
    self._storage = learner_storage
    self._file = file_system.FileSystem(
        tmp_models_directory, models_directory, checkpoints_directory,
        summaries_directory)
    self._assignment_path = assignment_path
    # Generator produced by _ProcessAssignmentIncrementally.
    self._process_assignment_generator = None
    self._always_block_when_fetching = always_block_when_fetching

  @property
  def _assignment_path_as_proto(self):
    """Get _assignment_path as a proto or None if no path is assigned."""
    if not self._assignment_path:
      return None
    components = self._assignment_path.split('/')
    if len(components) != 4:
      falken_logging.error(f'Invalid assignment path {self._assignment_path})')
      return None
    return falken_schema_pb2.Assignment(
        project_id=components[0],
        brain_id=components[1],
        session_id=components[2],
        assignment_id=components[3])

  def fetch_assignment(self, timeout):
    """Fetch an assignment from the DB or the manual assignment.

    Args:
      timeout: Time (in seconds) to wait for an assignment.

    Returns:
      Assignment proto or None if no assignments are available.
    """
    assignment_proto = self._assignment_path_as_proto
    if assignment_proto:
      return assignment_proto

    falken_logging.info('Waiting for assignment.')
    assignment = self._storage.receive_assignment(timeout=timeout)
    if assignment is None:
      return None
    return assignment

  def process_assignment(self, timeout=_DEFAULT_ASSIGNMENT_PROCESSING_TIMEOUT):
    """Processes an assignment, and returns the assignment stats."""
    self.setup_process_assignment(timeout=timeout)
    status, metadata = self.process_assignment_until(None)
    # If the assignment was stopped by another thread, it's in an indeterminate
    # state so do not validate the return status.
    if self._process_assignment_generator:
      self.stop_process_assignment()
      if status != assignment_processor.ProcessAssignmentStatus.FINISHED:
        raise RuntimeError(
            'Unexpected ProcessAssignment status "%s" with metadata "%s"' %
            (status, metadata))
    return metadata

  def shutdown(self):
    """Stop processing assignments and shut down all async operations."""
    self.stop_process_assignment()
    self._storage.shutdown()

  def setup_process_assignment(
      self, timeout=_DEFAULT_ASSIGNMENT_PROCESSING_TIMEOUT):
    """Sets up for running ProcessAssignmentUntil.

    Once SetupProcessAssignment is called, it is possible to call
    ProcessAssignmentUntil one or more times, and then call StopAssignment.
    This allows for controlling the flow of assignment processing, by allowing
    'pause' and 'resume' on processing, which is especially useful for tests
    which would otherwise need to use unreliable timeouts instead.

    Args:
      timeout: Max number of seconds allowed during assignment processing.
    """
    if self._process_assignment_generator is not None:
      raise ValueError('SetupProcessAssignment without finishing previous run')
    self._process_assignment_generator = self._process_assignment_incrementally(
        timeout=timeout)

  def process_assignment_until(
      self, until_status: assignment_processor.ProcessAssignmentStatus):
    """Processes an assignment until a given status is found.

    This function can be called multiple times in sequence, as described in
    SetupProcessAssignment.

    Args:
      until_status: a assignment_processor.ProcessAssignmentStatus value at
        which to pause processing an assignment.
        If None, it will process the assignment until it ends processing.

    Returns:
      status, metadata: assignment_processor.ProcessAssignmentStatus value and
        its corresponding metadata, as found just before pausing processing of
        an assignment.
    """
    status = None
    metadata = None
    try:
      while True:
        # Hold a reference to the generator as
        # self._process_assignment_generator can be modified by other threads.
        assignment_generator = self._process_assignment_generator
        if assignment_generator is None:
          break
        # Try to fetch the next tuple, if the generator is complete
        # StopIteration is raised and caught below.
        s, m = next(assignment_generator)
        status, metadata = s, m
        if status == until_status:
          break
    except StopIteration:
      self.stop_process_assignment()
    except:
      self.stop_process_assignment()
      raise

    if until_status is not None and until_status != status:
      raise ValueError(
          f'assignment_processor.ProcessAssignmentStatus finished at status '
          f'"{status}", without finding expected status "{until_status}".')

    return status, metadata

  def stop_process_assignment(self):
    """Stops processing an assignment.

    This allows SetupProcessAssignment to be called again.
    """
    self._process_assignment_generator = None

  @staticmethod
  def register_error_listener(error_listener):
    """Register a callable that is notified when an error occurs.

    Args:
      error_listener: Callable that is called with arguments
        (project_id, brain_id, session_id, assignment_id) if an error occurs
        when processing an assignment.
    """
    Learner._error_listeners.add(error_listener)

  @staticmethod
  def _notify_error_listeners(project_id, brain_id, session_id, assignment_id):
    """Report an error associated with the specified assignment.

    Args:
      project_id: Project ID associated  with the error.
      brain_id: Brain ID associated with the error.
      session_id: Session ID associated with the error.
      assignment_id: Assignment ID associated with the error.
    """
    for listener in Learner._error_listeners:
      listener(project_id, brain_id, session_id, assignment_id)

  def _process_assignment_incrementally(
      self, timeout=_DEFAULT_ASSIGNMENT_PROCESSING_TIMEOUT):
    """Wait for an assignment and work on it to completion.

    Args:
      timeout: Max number of seconds to wait for an assignment.

    Yields:
      Pairs (assignment_processor.ProcessAssignmentStatus, status_metadata).
      This allows for functions like ProcessAssignmentUntil to pause and resume
      this function.
    """
    read_assignment = self.fetch_assignment(timeout)
    if read_assignment is None:
      yield assignment_processor.ProcessAssignmentStatus.FINISHED, None
      return
    write_assignment = read_assignment

    # If we're reading from an existing, write the results to a new
    # session to avoid polluting the source data.
    if self._assignment_path_as_proto:
      write_assignment = self._storage.create_session_and_assignment(
          read_assignment.project_id,
          read_assignment.brain_id,
          str(uuid.uuid4()),
          read_assignment.assignment_id)
      falken_logging.info(
          f'Writing to a new session {write_assignment.session_id}',
          brain_id=write_assignment.brain_id,
          session_id=write_assignment.session_id,
          assignment_id=write_assignment.assignment_id)

    falken_logging.info(
        'Processing assignment.',
        project_id=read_assignment.project_id,
        brain_id=read_assignment.brain_id,
        session_id=read_assignment.session_id,
        assignment_id=read_assignment.assignment_id)
    with assignment_processor.AssignmentProcessor(
        read_assignment, self._file, self._storage, self._brain_cache,
        get_session_state=((lambda: storage.SessionState.IN_PROGRESS)
                           if self._assignment_path else None),
        write_assignment=write_assignment,
        always_block_when_fetching=self._always_block_when_fetching) as proc:
      try:
        for y in proc.process():
          yield y
        falken_logging.info(
            'Processed assignment.',
            brain_id=read_assignment.brain_id,
            session_id=read_assignment.session_id,
            assignment_id=read_assignment.assignment_id)
        # Always mark the assignment done to avoid deadlocking the queue
        # receiver thread. The exception will be caught by learner_main.
        self._storage.record_assignment_done()
      except Exception as e:  # pylint: disable=broad-except
        falken_logging.error(
            f'Exception found when processing assignment: {e}.'
            f'Traceback:\n{traceback.format_exc()}',
            brain_id=read_assignment.brain_id,
            session_id=read_assignment.session_id,
            assignment_id=read_assignment.assignment_id)
        self._storage.handle_assignment_error(read_assignment, e)
        self._notify_error_listeners(read_assignment.project_id,
                                     read_assignment.brain_id,
                                     read_assignment.session_id,
                                     read_assignment.assignment_id)
        raise e

    yield assignment_processor.ProcessAssignmentStatus.FINISHED, (
        proc.assignment_stats, proc.stats)
