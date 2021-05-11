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
"""Query datastore for a list of Falken objects."""

from absl import logging
from api import proto_conversion
from data_store import resource_id

# pylint: disable=unused-import,g-bad-import-order
import common.generate_protos
import data_store_pb2
import episode_pb2
import falken_service_pb2
from google.rpc import code_pb2


class ListHandler:
  """Handles listing of proto instances for a given request.

  This is a base class extended by implementation handlers for each type of
  request.
  """

  def __init__(self, request, context, data_store, request_args,
               glob_pattern, response_proto_type,
               response_proto_repeated_field_name):
    self._request = request
    self._context = context
    self._request_type = type(request)
    self._data_store = data_store
    self._glob_pattern = glob_pattern
    self._request_args = request_args
    self._response_proto_type = response_proto_type
    self._response_proto_repeated_field_name = (
        response_proto_repeated_field_name)

  def read(self, res_id):
    """Read a resource based on its resource ID.

    Args:
      res_id: The resource ID represented as a string.
    Returns:
      The resource represented as a proto.
    """
    return self._data_store.read(
        resource_id.FalkenResourceId(res_id))

  def _get_list_glob(self, *args):
    for arg in args:
      if '/' in arg:
        raise ValueError('ID strings may not contain "/".')
    return self._glob_pattern.format(*args)

  def list(self):
    """Retrieves instances of the requested proto in data store.

    Returns:
      session: falken_service_pb2.List*Response proto containing the protos
        that were requested and the next_page_token.

    Raises:
      Exception: The gRPC context is aborted when the required fields are not
        specified in the request, which raises an exception to terminate the RPC
        with a no-OK status.
    """
    logging.debug('List called with request %s', str(self._request))

    args = []
    for arg in self._request_args:
      if not getattr(self._request, arg):
        self._context.abort(
            code_pb2.INVALID_ARGUMENT,
            f'Could not find {arg} in {self._request_type}.')
      args.append(getattr(self._request, arg))

    response = self._response_proto_type()

    list_ids, next_token = self._data_store.list(
        resource_id.FalkenResourceId(self._get_list_glob(*args)),
        page_size=self._request.page_size or None,
        page_token=self._request.page_token or None)

    response.next_page_token = next_token or ''

    self._fill_response(response, list_ids)

    return response

  def _fill_response(self, response, res_ids):
    """Reads proto from datastore from ids and fills up the response.

    Args:
      response: falken_service_pb2.List*Response instance getting populated.
      res_ids: Resource id string of the protos to fill the response with.
    """
    for res_id in res_ids:
      getattr(response, self._response_proto_repeated_field_name).append(
          proto_conversion.ProtoConverter.convert_proto(
              self.read(res_id)))


class ListBrainsHandler(ListHandler):
  """Handles listing brains for a project ID."""

  def __init__(self, request, context, data_store):
    super().__init__(request, context, data_store, ['project_id'],
                     'projects/{0}/brains/*',
                     falken_service_pb2.ListBrainsResponse, 'brains')


class ListSessionsHandler(ListHandler):
  """Handles listing sessions for a brain ID."""

  def __init__(self, request, context, data_store):
    super().__init__(request, context, data_store, ['project_id', 'brain_id'],
                     'projects/{0}/brains/{1}/sessions/*',
                     falken_service_pb2.ListSessionsResponse, 'sessions')


class ListEpisodeChunksHandler(ListHandler):
  """Handles listing episode chunks for a session or episode ID.

  ListEpisodeChunksRequest contains additional filter functionality which is
  handled in this class.
  """

  def __init__(self, request, context, data_store):
    if (request.filter ==
        falken_service_pb2.ListEpisodeChunksRequest.SPECIFIED_EPISODE):
      res_id_glob = (
          'projects/{0}/brains/{1}/sessions/{2}/episodes/{3}/chunks/*')
      args = ['project_id', 'brain_id', 'session_id', 'episode_id']
    else:
      res_id_glob = 'projects/{0}/brains/{1}/sessions/{2}/episodes/*/chunks/*'
      args = ['project_id', 'brain_id', 'session_id']

    super().__init__(request, context, data_store,
                     args, res_id_glob,
                     falken_service_pb2.ListEpisodeChunksResponse,
                     'episode_chunks')

  def read(self, res_id: str):
    """Override parent 'read' to provide ID-only read functionality."""
    if (self._request.filter !=
        falken_service_pb2.ListEpisodeChunksRequest.EPISODE_IDS):
      return super().read(res_id)

    # Translate string to ResourceId object.
    res_id = resource_id.FalkenResourceId(res_id)

    return data_store_pb2.EpisodeChunk(
        project_id=res_id.project,
        brain_id=res_id.brain,
        session_id=res_id.session,
        episode_id=res_id.episode,
        chunk_id=int(res_id.chunk),
        data=episode_pb2.EpisodeChunk(
            episode_id=res_id.episode, chunk_id=int(res_id.chunk)))
