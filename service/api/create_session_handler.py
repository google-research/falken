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
"""Create a new session to capture episode experiences."""

from absl import logging
from api import proto_conversion
from api import resource_id

import common.generate_protos  # pylint: disable=unused-import
from data_store import resource_id as data_resource_id
import data_store_pb2
from google.rpc import code_pb2
import session_pb2


def create_session(request, context, data_store):
  """Creates a new session.

  Stores the session in data_store and converts the data_store to the
    API-accepted session proto and returns it.

  Args:
    request: falken_service_pb2.CreateSessionRequest containing information
      about the session requested to be created.
    context: grpc.ServicerContext containing context about the RPC.
    data_store: Falken data_store.DataStore object to write the session.

  Returns:
    session: session_pb2.Session proto object of the session that was created.

  Raises:
    Exception: The gRPC context is aborted when the session spec is invalid,
      which raises an exception to terminate the RPC with a no-OK status.
  """
  logging.debug('CreateSession called for project_id %s with session_spec %s.',
                request.project_id, str(request.spec))
  starting_snapshot_id, previous_session_id = (
      _get_snapshot_id_and_previous_session_id(request.spec, data_store))

  previous_session = None
  if previous_session_id:
    previous_session = data_store.read(
        data_resource_id.FalkenResourceId(
            f'projects/{request.spec.project_id}/brains/'
            f'{request.spec.brain_id}/sessions/{previous_session_id}'))

  _validate_session(
      request.spec, context, starting_snapshot_id, previous_session)
  write_data_store_session = data_store_pb2.Session(
      project_id=request.spec.project_id,
      brain_id=request.spec.brain_id,
      session_id=resource_id.generate_resource_id(),
      session_type=request.spec.session_type,
      user_agent=resource_id.extract_metadata_value(context, 'user-agent'))
  if starting_snapshot_id:
    write_data_store_session.starting_snapshot_ids.append(starting_snapshot_id)

  data_store.write(write_data_store_session)
  return proto_conversion.ProtoConverter.convert_proto(
      data_store.read(
          data_resource_id.FalkenResourceId(
              f'projects/{write_data_store_session.project_id}/brains/'
              f'{write_data_store_session.brain_id}/sessions/'
              f'{write_data_store_session.session_id}')))


def _validate_session(
    session_spec, context, snapshot_id=None, previous_session=None):
  """Validates the session request.

  Args:
    session_spec: falken_service_pb2.CreateSessionRequest containing information
      about the session requested to be created.
    context: grpc.ServicerContext which can be used to abort the RPC.
    snapshot_id: Optional snapshot ID to start this session from.
    previous_session: Optional data_store_pb2.Session instance for the
      previous session.

  Raises:
    Exception: The gRPC context is aborted when the session spec is invalid,
      which raises an exception to terminate the RPC with a no-OK status.
  """
  if not session_spec.session_type:
    context.abort(
        code_pb2.INVALID_ARGUMENT,
        'Session type not set in the request. Please specify session type.')

  brain_id = session_spec.brain_id
  if (session_spec.session_type == session_pb2.INFERENCE or
      session_spec.session_type == session_pb2.EVALUATION) and not snapshot_id:
    context.abort(
        code_pb2.INVALID_ARGUMENT,
        f'Session type {session_spec.session_type} requires a starting '
        f'snapshot for brain {brain_id}.')

  if (session_spec.session_type == session_pb2.EVALUATION and
      previous_session.session_type != session_pb2.INTERACTIVE_TRAINING):
    context.abort(
        code_pb2.INVALID_ARGUMENT,
        'Evaluation sessions must have a starting snapshot produced from an '
        f'interactive training session for brain {brain_id}.')


def _get_snapshot_id_and_previous_session_id(session_spec, data_store):
  """Retrieve the snapshot ID and previous session ID in a tuple.

  Args:
    session_spec: session_pb2.SessionSpec proto containing info about current
      session to draw the previous session and snapshot from.
    data_store: data_store.DataStore instance to retreive the snapshot object
      from.

  Returns:
    snapshot_id, previous_session_id.
  """
  if session_spec.snapshot_id:
    snapshot = data_store.read(
        data_resource_id.FalkenResourceId(
            f'projects/{session_spec.project_id}/brains/{session_spec.brain_id}'
            f'/snapshots/{session_spec.snapshot_id}'))
  else:
    snapshot = data_store.get_most_recent_snapshot(
        session_spec.project_id, session_spec.brain_id)
  if snapshot:
    return snapshot.snapshot_id, snapshot.session_id
  return '', ''
