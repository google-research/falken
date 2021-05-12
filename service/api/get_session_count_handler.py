
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
"""Count existing sessions for a brain."""

from absl import logging

import common.generate_protos  # pylint: disable=unused-import

from data_store import resource_id
import falken_service_pb2
from google.rpc import code_pb2


def get_session_count(request, context, data_store):
  """Retrieve an existing session for a given brain by name.

  Args:
    request: falken_service_pb2.GetSessionCountRequest containing information
      about which sessions to count.
    context: grpc.ServicerContext containing context about the RPC.
    data_store: Falken data_store.DataStore object to count the sessions from.

  Returns:
    falken_service_pb2.GetSessionCountResponse containing the session count.

  Raises:
    Exception: The gRPC context is aborted when the required fields are not
      specified in the request, which raises an exception to terminate the RPC
      with a no-OK status.
  """
  logging.debug('GetSessionCount called for project_id %s and brain_id %s.',
                request.project_id, request.brain_id)

  if not (request.project_id and request.brain_id):
    context.abort(
        code_pb2.INVALID_ARGUMENT,
        'Project ID and brain ID must be specified in GetSessionCountRequest.')
    return

  session_ids, _ = data_store.list(resource_id.FalkenResourceId(
      project=request.project_id, brain=request.brain_id, session='*'))
  return falken_service_pb2.GetSessionCountResponse(
      session_count=len(session_ids))
