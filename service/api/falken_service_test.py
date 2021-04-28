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
# pylint: disable=g-bad-import-order
"""Tests for falken.service.api.falken_service."""
from concurrent import futures
import os
import os.path

from absl.testing import absltest
from absl import flags

from unittest import mock

import common.generate_protos

from api import falken_service
import falken_service_pb2
import falken_service_pb2_grpc
import grpc

FLAGS = flags.FLAGS


class FalkenServiceTest(absltest.TestCase):
  """Tests FalkenService."""

  def tearDown(self):
    """Tear down the testing environment."""
    super(FalkenServiceTest, self).tearDown()
    common.generate_protos.clean_up()

  @mock.patch.object(falken_service, 'read_server_credentials', autospec=True)
  def test_serve(self, read_credentials):
    """Test that Falken service can be started up and connected to."""
    FLAGS.port = 50051
    read_credentials.return_value = grpc.ssl_server_credentials(
        ((b'test_private_key', b'test_certificate_chain'),))
    real_server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    with mock.patch.object(grpc, 'server', autospec=True) as server:
      mock_server = mock.Mock()
      mock_server.add_generic_rpc_handlers.side_effect = (
          real_server.add_generic_rpc_handlers)
      mock_server.add_secure_port.side_effect = (
          lambda port, _: real_server.add_insecure_port(port))
      mock_server.start.side_effect = real_server.start
      server.return_value = mock_server
      falken_service.serve()

    with grpc.insecure_channel('localhost:50051') as channel:
      stub = falken_service_pb2_grpc.FalkenServiceStub(channel)
      with self.assertRaises(grpc._channel._InactiveRpcError) as e:  # pylint: disable=g-error-prone-assert-raises
        stub.CreateBrain(falken_service_pb2.CreateBrainRequest())
        self.assertIn('Method not implemented!', e.details())

    real_server.stop(None)

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


if __name__ == '__main__':
  absltest.main()
