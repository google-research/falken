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
      get_session_handler.GetSession(
          falken_service_pb2.GetSessionRequest(), mock_context, None)
    mock_context.abort.assert_called_once_with(
        code_pb2.INVALID_ARGUMENT,
        'Project ID, brain ID, session ID must be specified in '
        'GetSessionRequest.')

  @mock.patch.object(proto_conversion.ProtoConverter, 'convert_proto')
  def test_get_session(self, convert_proto):
    mock_context = mock.Mock()
    mock_context.abort.side_effect = Exception()
    mock_ds = mock.Mock()
    mock_ds.read_session.return_value = data_store_pb2.Session()
    convert_proto.return_value = session_pb2.Session()

    self.assertEqual(
        get_session_handler.GetSession(
            falken_service_pb2.GetSessionRequest(
                project_id='test_project_id',
                brain_id='test_brain_id',
                session_id='test_session_id'),
            mock_context, mock_ds),
        convert_proto.return_value)

    mock_context.abort.assert_not_called()
    mock_ds.read_session.assert_called_once_with(
        'test_project_id', 'test_brain_id', 'test_session_id')
    convert_proto.assert_called_once_with(mock_ds.read_session.return_value)


if __name__ == '__main__':
  absltest.main()
