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
"""Tests for get_session_count_handler."""
from unittest import mock

from absl.testing import absltest
from api import get_session_count_handler
from data_store import resource_id

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import falken_service_pb2
from google.rpc import code_pb2


class GetSessionCountHandlerTest(absltest.TestCase):

  def test_get_session_count_bad_request(self):
    mock_context = mock.Mock()
    mock_context.abort.side_effect = Exception()
    with self.assertRaises(Exception):
      get_session_count_handler.get_session_count(
          falken_service_pb2.GetSessionRequest(), mock_context, None)
    mock_context.abort.assert_called_once_with(
        code_pb2.INVALID_ARGUMENT,
        'Project ID and brain ID must be specified in GetSessionCountRequest.')

  def test_get_session_count(self):
    mock_context = mock.Mock()
    mock_context.abort.side_effect = Exception()
    mock_ds = mock.Mock()
    mock_ds.list_by_proto_ids.return_value = (
        [resource_id.FalkenResourceId('projects/p0/brains/b0/sessions/s0'),
         resource_id.FalkenResourceId('projects/p0/brains/b0/sessions/s1'),
         resource_id.FalkenResourceId('projects/p0/brains/b0/sessions/s2')],
        None)

    self.assertEqual(
        get_session_count_handler.get_session_count(
            falken_service_pb2.GetSessionCountRequest(
                project_id='test_project_id',
                brain_id='test_brain_id'),
            mock_context, mock_ds),
        falken_service_pb2.GetSessionCountResponse(session_count=3))

    mock_context.abort.assert_not_called()
    mock_ds.list_by_proto_ids.assert_called_once_with(
        project_id='test_project_id', brain_id='test_brain_id', session_id='*')


if __name__ == '__main__':
  absltest.main()
