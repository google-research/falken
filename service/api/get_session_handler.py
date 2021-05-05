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
"""Retrieve an existing session for a given brain by name."""

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
        'Project ID, brain ID, session ID must be specified in '
        'GetSessionRequest.')
    return

  return proto_conversion.ProtoConverter.convert_proto(
      data_store.read_session(
          request.project_id, request.brain_id, request.session_id))
