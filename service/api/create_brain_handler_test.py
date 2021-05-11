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
"""Tests for create_brain_handler."""
import copy
import tempfile
from unittest import mock

from absl.testing import absltest
from api import create_brain_handler
from api import proto_conversion
from api import resource_id
from api import test_constants

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import brain_pb2
import data_store_pb2
import falken_service_pb2
from google.protobuf import text_format
from google.protobuf import timestamp_pb2
from google.rpc import code_pb2


class CreateBrainHandlerTest(absltest.TestCase):

  def setUp(self):
    """Create a file system object that uses a temporary directory."""
    super().setUp()
    self._temp_dir = tempfile.TemporaryDirectory()
    self._ds = mock.Mock()

  def tearDown(self):
    """Clean up the temporary directory for flatbuffers generation."""
    super().tearDown()
    self._temp_dir.cleanup()

  @mock.patch.object(proto_conversion.ProtoConverter,
                     'convert_proto')
  @mock.patch.object(resource_id, 'generate_resource_id')
  def test_valid_request(self, generate_resource_id, convert_proto):
    generate_resource_id.return_value = 'test_brain_uuid'
    request = falken_service_pb2.CreateBrainRequest(
        display_name='test_brain',
        brain_spec=text_format.Parse(test_constants.TEST_BRAIN_SPEC,
                                     brain_pb2.BrainSpec()),
        project_id='test_project')
    context = mock.Mock()
    write_brain = data_store_pb2.Brain(
        project_id=request.project_id,
        brain_id='test_brain_uuid',
        name=request.display_name,
        brain_spec=text_format.Parse(test_constants.TEST_BRAIN_SPEC,
                                     brain_pb2.BrainSpec()))
    data_store_brain = copy.copy(write_brain)
    data_store_brain.created_micros = 1619726720852543
    expected_brain = brain_pb2.Brain(
        project_id=request.project_id,
        brain_id='test_brain_uuid',
        display_name=request.display_name,
        brain_spec=text_format.Parse(test_constants.TEST_BRAIN_SPEC,
                                     brain_pb2.BrainSpec()),
        create_time=timestamp_pb2.Timestamp(seconds=1619726720))
    self._ds.read.return_value = (data_store_brain)
    convert_proto.return_value = expected_brain

    self.assertEqual(
        create_brain_handler.create_brain(request, context, self._ds),
        expected_brain)

    generate_resource_id.assert_called_once_with()
    self._ds.write.assert_called_once_with(write_brain)
    self.assertEqual(
        str(self._ds.read.call_args[0][0]),
        'projects/test_project/brains/test_brain_uuid')
    convert_proto.called_once_with(data_store_brain)

  def test_missing_brain_spec(self):
    request = falken_service_pb2.CreateBrainRequest(
        display_name='test_brain', brain_spec=None, project_id='test_project')
    context = mock.Mock()
    self.assertIsNone(
        create_brain_handler.create_brain(request, context, self._ds))
    context.abort.assert_called_with(
        code_pb2.INVALID_ARGUMENT,
        'Unable to create Brain. BrainSpec spec invalid. Error: '
        'InvalidSpecError(\'BrainSpec must have an observation spec and action '
        'spec.\')')


if __name__ == '__main__':
  absltest.main()
