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
"""Tests for proto_conversion."""

from absl.testing import absltest
from api import proto_conversion
from api import test_constants

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import brain_pb2
import data_store_pb2
from google.protobuf import text_format
from google.protobuf import timestamp_pb2


class ProtoConversionTest(absltest.TestCase):

  def test_convert_data_store_brain_proto_empty(self):
    data_store_brain = data_store_pb2.Brain()
    expected_common_brain = brain_pb2.Brain(
        brain_spec=brain_pb2.BrainSpec(),
        create_time=timestamp_pb2.Timestamp(seconds=0))
    self.assertEqual(
        proto_conversion.ProtoConverter.convert_data_store_proto(
            data_store_brain), expected_common_brain)

  def test_convert_data_store_brain_proto(self):
    brain_spec = text_format.Parse(test_constants.TEST_BRAIN_SPEC,
                                   brain_pb2.BrainSpec())
    data_store_brain = data_store_pb2.Brain(
        project_id='test_project',
        brain_id='test_brain_id',
        name='test_brain_name',
        created_micros=1619726720852543,
        brain_spec=brain_spec)
    expected_common_brain = brain_pb2.Brain(
        project_id=data_store_brain.project_id,
        brain_id=data_store_brain.brain_id,
        display_name=data_store_brain.name,
        brain_spec=brain_spec,
        create_time=timestamp_pb2.Timestamp(seconds=1619726720852543 //
                                            1000000))
    self.assertEqual(
        proto_conversion.ProtoConverter.convert_data_store_proto(
            data_store_brain), expected_common_brain)


if __name__ == '__main__':
  absltest.main()
