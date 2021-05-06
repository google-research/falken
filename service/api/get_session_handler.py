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
"""Retrieve an existing session."""

from absl import logging
from api import proto_conversion

import common.generate_protos  # pylint: disable=unused-import
from google.rpc import code_pb2


def GetSession(request, context, data_store):
  """Retrieve an existing session for a given brain by name.

  Args:
    request: falken_service_pb2.GetSessionRequest containing information
      about the session to retrieve.
    context: grpc.ServicerContext containing context about the RPC.
    data_store: Falken data_store.DataStore object to read the sessions from.

  Returns:
    session: session_pb2.Session proto that was requested.

  Raises:
    Exception: The gRPC context is aborted when the required fields are not
      specified in the request, which raises an exception to terminate the RPC
      with a no-OK status.
  """
  logging.debug('GetSession called for project_id %s with brain_id %s and '
                'session_id %s.', request.project_id, request.brain_id,
                request.session_id)
  if not (request.project_id and request.brain_id and request.session_id):
    context.abort(
        code_pb2.INVALID_ARGUMENT,
        'Project ID, brain ID, and session ID must be specified in '
        'GetSessionRequest.')
    return

  return _read_and_convert_session(
      data_store, request.project_id, request.brain_id, request.session_id)


def GetSessionByIndex(request, context, data_store):
  """Retrieve a session from a given brain from the data store by index.

  Args:
    request: falken_service_pb2.GetSessionRequest containing information
      about the session to retrieve.
    context: grpc.ServicerContext containing context about the RPC.
    data_store: Falken data_store.DataStore object to read the sessions from.

  Returns:
    session: session_pb2.Session proto that was requested.

  Raises:
    Exception: The gRPC context is aborted when the required fields are not
      specified in the request, which raises an exception to terminate the RPC
      with a no-OK status.
  """
  logging.debug(
      'GetSessionByIndex called for project_id %s with brain_id %s and index '
      '%d.', request.project_id, request.brain_id, request.session_index)
  if not (request.project_id and request.brain_id and request.session_index):
    context.abort(
        code_pb2.INVALID_ARGUMENT,
        'Project ID, brain ID, and session index must be specified in '
        'GetSessionByIndexRequest.')

  session_ids, _ = data_store.list_sessions(
      request.project_id, request.brain_id, request.session_index+1)
  if len(session_ids) < request.session_index:
    context.abort(
        code_pb2.INVALID_ARGUMENT,
        f'Session at index {request.session_index} was not found.')

  return _read_and_convert_session(
      data_store, request.project_id, request.brain_id,
      session_ids[request.session_index])


def _read_and_convert_session(data_store, project_id, brain_id, session_id):  # pylint: disable=invalid-name
  return proto_conversion.ProtoConverter.convert_proto(
      data_store.read_session(project_id, brain_id, session_id))

