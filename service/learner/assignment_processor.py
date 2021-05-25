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
"""Handles assignment processing."""

import enum
import json
import time
import traceback
import uuid

from learner import data_fetcher
from learner import file_system
from learner import model_exporter
from learner import model_manager
from learner import stats_collector
from learner import storage
from learner.brains import brain_cache as brain_cache_module
from learner.brains import continuous_imitation_brain
from learner.brains import demonstration_buffer
from log import falken_logging

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import action_pb2
import episode_pb2
import data_store_pb2 as falken_schema_pb2


# How long to work on a single assignment in a single learner at most.
_MAX_ASSIGNMENT_WORK_TIME_SECS = 60*60

_CHUNK_STATE_TO_STEP_PHASE = {
    episode_pb2.UNSPECIFIED: demonstration_buffer.StepPhase.UNSPECIFIED,
    episode_pb2.IN_PROGRESS: demonstration_buffer.StepPhase.IN_PROGRESS,
    episode_pb2.SUCCESS: demonstration_buffer.StepPhase.SUCCESS,
    episode_pb2.FAILURE: demonstration_buffer.StepPhase.FAILURE,
    episode_pb2.ABORTED: demonstration_buffer.StepPhase.ABORTED,
    episode_pb2.GAVE_UP: demonstration_buffer.StepPhase.GAVE_UP,
}

_DEFAULT_LEARNER_HPARAMS = {
    # Should learning continue or restart when new data is received?
    'continuous': True,
    # The minimum interval between model saves, measured in batches trained.
    # If set to None, the model is never saved.
    'save_interval_batches': 20_000,
    # Minimum number of (steps * batch_size) before finishing training (or
    # restarting). If None, we don't require a minimum amount of steps to train.
    'min_train_examples': None,
    # Maximum number of (steps * batch_size). If None, we don't require
    # a maximum amount of steps to train.
    'max_train_examples': None,
    # Export models in the main thread.
    'synchronous_export': False,
}


class Error(Exception):
  """Base class for exceptions."""


class HParamError(Exception):
  """Raised if there is an unknown hyperparameter in the assignment."""


class NoDataError(Error):
  """Learner could not find new data to train on."""


class ExceededMaxWorkTimeError(Error):
  """Learner exceeded maximum work time on a single assignment."""


class AssignmentStats:
  """Returns stats about assignment processing for testing / debugging.

  In contrast to StatsCollector these are stats that are use to track
  information about an entire assignment rather than information about
  each trained model.

  Attributes:
    queries_completed: Number of Spanner fetch chunk queries completed.
    frames_added: Number of frames added to the brain from fetched
      demonstration data.
    models_recorded: Number of models saved during this assignment.
    brain_train_steps: Number of calls to brain.train() during the assignment.
    num_restarts: Number of times training has been restarted from scratch
      with a newly initialized model.
    brain_global_step: The value of the global step variable. (Resets with
      restarts.)
  """

  def __init__(self):
    self.queries_completed = 0
    self.frames_added = 0
    self.models_recorded = 0
    self.brain_train_steps = 0
    self.num_restarts = 0
    self.brain_global_step = 0


# Lists the possible processing assignment status, e.g. those that
# ProcessAssignmentUntil can handle.
class ProcessAssignmentStatus(enum.Enum):
  """Possible stopping points for assignment processing.

  Can be used in calls to ProcessAssignmentUntil.
  """
  # A step has been processed in the current assignment.
  PROCESSED_STEP = 1
  # A step has been processed in the current assignment, and training should
  # restart before processing the next step.
  PROCESSED_STEP_NEEDS_RESTART = 2
  # A model has been saved.
  SAVED_MODEL = 3
  # The assignment is about to fetch data. Useful for making sure more data
  # is available when it fetches, during a test.
  WILL_FETCH_DATA = 4
  # The assignment finished processing.
  FINISHED = 5


def _step_generator(episode_chunks):
  """Yields steps from EpisodeChunks."""
  for chunk in episode_chunks:
    for i, step in enumerate(chunk.data.steps):
      step_phase = demonstration_buffer.StepPhase.IN_PROGRESS
      if chunk.chunk_id == 0 and i == 0:
        # First step of first chunk is the start of the episode.
        step_phase = demonstration_buffer.StepPhase.START
      elif i == len(chunk.data.steps) - 1:
        # Last step of any chunk has equivalent phase as the chunk state.
        step_phase = _CHUNK_STATE_TO_STEP_PHASE.get(
            chunk.data.episode_state,
            demonstration_buffer.StepPhase.UNSPECIFIED)
        if step_phase == demonstration_buffer.StepPhase.UNSPECIFIED:
          raise ValueError(
              f'Unexpected chunk state: {chunk.data.episode_state}.')

      yield (chunk.episode_id, chunk.chunk_id, step.observation,
             step.reward.reward_value, step_phase, step.action,
             chunk.created_micros)


def _get_hparams(assignment_id):
  """Parse a hyperparemeters dictionary from an assignment ID.

  Args:
    assignment_id: Assignment ID to parse. If this is "default" an empty
      dictionary is returned.

  Returns:
    Dictionary containing the parsed hyperparameters.

  Raises:
    HParamError: If the assignment is malformed.
  """
  falken_logging.info(f'GetHParams got assignment_id {assignment_id}')
  if assignment_id == 'default':
    return {}
  try:
    return json.loads(assignment_id)
  except json.decoder.JSONDecodeError as error:
    error_message = (f'Failed to parse assignment ID: {error}\n' +
                     assignment_id)
    falken_logging.error(error_message)
    raise HParamError(error_message)


def populate_hparams_with_defaults_and_validate(hparams):
  """Construct hyperparameters for brain creation.

  Args:
    hparams: Hyperparameters that override the default learner hyperparameters.

  Returns:
    Hyperparameters dictionary that can be used to create a brain.

  Raises:
    HParamError: If the provided hyperparmeters overlap with default learner
      parameters or they're unknown.
  """
  result_hparams = continuous_imitation_brain.BCAgent.default_hparams()

  for hparam in _DEFAULT_LEARNER_HPARAMS:
    if hparam in result_hparams:
      raise HParamError(f'Learner HParam overlaps with brain HParam: {hparam}')
  result_hparams.update(_DEFAULT_LEARNER_HPARAMS)

  for hparam in hparams:
    if hparam not in result_hparams:
      raise HParamError(f'Unknown hparam in assignment: {hparam}')
  result_hparams.update(hparams)
  return result_hparams


class AssignmentProcessor:
  """Trains models based on incoming Assignments."""

  # How often to check the DB for new data.
  _DB_QUERY_INTERVAL_SECS = 10.0

  # How long to wait for training data
  _WAIT_FOR_DATA_BRAIN_SECS = 60

  def __init__(self,
               read_assignment: falken_schema_pb2.Assignment,
               filesys_helper: file_system.FileSystem,
               storage_helper: storage.Storage,
               brain_cache: brain_cache_module.BrainCache,
               get_session_state=None,
               write_assignment=None,
               always_block_when_fetching=False):
    """Create a new assignment processor.

    Args:
      read_assignment: The Assignment proto received from the queue.
      filesys_helper: A filesystem.Filesystem object.
      storage_helper: A storage.Storage helper.
      brain_cache: BrainCache instance.
      get_session_state: Callable which takes no arguments and returns
        storage.SessionState for the assignment. When this is None
        the session state is retrieved from the session associated with
        read_assignment in the database.
      write_assignment: Assignment proto used to write assignment results.
        If this is None, results are written to read_assignment.
      always_block_when_fetching: If True, always block during fetching. Useful
        for removing racing conditions in tests.
    """
    self._brain_cache = brain_cache
    self._read_assignment = read_assignment
    self._write_assignment = (
        write_assignment if write_assignment else read_assignment)
    falken_logging.info(f'Reading from {self._read_assignment}, '
                        f'writing to {self._write_assignment}')
    self._episode_id = ''
    self._episode_chunk_id = 0
    self._most_recent_demo_micros = 0
    self._file = filesys_helper
    self._storage = storage_helper
    self._brain = None
    self._hparams = None
    self._model_manager = None
    self._model_exporter = None
    self._always_block_when_fetching = always_block_when_fetching
    self._stats = stats_collector.StatsCollector(
        self._write_assignment.project_id,
        self._write_assignment.brain_id,
        self._write_assignment.session_id,
        self._write_assignment.assignment_id)
    self._assignment_stats = AssignmentStats()
    if get_session_state:
      self._get_session_state = get_session_state
    else:
      def _get_session_state():
        return self._storage.get_session_state(
            self._read_assignment.project_id,
            self._read_assignment.brain_id,
            self._read_assignment.session_id)
      self._get_session_state = _get_session_state

  def __enter__(self):
    """Start processing an assignment."""
    return self

  def __exit__(self, *unused_args):
    """Stop processing an assignment and clean up temporary storage."""
    self._file.wipe_checkpoints(self._write_assignment)

  @property
  def stats(self):
    """Returns StatsCollector about the processing task."""
    return self._stats

  @property
  def assignment_stats(self):
    """Returns AssignmentStats statistics about the processing task."""
    return self._assignment_stats

  @property
  def _min_train_batches(self):
    """Min amount of batches to train (or None if unrestricted)."""
    min_train_examples = self._hparams['min_train_examples']
    if min_train_examples is None:
      return None
    return int(min_train_examples / self._hparams['batch_size'])

  @property
  def _max_train_batches(self):
    """Max amount of batches to train (or None if unlimited)."""
    max_train_examples = self._hparams['max_train_examples']
    if max_train_examples is None:
      return None
    return int(max_train_examples / self._hparams['batch_size'])

  def _create_brain(self):
    """Creates a Brain."""
    brain_spec = self._storage.get_brain_spec(
        self._read_assignment.project_id, self._read_assignment.brain_id)
    falken_logging.info('Creating brain.',
                        brain_spec=brain_spec,
                        project_id=self._write_assignment.project_id,
                        brain_id=self._write_assignment.brain_id,
                        session_id=self._write_assignment.session_id)
    if not brain_spec:
      raise ValueError(
          f'Brain spec not found for project_id: '
          f'{self._read_assignment.project_id} and '
          f'brain_id: {self._read_assignment.brain_id}.')
    checkpoint_path = self._file.create_checkpoints_path(self._write_assignment)
    summary_path = self._file.create_summary_path(self._write_assignment)
    return self._brain_cache.GetOrCreateBrain(
        _get_hparams(self._read_assignment.assignment_id),
        brain_spec, checkpoint_path, summary_path)

  def _add_episode_chunks(self, chunks):
    """Insert new EpisodeData into the brain's replay buffer.

    Args:
      chunks: A batch of EpisodeChunks

    Returns:
      The number of demo frames contained in the provided chunks.
    """
    falken_logging.info('Adding {} new chunks.'.format(len(chunks)),
                        project_id=self._write_assignment.project_id,
                        brain_id=self._write_assignment.brain_id,
                        session_id=self._write_assignment.session_id)

    demo_frames = 0

    for (episode_id, chunk_id, observation, reward, phase, action,
         timestamp) in _step_generator(chunks):
      self._episode_id = episode_id
      self._episode_chunk_id = chunk_id
      self.assignment_stats.frames_added += 1
      self._brain.record_step(observation, reward, phase, episode_id, action,
                              timestamp)
      if action.source == action_pb2.ActionData.HUMAN_DEMONSTRATION:
        demo_frames += 1
        if timestamp > self._most_recent_demo_micros:
          self._most_recent_demo_micros = timestamp

    falken_logging.info(
        f'Finished adding {len(chunks)} new chunks with {demo_frames} '
        f'demo frames',
        project_id=self._write_assignment.project_id,
        brain_id=self._write_assignment.brain_id,
        session_id=self._write_assignment.session_id)
    return demo_frames

  def _chunk_generator(self):
    """Generates lists of chunks by querying the database.

    Yields:
      List of new chunks if available, None otherwise.
    """
    earliest_timestamp_micros = 0
    # Fetch data associated with ancestors AND with the current session.
    session_ids = self._storage.get_ancestor_session_ids(
        self._read_assignment.project_id,
        self._read_assignment.brain_id,
        self._read_assignment.session_id)
    session_ids.add(self._read_assignment.session_id)

    def generate_chunk_key(chunk):
      """Returns a unique string identifier for an episode chunk proto.

      Args:
        chunk: data_store_pb2.EpisodeChunk proto.

      Returns:
        Unique identifier for the chunk proto.
      """
      return f'{chunk.session_id}_{chunk.episode_id}_{chunk.chunk_id}'

    previous_chunk_keys = set()
    while True:  # Yield new chunks, potentially forever.
      new_chunks = []
      new_chunk_keys = set()
      for chunk in self._storage.get_episode_chunks(
          self._read_assignment.project_id,
          self._read_assignment.brain_id,
          session_ids, earliest_timestamp_micros):
        chunk_key = generate_chunk_key(chunk)
        if chunk_key not in previous_chunk_keys:
          # Update date_timestamp_micros to avoid refetching data.
          earliest_timestamp_micros = max(earliest_timestamp_micros,
                                          chunk.created_micros)
          new_chunks.append(chunk)
          new_chunk_keys.add(chunk_key)
      self.assignment_stats.queries_completed += 1
      if new_chunks:
        previous_chunk_keys = new_chunk_keys
        yield new_chunks
      else:
        yield None

  def _session_complete(self):
    """Returns true if the session is stale or ended."""
    session_state = self._get_session_state()
    complete = session_state in (
        storage.SessionState.STALE, storage.SessionState.ENDED)
    if complete:
      falken_logging.info(
          'Session complete, with state: '
          f'{storage.SessionState.as_string(session_state)}',
          project_id=self._write_assignment.project_id,
          brain_id=self._write_assignment.brain_id,
          session_id=self._write_assignment.session_id)
    return complete

  def _training_complete(self):
    """Returns true if training on the assignment is complete."""
    if self._session_complete():
      falken_logging.info(
          'Stopping training, reason: session has completed.',
          project_id=self._write_assignment.project_id,
          brain_id=self._write_assignment.brain_id,
          session_id=self._write_assignment.session_id)
      return True

    if self._min_train_batches is not None and (
        self._brain.tf_agent.train_step_counter < self._min_train_batches):
      # Unless the session is closed, we train the brain for min steps.
      return False

    if self._model_manager and self._model_manager.should_stop():
      falken_logging.info(
          f'Stopping training, reason: {self._model_manager.should_stop()}',
          project_id=self._write_assignment.project_id,
          brain_id=self._write_assignment.brain_id,
          session_id=self._write_assignment.session_id)
      return True

    if self._max_train_batches is not None and (
        self._brain.global_step >= self._max_train_batches):
      falken_logging.info(
          'Stopping training, reason: Exceeded max_train_batches of '
          f'{self._max_train_batches}',
          project_id=self._write_assignment.project_id,
          brain_id=self._write_assignment.brain_id,
          session_id=self._write_assignment.session_id)
      return True

    return False

  def _save_and_evaluate_policy(self, exporter):
    """Saves the current policy and evaluates it vs current best.

    Args:
      exporter: A ModelExporter.

    Returns:
      The ID of the model that was written.
    """
    falken_logging.info(
        'Writing tmp model.',
        project_id=self._write_assignment.project_id,
        brain_id=self._write_assignment.brain_id,
        session_id=self._write_assignment.session_id)
    self._stats.demonstration_frames = self._brain.num_train_frames
    self._stats.evaluation_frames = self._brain.num_eval_frames

    model_id = str(uuid.uuid4())
    with self._stats.record_event(
        stats_collector.FALKEN_EXPORT_CHECKPOINT_EVENT_NAME):
      tmp_checkpoint_path = self._file.create_tmp_checkpoint_path(
          self._write_assignment, model_id)
      self._brain.save_checkpoint(tmp_checkpoint_path)
      falken_logging.info(
          'Finished writing tmp model.',
          project_id=self._write_assignment.project_id,
          brain_id=self._write_assignment.brain_id,
          session_id=self._write_assignment.session_id)

    with self._stats.record_event(stats_collector.FALKEN_EVAL_EVENT_NAME):
      evals = list(self._brain.compute_full_evaluation())

    training_examples_completed = (
        self._brain.global_step * self._hparams['batch_size'])
    # The hparam can be set explicitly to None so we need to check for it.
    max_training_examples = (
        self._hparams['max_train_examples']
        if self._hparams.get('max_train_examples', None) else 0)

    exporter.export_model(tmp_checkpoint_path, evals, self._stats, model_id,
                          self._episode_id, self._episode_chunk_id,
                          training_examples_completed, max_training_examples,
                          self._most_recent_demo_micros)
    self.assignment_stats.models_recorded += 1

    # Compare new model to previous best and update accordingly.
    self._model_manager.record_new_model(model_id, evals)

    return model_id

  def _fetch_data(self, fetcher, initial_wait_for_data):
    """Fetches training / eval data from a fetcher and adds it to the brain.

    Args:
      fetcher: A data_fetcher.DataFetcher.
      initial_wait_for_data: Whether to wait for data on the first queue fetch.

    Returns:
      The number of demonstration frames that were added.
    """
    falken_logging.info(
        'Checking for new training data.',
        project_id=self._write_assignment.project_id,
        brain_id=self._write_assignment.brain_id,
        session_id=self._write_assignment.session_id)
    first_fetch = True
    demo_frames = 0
    while True:
      try:
        block, timeout = False, None
        if initial_wait_for_data and first_fetch:
          # Wait longer on the first fetch.
          block, timeout = True, self._WAIT_FOR_DATA_BRAIN_SECS
          # TODO(lph): Change datafetcher to auto-block on first query.
        elif self._always_block_when_fetching:
          # Short block for other fetches.
          block, timeout = True, 5
        first_fetch = False
        chunks = fetcher.get(block=block, timeout=timeout)
        demo_frames += self._add_episode_chunks(chunks)
      except data_fetcher.Empty:
        # If the underlying SQL queries did not complete, then we're not
        # waiting long enough for data to arrive.
        if (initial_wait_for_data and
            not self.assignment_stats.queries_completed):
          # We are in the first loop iteration and have not completed any
          # queries after _WAIT_FOR_DATA_BRAIN_SECS.
          raise NoDataError('Could not query DB for chunks.')
        return demo_frames

  def _process_step(self, fetcher):
    """Create and train a model.

    Args:
      fetcher: A data_fetcher.DataFetcher object to pull fresh data from.

    Yields:
      Pairs (ProcessAssignmentStatus, status_metadata). This allows for
      functions like ProcessAssignmentUntil to pause and resume Process.

    Raises:
      ExceededMaxWorkTimeError: If assignment takes too long to process.
    """
    if not self._brain:
      self._brain, self._hparams = self._create_brain()
      self._stats.training_steps = self._hparams['training_steps']
      self._stats.batch_size = self._hparams['batch_size']
      self._model_manager = model_manager.ModelManager()
    else:
      self._brain.reinitialize_agent()
      self._model_manager.reset_counters()

    with model_exporter.ModelExporter(self._write_assignment, self._storage,
                                      self._file, self._model_manager,
                                      self._brain.hparams) as exporter:
      saved_model_id = None
      loop_counter = 0
      restart_requested = False  # Whether to restart.
      # Enter main training loop.
      while not self._training_complete():
        if restart_requested and (
            self._min_train_batches is None or
            self._brain.tf_agent.train_step_counter >=
            self._min_train_batches):
          if saved_model_id is None:
            # Save if we didn't auto-save last loop iteration.
            saved_model_id = self._save_and_evaluate_policy(exporter)
            yield ProcessAssignmentStatus.SAVED_MODEL, saved_model_id
          falken_logging.info(
              f'Restarting training after {loop_counter} iterations.',
              project_id=self._write_assignment.project_id,
              brain_id=self._write_assignment.brain_id,
              session_id=self._write_assignment.session_id)
          yield ProcessAssignmentStatus.PROCESSED_STEP_NEEDS_RESTART, None
          return

        time_elapsed = time.perf_counter() - self._start_timestamp
        falken_logging.info(
            f'{time_elapsed}s elapsed since start of assignment.',
            brain_id=self._write_assignment.brain_id,
            session_id=self._write_assignment.session_id,
            assignment_id=self._write_assignment.assignment_id)

        if time_elapsed > _MAX_ASSIGNMENT_WORK_TIME_SECS:
          raise ExceededMaxWorkTimeError(
              f'Assignment took too long. Started {time_elapsed} seconds ago.'
          )

        # Grab all data from the fetcher.
        with self._stats.record_event(
            stats_collector.FALKEN_FETCH_CHUNK_EVENT_NAME):
          yield ProcessAssignmentStatus.WILL_FETCH_DATA, None
          demo_frames = self._fetch_data(
              fetcher,
              initial_wait_for_data=(loop_counter == 0))
          continuous = self._hparams['continuous']
          falken_logging.info(
              f'Finished data fetch, training iteration {loop_counter}. '
              f'Got {demo_frames} new demo frames, continuous={continuous}',
              project_id=self._write_assignment.project_id,
              brain_id=self._write_assignment.brain_id,
              session_id=self._write_assignment.session_id)
          if not continuous and loop_counter and demo_frames:
            restart_requested = True
            falken_logging.info('Received new data, requesting a restart.',
                                project_id=self._write_assignment.project_id,
                                brain_id=self._write_assignment.brain_id,
                                session_id=self._write_assignment.session_id)

        if not self._brain.num_train_frames:
          falken_logging.error(
              'No training frames available.',
              brain_id=self._write_assignment.brain_id,
              session_id=self._write_assignment.session_id,
              assignment_id=self._write_assignment.assignment_id)
          break

        # Perform training.
        with self._stats.record_event(
            stats_collector.FALKEN_TRAIN_BRAIN_EVENT_NAME):
          try:
            falken_logging.info('Training brain.',
                                project_id=self._write_assignment.project_id,
                                brain_id=self._write_assignment.brain_id,
                                session_id=self._write_assignment.session_id)
            self._brain.train()
            self.assignment_stats.brain_train_steps += 1
            self.assignment_stats.brain_global_step = self._brain.global_step
          except Exception as e:  # pylint: disable=broad-except
            falken_logging.error(
                f'Exception found when running _train_step: {e}.'
                f'Traceback:\n{traceback.format_exc()}',
                brain_id=self._write_assignment.brain_id,
                session_id=self._write_assignment.session_id,
                assignment_id=self._write_assignment.assignment_id)
            raise e

        batch_count = (self.assignment_stats.brain_train_steps *
                       self._hparams['training_steps'])
        if (self._hparams['save_interval_batches'] is not None and
            batch_count % self._hparams['save_interval_batches'] == 0):
          saved_model_id = self._save_and_evaluate_policy(exporter)
          yield ProcessAssignmentStatus.SAVED_MODEL, saved_model_id
        else:
          saved_model_id = None

        loop_counter += 1
      # End of main training loop.

      if saved_model_id is None and self.assignment_stats.brain_train_steps:
        #  If the last loop didn't save, save now.
        saved_model_id = self._save_and_evaluate_policy(exporter)
        yield ProcessAssignmentStatus.SAVED_MODEL, saved_model_id
    # End of exporter context

    # Learner completed normally, no restart indicated.
    yield ProcessAssignmentStatus.PROCESSED_STEP, None

  def process(self):
    """Train one or multiple brains.

    Yields:
      Pairs (ProcessAssignmentStatus, status_metadata). This allows for
      functions like ProcessAssignmentUntil to pause and resume Process.
    """
    with self._stats.record_event(stats_collector.FALKEN_PROCESS_EVENT_NAME):
      self._start_timestamp = time.perf_counter()

      if self._session_complete():
        falken_logging.info('Returning since assignment is '
                            'associated with closed or stale session.',
                            brain_id=self._read_assignment.brain_id,
                            session_id=self._read_assignment.session_id,
                            assignment_id=self._read_assignment.assignment_id)
        return

      falken_logging.info('Starting work on assignment.',
                          project_id=self._write_assignment.project_id,
                          brain_id=self._write_assignment.brain_id,
                          session_id=self._write_assignment.session_id,
                          assignment_id=self._write_assignment.assignment_id)

      with self._stats.record_event(
          stats_collector.FALKEN_MAIN_TRAINING_LOOP_EVENT_NAME):
        with data_fetcher.DataFetcher(self._chunk_generator(),
                                      self._DB_QUERY_INTERVAL_SECS) as fetcher:
          has_next_step = True
          while has_next_step:
            # Actually do the work.
            has_next_step = False
            for status, metadata in self._process_step(fetcher):
              if status == ProcessAssignmentStatus.PROCESSED_STEP_NEEDS_RESTART:
                has_next_step = True
              yield status, metadata

            if has_next_step:
              falken_logging.info(
                  'Restarting work on assignment.',
                  project_id=self._write_assignment.project_id,
                  brain_id=self._write_assignment.brain_id,
                  session_id=self._write_assignment.session_id,
                  assignment_id=self._write_assignment.assignment_id)
              self.assignment_stats.num_restarts += 1
              # Delete checkpoints to ensure that restarts start from scratch.
              self._file.wipe_checkpoints(self._write_assignment)

      if self.assignment_stats.brain_train_steps:
        falken_logging.info(
            'Completed assignment. '
            f'Called brain.train {self.assignment_stats.brain_train_steps} '
            'times.',
            project_id=self._write_assignment.project_id,
            brain_id=self._write_assignment.brain_id,
            session_id=self._write_assignment.session_id,
            assignment_id=self._write_assignment.assignment_id)
      else:
        # This should only happen in rare cases: A learner failed to ACK
        # after training to completion, e.g., due to preemption of the
        # learner at the end of training.
        falken_logging.warn(
            'Completed assignment without training.',
            project_id=self._write_assignment.project_id,
            brain_id=self._write_assignment.brain_id,
            session_id=self._write_assignment.session_id,
            assignment_id=self._write_assignment.assignment_id)
      # Clean-up checkpoints dir.
      self._file.wipe_checkpoints(self._write_assignment)
