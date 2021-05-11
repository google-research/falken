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
"""Tests for get_session_handler."""
from unittest import mock

from absl.testing import absltest
from api import get_session_handler
from api import proto_conversion
from data_store import resource_id

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import session_pb2
import data_store_pb2
import falken_service_pb2
from google.rpc import code_pb2


class GetSessionHandlerTest(absltest.TestCase):

  def test_get_session_bad_request(self):
    mock_context = mock.Mock()
    mock_context.abort.side_effect = Exception()
    with self.assertRaises(Exception):
      get_session_handler.get_session(
          falken_service_pb2.GetSessionRequest(), mock_context, None)
    mock_context.abort.assert_called_once_with(
        code_pb2.INVALID_ARGUMENT,
        'Project ID, brain ID, and session ID must be specified in '
        'GetSessionRequest.')

  @mock.patch.object(get_session_handler, '_read_and_convert_session')
  def test_get_session(self, read_and_convert_session):
    mock_context = mock.Mock()
    mock_context.abort.side_effect = Exception()
    mock_ds = mock.Mock()
    read_and_convert_session.return_value = session_pb2.Session()

    self.assertEqual(
        get_session_handler.get_session(
            falken_service_pb2.GetSessionRequest(
                project_id='test_project_id',
                brain_id='test_brain_id',
                session_id='test_session_id'),
            mock_context, mock_ds),
        read_and_convert_session.return_value)

    mock_context.abort.assert_not_called()
    read_and_convert_session.assert_called_once_with(
        mock_ds, 'test_project_id', 'test_brain_id', 'test_session_id')

  def test_get_session_by_index_bad_request(self):
    mock_context = mock.Mock()
    mock_context.abort.side_effect = Exception()
    with self.assertRaises(Exception):
      get_session_handler.get_session_by_index(
          falken_service_pb2.GetSessionByIndexRequest(), mock_context, None)
    mock_context.abort.assert_called_once_with(
        code_pb2.INVALID_ARGUMENT,
        'Project ID, brain ID, and session index must be specified in '
        'GetSessionByIndexRequest.')

  def test_get_session_by_index_session_not_found(self):
    mock_context = mock.Mock()
    mock_context.abort.side_effect = Exception()
    mock_ds = mock.Mock()
    mock_ds.list.return_value = ([], None)

    with self.assertRaises(Exception):
      get_session_handler.get_session_by_index(
          falken_service_pb2.GetSessionByIndexRequest(
              project_id='test_project_id',
              brain_id='test_brain_id',
              session_index=20), mock_context, mock_ds)
    mock_context.abort.assert_called_once_with(
        code_pb2.INVALID_ARGUMENT,
        'Session at index 20 was not found.')
    mock_ds.list.assert_called_once_with(
        resource_id.FalkenResourceId(
            project='test_project_id',
            brain='test_brain_id',
            session='*'), page_size=21)

  @mock.patch.object(get_session_handler, '_read_and_convert_session')
  def test_get_session_by_index(self, read_and_convert_session):
    mock_context = mock.Mock()
    mock_context.abort.side_effect = Exception()
    mock_ds = mock.Mock()
    mock_ds.list.return_value = (
        ['test_session_id_0', 'test_session_id_1', 'test_session_id_2'], None)
    read_and_convert_session.return_value = session_pb2.Session()

    self.assertEqual(
        get_session_handler.get_session_by_index(
            falken_service_pb2.GetSessionByIndexRequest(
                project_id='test_project_id',
                brain_id='test_brain_id',
                session_index=2),
            mock_context, mock_ds),
        read_and_convert_session.return_value)

    mock_context.abort.assert_not_called()
    mock_ds.list.assert_called_once_with(
        resource_id.FalkenResourceId(
            project='test_project_id',
            brain='test_brain_id',
            session='*'), page_size=3)
    read_and_convert_session.assert_called_once_with(
        mock_ds, 'test_project_id', 'test_brain_id', 'test_session_id_2')

  @mock.patch.object(proto_conversion.ProtoConverter, 'convert_proto')
  def test_read_and_convert_session(self, convert_proto):
    mock_ds = mock.Mock()
    mock_ds.read.return_value = data_store_pb2.Session()
    convert_proto.return_value = session_pb2.Session()

    self.assertEqual(
        get_session_handler._read_and_convert_session(
            mock_ds, 'test_project_id', 'test_brain_id', 'test_session_id'),
        convert_proto.return_value)

    mock_ds.read.assert_called_once_with(
        resource_id.FalkenResourceId(
            project='test_project_id',
            brain='test_brain_id',
            session='test_session_id'))
    convert_proto.assert_called_once_with(mock_ds.read.return_value)


if __name__ == '__main__':
  absltest.main()
