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

import common.generate_protos  # pylint: disable=unused-import
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

  _store_episode_chunks()

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
    chunks: Episode chunks being checked.

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


def _store_episode_chunks():
  raise NotImplementedError('Method not implemented!')


def _start_assignment():
  raise NotImplementedError('Method not implemented!')


def _get_training_state():
  raise NotImplementedError('Method not implemented!')


def _select_model():
  raise NotImplementedError('Method not implemented!')


def _get_training_progress():
  raise NotImplementedError('Method not implemented!')
