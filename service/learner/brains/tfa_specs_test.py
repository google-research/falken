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
from google.protobuf import text_format
from learner.brains import specs
from learner.brains import specs_test
from learner.brains import tfa_specs
import numpy as np
import tensorflow as tf
from tf_agents.specs import tensor_spec

import common.generate_protos  # pylint: disable=unused-import
import action_pb2
import brain_pb2
import observation_pb2
import primitives_pb2


class ProtobufNodeTfaSpecConverterTest(absltest.TestCase):

  def test_to_tfa_tensor_spec_invalid_type(self):
    """Ensure TensorSpec conversion from an invalid ProtobufNode fails."""
    node = tfa_specs.ProtobufNodeTfaSpecConverter(
        specs.ProtobufNode('invalid', action_pb2.ActionSpec(), ''))
    with self.assertRaisesWithLiteralMatch(
        specs.InvalidSpecError,
        'Unable to convert ActionSpec at "invalid" to TensorSpec.'):
      node.to_tfa_tensor_spec()

  def test_category_type_to_tfa_tensor_spec(self):
    """Test conversion from CategoryType ProtobufNode to BoundedTensorSpec."""
    spec = primitives_pb2.CategoryType()
    spec.enum_values.extend(['foo', 'bar', 'baz'])
    node = tfa_specs.ProtobufNodeTfaSpecConverter(
        specs.ProtobufNode('test', spec, ''))
    self.assertEqual(node.to_tfa_tensor_spec(),
                     tensor_spec.BoundedTensorSpec((1,), tf.int32, 0, 2,
                                                   name='test'))

  def test_number_type_to_tfa_tensor_spec(self):
    """Test conversion from NumberType ProtobufNode to BoundedTensorSpec."""
    spec = primitives_pb2.NumberType()
    spec.minimum = 1
    spec.maximum = 10
    node = tfa_specs.ProtobufNodeTfaSpecConverter(
        specs.ProtobufNode('test', spec, ''))
    self.assertEqual(node.to_tfa_tensor_spec(),
                     tensor_spec.BoundedTensorSpec((1,), tf.float32, 1, 10,
                                                   name='test'))

  def test_position_type_to_tfa_tensor_spec(self):
    """Test conversion from PositionType ProtobufNode to BoundedTensorSpec."""
    node = tfa_specs.ProtobufNodeTfaSpecConverter(
        specs.ProtobufNode('test', primitives_pb2.PositionType(), ''))
    self.assertEqual(node.to_tfa_tensor_spec(),
                     tensor_spec.TensorSpec((3,), tf.float32, name='test'))

  def test_rotation_type_to_tfa_tensor_spec(self):
    """Test conversion from RotationType ProtobufNode to BoundedTensorSpec."""
    node = tfa_specs.ProtobufNodeTfaSpecConverter(
        specs.ProtobufNode('test', primitives_pb2.RotationType(), ''))
    self.assertEqual(node.to_tfa_tensor_spec(),
                     tensor_spec.TensorSpec((4,), tf.float32, name='test'))

  def test_feeler_type_to_tfa_tensor_spec(self):
    """Test conversion from FeelerType ProtobufNode to BoundedTensorSpec."""
    spec = observation_pb2.FeelerType()
    spec.count = 2
    spec.distance.minimum = 10
    spec.distance.maximum = 100
    data = spec.experimental_data.add()
    data.minimum = 1
    data.maximum = 2
    data = spec.experimental_data.add()
    data.minimum = 3
    data.maximum = 4
    node = tfa_specs.ProtobufNodeTfaSpecConverter(
        specs.ProtobufNode('test', spec, ''))
    self.assertEqual(node.to_tfa_tensor_spec(),
                     tensor_spec.BoundedTensorSpec(
                         (2, 3,), tf.float32, minimum=10, maximum=100,
                         name='test'))

  def test_joystick_type_to_tfa_tensor_spec(self):
    """Test conversion from JoystickType ProtobufNode to BoundedTensorSpec."""
    node = tfa_specs.ProtobufNodeTfaSpecConverter(
        specs.ProtobufNode('test', action_pb2.JoystickType(), ''))
    self.assertEqual(node.to_tfa_tensor_spec(),
                     tensor_spec.BoundedTensorSpec(
                         (2,), tf.float32, minimum=-1, maximum=1, name='test'))


class TfAgentsSpecBaseMixInTest(absltest.TestCase):

  def test_spec_base_get_proto_nest(self):
    """Test accessing a nest of spec protos from a SpecBase."""
    spec = observation_pb2.ObservationSpec()
    spec.player.position.CopyFrom(primitives_pb2.PositionType())
    nest = tfa_specs.SpecBase(spec).spec_nest
    want = {'player': {'position': spec.player.position}}
    self.assertEqual(want, nest)

  def test_spec_base_get_tfa_spec(self):
    """Convert from a spec proto to TF Agents TensorSpec nest."""
    spec = observation_pb2.ObservationSpec()
    spec.player.position.CopyFrom(primitives_pb2.PositionType())
    nest = tfa_specs.SpecBase(spec).tfa_spec
    expected_position_spec = tensor_spec.TensorSpec(
        shape=(3,), dtype=tf.float32, name='position')
    want = {'player': {'position': expected_position_spec}}
    self.assertEqual(want, nest)

  def test_observation_data_to_nest(self):
    """Tests conversion from an ObservationData to a tf-agents nest."""
    observation_spec = observation_pb2.ObservationSpec()
    text_format.Parse(specs_test._OBSERVATION_SPEC, observation_spec)
    observation_data = observation_pb2.ObservationData()
    text_format.Parse(specs_test._OBSERVATION_DATA, observation_data)
    value = tfa_specs.ObservationSpec(observation_spec).tfa_value(
        observation_data)
    want = {
        'global_entities': {
            '0': {'rotation': np.array([0.0, 0.0, 0.0, 1.0]),
                  'pizzazz': np.array([64.])},
            '1': {'chutzpah': np.array([34.])}
        },
        'player': {
            'position': np.array([0., 10., 20.]),
            'rotation': np.array([0., 0., 0., 1.0]),
            'panache': np.array([60.]),
            'favorite_poison': np.array([1], dtype=np.int32),
            'feeler': np.array([
                [1.0, 1.1],
                [2.0, 2.1],
                [3.0, 3.1]], dtype=np.float32)
        },
        'camera': {
            'position': np.array([10., 10., 10.]),
            'rotation': np.array([0., 0., 0., 1.0]),
        }
    }
    tf.nest.assert_same_structure(value, want, expand_composites=True)

    # Round floats and convert to list.
    value = tf.nest.map_structure(lambda x: x.round(2).tolist(), value)
    want = tf.nest.map_structure(lambda x: x.round(2).tolist(), want)
    self.assertEqual(value, want)

  def test_action_data_to_nest(self):
    """Tests conversion from an ActionData to a tf-agents nest."""
    action_spec = action_pb2.ActionSpec()
    text_format.Parse(specs_test._ACTION_SPEC, action_spec)
    action_data = action_pb2.ActionData()
    text_format.Parse(specs_test._ACTION_DATA, action_data)
    value = tfa_specs.ActionSpec(action_spec).tfa_value(action_data)
    # Convert np arrays to list to allow comparison with want.
    value = tf.nest.map_structure(list, value)
    want = {
        'trouble': [1500.0],
        'what_do': [1],
        'left_stick': [0.0, 1.0],
        'right_stick': [-1.0, 0.0]
    }
    self.assertEqual(want, value)




if __name__ == '__main__':
  absltest.main()
