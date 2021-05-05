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
"""Tests for list_brains_handler."""
from unittest import mock

from absl.testing import absltest
from api import list_brains_handler

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import brain_pb2
import data_store_pb2
import falken_service_pb2
from google.protobuf import timestamp_pb2
from google.rpc import code_pb2


class ListBrainsHandlerTest(absltest.TestCase):

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

  def test_list_brains_no_project_id(self):
    mock_context = mock.Mock()
    list_brains_handler.ListBrains(
        falken_service_pb2.ListBrainsRequest(), mock_context, None)
    mock_context.abort.assert_called_once_with(
        code_pb2.INVALID_ARGUMENT,
        'Project ID not specified in the ListBrains call.')

  @mock.patch.object(list_brains_handler, '_fill_response_brains')
  def test_list_brains_no_pagination(self, fill_response_brains):
    mock_context = mock.Mock()
    mock_ds = mock.Mock()
    mock_ds.list_brains.return_value = ([
        'brain_id_0', 'brain_id_1', 'brain_id_2', 'brain_id_3'], None)

    expected_response = falken_service_pb2.ListBrainsResponse(
        brains=[],  # Empty because we are mocking out fill_response_brain.
        next_page_token=None)

    self.assertEqual(
        list_brains_handler.ListBrains(
            falken_service_pb2.ListBrainsRequest(
                project_id='test_project_id'),
            mock_context, mock_ds),
        expected_response)

    fill_response_brains.assert_called_once_with(
        'test_project_id', mock.ANY, mock_ds.list_brains.return_value[0],
        mock_ds)
    mock_ds.list_brains.called_once_with('test_project_id', None, mock.ANY)
    self.assertIsNone(mock_ds.list_brains.call_args.args[2].page_token)

  @mock.patch.object(list_brains_handler, '_fill_response_brains')
  def test_list_brains_with_pagination(self, fill_response_brains):
    mock_context = mock.Mock()
    mock_ds = mock.Mock()
    mock_ds.list_brains.return_value = ([
        'brain_id_1', 'brain_id_2', 'brain_id_3', 'brain_id_4'], '5')

    expected_response = falken_service_pb2.ListBrainsResponse(
        brains=[],  # Empty because we are mocking out fill_response_brain.
        next_page_token='5')

    self.assertEqual(
        list_brains_handler.ListBrains(
            falken_service_pb2.ListBrainsRequest(
                project_id='test_project_id',
                page_size=4,
                page_token='2'),
            mock_context, mock_ds),
        expected_response)

    fill_response_brains.assert_called_once_with(
        'test_project_id', mock.ANY, mock_ds.list_brains.return_value[0],
        mock_ds)
    mock_ds.list_brains.assert_called_once_with('test_project_id', 4, mock.ANY)
    self.assertEqual(mock_ds.list_brains.call_args.args[2].page_token, '2')

  def test_fill_response_brains(self):
    mock_ds = mock.Mock()
    mock_ds.read_brain.side_effect = [
        ListBrainsHandlerTest._ds_brain(1),
        ListBrainsHandlerTest._ds_brain(2),
        ListBrainsHandlerTest._ds_brain(3),
        ListBrainsHandlerTest._ds_brain(4)]

    expected_response = falken_service_pb2.ListBrainsResponse(
        brains=[ListBrainsHandlerTest._brain(1),
                ListBrainsHandlerTest._brain(2),
                ListBrainsHandlerTest._brain(3),
                ListBrainsHandlerTest._brain(4)])

    response = falken_service_pb2.ListBrainsResponse()
    list_brains_handler._fill_response_brains(
        'test_project_id', response,
        ['brain_id_1', 'brain_id_2', 'brain_id_3', 'brain_id_4'],
        mock_ds)
    self.assertEqual(response, expected_response)

    mock_ds.read_brain.assert_has_calls([
        mock.call('test_project_id', 'brain_id_1'),
        mock.call('test_project_id', 'brain_id_2'),
        mock.call('test_project_id', 'brain_id_3'),
        mock.call('test_project_id', 'brain_id_4')])


if __name__ == '__main__':
  absltest.main()
