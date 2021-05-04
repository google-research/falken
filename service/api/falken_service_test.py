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
"""Tests for falken.service.api.falken_service."""

import os
import os.path
import tempfile
from unittest import mock

from absl import flags
from absl.testing import absltest
from api import falken_service
from api import resource_id
from api import test_constants

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import brain_pb2
from data_store import data_store
import data_store_pb2
import falken_service_pb2
import falken_service_pb2_grpc
from google.protobuf import text_format
from google.rpc import code_pb2
import grpc


FLAGS = flags.FLAGS


class FalkenServiceTest(absltest.TestCase):
  """Tests FalkenService."""

  def setUp(self):
    """Create a file system object that uses a temporary directory."""
    super().setUp()
    self._temp_dir = tempfile.TemporaryDirectory()
    FLAGS.root_dir = os.path.join(self._temp_dir.name, 'test')

  def tearDown(self):
    """Tear down the testing environment."""
    super().tearDown()
    common.generate_protos.clean_up()
    self._temp_dir.cleanup()

  def test_configure_server(self):
    """Test server configuration with a port and credentials."""
    credentials = grpc.ssl_server_credentials(
        ((b'test_private_key', b'test_certificate_chain'),))
    server = mock.Mock()
    falken_service._configure_server(server, 12345, credentials)
    server.add_secure_port.assert_called_with('[::]:12345', credentials)

  @mock.patch.object(falken_service, 'read_server_credentials', autospec=True)
  @mock.patch.object(falken_service, '_configure_server', autospec=True)
  @mock.patch.object(falken_service.FalkenService, '_create_api_keys')
  @mock.patch.object(falken_service.FalkenService,
                     '_validate_project_and_api_key')
  def test_serve(self, unused_validate_project_and_api_key,
                 unused_mock_create_api_keys, mock_configure_server,
                 mock_read_credentials):
    """Test that Falken service can be started up and connected to."""
    FLAGS.port = 50051
    ssl_credentials = grpc.ssl_server_credentials(
        ((b'test_private_key', b'test_certificate_chain'),))
    mock_read_credentials.return_value = ssl_credentials
    mock_configure_server.side_effect = (
        lambda server, port, _: server.add_insecure_port(f'[::]:{port}'))
    server = falken_service.serve()

    mock_configure_server.assert_called_with(
        server, 50051, ssl_credentials)

    response = None
    with grpc.insecure_channel('localhost:50051') as channel:
      stub = falken_service_pb2_grpc.FalkenServiceStub(channel)
      response = stub.CreateBrain(
          falken_service_pb2.CreateBrainRequest(
              project_id='test_project',
              display_name='test_brain',
              brain_spec=text_format.Parse(test_constants.TEST_BRAIN_SPEC,
                                           brain_pb2.BrainSpec())))
    self.assertIsNotNone(response.brain_id)
    self.assertEqual(response.project_id, 'test_project')
    self.assertEqual(response.display_name, 'test_brain')
    self.assertEqual(
        response.brain_spec,
        text_format.Parse(test_constants.TEST_BRAIN_SPEC,
                          brain_pb2.BrainSpec()))
    server.stop(None)

  def test_read_server_credentials(self):
    """Test read_server_credentials."""
    test_private_key = b'test_private_key'
    test_certificate_chain = b'test_certificate_chain'
    with open(os.path.join(FLAGS.test_tmpdir, 'key.pem'), 'wb') as f:
      f.write(test_private_key)
    with open(os.path.join(FLAGS.test_tmpdir, 'cert.pem'), 'wb') as f:
      f.write(test_certificate_chain)
    FLAGS.ssl_dir = FLAGS.test_tmpdir
    self.assertEqual(
        hash(falken_service.read_server_credentials()),
        hash(
            grpc.ssl_server_credentials(
                ((test_private_key, test_certificate_chain),))))

  @mock.patch.object(resource_id, 'generate_base64_id')
  @mock.patch.object(data_store, 'DataStore')
  def test_create_api_keys(self, datastore, generate_base64_id):
    """Test creation of API keys for project_ids specified in FLAGS."""
    mock_ds = mock.Mock()
    datastore.return_value = mock_ds
    generate_base64_id.return_value = 'api_key'
    FLAGS.project_ids = ['project_id_1', 'project_id_2']
    expected_write_project_calls = [
        mock.call(
            data_store_pb2.Project(
                project_id='project_id_1',
                name='project_id_1',
                api_key='api_key')),
        mock.call(
            data_store_pb2.Project(
                project_id='project_id_2',
                name='project_id_2',
                api_key='api_key')),
    ]
    falken_service.FalkenService()
    self.assertEqual(generate_base64_id.call_count, 2)
    self.assertCountEqual(mock_ds.write_project.call_args_list,
                          expected_write_project_calls)

  @mock.patch.object(falken_service.FalkenService, '_create_api_keys')
  @mock.patch.object(data_store, 'DataStore')
  def test_validate_project_and_api_key(self, ds, unused_create_api_keys):
    """Test validation of project and api key."""
    request = mock.Mock()
    request.project_id = 'test_project_id'
    context = mock.Mock()
    context.invocation_metadata.return_value = [
        (falken_service._API_METADATA_KEY, 'test_api_key')
    ]
    datastore = mock.Mock()
    datastore.read_project.return_value = data_store_pb2.Project(
        project_id='test_project_id', api_key='test_api_key')
    ds.return_value = datastore

    falken_service.FalkenService()._validate_project_and_api_key(
        request, context)
    ds.read_project.called_once_with('test_project_id')
    context.abort.assert_not_called()

  @mock.patch.object(falken_service.FalkenService, '_create_api_keys')
  @mock.patch.object(data_store, 'DataStore')
  def test_validate_project_and_no_api_key(
      self, unused_ds, unused_create_api_keys):
    """Test validation of project and api key when api key is not set."""
    context = mock.Mock()
    context.invocation_metadata.return_value = []
    falken_service.FalkenService()._validate_project_and_api_key(
        mock.Mock(), context)
    context.abort.assert_called_with(code_pb2.UNAUTHENTICATED,
                                     'No API key found in the metadata.')

  @mock.patch.object(falken_service.FalkenService, '_create_api_keys')
  @mock.patch.object(data_store, 'DataStore')
  def test_validate_project_and_no_project_id(
      self, unused_ds, unused_create_api_keys):
    """Test validation of project and api key when project ID is not set."""
    context = mock.Mock()
    context.invocation_metadata.return_value = [
        (falken_service._API_METADATA_KEY, 'test_api_key')
    ]
    request = mock.Mock()
    request.project_id = ''
    falken_service.FalkenService()._validate_project_and_api_key(
        request, context)
    context.abort.assert_called_with(code_pb2.UNAUTHENTICATED,
                                     'No project ID set in the request.')

  @mock.patch.object(falken_service.FalkenService, '_create_api_keys')
  @mock.patch.object(data_store, 'DataStore')
  def test_validate_unmatching_project_id_and_api_key(
      self, ds, unused_create_api_keys):
    """Test validation of project and api key when api key does not match."""
    context = mock.Mock()
    context.invocation_metadata.return_value = [
        (falken_service._API_METADATA_KEY, 'test_api_key')
    ]
    request = mock.Mock()
    request.project_id = 'test_project_id'
    datastore = mock.Mock()
    datastore.read_project.return_value = data_store_pb2.Project(
        project_id='test_project_id', api_key='different_api_key')
    ds.return_value = datastore

    falken_service.FalkenService()._validate_project_and_api_key(
        request, context)
    context.abort.assert_called_with(
        code_pb2.UNAUTHENTICATED,
        'Project ID test_project_id and API key test_api_key does not match. '
        'Found different_api_key instead.')
    ds.read_project.called_once_with('test_project_id')


if __name__ == '__main__':
  absltest.main()
