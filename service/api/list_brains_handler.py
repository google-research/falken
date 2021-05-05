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
"""Lists brains for a given project."""

from absl import logging
from api import proto_conversion

import common.generate_protos  # pylint: disable=unused-import
from data_store import data_store as ds
import falken_service_pb2
from google.rpc import code_pb2


def ListBrains(request, context, data_store):
  """Lists brains for a project.

  Aborts the RPC if project_id is not specified.

  Args:
    request: falken_service_pb2.ListBrainsRequest specifying the project_id to
      query and page_size and page_token for paginated response.
    context: grpc.ServicerContext containing context about the RPC.
    data_store: Falken data_store.DataStore object to read the brains from.

  Returns:
    brain: falken_service_pb2.ListBrainsResponse containing brains and the
      next_page_token.
  """
  logging.debug('ListBrains called for project %s with page size %d and '
                'page_token %s.', request.project_id, request.page_size,
                request.page_token)
  if not request.project_id:
    context.abort(
        code_pb2.INVALID_ARGUMENT,
        'Project ID not specified in the ListBrains call.')
    return

  response = falken_service_pb2.ListBrainsResponse()

  list_options = ds.ListOptions(page_token=request.page_token or None)
  list_brains, next_token = data_store.list_brains(
      request.project_id, request.page_size or None, list_options)
  response.next_page_token = next_token or ''
  _fill_response_brains(request.project_id, response, list_brains, data_store)

  return response


def _fill_response_brains(project_id, response, brain_ids, data_store):  # pylint: disable=invalid-name
  """Reads brain from datastore from list_brains and fills up the response.

  Args:
    project_id: Project ID associated with the brains used to query the data
      store.
    response: falken_service_pb2.ListBrainsResponse that will be populated.
    brain_ids: Brain IDs of the brains to populate the response with.
    data_store: data_store.DataStore instance to query for the brains.
  """
  for brain_id in brain_ids:
    response.brains.append(
        proto_conversion.ProtoConverter.convert_proto(
            data_store.read_brain(project_id, brain_id)))
