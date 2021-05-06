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

import common.generate_protos  # pylint: disable=unused-import
from data_store import data_store as ds
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
               request_optional_args, list_method, read_method,
               response_proto_type, response_proto_repeated_field_name):
    self._request = request
    self._context = context
    self._request_type = type(request)
    self._data_store = data_store
    self._request_args = request_args
    self._request_optional_args = request_optional_args
    self._list_method = list_method
    self._read_method = read_method
    self._response_proto_type = response_proto_type
    self._response_proto_repeated_field_name = (
        response_proto_repeated_field_name)

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

    for optional_arg in self._request_optional_args:
      value = getattr(self._request, optional_arg)
      if value:
        args.append(value)

    response = self._response_proto_type()

    list_options = ds.ListOptions(
        page_token=self._request.page_token or None)
    list_ids, next_token = self._list_method(
        *args, self._request.page_size or None,
        list_options)
    response.next_page_token = next_token or ''

    self._fill_response(response, list_ids, *args)

    return response

  def _fill_response(self, response, list_ids, *args):
    """Reads proto from datastore from ids and fills up the response.

    Args:
      response: falken_service_pb2.List*Response instance getting populated.
      list_ids: IDs of the proto instances to fill the response with.
      *args: Args to query the data_store read method with.
    """
    for list_id in list_ids:
      getattr(response, self._response_proto_repeated_field_name).append(
          proto_conversion.ProtoConverter.convert_proto(
              self._read_method(*args, list_id)))


class ListBrainsHandler(ListHandler):
  """Handles listing brains for a project ID."""

  def __init__(self, request, context, data_store):
    super().__init__(request, context, data_store, ['project_id'], [],
                     data_store.list_brains, data_store.read_brain,
                     falken_service_pb2.ListBrainsResponse, 'brains')


class ListSessionsHandler(ListHandler):
  """Handles listing sessions for a brain ID."""

  def __init__(self, request, context, data_store):
    super().__init__(request, context, data_store, ['project_id', 'brain_id'],
                     [], data_store.list_sessions, data_store.read_session,
                     falken_service_pb2.ListSessionsResponse, 'sessions')


class ListEpisodeChunksHandler(ListHandler):
  """Handles listing episode chunks for a session or episode ID.

  ListEpisodeChunksRequest contains additional filter functionality which is
  handled in this class.
  """

  def __init__(self, request, context, data_store):
    super().__init__(request, context, data_store,
                     ['project_id', 'brain_id', 'session_id'],
                     [], data_store.list_episode_chunks,
                     data_store.read_episode_chunk,
                     falken_service_pb2.ListEpisodeChunksResponse,
                     'episode_chunks')
    if (request.filter ==
        falken_service_pb2.ListEpisodeChunksRequest.SPECIFIED_EPISODE):
      self._request_optional_args = ['episode_id']
    if (request.filter ==
        falken_service_pb2.ListEpisodeChunksRequest.EPISODE_IDS):
      self._read_method = self._create_episode_chunk_with_id_only

  def _create_episode_chunk_with_id_only(
      self, project_id, brain_id, session_id, episode_id, chunk_id):
    """Creates an EpisodeChunk proto instance with the IDs only."""
    return data_store_pb2.EpisodeChunk(
        project_id=project_id, brain_id=brain_id, session_id=session_id,
        episode_id=episode_id, chunk_id=chunk_id,
        data=episode_pb2.EpisodeChunk(
            episode_id=episode_id, chunk_id=chunk_id))
