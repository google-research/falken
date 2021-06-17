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

from absl.testing import absltest
from learner.brains import data_protobuf_converter

import common.generate_protos  # pylint: disable=unused-import
import action_pb2
import observation_pb2
import primitives_pb2


class DataProtobufConverterTest(absltest.TestCase):
  """Test data_protobuf_converter.ProtobufConverter."""

  def test_unknown_to_tensor(self):
    """Convert an unsupported proto to a tensor."""
    with self.assertRaisesWithLiteralMatch(
        data_protobuf_converter.ConversionError,
        'Failed to convert observations () to a tensor.'):
      data_protobuf_converter.DataProtobufConverter.leaf_to_tensor(
          observation_pb2.ObservationData(), 'observations')

  def test_category_to_tensor(self):
    """Convert Category proto to tensor."""
    data = primitives_pb2.Category()
    data.value = 42
    self.assertCountEqual(
        data_protobuf_converter.DataProtobufConverter.leaf_to_tensor(
            data, 'category'), [42])

  def test_number_to_tensor(self):
    """Convert Number proto to tensor."""
    data = primitives_pb2.Number()
    data.value = 3.0
    self.assertCountEqual(
        data_protobuf_converter.DataProtobufConverter.leaf_to_tensor(
            data, 'number'), [3.0])

  def test_position_to_tensor(self):
    """Convert Position proto to tensor."""
    data = primitives_pb2.Position()
    data.x = 1.0
    data.y = 2.5
    data.z = 3.5
    self.assertCountEqual(
        data_protobuf_converter.DataProtobufConverter.leaf_to_tensor(
            data, 'position'),
        [1.0, 2.5, 3.5])

  def test_rotation_to_tensor(self):
    """Convert Rotation proto to tensor."""
    data = primitives_pb2.Rotation()
    data.x = 1.0
    data.y = -1.0
    data.z = 2.0
    data.w = 5.0
    self.assertCountEqual(
        data_protobuf_converter.DataProtobufConverter.leaf_to_tensor(
            data, 'rotation'),
        [1.0, -1.0, 2.0, 5.0])


if __name__ == '__main__':
  absltest.main()
