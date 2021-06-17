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

import random

import common.generate_protos  # pylint: disable=unused-import

import action_pb2
import observation_pb2
import primitives_pb2


class DataProtobufGenerator:
  """Generates a data proto from an observation or action spec."""

  # Lazily initialized in from_spec().
  _SPEC_PROTO_CLASS_TO_CREATE_ADD_METHODS = None
  # Lazily initialized in randomize_leaf_data_proto().
  _DATA_PROTO_CLASS_TO_RANDOMIZE_METHOD = None

  # Used by _add_to_action_data_proto() and
  # _add_to_entity_proto() to map a data leaf proto to a field name.
  _LEAF_DATA_PROTO_CLASS_TO_FIELD_NAME = {
      primitives_pb2.Category: 'category',
      primitives_pb2.Number: 'number',
      action_pb2.Joystick: 'joystick',
      observation_pb2.Feeler: 'feeler',
  }

  _ENTITY_DATA_PROTO_CLASS_TO_FIELD_NAME = {
      primitives_pb2.Position: 'position',
      primitives_pb2.Rotation: 'rotation',
  }

  @staticmethod
  def _create_action_data_proto(unused_spec_proto):
    """Create an instance of the ActionData proto.

     Args:
       unused_spec_proto: Unused.

    Returns:
      ActionData proto instance with the action source initialized to
      HUMAN_DEMONSTRATION so that valid training data is generated.
    """
    action_data = action_pb2.ActionData()
    action_data.source = action_pb2.ActionData.ActionSource.HUMAN_DEMONSTRATION
    return action_data

  @staticmethod
  def _add_to_action_data_proto(data_proto, child_data_proto, unused_node):
    """Add a child message to an ActionData proto.

    Args:
      data_proto: ActionData proto to add child message to.
      child_data_proto: Child message to add to data_proto.
      unused_node: Unused.
    """
    action = data_proto.actions.add()
    child_data_proto_type = type(child_data_proto)
    field_name = DataProtobufGenerator._LEAF_DATA_PROTO_CLASS_TO_FIELD_NAME.get(
        child_data_proto_type)
    assert field_name, f'Unsupported action data type {child_data_proto_type}'
    getattr(action, field_name).CopyFrom(child_data_proto)

  @staticmethod
  def _create_category_proto(unused_spec_proto):
    """Create an instance of the Category proto.

     Args:
       unused_spec_proto: Unused.

    Returns:
      Category proto instance with a value of 0.
    """
    category = primitives_pb2.Category()
    category.value = 0
    return category

  @staticmethod
  def _create_number_proto(spec_proto):
    """Create an instance of the Number proto from the provided spec.

    Args:
      spec_proto: NumberType spec proto.

    Returns:
      Number proto instance set to the minimum value in the spec.
    """
    number = primitives_pb2.Number()
    number.value = spec_proto.minimum
    return number

  @staticmethod
  def _create_joystick_proto(unused_spec_proto):
    """Create an instance of the Joystick proto.

     Args:
       unused_spec_proto: Unused.

    Returns:
      Joystick proto with a neutral (origin) position.
    """
    joystick = action_pb2.Joystick()
    joystick.x_axis = 0.0
    joystick.y_axis = 0.0
    return joystick

  @staticmethod
  def _create_position_proto(unused_spec_proto):
    """Create an instance of the Position proto.

     Args:
       unused_spec_proto: Unused.

    Returns:
      Position proto at the origin.
    """
    position = primitives_pb2.Position()
    position.x = 0.0
    position.y = 0.0
    position.z = 0.0
    return position

  @staticmethod
  def _create_rotation_proto(unused_spec_proto):
    """Create an instance of the Rotation proto.

     Args:
       unused_spec_proto: Unused.

    Returns:
      Identity Rotation proto.
    """
    rotation = primitives_pb2.Rotation()
    rotation.x = 0.0
    rotation.y = 0.0
    rotation.z = 0.0
    rotation.w = 1.0
    return rotation

  @staticmethod
  def _create_observation_data_proto(unused_spec_proto):
    """Create an instance of the ObservationData proto.

     Args:
       unused_spec_proto: Unused.

    Returns:
      ObservationData proto.
    """
    return observation_pb2.ObservationData()

  @staticmethod
  def _add_to_observation_data_proto(data_proto, child_data_proto, node):
    """Add a child message to a data proto.

    Args:
      data_proto: Proto to add child message to.
      child_data_proto: Child message to add to data_proto.
      node: ProtobufNode instance that references the spec of child_data_proto.
    """
    if node.name == 'player':
      data_proto.player.CopyFrom(child_data_proto)
    elif node.name == 'camera':
      data_proto.camera.CopyFrom(child_data_proto)
    else:
      data_proto.global_entities.append(child_data_proto)

  @staticmethod
  def _create_entity_proto(unused_spec_proto):
    """Create an instance of the Entity proto.

     Args:
       unused_spec_proto: Unused.

    Returns:
      Entity proto.
    """
    return observation_pb2.Entity()

  @staticmethod
  def _add_to_entity_proto(data_proto, child_data_proto, unused_node):
    """Add a child message to a data proto.

    Args:
      data_proto: Proto to add child message to.
      child_data_proto: Child message to add to data_proto.
      unused_node: Unused.
    """
    child_data_proto_type = type(child_data_proto)
    field_name = (
        DataProtobufGenerator._ENTITY_DATA_PROTO_CLASS_TO_FIELD_NAME.get(
            child_data_proto_type))
    if field_name:
      getattr(data_proto, field_name).CopyFrom(child_data_proto)
    else:
      entity_field = data_proto.entity_fields.add()
      field_name = (
          DataProtobufGenerator._LEAF_DATA_PROTO_CLASS_TO_FIELD_NAME.get(
              child_data_proto_type))
      assert field_name, ('Unsupported entity field type ' +
                          str(child_data_proto_type))
      getattr(entity_field, field_name).CopyFrom(child_data_proto)

  @staticmethod
  def _create_feeler_proto(spec_proto):
    """Create an instance of the Feeler proto from the supplied spec.

    Args:
      spec_proto: Spec proto for the generated data.

    Returns:
      Feeler proto that conforms to the spec.
    """
    feeler = observation_pb2.Feeler()
    number_of_feelers = spec_proto.count
    minimum_distance = spec_proto.distance.minimum
    minimum_experimental_data = [
        number.minimum for number in spec_proto.experimental_data]
    for _ in range(number_of_feelers):
      measurement = feeler.measurements.add()
      measurement.distance.value = minimum_distance
      for minimum in minimum_experimental_data:
        number = measurement.experimental_data.add()
        number.value = minimum
    return feeler

  @staticmethod
  def _null_modify_data_proto(unused_data_proto, unused_spec_proto):
    """Method that does not modify a data proto.

    Args:
      unused_data_proto: Data protobuf to modify (unused).
      unused_spec_proto: Spec protobuf for the data (unused).
    """
    pass

  @staticmethod
  def _randomize_category_proto(data_proto, spec_proto):
    """Randomizes the contents of a Category proto conformant to the spec.

    Args:
      data_proto: Category protobuf to modify.
      spec_proto: Spec protobuf for the data.
    """
    data_proto.value = random.randrange(
        0, max(0, len(spec_proto.enum_values) - 1))

  @staticmethod
  def _randomize_number_proto(data_proto, spec_proto):
    """Randomizes the contents of a Number proto conformant to the spec.

    Args:
      data_proto: Number protobuf to modify.
      spec_proto: Spec protobuf for the data.
    """
    data_proto.value = random.uniform(spec_proto.minimum, spec_proto.maximum)

  @staticmethod
  def _random_axis_value():
    """Generate a random value between -1.0...1.0."""
    return random.uniform(-1.0, 1.0)

  @staticmethod
  def _randomize_joystick_proto(data_proto, unused_spec_proto):
    """Randomizes the contents of a Joystick proto.

    Args:
      data_proto: Number protobuf to modify.
      unused_spec_proto: Unused.
    """
    data_proto.x_axis = DataProtobufGenerator._random_axis_value()
    data_proto.y_axis = DataProtobufGenerator._random_axis_value()

  @staticmethod
  def _randomize_position_proto(data_proto, unused_spec_proto):
    """Randomizes the contents of a Position proto in the unit circle.

    Args:
      data_proto: Position protobuf to modify.
      unused_spec_proto: Spec protobuf for the data.
    """
    data_proto.x = DataProtobufGenerator._random_axis_value()
    data_proto.y = DataProtobufGenerator._random_axis_value()
    data_proto.z = DataProtobufGenerator._random_axis_value()

  @staticmethod
  def _randomize_rotation_proto(data_proto, unused_spec_proto):
    """Randomizes the contents of a Rotation proto.

    Args:
      data_proto: Rotation protobuf to modify.
      unused_spec_proto: Spec protobuf for the data.
    """
    data_proto.x = DataProtobufGenerator._random_axis_value()
    data_proto.y = DataProtobufGenerator._random_axis_value()
    data_proto.z = DataProtobufGenerator._random_axis_value()
    data_proto.w = DataProtobufGenerator._random_axis_value()

  @staticmethod
  def _randomize_feeler_proto(data_proto, spec_proto):
    """Randomizes the contents of a Feeler proto conformant to the spec.

    Args:
      data_proto: Feeler protobuf to modify.
      spec_proto: Spec protobuf for the data.
    """
    experimental_data_count = len(spec_proto.experimental_data)
    for measurement in data_proto.measurements:
      DataProtobufGenerator._randomize_number_proto(
          measurement.distance, spec_proto.distance)
      for i in range(experimental_data_count):
        DataProtobufGenerator._randomize_number_proto(
            measurement.experimental_data[i],
            spec_proto.experimental_data[i])

  @staticmethod
  def randomize_leaf_data_proto(data_proto, spec_proto):
    """Randomizes the contents of leaf data proto conformant to the spec.

    Non-leaf protos, like ObservationData, are not modified.

    Args:
      data_proto: Leaf data protobuf to modify.
      spec_proto: Spec protobuf for the data.
    """
    if not DataProtobufGenerator._DATA_PROTO_CLASS_TO_RANDOMIZE_METHOD:
      DataProtobufGenerator._DATA_PROTO_CLASS_TO_RANDOMIZE_METHOD = {
          action_pb2.ActionData: DataProtobufGenerator._null_modify_data_proto,
          action_pb2.Joystick: DataProtobufGenerator._randomize_joystick_proto,
          observation_pb2.Entity: DataProtobufGenerator._null_modify_data_proto,
          observation_pb2.Feeler: DataProtobufGenerator._randomize_feeler_proto,
          observation_pb2.ObservationData: (
              DataProtobufGenerator._null_modify_data_proto),
          primitives_pb2.Category: (
              DataProtobufGenerator._randomize_category_proto),
          primitives_pb2.Number: DataProtobufGenerator._randomize_number_proto,
          primitives_pb2.Position: (
              DataProtobufGenerator._randomize_position_proto),
          primitives_pb2.Rotation: (
              DataProtobufGenerator._randomize_rotation_proto),
      }
    randomize_method = (
        DataProtobufGenerator._DATA_PROTO_CLASS_TO_RANDOMIZE_METHOD.get(
            type(data_proto)))
    randomize_method(data_proto, spec_proto)

  @staticmethod
  def from_spec_node(node, modify_data_proto=None):
    """Traverse a tree of protobuf spec nodes, generating data protos.

    Args:
      node: ProtobufNode instance that references a spec proto to
        traverse to produce a data protobuf.
      modify_data_proto: Callable that takes (data_proto, spec_proto) as
        arguments, where data_proto is the generated data protobuf and
        spec_proto is the spec protobuf used to generate the data.
        This method provides a way to customize the newly generated data proto.

    Returns:
      List of data protobufs based upon the protobuf, or repeated message field
      associated with the supplied node. For example, given a node that
      references an ObservationSpec this will generate a single ObservationData
      proto populated with data that is in the range of the provided spec.
      If a protobuf node references a repeated field, e.g
      ObservationSpec.global_entities, this method will return a list of Entity
      protos for each entity specified by the field.
    """
    modify_data_proto = (modify_data_proto if modify_data_proto else
                         DataProtobufGenerator._null_modify_data_proto)
    if not DataProtobufGenerator._SPEC_PROTO_CLASS_TO_CREATE_ADD_METHODS:
      DataProtobufGenerator._SPEC_PROTO_CLASS_TO_CREATE_ADD_METHODS = {
          action_pb2.ActionSpec: (
              DataProtobufGenerator._create_action_data_proto,
              DataProtobufGenerator._add_to_action_data_proto),
          action_pb2.JoystickType: (
              DataProtobufGenerator._create_joystick_proto, None),
          observation_pb2.EntityType: (
              DataProtobufGenerator._create_entity_proto,
              DataProtobufGenerator._add_to_entity_proto),
          observation_pb2.FeelerType: (
              DataProtobufGenerator._create_feeler_proto, None),
          observation_pb2.ObservationSpec: (
              DataProtobufGenerator._create_observation_data_proto,
              DataProtobufGenerator._add_to_observation_data_proto),
          primitives_pb2.CategoryType: (
              DataProtobufGenerator._create_category_proto, None),
          primitives_pb2.NumberType: (
              DataProtobufGenerator._create_number_proto, None),
          primitives_pb2.PositionType: (
              DataProtobufGenerator._create_position_proto, None),
          primitives_pb2.RotationType: (
              DataProtobufGenerator._create_rotation_proto, None),
      }

    create_and_add_methods = (
        DataProtobufGenerator._SPEC_PROTO_CLASS_TO_CREATE_ADD_METHODS.get(
            type(node.proto)))
    data_protos = []
    # If this isn't a repeated message container, create the container proto.
    if create_and_add_methods:
      create_data_proto, add_to_data_proto = create_and_add_methods
      container_data_proto = create_data_proto(node.proto)
      modify_data_proto(container_data_proto, node.proto)
      data_protos.append(container_data_proto)
    # The class for a repeated message container isn't public so detect via
    # the add() method.
    elif hasattr(node.proto, 'add') and callable(getattr(node.proto, 'add')):
      # Just return a list of child protos if this is a repeated message
      # container.
      container_data_proto = None

    for child_node in node.children:
      child_data_protos = DataProtobufGenerator.from_spec_node(
          child_node, modify_data_proto=modify_data_proto)
      if container_data_proto:
        for child_data_proto in child_data_protos:
          add_to_data_proto(container_data_proto, child_data_proto, child_node)
      else:
        data_protos.extend(child_data_protos)
    return data_protos
