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
"""Submit episode chunks and returns session info containing state and model."""

from absl import logging
from api import data_cache
from api import model_selector

import common.generate_protos  # pylint: disable=unused-import
from data_store import resource_id

# pylint: disable=g-bad-import-order
import action_pb2
import data_store_pb2
import episode_pb2
import falken_service_pb2
from google.rpc import code_pb2
from learner.brains import specs


def submit_episode_chunks(request, context, data_store):
  """Submits episode chunks to be trained on and returns session info.

  Args:
    request: falken_service_pb2.SubmitEpisodeChunksRequest containing info about
      the chunk and chunks itself that are submitted.
    context: grpc.ServicerContext containing context about the RPC.
    data_store: Falken data_store.DataStore object to write the chunks to and
      retrieve session info from.

  Returns:
    falken_service_pb2.SubmitEpisodeChunksResponse containing session info for
      the session that episode chunks were submitted for.

  Raises:
    Exception: The gRPC context is aborted when the required fields are not
      specified in the request, which raises an exception to terminate the RPC
      with a no-OK status.
  """
  logging.debug(
      'SubmitEpisodeChunksHandler called for project %s brain %s session %s.',
      request.project_id, request.brain_id, request.session_id)

  try:
    _check_episode_data_with_brain_spec(
        data_store, request.project_id, request.brain_id, request.chunks)
  except specs.TypingError as e:
    context.abort(
        code_pb2.INVALID_ARGUMENT,
        'Episode data failed did not match the brain spec for the session. '
        f'{e}')

  episode_resource_id = resource_id.FalkenResourceId(
      project=request.project_id, brain=request.brain_id,
      sessions=request.session_id, episode=request.chunks[0].episode_id)

  _store_episode_chunks(data_store, request.chunks, episode_resource_id)

  _start_assignment()

  _get_training_state()

  _select_model()

  _get_training_progress()

  return falken_service_pb2.SubmitEpisodeChunksHandlerResponse()


def _check_episode_data_with_brain_spec(
    data_store, project_id, brain_id, chunks):
  """Check for the episode data against the brain spec.

  Args:
    data_store: data_store.DataStore instance that contains the brain spec.
    project_id: Project ID of the episode being checked.
    brain_id: Brain ID of the episode being checked.
    chunks: List of episode_pb2.EpisodeChunk being checked.

  Raises:
    specs.TypingError if type checking fails.
  """
  brain_spec_proto = data_cache.get_brain_spec(data_store, project_id, brain_id)

  for chunk_nr in range(0, len(chunks)):
    chunk = chunks[chunk_nr]
    if not chunk.steps:
      # Empty chunks are only allowed if they close the episode.
      if chunk.episode_state == episode_pb2.IN_PROGRESS:
        raise specs.TypingError(
            'Received an empty chunk that does not close the episode at '
            f'chunk_index: {chunk_nr}.')
      # A chunk with ID 0 may not be empty even if it does close the episode,
      # since that would indicate an empty episode.
      elif not chunk.chunk_id:
        raise specs.TypingError(
            f'Received an empty episode at chunk_index: {chunk_nr}.')

    brain_spec = specs.BrainSpec(brain_spec_proto)

    for step_nr in range(0, len(chunk.steps)):
      step = chunk.steps[step_nr]
      try:
        # Check action data against action spec.
        _ = brain_spec.action_spec.proto_node.data_to_proto_nest(step.action)
        # Check observation data against observation spec.
        _ = brain_spec.observation_spec.proto_node.data_to_proto_nest(
            step.observation)
      except specs.TypingError as e:
        raise specs.TypingError(
            f'Brainspec check failed in chunk {chunk_nr}, step {step_nr}: {e}')


def _store_episode_chunks(data_store, chunks, episode_resource_id):
  """Stores episode chunks and online eval results in data_store.

  Args:
    data_store: data_store.DataStore instance to record episode chunks to.
    chunks: list of episode_pb2.EpisodeChunk instances to store.
    episode_resource_id: data_store.resource_id.FalkenResourceID instance
      containing resource IDs for the episode.

  Raises:
    ValueError if the episodes received has issues such as containing invalid
      data or incomplete episodes.
  """
  write_episode_chunk = data_store_pb2.EpisodeChunk(
      # Set properties common to all chunks.
      project_id=episode_resource_id.project,
      brain_id=episode_resource_id.brain,
      session_id=episode_resource_id.session)

  # Sort request chunks by chunk ID. This is to ensure the GetEpisodeSteps has
  # previous chunks accessible before querying later chunks.
  for chunk in chunks:
    try:
      steps_type = _get_steps_type(chunk)
    except ValueError as e:
      raise ValueError('Encountered error while getting steps type for episode '
                       f'{chunk.episode_id} chunk {chunk.chunk_id}. {e}')
    write_episode_chunk.chunk_id = chunk.chunk_id
    write_episode_chunk.episode_id = chunk.episode_id
    write_episode_chunk.steps_type = steps_type
    write_episode_chunk.data.CopyFrom(chunk)
    data_store.write_episode_chunk(write_episode_chunk)

    # Record online evaluation results.
    try:
      _record_online_evaluation(data_store, write_episode_chunk,
                                episode_resource_id)
    except ValueError as e:
      raise ValueError(
          'Encountered error while recording online evaluation for episode '
          f'{chunk.episode_id} chunk {chunk.chunk_id}. {e}')


def _get_steps_type(chunk):
  """Get steps type defined in data_store_pb2.StepsType from the steps.

  Args:
    chunk: episode_pb2.EpisodeChunk containing steps each containing an action
      source.

  Returns:
    data_store_pb2.StepsType based on the combinations of action sources.

  Raises:
    ValueError if the chunk contains a step with an unsupported step type.
  """
  seen_human_demo = False
  seen_brain_action = False
  for step in chunk.steps:
    if step.action.source == action_pb2.ActionData.HUMAN_DEMONSTRATION:
      seen_human_demo = True
    # We don't make a distinction between NO_SOURCE and BRAIN_ACTION at the
    # chunk level for simplicity.
    elif (step.action.source == action_pb2.ActionData.BRAIN_ACTION or
          step.action.source == action_pb2.ActionData.NO_SOURCE):
      seen_brain_action = True
    else:
      raise ValueError(f'Unsupported step type: {step.action.source}')
    if seen_human_demo and seen_brain_action:
      return data_store_pb2.MIXED
  if seen_human_demo:
    return data_store_pb2.ONLY_DEMONSTRATIONS
  if seen_brain_action:
    return data_store_pb2.ONLY_INFERENCES
  # This happens if a chunk has no steps in it.
  return data_store_pb2.UNKNOWN


def _record_online_evaluation(data_store, chunk, episode_resource_id):
  """Calculates episode completion state and score, and stores in data_store.

  Args:
    data_store: data_store.DataStore instance to record online evaluations to.
    chunk: data_store_pb2.EpisodeChunk instance containing data to extract score
      and state from.
    episode_resource_id: resource_id.EpisodeResourceId instance containing
      resource IDs for the episode.

  Raises:
    ValueError if the episodes received has issues such as containing invalid
      data or incomplete episodes.
  """
  try:
    complete = _episode_complete(chunk)
  except ValueError as e:
    raise e
  if not complete:
    return

  try:
    episode_score = _episode_score(chunk)
  except ValueError as e:
    raise e

  # Fetch previous episode chunk inference info for the same episode.
  model_ids = []
  steps_type, model_ids = _get_episode_steps_type(data_store, chunk,
                                                  episode_resource_id)
  if not steps_type and not model_ids:
    # Previous chunks were not found. This should not happen since chunks
    # should be submitted in sequence. This is under SDK control though,
    # so we log an error and move on. (The outcome is just a missing eval,
    # which is not critical. The system should be resilient to missing evals.)
    logging.error(
        'Failed to find all previous chunks for episode %s '
        'chunk %d.', chunk.episode_id, chunk.chunk_id)
    return

  if steps_type != data_store_pb2.ONLY_INFERENCES or not model_ids:
    # If there were non-inference action sources or multiple models used to
    # perform inference, then we can't score the episode.
    logging.info(
        'Skipping online eval for complete episode of type %s and %d inference '
        'models.', str(steps_type), len(model_ids))
    return

  model_id = model_ids[0]
  logging.debug('Recording score %d for episode %d model %s.', episode_score,
                episode_resource_id.episode, model_id)
  data_store.write_online_evaluation(
      data_store_pb2.OnlineEvaluation(
          project_id=episode_resource_id.project,
          brain_id=episode_resource_id.brain,
          session_id=episode_resource_id.session,
          episode_id=episode_resource_id.episode,
          model=model_id,
          score=episode_score))
  return


def _episode_complete(chunk):
  """Returns episode completion state based on episode state.

  Args:
    chunk: data_store_pb2.EpisodeChunk instance.

  Returns:
    Boolean False if episode is incomplete and True if episode is complete.

  Raises:
    ValueError if an an unsupported episode state was received.
  """
  if chunk.data.episode_state in [
      episode_pb2.IN_PROGRESS, episode_pb2.UNSPECIFIED, episode_pb2.ABORTED
  ]:
    return False
  elif chunk.data.episode_state in [
      episode_pb2.SUCCESS, episode_pb2.FAILURE, episode_pb2.GAVE_UP
  ]:
    return True
  raise ValueError(
      f'Unsupported episode state {chunk.data.episode_state} in episode '
      f'{chunk.episode_id} chunk {chunk.chunk_id}.')


def _episode_score(chunk):
  """Returns episode score based on episode state.

  Args:
    chunk: data_store_pb2.EpisodeChunk instance.

  Returns:
    model_selector.EPISODE_SUCCESS or EPISODE_FAILURE.

  Raises:
    ValueError if an incomplete episode was received.
  """
  if chunk.data.episode_state == episode_pb2.SUCCESS:
    return model_selector.EPISODE_SCORE_SUCCESS
  elif chunk.data.episode_state in [episode_pb2.FAILURE, episode_pb2.GAVE_UP]:
    return model_selector.EPISODE_SCORE_FAILURE
  raise ValueError(f'Incomplete episode {chunk.episode_id} chunk '
                   f'{chunk.chunk_id} can\'t be scored.')


def _get_episode_steps_type(data_store, current_chunk, episode_resource_id):
  """Get the merged StepsType of the episode and model_ids used in inference.

  Args:
    data_store: data_store.DataStore instance to check previous episode chunks.
    current_chunk: episode_pb2.EpisodeChunk containing the current_step.
    episode_resource_id: resource_id.EpisodeResourceId instance containing
      resource IDs for the episode.

  Returns:
    steps_type, model_ids: A tuple of the merged data_store_pb2.StepsType and
      set of model_id strings.

  Raises:
    FileNotFoundError: when the chunk ID does not line up with the number of
      previous chunks found.
  """
  model_ids = set()

  # Adds model to set if used in inference.
  if (current_chunk.steps_type != data_store_pb2.ONLY_DEMONSTRATIONS and
      current_chunk.data.model_id):
    model_ids.add(current_chunk.data.model_id)

  if current_chunk.chunk_id == 0:  # First chunk, nothing to merge with.
    return current_chunk.steps_type, model_ids

  # Read episode chunks from data_store for the same episode.
  read_chunk_ids, _ = data_store.list_episode_chunks(
      episode_resource_id.project, episode_resource_id.brain,
      episode_resource_id.session, episode_resource_id.episode)

  count = 0
  steps_type = data_store_pb2.UNKNOWN
  for chunk_id in read_chunk_ids:
    chunk = data_store.read_episode_chunk(episode_resource_id.project,
                                          episode_resource_id.brain,
                                          episode_resource_id.session,
                                          episode_resource_id.episode, chunk_id)
    steps_type = _merge_steps_types(steps_type, chunk.steps_type)
    if (chunk.steps_type != data_store_pb2.ONLY_DEMONSTRATIONS and
        chunk.data.model_id):
      model_ids.add(chunk.data.model_id)
    count += 1

  if count != current_chunk.chunk_id:
    raise FileNotFoundError(
        'Did not find all previous chunks for chunk id '
        f'{current_chunk.chunk_id}, only got {count} chunks.')
  return steps_type, model_ids


def _merge_steps_types(type_left, type_right):
  """Merge steps types.

  Compute join/least upper bound in the lattice:

                   MIXED
                  |     |
     ONLY_INFERENCE     ONLY_DEMONSTRATIONS
                  |     |
                  UNKNOWN

  Args:
    type_left: data_store_pb2.StepsType instance to merge.
    type_right: data_store_pb2.StepsType instance to merge.

  Returns:
    data_store_pb2.StepsType instance.
  """
  if type_left == type_right:
    return type_left
  if type_left == data_store_pb2.UNKNOWN:
    return type_right
  if type_right == data_store_pb2.UNKNOWN:
    return type_left
  return data_store_pb2.MIXED


def _start_assignment():
  raise NotImplementedError('Method not implemented!')


def _get_training_state():
  raise NotImplementedError('Method not implemented!')


def _select_model():
  raise NotImplementedError('Method not implemented!')


def _get_training_progress():
  raise NotImplementedError('Method not implemented!')