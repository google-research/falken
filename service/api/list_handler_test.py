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
"""Tests for list_handler."""
from unittest import mock

from absl.testing import absltest
from api import list_handler

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import brain_pb2
import data_store_pb2
import falken_service_pb2
from google.protobuf import timestamp_pb2
from google.rpc import code_pb2


class ListHandlerTest(absltest.TestCase):

  @mock.patch.object(list_handler.ListHandler, '__init__')
  def test_list_handler_list_brains(self, list_handler_base):
    mock_request = mock.Mock()
    mock_context = mock.Mock()
    mock_ds = mock.Mock()
    list_handler.ListBrainsHandler(mock_request, mock_context, mock_ds)
    list_handler_base.assert_called_with(
        mock_request, mock_context, mock_ds, ['project_id'], [],
        mock_ds.list_brains, mock_ds.read_brain,
        falken_service_pb2.ListBrainsResponse,
        'brains')

  @mock.patch.object(list_handler.ListHandler, '__init__')
  def test_list_handler_list_sessions(self, list_handler_base):
    mock_request = mock.Mock()
    mock_context = mock.Mock()
    mock_ds = mock.Mock()
    list_handler.ListSessionsHandler(mock_request, mock_context, mock_ds)
    list_handler_base.assert_called_with(
        mock_request, mock_context, mock_ds, ['project_id', 'brain_id'], [],
        mock_ds.list_sessions, mock_ds.read_session,
        falken_service_pb2.ListSessionsResponse,
        'sessions')

  @mock.patch.object(list_handler.ListHandler, '__init__')
  def test_list_handler_list_episode_chunks_no_filter(self, list_handler_base):
    mock_request = mock.Mock()
    mock_context = mock.Mock()
    mock_ds = mock.Mock()
    list_handler.ListEpisodeChunksHandler(mock_request, mock_context, mock_ds)
    list_handler_base.assert_called_with(
        mock_request, mock_context, mock_ds,
        ['project_id', 'brain_id', 'session_id'], [],
        mock_ds.list_episode_chunks, mock_ds.read_episode_chunk,
        falken_service_pb2.ListEpisodeChunksResponse, 'episode_chunks')

  @mock.patch.object(list_handler.ListHandler, '__init__')
  def test_list_handler_list_episode_chunks_ids_only(self, list_handler_base):
    request = falken_service_pb2.ListEpisodeChunksRequest(
        filter=falken_service_pb2.ListEpisodeChunksRequest.EPISODE_IDS)
    mock_context = mock.Mock()
    mock_ds = mock.Mock()
    handler = list_handler.ListEpisodeChunksHandler(
        request, mock_context, mock_ds)
    list_handler_base.assert_called_with(
        request, mock_context, mock_ds,
        ['project_id', 'brain_id', 'session_id'], [],
        mock_ds.list_episode_chunks, mock_ds.read_episode_chunk,
        falken_service_pb2.ListEpisodeChunksResponse, 'episode_chunks')
    self.assertEqual(handler._read_method,
                     handler._create_episode_chunk_with_id_only)

  @mock.patch.object(list_handler.ListHandler, '__init__')
  def test_list_handler_list_episode_chunks_specified_episode_id(
      self, list_handler_base):
    request = falken_service_pb2.ListEpisodeChunksRequest(
        filter=falken_service_pb2.ListEpisodeChunksRequest.SPECIFIED_EPISODE)
    mock_context = mock.Mock()
    mock_ds = mock.Mock()
    handler = list_handler.ListEpisodeChunksHandler(
        request, mock_context, mock_ds)
    list_handler_base.assert_called_with(
        request, mock_context, mock_ds,
        ['project_id', 'brain_id', 'session_id'], [],
        mock_ds.list_episode_chunks, mock_ds.read_episode_chunk,
        falken_service_pb2.ListEpisodeChunksResponse, 'episode_chunks')
    self.assertEqual(handler._request_optional_args, ['episode_id'])

  def test_list_missing_ids(self):
    mock_context = mock.Mock()
    mock_context.abort.side_effect = Exception()
    request = falken_service_pb2.ListBrainsRequest()
    with self.assertRaises(Exception):
      list_handler.ListBrainsHandler(
          request, mock_context, mock.Mock()).list()
    mock_context.abort.assert_called_once_with(
        code_pb2.INVALID_ARGUMENT,
        'Could not find project_id in '
        '<class \'falken_service_pb2.ListBrainsRequest\'>.')

  @mock.patch.object(list_handler.ListHandler, '_fill_response')
  def test_list_no_pagination(self, fill_response):
    mock_context = mock.Mock()
    mock_ds = mock.Mock()
    mock_ds.list_brains.return_value = ([
        'brain_id_0', 'brain_id_1', 'brain_id_2', 'brain_id_3'], None)

    expected_response = falken_service_pb2.ListBrainsResponse(
        brains=[],  # Empty because we are mocking out fill_response.
        next_page_token=None)
    request = falken_service_pb2.ListBrainsRequest(project_id='test_project_id')
    self.assertEqual(
        list_handler.ListBrainsHandler(request, mock_context, mock_ds).list(),
        expected_response)

    fill_response.assert_called_once_with(
        mock.ANY, mock_ds.list_brains.return_value[0], 'test_project_id')
    mock_ds.list_brains.called_once_with('test_project_id', None, mock.ANY)
    self.assertIsNone(mock_ds.list_brains.call_args.args[2].page_token)

  @mock.patch.object(list_handler.ListHandler, '_fill_response')
  def test_list_with_optional_args(self, fill_response):
    mock_context = mock.Mock()
    mock_ds = mock.Mock()
    mock_ds.list_episode_chunks.return_value = (
        ['ep_chunk_id_0', 'ep_chunk_id_1', 'ep_chunk_id_2', 'ep_chunk_id_3'],
        None)

    expected_response = falken_service_pb2.ListEpisodeChunksResponse(
        episode_chunks=[],  # Empty because we are mocking out fill_response.
        next_page_token=None)
    request = falken_service_pb2.ListEpisodeChunksRequest(
        project_id='test_project_id', brain_id='test_brain_id',
        session_id='test_session_id', episode_id='test_episode_id',
        filter=falken_service_pb2.ListEpisodeChunksRequest.SPECIFIED_EPISODE)
    self.assertEqual(
        list_handler.ListEpisodeChunksHandler(
            request, mock_context, mock_ds).list(),
        expected_response)

    fill_response.assert_called_once_with(
        mock.ANY, mock_ds.list_episode_chunks.return_value[0],
        'test_project_id', 'test_brain_id', 'test_session_id',
        'test_episode_id')
    mock_ds.list_episode_chunks.called_once_with(
        'test_project_id', 'test_brain_id', 'test_session_id',
        'test_episode_id', None, mock.ANY)
    self.assertIsNone(
        mock_ds.list_episode_chunks.call_args.args[5].page_token)

  @mock.patch.object(list_handler.ListHandler, '_fill_response')
  def test_list_with_pagination(self, fill_response):
    mock_context = mock.Mock()
    mock_ds = mock.Mock()
    mock_ds.list_brains.return_value = ([
        'brain_id_1', 'brain_id_2', 'brain_id_3', 'brain_id_4'], '5')

    expected_response = falken_service_pb2.ListBrainsResponse(
        brains=[],  # Empty because we are mocking out fill_response.
        next_page_token='5')
    request = falken_service_pb2.ListBrainsRequest(
        project_id='test_project_id', page_size=4, page_token='2')
    self.assertEqual(
        list_handler.ListBrainsHandler(request, mock_context, mock_ds).list(),
        expected_response)

    fill_response.assert_called_once_with(
        mock.ANY, mock_ds.list_brains.return_value[0], 'test_project_id')
    mock_ds.list_brains.assert_called_once_with('test_project_id', 4, mock.ANY)
    self.assertEqual(mock_ds.list_brains.call_args.args[2].page_token, '2')

  @staticmethod
  def _ds_brain(index):
    return data_store_pb2.Brain(
        brain_id=f'brain_id_{index}')

  @staticmethod
  def _brain(index):
    return brain_pb2.Brain(
        brain_id=f'brain_id_{index}',
        brain_spec=brain_pb2.BrainSpec(),
        create_time=timestamp_pb2.Timestamp())

  def test_fill_response(self):
    mock_ds = mock.Mock()
    mock_ds.read_brain.side_effect = [
        ListHandlerTest._ds_brain(1),
        ListHandlerTest._ds_brain(2),
        ListHandlerTest._ds_brain(3),
        ListHandlerTest._ds_brain(4)]

    expected_response = falken_service_pb2.ListBrainsResponse(
        brains=[ListHandlerTest._brain(1),
                ListHandlerTest._brain(2),
                ListHandlerTest._brain(3),
                ListHandlerTest._brain(4)])

    response = falken_service_pb2.ListBrainsResponse()
    list_handler.ListBrainsHandler(
        mock.Mock(), mock.Mock(), mock_ds)._fill_response(
            response, ['brain_id_1', 'brain_id_2', 'brain_id_3', 'brain_id_4'],
            'test_project_id')
    self.assertEqual(response, expected_response)

    mock_ds.read_brain.assert_has_calls([
        mock.call('test_project_id', 'brain_id_1'),
        mock.call('test_project_id', 'brain_id_2'),
        mock.call('test_project_id', 'brain_id_3'),
        mock.call('test_project_id', 'brain_id_4')])


if __name__ == '__main__':
  absltest.main()
