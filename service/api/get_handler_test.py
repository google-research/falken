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
"""Tests for get_handler."""
import os.path
import tempfile
from unittest import mock
import zipfile

from absl.testing import absltest
from api import get_handler
from api import proto_conversion
from data_store import resource_id

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import brain_pb2
import session_pb2
import serialized_model_pb2
import data_store_pb2
import falken_service_pb2
from google.rpc import code_pb2


class GetHandlerTest(absltest.TestCase):

  def setUp(self):
    """Create a temporary directory with a zip file inside."""
    super().setUp()
    self._temporary_directories = []

  def tearDown(self):
    """Clean up all temporary directories."""
    super().tearDown()
    for t in self._temporary_directories:
      t.cleanup()

  @mock.patch.object(get_handler.GetHandler, '__init__')
  def test_get_handler_get_brain(self, get_handler_base):
    mock_request = mock.Mock()
    mock_context = mock.Mock()
    mock_ds = mock.Mock()
    get_handler.GetBrainHandler(mock_request, mock_context, mock_ds)
    get_handler_base.assert_called_once_with(
        mock_request, mock_context, mock_ds, ['project_id', 'brain_id'],
        'projects/{0}/brains/{1}')

  @mock.patch.object(get_handler.GetHandler, '__init__')
  def test_get_handler_get_session(self, get_handler_base):
    mock_request = mock.Mock()
    mock_context = mock.Mock()
    mock_ds = mock.Mock()
    get_handler.GetSessionHandler(mock_request, mock_context, mock_ds)
    get_handler_base.assert_called_once_with(
        mock_request, mock_context, mock_ds,
        ['project_id', 'brain_id', 'session_id'],
        'projects/{0}/brains/{1}/sessions/{2}')

  @mock.patch.object(get_handler.GetHandler, '__init__')
  def test_get_handler_get_session_by_index(self, get_handler_base):
    mock_request = mock.Mock()
    mock_context = mock.Mock()
    mock_ds = mock.Mock()
    get_handler.GetSessionByIndexHandler(mock_request, mock_context, mock_ds)
    get_handler_base.assert_called_once_with(
        mock_request, mock_context, mock_ds,
        ['project_id', 'brain_id'], 'projects/{0}/brains/{1}/sessions/*')

  def setup_compressed_model(self):
    """Create a temporary directory with a zip file inside.

    Returns:
      A string containing the path to the compressed model.
    """
    temp_dir = tempfile.TemporaryDirectory()
    self._temporary_directories.append(temp_dir)
    zip_path = os.path.join(temp_dir.name, 'model.zip')
    zip_contents = {
        'saved_model/a.txt': 'file 1 data',
        'saved_model/abc/b.txt': 'file 2 data',
        'saved_model/abc/': ''
    }
    with zipfile.ZipFile(zip_path, 'w') as zipped_file:
      for name, contents in zip_contents.items():
        zipped_file.writestr(name, contents)
    return zip_path

  def test_get_handler_get_model(self):
    zip_path = self.setup_compressed_model()
    request = falken_service_pb2.GetModelRequest(
        project_id='p0', brain_id='b0', model_id='m0')
    mock_context = mock.Mock()
    mock_ds = mock.Mock()
    model_handler = get_handler.GetModelHandler(request, mock_context, mock_ds)
    self.assertEqual(model_handler._request_args,
                     ['project_id', 'brain_id', 'model_id'])
    self.assertEqual(model_handler._glob_pattern,
                     'projects/{0}/brains/{1}/sessions/*/models/{2}')

    mock_ds.list.return_value = ([
        resource_id.FalkenResourceId(
            'projects/p0/brains/b0/sessions/s0/models/m0')], None)
    mock_ds.read.return_value = data_store_pb2.Model(
        compressed_model_path=zip_path)
    self.assertEqual(
        model_handler.get(), falken_service_pb2.Model(
            model_id='m0',
            serialized_model=serialized_model_pb2.SerializedModel(
                packed_files_payload=serialized_model_pb2.PackedFiles(
                    files={'a.txt': b'file 1 data', 'abc/b.txt': b'file 2 data'}
                    ))))

    mock_ds.list.assert_called_once_with(resource_id.FalkenResourceId(
        'projects/p0/brains/b0/sessions/*/models/m0'), page_size=2)
    mock_ds.read.assert_called_once_with(
        resource_id.FalkenResourceId(
            'projects/p0/brains/b0/sessions/s0/models/m0'))

  def test_get_handler_get_model_snapshot_specified_both(self):
    request = falken_service_pb2.GetModelRequest(
        snapshot_id='s0', model_id='m0')
    mock_context = mock.Mock()
    mock_context.abort.side_effect = Exception()
    mock_ds = mock.Mock()
    with self.assertRaises(Exception):
      get_handler.GetModelHandler(request, mock_context, mock_ds)
    mock_context.abort.assert_called_once_with(
        code_pb2.INVALID_ARGUMENT,
        'Either model ID or snapshot ID should be specified, not both. '
        'Found snapshot_id s0 and model_id m0.')

  def test_get_handler_get_model_snapshot(self):
    zip_path = self.setup_compressed_model()
    request = falken_service_pb2.GetModelRequest(
        project_id='p0', brain_id='b0', snapshot_id='s0')
    mock_context = mock.Mock()
    mock_ds = mock.Mock()
    model_handler = get_handler.GetModelHandler(request, mock_context, mock_ds)
    self.assertEqual(model_handler._request_args,
                     ['project_id', 'brain_id', 'snapshot_id'])
    self.assertEqual(model_handler._glob_pattern,
                     'projects/{0}/brains/{1}/snapshots/{2}')

    mock_ds.read.side_effect = [
        data_store_pb2.Snapshot(
            project_id='p0', brain_id='b0', session='s0', model='m0'),
        data_store_pb2.Model(compressed_model_path=zip_path)
    ]
    mock_ds.list.return_value = [
        resource_id.FalkenResourceId(
            'projects/p0/brains/b0/sessions/s0/models/m0')], None

    self.assertEqual(
        model_handler.get(), falken_service_pb2.Model(
            model_id='m0',
            serialized_model=serialized_model_pb2.SerializedModel(
                packed_files_payload=serialized_model_pb2.PackedFiles(
                    files={'a.txt': b'file 1 data', 'abc/b.txt': b'file 2 data'}
                    ))))

    mock_ds.read.assert_has_calls([
        mock.call(
            resource_id.FalkenResourceId('projects/p0/brains/b0/snapshots/s0')),
        mock.call(
            resource_id.FalkenResourceId(
                'projects/p0/brains/b0/sessions/s0/models/m0'))
    ])

  def test_get_missing_request_args(self):
    mock_context = mock.Mock()
    mock_context.abort.side_effect = Exception()
    request = falken_service_pb2.GetBrainRequest()
    with self.assertRaises(Exception):
      get_handler.GetBrainHandler(
          request, mock_context, mock.Mock()).get()
    mock_context.abort.assert_called_once_with(
        code_pb2.INVALID_ARGUMENT,
        'Could not find project_id in '
        '<class \'falken_service_pb2.GetBrainRequest\'>.')

  @mock.patch.object(get_handler.GetHandler, '_read_and_convert_proto')
  def test_get(self, read_and_convert_proto):
    mock_context = mock.Mock()
    mock_context.abort.side_effect = Exception()
    request = falken_service_pb2.GetBrainRequest(
        project_id='p0', brain_id='b0')
    read_and_convert_proto.return_value = mock.Mock()

    self.assertEqual(
        get_handler.GetBrainHandler(request, mock_context, mock.Mock()).get(),
        read_and_convert_proto.return_value)

    mock_context.abort.assert_not_called()
    read_and_convert_proto.assert_called_once_with(
        resource_id.FalkenResourceId('projects/p0/brains/b0'))

  def test_get_session_by_index_bad_request(self):
    mock_context = mock.Mock()
    mock_context.abort.side_effect = Exception()
    with self.assertRaises(Exception):
      get_handler.GetSessionByIndexHandler(
          falken_service_pb2.GetSessionByIndexRequest(),
          mock_context, None).get()
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
      get_handler.GetSessionByIndexHandler(
          falken_service_pb2.GetSessionByIndexRequest(
              project_id='test_project_id',
              brain_id='test_brain_id',
              session_index=20), mock_context, mock_ds).get()
    mock_context.abort.assert_called_once_with(
        code_pb2.INVALID_ARGUMENT,
        'Session at index 20 was not found.')
    mock_ds.list.assert_called_once_with(
        resource_id.FalkenResourceId(
            'projects/test_project_id/brains/test_brain_id/sessions/*'),
        page_size=21)

  @mock.patch.object(get_handler.GetHandler, '_read_and_convert_proto')
  def test_get_session_by_index(self, read_and_convert_proto):
    mock_context = mock.Mock()
    mock_context.abort.side_effect = Exception()
    mock_ds = mock.Mock()
    brain_res_id = 'projects/test_project_id/brains/test_brain_id'
    mock_ds.list.return_value = ([
        resource_id.FalkenResourceId(
            f'{brain_res_id}/sessions/test_session_id_0'),
        resource_id.FalkenResourceId(
            f'{brain_res_id}/sessions/test_session_id_1'),
        resource_id.FalkenResourceId(
            f'{brain_res_id}/sessions/test_session_id_2')], None)
    read_and_convert_proto.return_value = session_pb2.Session()

    self.assertEqual(
        get_handler.GetSessionByIndexHandler(
            falken_service_pb2.GetSessionByIndexRequest(
                project_id='test_project_id',
                brain_id='test_brain_id',
                session_index=2),
            mock_context, mock_ds).get(),
        read_and_convert_proto.return_value)

    mock_context.abort.assert_not_called()
    mock_ds.list.assert_called_once_with(
        resource_id.FalkenResourceId(
            'projects/test_project_id/brains/test_brain_id/sessions/*'),
        page_size=3)
    read_and_convert_proto.assert_called_once_with(
        resource_id.FalkenResourceId(
            'projects/test_project_id/brains/test_brain_id/sessions/'
            'test_session_id_2'))

  @mock.patch.object(proto_conversion.ProtoConverter, 'convert_proto')
  def test_read_and_convert_session(self, convert_proto):
    mock_ds = mock.Mock()
    mock_ds.read.return_value = data_store_pb2.Brain()
    convert_proto.return_value = brain_pb2.Brain()

    request = falken_service_pb2.GetBrainRequest(
        project_id='p0', brain_id='b0')
    res_id = resource_id.FalkenResourceId('projects/p0/brains/b0')

    self.assertEqual(
        get_handler.GetBrainHandler(
            request, mock.Mock(), mock_ds)._read_and_convert_proto(res_id),
        convert_proto.return_value)

    mock_ds.read.assert_called_once_with(res_id)
    convert_proto.assert_called_once_with(mock_ds.read.return_value)

if __name__ == '__main__':
  absltest.main()
