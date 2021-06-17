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

from learner.brains import data_protobuf_converter
from learner.brains import specs
import tensorflow as tf
from tf_agents.specs import tensor_spec

import common.generate_protos  # pylint: disable=unused-import
import action_pb2
import observation_pb2
import primitives_pb2


class TfAgentsSpecBaseMixIn:
  """Mix-in for specs.SpecBase that converts to TF-Agents specs and numpy."""

  def __init__(self):
    """Create TF-Agents and proto spec nests."""
    # Nested dictionary of TF Agents TensorSpec instances generated from the
    # proto spec.
    self._tf_agents_spec_nest = tf.nest.map_structure(
        lambda node: ProtobufNodeTfaSpecConverter(node).to_tfa_tensor_spec(),
        self._node_nest)
    # Nested dictionary of protos.
    self._proto_spec_nest = tf.nest.map_structure(
        lambda node: node.proto, self._node_nest)

  @property
  def tfa_spec(self):
    """Returns a nested dictionary of TF Agents TensorSpec instances."""
    return self._tf_agents_spec_nest

  @property
  def spec_nest(self):
    """Returns the proto as a proto spec nest."""
    return self._proto_spec_nest

  def tfa_value(self, data):
    """Converts ActionData or ObservationData from protobuf to TF Agents format.

    Args:
      data: ActionData or ObservationData proto.

    Returns:
      The data formatted as a dictionary of dictionaries of numpy arrays.
    """
    return next(iter(self._spec_proto_node.data_to_proto_nest(
        data,
        mapper=data_protobuf_converter.DataProtobufConverter.leaf_to_tensor,
        options=specs.ProtobufDataValidationOptions(
            check_feeler_data_with_spec=False)).values()))


class SpecBase(specs.SpecBase, TfAgentsSpecBaseMixIn):
  """SpecBase that converts to TF-Agents specs and numpy arrays."""
  pass


class BrainSpec(specs.BrainSpec):
  """BrainSpec that converst to TF-Agents specs and numpy arrays."""

  def __init__(self, brain_spec_pb):
    """Parse and validate the provided spec proto.

    Args:
      brain_spec_pb: BrainSpec protobuf to parse and validate.
    """
    super().__init__(brain_spec_pb, spec_base_class=SpecBase,
                     action_spec_class=ActionSpec,
                     observation_spec_class=ObservationSpec)


class ActionSpec(specs.ActionSpec, TfAgentsSpecBaseMixIn):
  """ActionSpec that converts to TF-Agents specs and numpy arrays."""
  pass


class ObservationSpec(specs.ObservationSpec, TfAgentsSpecBaseMixIn):
  """ObservationSpec that converts to TF-Agents specs and numpy arrays."""
  pass
 

class ProtobufNodeTfaSpecConverter:
  """Converts from a spec protobuf to TF-Agents spec."""

  def __init__(self,  protobuf_node):
    """Initialize with a ProtobufNode to convert from.

    Args:
      protobuf_node: ProtobufNode that references a spec proto to convert.
    """
    self._protobuf_node = protobuf_node

  def _category_type_to_tfa_tensor_spec(self):
    """Convert a CategoryType node to a TF Agents BoundedTensorSpec.

    Returns:
      BoundedTensorSpec instance.
    """
    return tensor_spec.BoundedTensorSpec(
        (1,), tf.int32, 0, len(self._protobuf_node.proto.enum_values) - 1,
        name=self._protobuf_node.name)

  def _number_type_to_tfa_tensor_spec(self):
    """Convert a NumberType node to a TF Agents BoundedTensorSpec.

    Returns:
      BoundedTensorSpec instance.
    """
    return tensor_spec.BoundedTensorSpec(
        (1,), tf.float32, self._protobuf_node.proto.minimum,
       self._protobuf_node.proto.maximum, name=self._protobuf_node.name)

  def _position_type_to_tfa_tensor_spec(self):
    """Convert a PositionType node to a TF Agents TensorSpec.

    Returns:
      TensorSpec instance.
    """
    return tensor_spec.TensorSpec((3,), tf.float32,
                                  name=self._protobuf_node.name)

  def _rotation_type_to_tfa_tensor_spec(self):
    """Convert a RotationType node to a TF Agents TensorSpec.

    Returns:
      TensorSpec instance.
    """
    return tensor_spec.TensorSpec((4,), tf.float32,
                                  name=self._protobuf_node.name)

  def _feeler_type_to_tfa_tensor_spec(self):
    """Convert a FeelerType node to a TF Agents BoundedTensorSpec.

    Returns:
      BoundedTensorSpec instance.
    """
    return tensor_spec.BoundedTensorSpec(
        (self._protobuf_node.proto.count,
        (1 + len(self._protobuf_node.proto.experimental_data)),),
        tf.float32, minimum=self._protobuf_node.proto.distance.minimum,
        maximum=self._protobuf_node.proto.distance.maximum,
        name=self._protobuf_node.name)

  def _joystick_type_to_tfa_tensor_spec(self):
    """Convert a JoystickType node to a TF Agents BoundedTensorSpec.

    Returns:
      BoundedTensorSpec instance.
    """
    return tensor_spec.BoundedTensorSpec(
        (2,), tf.float32, name=self._protobuf_node.name, minimum=-1, maximum=1)

  def to_tfa_tensor_spec(self):
    """Returns a TF Agents TensorSpec instance for a leaf node.

    Returns:
      TensorSpec instance determined by node.

    Raises:
      InvalidSpecError: If the node is not a leaf node.
    """
    proto_class_to_converter = {
        primitives_pb2.CategoryType: self._category_type_to_tfa_tensor_spec,
        primitives_pb2.NumberType: self._number_type_to_tfa_tensor_spec,
        primitives_pb2.PositionType: self._position_type_to_tfa_tensor_spec,
        primitives_pb2.RotationType: self._rotation_type_to_tfa_tensor_spec,
        observation_pb2.FeelerType: self._feeler_type_to_tfa_tensor_spec,
        action_pb2.JoystickType: self._joystick_type_to_tfa_tensor_spec
    }
    converter = proto_class_to_converter.get(type(self._protobuf_node.proto))
    if not converter:
      raise specs.InvalidSpecError(
          f'Unable to convert {type(self._protobuf_node.proto).__qualname__} '
          f'at "{self._protobuf_node.path}" to TensorSpec.')
    return converter()
