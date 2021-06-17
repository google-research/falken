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

"""Wrapper classes for Falken observation and action specs."""

# pylint: disable=g-bad-import-order
import collections

import common.generate_protos  # pylint: disable=unused-import

import action_pb2
import brain_pb2
import observation_pb2
import primitives_pb2

# Optional fields of ObservationData and ObservationSpec protobufs.
OBSERVATION_OPTIONAL_ENTITIES = ['player', 'camera']
# Optional fields of EntityType and Entity protobufs.
ENTITY_OPTIONAL_FIELDS = ['position', 'rotation']


class InvalidSpecError(Exception):
  """Raised when the spec is invalid."""


class TypingError(Exception):
  """Raised when data doesn't match the spec."""


class BrainSpec:
  """A wrapper class for an observation and action spec proto."""

  def __init__(self, brain_spec_pb, spec_base_class=None,
               action_spec_class=None, observation_spec_class=None):
    """Parse and validate the provided spec proto.

    Args:
      brain_spec_pb: BrainSpec protobuf to parse and validate.
      spec_base_class: SpecBase class to use for brain validation.
      action_spec_class: SpecBase class to use for action validation and
        conversion.
      observation_spec_class: SpecBase class to use for action validation and
        conversion.
    """
    assert isinstance(brain_spec_pb, brain_pb2.BrainSpec)
    spec_base_class = spec_base_class if spec_base_class else SpecBase
    action_spec_class = action_spec_class if action_spec_class else ActionSpec
    observation_spec_class = (observation_spec_class
                              if observation_spec_class else ObservationSpec)
    _ = spec_base_class(brain_spec_pb)
    self.action_spec = action_spec_class(brain_spec_pb.action_spec)
    self.observation_spec = observation_spec_class(
        brain_spec_pb.observation_spec)
    self.validate_joystick_references()

  def validate_joystick_references(self):
    """Validate joystick actions reference existing entities.

    Raises:
      InvalidSpecError: If invalid references are found or referenced entities
        do not have positions or rotations.
    """
    references_by_joystick_name = collections.defaultdict(set)

    for node in self.action_spec.proto_node.children:
      action = node.proto
      if isinstance(action, action_pb2.JoystickType):
        if action.control_frame:
          references_by_joystick_name[node.name].add(action.control_frame)
        if action.controlled_entity:
          references_by_joystick_name[node.name].add(action.controlled_entity)

    joystick_names_by_reference = collections.defaultdict(set)
    invalid_references_by_joystick = []
    for joystick_name, references in sorted(
        references_by_joystick_name.items()):
      invalid_references = []
      for reference in references:
        # In future, we may support named entities as well in addition to the
        # fixed player and camera entities.
        if reference in OBSERVATION_OPTIONAL_ENTITIES:
          joystick_names_by_reference[reference].add(joystick_name)
        else:
          invalid_references.append(reference)

      if invalid_references:
        invalid_references_by_joystick.append(
            f'{joystick_name} --> {sorted(invalid_references)}')

    # Report all invalid entity references by joysticks.
    if invalid_references_by_joystick:
      msg = ', '.join(invalid_references_by_joystick)
      raise InvalidSpecError(f'Joystick(s) reference invalid entities: {msg}.')

    # Get all entities by name.
    observation_node = self.observation_spec.proto_node
    entities_by_name = {}
    for optional_field in OBSERVATION_OPTIONAL_ENTITIES:
      entity_node = observation_node.child_by_proto_field_name(optional_field)
      if entity_node:
        entities_by_name[entity_node.name] = entity_node
    global_entities = observation_node.child_by_proto_field_name(
        'global_entities')
    if global_entities:
      for entity_node in global_entities.children:
        entities_by_name[entity_node.name] = entity_node

    # Check that all referenced entities exist and have positions and rotations.
    for reference, joystick_names in joystick_names_by_reference.items():
      joystick_names = sorted(joystick_names)
      entity_node = entities_by_name.get(reference)
      if not entity_node:
        raise InvalidSpecError(f'Missing entity {reference} referenced by '
                               f'joysticks {joystick_names}.')
      if not entity_node.child_by_proto_field_name('position'):
        raise InvalidSpecError(f'Entity {reference} referenced by joysticks '
                               f'{joystick_names} has no position.')
      if not entity_node.child_by_proto_field_name('rotation'):
        raise InvalidSpecError(f'Entity {reference} referenced by joysticks '
                               f'{joystick_names} has no rotation.')


class SpecBase:
  """Base class for an action or observation spec."""

  def __init__(self, spec):
    """Parse and validate the provided spec proto.

    Args:
      spec: Spec protobuf to parse and validate.
    """
    self._spec_proto = spec
    self._spec_proto_node = ProtobufNode.from_spec(spec)
    self._node_nest = self._spec_proto_node.as_nest(include_self=False)
    super().__init__()

  @property
  def proto(self):
    """Return the underlying proto buffer."""
    return self._spec_proto

  @property
  def proto_node(self):
    """Get the ProtobufNode referencing the underlying protocol buffer."""
    return self._spec_proto_node

  def __str__(self):
    """String representation of the proto owned by this object."""
    return str(self._spec_proto)


class ObservationSpec(SpecBase):
  """A wrapper class for an ObservationSpec proto.

  ObservationSpec proto defines the observation space for an agent. This class
  is a helper class used to translate spec information and value to a TF Agents
  compatible format.
  """

  def __init__(self, spec_proto):
    assert isinstance(spec_proto, observation_pb2.ObservationSpec)
    super().__init__(spec_proto)


class ActionSpec(SpecBase):
  """A wrapper class for an ActionSpec proto.

  An ActionSpec proto defines the action space for an agent.  This class
  is a helper class used to translate spec information and value to a TF Agents
  compatible format.
  """

  def __init__(self, spec_proto):
    assert isinstance(spec_proto, action_pb2.ActionSpec)
    super().__init__(spec_proto)


def _concat_path(prefix, component):
  """Add a component to a path.

  Args:
    prefix: Prefix of the path. If this is empty, it isn't included in the
      returned path.
    component: Component to add to the path.

  Returns:
    Concatenated path string.
  """
  return f'{prefix}/{component}' if prefix else component


def _get_optional_fields_from_proto(proto, field_names):
  """Get optional fields from the specified proto.

  Args:
    proto: Proto to query.
    field_names: Names of the fields to find.

  Returns:
    List of (field_name, field_proto) tuples where field_name is the
    name of the field and field_proto is the sub-message proto.
  """
  return [(f, getattr(proto, f)) for f in field_names if proto.HasField(f)]


def _label_repeated_field(proto, field_name):
  """Label elements of a repeated proto field.

  Args:
    proto: Proto to query.
    field_name: Repeated field name to enumerate.

  Yields:
    (index, name, field_proto) tuples where index is the index of the field,
    name is `field_name[index]` and field_proto is the proto in the
    repeated field at the index index.
  """
  repeated_field = getattr(proto, field_name)
  for i in range(len(repeated_field)):
    yield (i, f'{field_name}[{i}]', repeated_field[i])
  return


def _get_proto_name(proto):
  """Get the value of a proto's name field or return the proto type name.

  Args:
    proto: Proto to query.

  Returns:
    Human readable name of the proto.
  """
  if 'name' in proto.DESCRIPTOR.fields_by_name:
    return proto.name
  return proto .DESCRIPTOR.name


class ProtobufValidator:
  """Validates a protobuf."""

  # Lazily initialized by check_spec().
  _SPEC_PROTO_CLASS_TO_VALIDATOR = None
  # Lazily initialized by check_data().
  _DATA_PROTO_CLASS_TO_VALIDATOR = None

  @staticmethod
  def _check_category_type(spec, path_prefix):
    """Validate a CategoryType proto.

    Args:
      spec: CategoryType proto to validate.
      path_prefix: Prefix to add to the path when reporting errors.

    Raises:
      InvalidSpecError: If there are less than 2 categories.
    """
    if len(spec.enum_values) < 2:
      raise InvalidSpecError(
          f'{path_prefix} has less than two categories: {spec.enum_values}.')

  @staticmethod
  def _check_number_type(spec, path_prefix):
    """Validate a NumberType proto.

    Args:
      spec: NumberType proto to validate.
      path_prefix: Prefix to add to the path when reporting errors.

    Raises:
      InvalidSpecError: If the minimum value is the same as or exceeds the
        maximum.
    """
    if spec.minimum >= spec.maximum:
      raise InvalidSpecError(
          f'{path_prefix} has invalid or missing range: '
          f'[{spec.minimum}, {spec.maximum}].')

  @staticmethod
  def _check_feeler_type(spec, path_prefix):
    """Validate a FeelerType proto.

    Args:
      spec: FeelerType proto to validate.
      path_prefix: Prefix to add to the path when reporting errors.

    Raises:
      InvalidSpecError: If the count is less than 1, yaw angles don't match
        the count or distance and experimental data ranges are invalid.
    """
    if spec.count < 1:
      raise InvalidSpecError(
          f'{path_prefix} has feeler count {spec.count}, requires at least 1.')
    ProtobufValidator._check_number_type(spec.distance,
                                         _concat_path(path_prefix, 'distance'))
    if len(spec.yaw_angles) != spec.count:
      raise InvalidSpecError(
          f'{path_prefix} has {len(spec.yaw_angles)} yaw_angles that '
          f'mismatch feeler count {spec.count}.')
    for i, experimental_data in enumerate(spec.experimental_data):
      ProtobufValidator._check_number_type(
          experimental_data,
          _concat_path(path_prefix, f'experimental_data[{i}]'))

  @staticmethod
  def _check_joystick_type(spec, path_prefix):
    """Validate a JoystickType proto.

    Args:
      spec: JoystickType proto to validate.
      path_prefix: Prefix to add to the path when reporting errors.

    Raises:
      InvalidSpecError: If the axes mode isn't set, a controlled entity isn't
        set or the control frame is set with an incompatible axes mode.
    """
    if spec.axes_mode == action_pb2.UNDEFINED:
      raise InvalidSpecError(f'{path_prefix} has undefined axes_mode.')
    if not spec.controlled_entity:
      raise InvalidSpecError(f'{path_prefix} has no controlled_entity.')
    if spec.control_frame and spec.axes_mode != action_pb2.DIRECTION_XZ:
      raise InvalidSpecError(
          f'{path_prefix} has invalid control frame "{spec.control_frame}". '
          f'control_frame should only be set if axes_mode is DIRECTION_XZ, '
          'axes_mode is currently '
          f'{action_pb2.JoystickAxesMode.Name(spec.axes_mode)}.')

  @staticmethod
  def _check_oneof_field_set(proto, path, oneof_name):
    """Validate a proto oneof field is set.

    Args:
      proto: Proto to check.
      path: Human readable path to the proto.
      oneof_name: "oneof" field name to check to see whether it's set.

    Raises:
      InvalidSpecError: If the proto does not contain one of the specified
        fields.
    """
    if not proto.WhichOneof(oneof_name):
      expected_fields = ', '.join([
          f.name for f in proto.DESCRIPTOR.oneofs_by_name[oneof_name].fields])
      raise InvalidSpecError(
          f'{path} {oneof_name} must have one of [{expected_fields}] set.')

  @staticmethod
  def _check_entity_field_type(spec, path_prefix):
    """Validate an EntityFieldType proto.

    Args:
      spec: EntityType proto to validate.
      path_prefix: Prefix to add to the path when reporting errors.

    Raises:
      InvalidSpecError: If the proto does not contain a required type field.
    """
    ProtobufValidator._check_oneof_field_set(spec, path_prefix, 'type')

  @staticmethod
  def _check_entity_type(spec, path_prefix):
    """Validate an EntityType proto.

    Args:
      spec: EntityType proto to validate.
      path_prefix: Prefix to add to the path when reporting errors.

    Raises:
      InvalidSpecError: If any custom entity fields have no name, have a
        reserved name or duplicate name.
    """
    existing_names = set()
    for i, entity_field_type in enumerate(spec.entity_fields):
      path = _concat_path(path_prefix, f'entity_field[{i}]')
      if not entity_field_type.name:
        raise InvalidSpecError(f'{path} has no name.')
      if entity_field_type.name in ENTITY_OPTIONAL_FIELDS:
        raise InvalidSpecError(
            f'{path} has reserved name "{entity_field_type.name}".')
      if entity_field_type.name in existing_names:
        raise InvalidSpecError(
            f'{path} has name "{entity_field_type.name}" '
            f'that already exists in {path_prefix}')
      existing_names.add(entity_field_type.name)

  @staticmethod
  def _check_action_type(spec, path_prefix):
    """Validate an ActionType proto.

    Args:
      spec: ActionType proto to validate.
      path_prefix: Prefix to add to the path when reporting errors.

    Raises:
      InvalidSpecError: If a required type isn't present.
    """
    ProtobufValidator._check_oneof_field_set(spec, path_prefix, 'action_types')

  @staticmethod
  def _check_action_spec(spec, path_prefix):
    """Validate an ActionSpec proto.

    Args:
      spec: ActionSpec proto to validate.
      path_prefix: Prefix to add to the path when reporting errors.

    Raises:
      InvalidSpecError: If any actions have no names or duplicate names.
    """
    existing_names = set()
    if not spec.actions:
      raise InvalidSpecError(f'{path_prefix} is empty.')
    for i, action_type in enumerate(spec.actions):
      path = _concat_path(path_prefix, f'actions[{i}]')
      if not action_type.name:
        raise InvalidSpecError(f'{path} has no name.')
      if action_type.name in existing_names:
        raise InvalidSpecError(
            f'{path} has duplicate name "{action_type.name}".')
      existing_names.add(action_type.name)

  @staticmethod
  def _check_observation_spec(spec, path_prefix):
    """Validate a ObservationSpec proto.

    Args:
      spec: ObservationSpec proto to validate.
      path_prefix: Prefix to add to the path when reporting errors.

    Raises:
      InvalidSpecError: If any actions have no names or duplicate names.
    """
    if not spec.HasField('player') and not spec.global_entities:
      raise InvalidSpecError(
          f'{path_prefix} must contain at least one non-camera entity.')

  @staticmethod
  def _check_brain_spec(spec, path_prefix):
    """Validate a BrainSpec proto.

    Args:
      spec: BrainSpec proto to validate.
      path_prefix: Prefix to add to the path when reporting errors.

    Raises:
      InvalidSpecError: If any actions have no names or duplicate names.
    """
    if not spec.HasField(
        'observation_spec') or not spec.HasField('action_spec'):
      raise InvalidSpecError(
          f'{path_prefix} must have an observation spec and action spec.')

  @staticmethod
  def _null_spec_check(unused_spec, unused_path_prefix):
    """Do not perform any validation of the specified proto.

    Args:
      unused_spec: Ignored.
      unused_path_prefix: Ignored.
    """
    pass

  @staticmethod
  def check_spec(spec, path_prefix):
    """Validate a spec proto.

    To keep traversal of the spec proto separate from validation, this method
    does not recursively validate the provided spec proto. To traverse and
    validate a spec proto use ProtobufNode.from_spec().

    Args:
      spec: Spec proto to validate.
      path_prefix: Prefix to add to the path when reporting errors.

    Raises:
      InvalidSpecError: If validation fails or no validator is found for the
        specified proto.
    """
    if not ProtobufValidator._SPEC_PROTO_CLASS_TO_VALIDATOR:
      ProtobufValidator._SPEC_PROTO_CLASS_TO_VALIDATOR = {
          brain_pb2.BrainSpec:
              ProtobufValidator._check_brain_spec,
          action_pb2.ActionSpec:
              ProtobufValidator._check_action_spec,
          action_pb2.ActionType:
              ProtobufValidator._check_action_type,
          action_pb2.JoystickType:
              ProtobufValidator._check_joystick_type,
          observation_pb2.EntityFieldType:
              ProtobufValidator._check_entity_field_type,
          observation_pb2.EntityType:
              ProtobufValidator._check_entity_type,
          observation_pb2.FeelerType:
              ProtobufValidator._check_feeler_type,
          observation_pb2.ObservationSpec:
              ProtobufValidator._check_observation_spec,
          primitives_pb2.CategoryType:
              ProtobufValidator._check_category_type,
          primitives_pb2.NumberType:
              ProtobufValidator._check_number_type,
          primitives_pb2.PositionType:
              ProtobufValidator._null_spec_check,
          primitives_pb2.RotationType:
              ProtobufValidator._null_spec_check
      }
    validator = ProtobufValidator._SPEC_PROTO_CLASS_TO_VALIDATOR.get(type(spec))
    if not validator:
      raise InvalidSpecError(
          f'Validator not found for {type(spec).__qualname__} at '
          f'"{path_prefix}".')
    validator(spec, path_prefix)

  @staticmethod
  def _check_spec_proto_class(data, spec, spec_proto_class, path_prefix):
    """Check that a spec proto matches the expected protobuf type.

    Args:
      data: Data proto to report if the spec doesn't match.
      spec: Spec proto instance to check.
      spec_proto_class: Expected proto class / message type.
      path_prefix: Path to the proto to report if the spec doesn't match.

    Raises:
      TypingError: If the spec doesn't match the expected class.
    """
    # isinstance() is a lot slower than checking directly against the class.
    # pylint: disable=unidiomatic-typecheck
    if type(spec) != spec_proto_class:
      raise TypingError(f'{path_prefix} data does not match spec. data is '
                        f'{type(data).__qualname__}, spec is '
                        f'{type(spec).__qualname__}')

  @staticmethod
  def _check_category(data, spec, path_prefix, check_spec_class):
    """Check that a Category proto conforms to the provided spec proto.

    Args:
      data: Category protobuf.
      spec: CategoryType protobuf to check data with.
      path_prefix: Prefix to add to the path when reporting errors.
      check_spec_class: Whether this method should check the spec proto class.

    Raises:
      TypingError: If the data is out of range.
    """
    if check_spec_class:
      ProtobufValidator._check_spec_proto_class(
          data, spec, primitives_pb2.CategoryType, path_prefix)
    number_of_values = len(spec.enum_values) - 1
    if data.value < 0 or data.value > number_of_values:
      enum_items = ', '.join(spec.enum_values)
      raise TypingError(
          f'{path_prefix} category has value {data.value} that is out of the '
          f'specified range [0, {number_of_values}] ({enum_items}).')

  @staticmethod
  def _check_number(data, spec, path_prefix, check_spec_class):
    """Check that a Number proto conforms to the provided spec proto.

    Args:
      data: Number protobuf.
      spec: NumberType protobuf to check data with.
      path_prefix: Prefix to add to the path when reporting errors.
      check_spec_class: Whether this method should check the spec proto class.

    Raises:
      TypingError: If the data is out of range.
    """
    if check_spec_class:
      ProtobufValidator._check_spec_proto_class(
          data, spec, primitives_pb2.NumberType, path_prefix)
    if data.value < spec.minimum or data.value > spec.maximum:
      raise TypingError(
          f'{path_prefix} number has value {data.value} that is out of the '
          f'specified range [{spec.minimum}, {spec.maximum}].')

  @staticmethod
  def _check_repeated_count_matches(data_repeated_field,
                                    data_repeated_fieldname,
                                    data_typename,
                                    spec_repeated_field,
                                    spec_repeated_fieldname, path_prefix):
    """Check the length of two repeated proto fields match.

    Args:
      data_repeated_field: Proto repeated field to check.
      data_repeated_fieldname: Name of the repeated field in the data proto.
      data_typename: String type to report in the exception.
      spec_repeated_field: Proto repeated field to validate against.
      spec_repeated_fieldname: Name of the expected repeated field.
      path_prefix: Prefix to add to the path when reporting errors.

    Raises:
      TypingError: If the length of the two repeated fields do not match.
    """
    if len(data_repeated_field) != len(spec_repeated_field):
      raise TypingError(
          f'{path_prefix} {data_typename} contains '
          f'{len(data_repeated_field)} {data_repeated_fieldname} vs. '
          f'expected {len(spec_repeated_field)} {spec_repeated_fieldname}.')

  @staticmethod
  def _check_feeler(data, spec, path_prefix, check_spec_class):
    """Check that a Feeler proto conforms to the provided spec proto.

    Args:
      data: Feeler protobuf.
      spec: FeelerType protobuf.
      path_prefix: Prefix to add to the path when reporting errors.
      check_spec_class: Whether this method should check the spec proto class.

    Raises:
      TypingError: If the number of feelers mismatches the spec, the number of
        experimental_data measures for each feeler differs from the spec,
        the distance of each feeler or experimental_data are out of range.
    """
    if check_spec_class:
      ProtobufValidator._check_spec_proto_class(
          data, spec, observation_pb2.FeelerType, path_prefix)
    measurements = data.measurements
    measurements_count = len(data.measurements)
    if measurements_count != spec.count:
      raise TypingError(
          f'{path_prefix} feeler has an invalid number of measurements '
          f'{measurements_count} vs. expected {spec.count}.')

    for i in range(measurements_count):
      measurement = measurements[i]
      measurement_path = _concat_path(path_prefix, f'measurements[{i}]')
      ProtobufValidator._check_number(measurement.distance, spec.distance,
                                      _concat_path(measurement_path,
                                                   'distance'), False)

      experimental_data = measurement.experimental_data
      ProtobufValidator._check_repeated_count_matches(
          experimental_data, 'experimental_data', 'feeler',
          spec.experimental_data, 'experimental_data', measurement_path)

      for j in range(len(experimental_data)):
        experimental_data_path = _concat_path(measurement_path,
                                              f'experimental_data[{j}]')
        ProtobufValidator._check_number(
            experimental_data[j], spec.experimental_data[j],
            experimental_data_path, False)

  @staticmethod
  def _check_matching_oneof(data, data_oneof, data_typename, spec, spec_oneof,
                            path_prefix):
    """Check that a oneof field of data is present in spec.

    Args:
      data: Data protobuf.
      data_oneof: Name of the data oneof field to check.
      data_typename: Name of the data type to report in the exception.
      spec: Spec protobuf.
      spec_oneof: Name of the spec oneof field to check.
      path_prefix: Prefix to add to the path when reporting errors.

    Raises:
      TypingError: If the data doesn't have the expected type.
    """
    spec_type = spec.WhichOneof(spec_oneof)
    data_type = data.WhichOneof(data_oneof)
    if spec_type != data_type:
      raise TypingError(f'{path_prefix}/{data_oneof} {data_typename} '
                        f'"{data_type}" does not match the spec {spec_oneof} '
                        f'"{spec_type}".')

  @staticmethod
  def _check_entity_field(data, spec, path_prefix, check_spec_class):
    """Check that an EntityField proto conforms to the provided spec proto.

    Args:
      data: EntityField protobuf.
      spec: EntityFieldType protobuf.
      path_prefix: Prefix to add to the path when reporting errors.
      check_spec_class: Whether this method should check the spec proto class.

    Raises:
      TypingError: If the data doesn't have the expected type.
    """
    if check_spec_class:
      ProtobufValidator._check_spec_proto_class(
          data, spec, observation_pb2.EntityFieldType, path_prefix)
    ProtobufValidator._check_matching_oneof(
        data, 'value', 'entity field', spec, 'type', path_prefix)

  @staticmethod
  def _check_optional_fields(data, optional_fields, spec, path_prefix):
    """Check that a data proto contains the same optional fields as a spec.

    Args:
      data: Data protobuf.
      optional_fields: List of optional field names.
      spec: Spec protobuf.
      path_prefix: Prefix to add to the path when reporting errors.

    Raises:
      TypingError: If the optional fields in the data don't conform to the spec.
    """
    has_field_message = (
        lambda has, name: f'has "{name}"' if has else f'does not have "{name}"')
    for field in optional_fields:
      data_has_field = data.HasField(field)
      spec_has_field = spec.HasField(field)
      if data_has_field != spec_has_field:
        raise TypingError(f'{path_prefix} entity '
                          f'{has_field_message(data_has_field, field)} but '
                          f'spec {has_field_message(spec_has_field, field)}.')

  @staticmethod
  def _check_entity(data, spec, path_prefix, unused_check_spec_class):
    """Check that an Entity proto conforms to the provided spec proto.

    Args:
      data: Entity protobuf.
      spec: EntityType protobuf.
      path_prefix: Prefix to add to the path when reporting errors.
      unused_check_spec_class: Not used.

    Raises:
      TypingError: If the optional fields in the data don't conform to the spec
        or the number of entity fields mismatch.
    """
    ProtobufValidator._check_optional_fields(data, ENTITY_OPTIONAL_FIELDS,
                                             spec, path_prefix)
    ProtobufValidator._check_repeated_count_matches(
        data.entity_fields, 'entity_fields', 'entity',
        spec.entity_fields, 'entity_fields', path_prefix)

  @staticmethod
  def _check_action(data, spec, path_prefix, check_spec_class):
    """Check that an Action proto conforms to the provided spec proto.

    Args:
      data: Action protobuf.
      spec: ActionType protobuf.
      path_prefix: Prefix to add to the path when reporting errors.
      check_spec_class: Whether this method should check the spec proto class.

    Raises:
      TypingError: If the data doesn't have the expected type.
    """
    if check_spec_class:
      ProtobufValidator._check_spec_proto_class(
          data, spec, action_pb2.ActionType, path_prefix)
    ProtobufValidator._check_matching_oneof(
        data, 'action', 'action', spec, 'action_types', path_prefix)

  @staticmethod
  def _check_position(data, spec, path_prefix, check_spec_class):
    """Check that a Position proto conforms to the provided spec proto.

    Args:
      data: Position protobuf.
      spec: PositionType protobuf.
      path_prefix: Prefix to add to the path when reporting errors.
      check_spec_class: Whether this method should check the spec proto class.

    Raises:
      TypingError: If the data doesn't have the expected type.
    """
    if check_spec_class:
      ProtobufValidator._check_spec_proto_class(
          data, spec, primitives_pb2.PositionType, path_prefix)

  @staticmethod
  def _check_rotation(data, spec, path_prefix, check_spec_class):
    """Check that a Rotation proto conforms to the provided spec proto.

    Args:
      data: Rotation protobuf.
      spec: RotationType protobuf.
      path_prefix: Prefix to add to the path when reporting errors.
      check_spec_class: Whether this method should check the spec proto class.

    Raises:
      TypingError: If the data doesn't have the expected type.
    """
    if check_spec_class:
      ProtobufValidator._check_spec_proto_class(
          data, spec, primitives_pb2.RotationType, path_prefix)

  @staticmethod
  def _check_action_data(data, spec, path_prefix, check_spec_class):
    """Check that an ActionData proto conforms to the provided spec proto.

    Args:
      data: ActionData protobuf.
      spec: ActionSpec protobuf.
      path_prefix: Prefix to add to the path when reporting errors.
      check_spec_class: Whether this method should check the spec proto class.

    Raises:
      TypingError: If the data has a unexpected number of actions or the action
        source is unknown.
    """
    if check_spec_class:
      ProtobufValidator._check_spec_proto_class(
          data, spec, action_pb2.ActionSpec, path_prefix)
    if data.source == action_pb2.ActionData.SOURCE_UNKNOWN:
      raise TypingError(f'{path_prefix} action data\'s source is unknown.')
    ProtobufValidator._check_repeated_count_matches(
        data.actions, 'actions', 'actions', spec.actions, 'actions',
        path_prefix)

  @staticmethod
  def _check_joystick(data, spec, path_prefix, check_spec_class):
    """Check that a Joystick proto conforms to the provided spec proto.

    Args:
      data: Joystick protobuf.
      spec: JoystickType protobuf.
      path_prefix: Prefix to add to the path when reporting errors.
      check_spec_class: Whether this method should check the spec proto class.

    Raises:
      TypingError: If an axis value is out of range.
    """
    if check_spec_class:
      ProtobufValidator._check_spec_proto_class(
          data, spec, action_pb2.JoystickType, path_prefix)

    def check_axis(value, axis):
      """Check that a joystick axis value is within range.

      Args:
        value: Value to check.
        axis: Name of the axis.

      Raises:
        TypingError: If an axis value is out of range.
      """
      if value < -1.0 or value > 1.0:
        raise TypingError(f'{path_prefix} joystick {axis} value {value} is out '
                          'of range [-1.0, 1.0].')
    check_axis(data.x_axis, 'x_axis')
    check_axis(data.y_axis, 'y_axis')

  @staticmethod
  def _check_observation(data, spec, path_prefix, check_spec_class):
    """Check that an Observation proto conforms to the provided spec proto.

    Args:
      data: Observation protobuf.
      spec: ObservationSpec protobuf.
      path_prefix: Prefix to add to the path when reporting errors.
      check_spec_class: Whether this method should check the spec proto class.

    Raises:
      TypingError: If the data contains an unexpected number of entities.
    """
    if check_spec_class:
      ProtobufValidator._check_spec_proto_class(
          data, spec, observation_pb2.ObservationSpec, path_prefix)
    ProtobufValidator._check_optional_fields(
        data, OBSERVATION_OPTIONAL_ENTITIES, spec, path_prefix)
    ProtobufValidator._check_repeated_count_matches(
        data.global_entities, 'global_entities', 'observations',
        spec.global_entities, 'global_entities', path_prefix)

  @staticmethod
  def check_data(data, spec, path_prefix, check_spec_class):
    """Check that a data proto conforms to the provided spec proto.

    To keep traversal of the data and spec protos separate from validation,
    this method does not recursively validate the provided data proto. To
    traverse and validate a data proto use ProtobufNode.data_to_proto_nest().

    Args:
      data: Data protobuf.
      spec: Spec protobuf.
      path_prefix: String path to the protobuf.
      check_spec_class: Whether this method should check the spec proto class.

    Raises:
      TypingError: If the data protobuf does not conform the spec protobuf or
        the data proto is not supported.
    """
    if not ProtobufValidator._DATA_PROTO_CLASS_TO_VALIDATOR:
      ProtobufValidator._DATA_PROTO_CLASS_TO_VALIDATOR = {
          action_pb2.ActionData: ProtobufValidator._check_action_data,
          action_pb2.Action: ProtobufValidator._check_action,
          action_pb2.Joystick: ProtobufValidator._check_joystick,
          observation_pb2.EntityField: ProtobufValidator._check_entity_field,
          observation_pb2.Entity: ProtobufValidator._check_entity,
          observation_pb2.Feeler: ProtobufValidator._check_feeler,
          observation_pb2.ObservationData: ProtobufValidator._check_observation,
          primitives_pb2.Category: ProtobufValidator._check_category,
          primitives_pb2.Number: ProtobufValidator._check_number,
          primitives_pb2.Position: ProtobufValidator._check_position,
          primitives_pb2.Rotation: ProtobufValidator._check_rotation,
      }
    validator = (
        ProtobufValidator._DATA_PROTO_CLASS_TO_VALIDATOR.get(type(data)))
    if not validator:
      raise TypingError(f'Validator not found for {type(data).__qualname__} at '
                        f'"{path_prefix}".')
    validator(data, spec, path_prefix, check_spec_class)


class ProtobufDataValidationOptions:
  """Options that control validation of data protos against spec protos."""

  def __init__(self, check_feeler_data_with_spec=True):
    """Initialize options.

    Args:
      check_feeler_data_with_spec: Whether to check each feeler proto against
        the spec. This operation is very expensive with large numbers of
        feelers. If the data has already been validated it is preferable to
        disable feeler validation.
    """
    self.check_feeler_data_with_spec = check_feeler_data_with_spec


class ProtobufNode:
  """Class that references a node in a protobuf.

  Attributes:
    proto: Referenced protobuf instance.
  """

  # Lazily initialized by _from_spec().
  _SPEC_PROTOCLASS_TO_PARSER = None

  def __init__(self, name, proto, proto_field_name):
    """Initialize this instance.

    Args:
      name: Human readable name of the node.
      proto: Protobuf instance.
      proto_field_name: Name of this field in the parent proto.
    """
    self._proto = proto
    self._name = name
    self._proto_field_name = proto_field_name
    self._children_by_proto_field_name = collections.OrderedDict()
    self._parent = None
    self._update_path()

  @property
  def children(self):
    """Get the sequence of children of this node."""
    return tuple(self._children_by_proto_field_name.values())

  @property
  def proto(self):
    """Get the protobuf owned by this node."""
    return self._proto

  @property
  def proto_field_name(self):
    """Get the name of this field in the parent proto."""
    return self._proto_field_name

  def child_by_proto_field_name(self, proto_field_name):
    """Get a child node by proto_field_name.

    Args:
      proto_field_name: Name of the child field.

    Returns:
      ProtobufNode instance if found, None otherwise.
    """
    return self._children_by_proto_field_name.get(proto_field_name)

  @property
  def parent(self):
    """Get the parent node of this node."""
    return self._parent

  @property
  def name(self):
    """Name of this node."""
    return self._name

  @property
  def path(self):
    """Human readable path of this node relative to its' ancestors."""
    return self._path

  def _update_path(self):
    """Update the human readable path of this node relative to ancestors."""
    parent = self.parent
    if parent:
      parent_path = parent._path  # pylint: disable=protected-access
      self._path = '/'.join([parent_path, self.name])
    else:
      self._path = self.name
    for child in self.children:
      child._update_path()  # pylint: disable=protected-access

  def add_children(self, children):
    """Add children node to this instance.

    Args:
      children: Sequence of ProtobufNode instances to add as children of this
        node.

    Returns:
      Reference to this node.
    """
    for child in children:
      assert child.proto_field_name not in self._children_by_proto_field_name
      # pylint: disable=protected-access
      child._remove_from_parent(update_path=False)
      child._parent = self  # pylint: disable=protected-access
      self._children_by_proto_field_name[child.proto_field_name] = child
      child._update_path()  # pylint: disable=protected-access
    return self

  def remove_from_parent(self):
    """Remove this node from its parent."""
    self._remove_from_parent()

  def _remove_from_parent(self, update_path=True):
    """Remove this node from its parent.

    Args:
      update_path: Whether to update this node's cached path.
    """
    if self._parent:
      # pylint: disable=protected-access
      del self._parent._children_by_proto_field_name[self.proto_field_name]
      self._parent = None
      if update_path:
        self._update_path()

  def __eq__(self, other):
    """Compare for equality with another ProtobufNode instance.

    Args:
      other: ProtobufNode instance to compare with.

    Returns:
      True if they're equivalent, False otherwise.
    """
    if not (other and issubclass(type(other), type(self))):
      return False
    if self.name != other.name:
      return False
    if self.proto_field_name != other.proto_field_name:
      return False
    if self.proto != other.proto:
      return False
    if len(self.children) != len(other.children):
      return False
    for this_child, other_child in zip(self.children, other.children):
      if this_child == other_child:
        continue
      return False
    return True

  def __ne__(self, other):
    """Compare for inequality with another ProtobufNode instance.

    Args:
      other: ProtobufNode instance to compare with.

    Returns:
      True if they're not equivalent, False otherwise.
    """
    return not self.__eq__(other)

  def __str__(self):
    """Construct a string representation.

    Returns:
      String representation of this instance.
    """
    children_string = ', '.join([str(child) for child in self.children])
    return (f'{self.name}: '
            f'(proto=({type(self.proto).__qualname__}, '
            f'{self.proto_field_name}: {self.proto}), '
            f'children=[{children_string}])')

  def as_nest(self, include_self=True):
    """Generate a nested dictionary from this node.

    Args:
      include_self: Whether to include this node in the returned nest.

    Returns:
      Nested dictionary with leaf values referencing ProtobufNode instances that
      correspond to leaves in this tree.
    """
    children = self.children
    if children:
      child_nest = {}
      nest = {self.name: child_nest}
      for child in self.children:
        child_nest[child.name] = child.as_nest(include_self=False)
    else:
      nest = {self.name: self}
    return nest if include_self else nest[self.name]

  @staticmethod
  def _infer_path_components_from_spec(spec, name, parent_path):
    """Infer path components from a spec proto.

    Args:
      spec: Spec proto to query.
      name: Override for the proto name.
      parent_path: String path to the proto.

    Returns:
      (name, parent_path, path) where:
      * name is the overridden name or the name derived from the spec proto.
      * parent_path is the supplied parent_path or an empty string if it was
        None.
      * path is the constructed path to the proto
    """
    parent_path = parent_path if parent_path else ''
    name = name if name else _get_proto_name(spec)
    path = _concat_path(parent_path, name)
    return (name, parent_path, path)

  @staticmethod
  def _from_leaf_spec(spec, name, unused_parent_path, proto_field_name):
    """Parse a leaf spec protobuf into a ProtobufNode instance.

    Args:
      spec: Protobuf to wrap in a ProtobufNode instance.
      name: Name of the node.
      unused_parent_path: Ignored.
      proto_field_name: Name of this proto field in the parent proto.

    Returns:
      ProtobufNode instance.
    """
    return ProtobufNode(name, spec, proto_field_name)

  @staticmethod
  def _from_entity_field_type(spec, name, parent_path, proto_field_name):
    """Parse an EntityFieldType protobuf into a ProtobufNode.

    Args:
      spec: Protobuf to wrap in a ProtobufNode instance.
      name: Name of the node.
      parent_path: String path to this protobuf.
      proto_field_name: Name of this proto field in the parent proto.

    Returns:
      ProtobufNode instance.
    """
    spec_field = getattr(spec, spec.WhichOneof('type'))
    return ProtobufNode._from_spec(spec_field, name, parent_path,
                                   proto_field_name)

  @staticmethod
  def _from_entity_type(spec, name, parent_path, proto_field_name):
    """Parse an EntityType protobuf into a ProtobufNode.

    Args:
      spec: Protobuf to wrap in a ProtobufNode instance.
      name: Name of the node.
      parent_path: String path to this protobuf.
      proto_field_name: Name of this proto field in the parent proto.

    Returns:
      ProtobufNode instance.
    """
    name, _, path = ProtobufNode._infer_path_components_from_spec(
        spec, name, parent_path)
    # Add top level "entity" node that is assigned the name of the entity.
    node = ProtobufNode(name, spec, proto_field_name)
    # Add built-in fields and custom named fields as children.
    fields = []
    for field_name, field_proto in _get_optional_fields_from_proto(
        spec, ENTITY_OPTIONAL_FIELDS):
      fields.append((field_name, field_proto, field_name))

    for _, field_name, field_proto in _label_repeated_field(
        spec, 'entity_fields'):
      fields.append((field_proto.name, field_proto, field_name))

    for node_name, field_proto, field_name in fields:
      node.add_children([ProtobufNode._from_spec(field_proto, node_name, path,
                                                 field_name)])
    return node

  @staticmethod
  def _from_brain_spec(spec, name, parent_path, proto_field_name):
    """Parse an BrainSpec protobuf into a ProtobufNode.

    Args:
      spec: Protobuf to wrap in a ProtobufNode instance.
      name: Name of the node.
      parent_path: String path to this protobuf.
      proto_field_name: Name of this proto field in the parent proto.

    Returns:
      ProtobufNode instance.
    """
    name, _, path = ProtobufNode._infer_path_components_from_spec(
        spec, name, parent_path)

    # Add top level "brain spec" node.
    node = ProtobufNode(name, spec, proto_field_name)

    # Add observation and action specs.
    node.add_children([
        ProtobufNode._from_observation_spec(spec.observation_spec,
                                            'observation_spec', path,
                                            'observation_spec'),
        ProtobufNode._from_action_spec(spec.action_spec, 'action_spec', path,
                                       'action_spec')
    ])
    return node

  @staticmethod
  def _from_observation_spec(spec, name, parent_path, proto_field_name):
    """Parse an ObservationSpec protobuf into a ProtobufNode.

    Args:
      spec: Protobuf to wrap in a ProtobufNode instance.
      name: Name of the node.
      parent_path: String path to this protobuf.
      proto_field_name: Name of this proto field in the parent proto.

    Returns:
      ProtobufNode instance.
    """
    name, _, path = ProtobufNode._infer_path_components_from_spec(spec, name,
                                                                  parent_path)
    # Add top level "observations" node.
    node = ProtobufNode(name, spec, proto_field_name)
    # Add observations/{entity_name} for each of the built-in entities.
    for field_name, field_proto in _get_optional_fields_from_proto(
        spec, OBSERVATION_OPTIONAL_ENTITIES):
      node.add_children([ProtobufNode._from_spec(field_proto, field_name, path,
                                                 field_name)])

    # Add observations/global_entities/{i} for each of the global entities.
    if spec.global_entities:
      global_entities_node = ProtobufNode('global_entities',
                                          spec.global_entities,
                                          'global_entities')
      node.add_children([global_entities_node])
      for i, global_entity_spec in enumerate(spec.global_entities):
        global_entities_node.add_children([
            ProtobufNode._from_spec(global_entity_spec, str(i), path,
                                    f'global_entities[{i}]')])
    return node

  @staticmethod
  def _from_action_type(spec, name, parent_path, proto_field_name):
    """Parse an ActionType protobuf into a ProtobufNode.

    Args:
      spec: Protobuf to wrap in a ProtobufNode instance.
      name: Name of the node.
      parent_path: String path to this protobuf.
      proto_field_name: Name of this proto field in the parent proto.

    Returns:
      ProtobufNode instance.
    """
    # Create a node for the action using the name supplied by the caller.
    spec_field = getattr(spec, spec.WhichOneof('action_types'))
    return ProtobufNode._from_spec(spec_field, name, parent_path,
                                   proto_field_name)

  @staticmethod
  def _from_action_spec(spec, name, parent_path, proto_field_name):
    """Parse an ActionSpec protobuf into a ProtobufNode.

    Args:
      spec: Protobuf to wrap in a ProtobufNode instance.
      name: Name of the node.
      parent_path: String path to this protobuf.
      proto_field_name: Name of this proto field in the parent proto.

    Returns:
      ProtobufNode instance.
    """
    name, _, path = ProtobufNode._infer_path_components_from_spec(spec, name,
                                                                  parent_path)
    # Add top level "actions" node.
    node = ProtobufNode(name, spec, proto_field_name)
    # Add actions/{actions_type.name} node for each named action.
    for i, action_type in enumerate(spec.actions):
      node.add_children([
          ProtobufNode._from_spec(action_type, action_type.name, path,
                                  f'actions[{i}]')])
    return node

  @staticmethod
  def _from_spec(spec, name, parent_path, proto_field_name):
    """Parse a spec protobuf into a tree of ProtobufNode instances.

    Args:
      spec: Protobuf to parse and validate.
      name: Name of the top level node to create. If this isn't specified it's
        derived from spec.name or the name of the protobuf type.
      parent_path: String path to the current node.
      proto_field_name: Name of this proto field in the parent proto.

    Returns:
      ProtobufNode instance that references the spec protobuf and its' children.

    Raises:
      InvalidSpecError: If the spec is missing required fields, observations
        or actions are missing names, use reserved names or have duplicate
        names.
    """
    _, _, path = ProtobufNode._infer_path_components_from_spec(spec, name,
                                                               parent_path)
    ProtobufValidator.check_spec(spec, path)

    if not ProtobufNode._SPEC_PROTOCLASS_TO_PARSER:
      ProtobufNode._SPEC_PROTOCLASS_TO_PARSER = {
          action_pb2.ActionSpec: ProtobufNode._from_action_spec,
          action_pb2.ActionType: ProtobufNode._from_action_type,
          action_pb2.JoystickType: ProtobufNode._from_leaf_spec,
          brain_pb2.BrainSpec: ProtobufNode._from_brain_spec,
          observation_pb2.EntityFieldType: ProtobufNode._from_entity_field_type,
          observation_pb2.EntityType: ProtobufNode._from_entity_type,
          observation_pb2.FeelerType: ProtobufNode._from_leaf_spec,
          observation_pb2.ObservationSpec: ProtobufNode._from_observation_spec,
          primitives_pb2.CategoryType: ProtobufNode._from_leaf_spec,
          primitives_pb2.NumberType: ProtobufNode._from_leaf_spec,
          primitives_pb2.PositionType: ProtobufNode._from_leaf_spec,
          primitives_pb2.RotationType: ProtobufNode._from_leaf_spec
      }

    parser = ProtobufNode._SPEC_PROTOCLASS_TO_PARSER.get(type(spec))
    if not parser:
      raise InvalidSpecError(
          f'Unknown spec type: {type(spec).__qualname__} ({spec} at '
          f'"{parent_path}")')
    return parser(spec, name, parent_path, proto_field_name)

  @staticmethod
  def from_spec(spec, name=None, parent_path=None):
    """Parse a spec protobuf into a tree of ProtobufNode instances.

    Args:
      spec: Protobuf to parse and validate.
      name: Name of the top level node to create. If this isn't specified it's
        derived from spec.name or the name of the protobuf type.
      parent_path: String path to the current node.

    Returns:
      ProtobufNode instance that references the spec protobuf and its' children.

    Raises:
      InvalidSpecError: If the spec is missing required fields, observations
        or actions are missing names, use reserved names or have duplicate
        names.
    """
    return ProtobufNode._from_spec(spec, name, parent_path, '')

  def _leaf_data_to_proto_nest(self, data, mapper, check_spec_class,
                               unused_options):
    """Wrap a data proto in a nest.

    Args:
      data: Data proto to wrap in a dictionary..
      mapper: Optional (proto, path) callable to execute for each leaf proto.
      check_spec_class: Whether this method should check the spec proto class.
      unused_options: Unused.

    Returns:
      Dictionary containing the supplied data keyed by the node name.
    """
    ProtobufValidator.check_data(data, self.proto, self.path,
                                 check_spec_class)
    return {self.name: mapper(data, self.path)}

  def _feeler_to_proto_nest(self, data, mapper, check_spec_class, options):
    """Wrap a feeler data proto in a nest.

    Args:
      data: Data proto to wrap in a dictionary.
      mapper: Optional (proto, path) callable to execute for each leaf proto.
      check_spec_class: Whether this method should check the spec proto class.
      options: ProtobufDataValidationOptions instance.

    Returns:
      Dictionary containing the supplied data keyed by the node name.
    """
    if options.check_feeler_data_with_spec:
      ProtobufValidator.check_data(data, self.proto, self.path,
                                   check_spec_class)
    return {self.name: mapper(data, self.path)}

  def _observation_data_to_proto_nest(self, data, mapper, check_spec_class,
                                      options):
    """Convert an ObservationData proto into a nest of protos.

    Args:
      data: ObservationData proto.
      mapper: Optional (proto, path) callable to execute for each leaf proto.
      check_spec_class: Whether this method should check the spec proto class.
      options: ProtobufDataValidationOptions instance.

    Returns:
      Nest of data protos.
    """
    ProtobufValidator.check_data(data, self.proto, self.path, check_spec_class)
    child_nest = {}
    nest = {self.name: child_nest}
    for data_field_name, data_field_proto in _get_optional_fields_from_proto(
        data, OBSERVATION_OPTIONAL_ENTITIES):
      spec_node = self.child_by_proto_field_name(data_field_name)
      # pylint: disable=protected-access
      child_nest.update(spec_node._entity_to_proto_nest(data_field_proto,
                                                        mapper, False, options))

    if data.global_entities:
      global_entities_spec_node = self.child_by_proto_field_name(
          'global_entities')
      global_entities_nest = {}
      child_nest['global_entities'] = global_entities_nest
      for _, data_field_name, data_field_proto in _label_repeated_field(
          data, 'global_entities'):
        spec_node = global_entities_spec_node.child_by_proto_field_name(
            data_field_name)
        # pylint: disable=protected-access
        global_entities_nest.update(spec_node._entity_to_proto_nest(
            data_field_proto, mapper, False, options))
    return nest

  def _entity_to_proto_nest(self, data, mapper, check_spec_class, options):
    """Convert an Entity proto into a nest of protos.

    Args:
      data: Entity proto.
      mapper: Optional (proto, path) callable to execute for each leaf proto.
      check_spec_class: Whether this method should check the spec proto class.
      options: ProtobufDataValidationOptions instance.

    Returns:
      Nest of data protos.
    """
    ProtobufValidator.check_data(data, self.proto, self.path, check_spec_class)
    child_nest = {}
    nest = {self.name: child_nest}
    for data_field_name, data_field_proto in _get_optional_fields_from_proto(
        data, ENTITY_OPTIONAL_FIELDS):
      spec_node = self.child_by_proto_field_name(data_field_name)
      # pylint: disable=protected-access
      child_nest.update(spec_node._data_to_proto_nest(
          data_field_proto, mapper, False, options))

    for i, data_field_name, data_field_proto in _label_repeated_field(
        data, 'entity_fields'):
      spec_node = self.child_by_proto_field_name(data_field_name)
      ProtobufValidator.check_data(data_field_proto,
                                   self.proto.entity_fields[i],
                                   spec_node.path, False)
      # pylint: disable=protected-access
      child_nest.update(spec_node._data_to_proto_nest(
          getattr(data_field_proto, data_field_proto.WhichOneof('value')),
          mapper, False, options))
    return nest

  def _action_data_to_proto_nest(self, data, mapper, check_spec_class, options):
    """Convert an ActionData proto into a nest of protos.

    Args:
      data: ActionData proto.
      mapper: Optional (proto, path) callable to execute for each leaf proto.
      check_spec_class: Whether this method should check the spec proto class.
      options: ProtobufDataValidationOptions instance.

    Returns:
      Nest of data protos.
    """
    ProtobufValidator.check_data(data, self.proto, self.path, check_spec_class)
    child_nest = {}
    nest = {self.name: child_nest}
    for i, data_field_name, data_field_proto in _label_repeated_field(
        data, 'actions'):
      spec_node = self.child_by_proto_field_name(data_field_name)
      ProtobufValidator.check_data(data_field_proto,
                                   self.proto.actions[i],
                                   spec_node.path, False)
      # pylint: disable=protected-access
      child_nest.update(spec_node._data_to_proto_nest(
          getattr(data_field_proto, data_field_proto.WhichOneof('action')),
          mapper, False, options))
    return nest

  def _data_to_proto_nest(self, data, mapper, check_spec_class, options):
    """Convert the provided data into a dictionary tree (nest) of protos.

    Args:
      data: Data protobuf to parse, validate against the provided spec and
        split into a nest.
      mapper: Optional (proto, path) callable to execute for each leaf proto.
        proto is the leaf data proto and path is the ProtobufNode.path.
        The return value of this method replaces the leaf proto in the nest.
      check_spec_class: Whether this method should check the spec proto class.
      options: ProtobufDataValidationOptions instance.

    Returns:
      Nest of data protos.

    Raises:
      TypingError: If the data protobuf does not conform this node's spec
        protobuf.
    """
    mapper = mapper if mapper else lambda data, path: data
    proto_class_to_parser = {
        primitives_pb2.Category: self._leaf_data_to_proto_nest,
        primitives_pb2.Number: self._leaf_data_to_proto_nest,
        primitives_pb2.Position: self._leaf_data_to_proto_nest,
        primitives_pb2.Rotation: self._leaf_data_to_proto_nest,
        observation_pb2.Feeler: self._feeler_to_proto_nest,
        action_pb2.Joystick: self._leaf_data_to_proto_nest,
        observation_pb2.ObservationData: self._observation_data_to_proto_nest,
        observation_pb2.Entity: self._entity_to_proto_nest,
        action_pb2.ActionData: self._action_data_to_proto_nest,
    }
    parser = proto_class_to_parser.get(type(data))
    if not parser:
      raise TypingError(f'Data proto {type(data).__qualname__} is not '
                        'supported.')
    return parser(data, mapper, check_spec_class, options)

  def data_to_proto_nest(self, data, mapper=None, options=None):
    """Convert the provided data into a dictionary tree (nest) of protos.

    Args:
      data: Data protobuf to parse, validate against the provided spec and
        split into a nest.
      mapper: Optional (proto, path) callable to execute for each leaf proto.
        proto is the leaf data proto and path is the ProtobufNode.path.
        The return value of this method replaces the leaf proto in the nest.
      options: Optional ProtobufDataValidationOptions instance.

    Returns:
      Nest of data protos.

    Raises:
      TypingError: If the data protobuf does not conform this node's spec
        protobuf.
    """
    return self._data_to_proto_nest(
        data, mapper, True,
        options if options else ProtobufDataValidationOptions())


