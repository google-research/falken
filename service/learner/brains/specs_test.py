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

"""Tests for specs."""

# pylint: disable=g-bad-import-order
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from google.protobuf import text_format
from tf_agents.specs import tensor_spec

import numpy as np
import tensorflow as tf

import common.generate_protos  # pylint: disable=unused-import
import action_pb2
import brain_pb2
import observation_pb2
import primitives_pb2
from learner.brains import specs

_OBSERVATION_SPEC = """
  player {
    position {}
    rotation {}
    entity_fields {
      name: "panache"
      number {
        minimum: 0.0
        maximum: 100.0
      }
    }
    entity_fields {
      name: "favorite_poison"
      category {
        enum_values: "GIN"
        enum_values: "ABSINTH"
        enum_values: "BATTERY_ACID"
      }
    }
    entity_fields {
      name: "feeler"
      feeler {
        count: 3
        distance {
            minimum: 0.0
            maximum: 100.0
        }
        yaw_angles: [-10.0, 0, 10.0]
        experimental_data: {
          minimum: 0.0
          maximum: 100.0
        }
      }
    }
  }
  camera {
    position {}
    rotation {}
  }
  global_entities {
    rotation { }
    entity_fields {
      name: "pizzazz"
      number {
        minimum: 0.0
        maximum: 100.0
      }
    }
  }
  global_entities {
    entity_fields {
      name: "chutzpah"
      number {
        minimum: 0.0
        maximum: 100.0
      }
    }
  }
"""


_OBSERVATION_DATA = """
  player {
    position {
      x: 0
      y: 10
      z: 20
    }
    rotation {
      w: 1
    }
    entity_fields {
      number {
        value: 60.0
      }
    }
    entity_fields {
      category {
        value: 1
      }
    }
    entity_fields {
      feeler {
        measurements: {
          distance {
            value: 1.0
          }
          experimental_data: {
            value: 1.1
          }
        }
        measurements: {
          distance {
            value: 2.0
          }
          experimental_data: {
            value: 2.1
          }
        }
        measurements: {
          distance {
            value: 3.0
          }
          experimental_data: {
            value: 3.1
          }
        }
      }
    }
  }
  camera {
    position {
      x: 10
      y: 10
      z: 10
    }
    rotation {
      w: 1
    }
  }
  global_entities {
    rotation {
      x: 0
      y: 0
      z: 0
      w: 1
    }
    entity_fields {
      number {
        value: 64
      }
    }
  }
  global_entities {
    entity_fields {
      number {
        value: 34
      }
    }
  }
"""


_ACTION_SPEC = """
  actions {
    name: "what_do"
    category {
      enum_values: "STAY"
      enum_values: "GO"
    }
  }
  actions {
    name: "trouble"
    number {
      minimum: 1000
      maximum: 2000
    }
  }
  actions {
    name: "left_stick"
    joystick {
      axes_mode: DIRECTION_XZ
      controlled_entity: "player"
      control_frame: "player"
    }
  }
  actions {
    name: "right_stick"
    joystick {
      axes_mode: DELTA_PITCH_YAW
      controlled_entity: "camera"
    }
  }
"""


_ACTION_DATA = """
  source: 2
  actions {
    category {
      value: 1
    }
  }
  actions {
    number {
      value: 1500
    }
  }
  actions {
    joystick {
      x_axis: 0
      y_axis: 1
    }
  }
  actions {
    joystick {
      x_axis: -1
      y_axis: 0
    }
  }
"""


class ProtobufValidatorTest(parameterized.TestCase):
  """Test ProtobufValidator."""

  def test_check_category_type_valid(self):
    """Check a valid CategoryType proto."""
    spec = primitives_pb2.CategoryType()
    spec.enum_values.append('gin')
    spec.enum_values.append('tonic')
    specs.ProtobufValidator.check_spec(spec, 'observations/player/drink')

  @parameterized.named_parameters(('EmptyCategory', []),
                                  ('SingleCategory', ['gin']))
  def test_check_category_type_not_enough_categories(self, categories):
    """Ensure validation fails with not enough categories."""
    spec = primitives_pb2.CategoryType()
    spec.enum_values.extend(categories)
    with self.assertRaisesWithLiteralMatch(
        specs.InvalidSpecError,
        'observations/player/drink has less than two categories: '
        f'{categories}.'):
      specs.ProtobufValidator.check_spec(spec, 'observations/player/drink')

  def test_check_number_type_valid(self):
    """Check a valid NumberType proto."""
    spec = primitives_pb2.NumberType()
    spec.minimum = 1
    spec.maximum = 42
    specs.ProtobufValidator.check_spec(spec, 'observations/player/health')

  @parameterized.named_parameters(
      ('ReservedNamePosition', 1.0, 1.0),
      ('ReservedNameRotation', -1.0, 1.0))
  def test_check_number_type_invalid_range(self, maximum, minimum):
    """Ensure validation fails with an invalid number range."""
    spec = primitives_pb2.NumberType()
    spec.minimum = minimum
    spec.maximum = maximum
    with self.assertRaisesWithLiteralMatch(
        specs.InvalidSpecError,
        'observations/player/health has invalid or missing range: '
        f'[{minimum}, {maximum}].'):
      specs.ProtobufValidator.check_spec(spec, 'observations/player/health')

  def test_check_number_type_no_range(self):
    spec = primitives_pb2.NumberType()
    with self.assertRaisesWithLiteralMatch(
        specs.InvalidSpecError,
        'observations/player/health has invalid or missing range: [0.0, 0.0].'):
      specs.ProtobufValidator.check_spec(spec, 'observations/player/health')

  def test_check_feeler_type_valid(self):
    """Check valid FeelerType proto."""
    spec = observation_pb2.FeelerType()
    spec.count = 2
    spec.distance.minimum = 1
    spec.distance.maximum = 5
    spec.yaw_angles.extend([-2, 2])
    data = spec.experimental_data.add()
    data.minimum = 0
    data.maximum = 9
    specs.ProtobufValidator.check_spec(spec, 'observations/player/feeler')

  def test_check_feeler_type_invalid_distance(self):
    """Ensure FeelerType validation fails with invalid distance range."""
    spec = observation_pb2.FeelerType()
    spec.count = 2
    spec.distance.minimum = 2
    spec.distance.maximum = 2
    spec.yaw_angles.extend([-2, 2])
    data = spec.experimental_data.add()
    data.minimum = 0
    data.maximum = 9
    with self.assertRaisesWithLiteralMatch(
        specs.InvalidSpecError,
        'observations/player/feeler/distance has invalid or '
        'missing range: [2.0, 2.0].'):
      specs.ProtobufValidator.check_spec(spec, 'observations/player/feeler')

  def test_check_feeler_type_invalid_experimental_data(self):
    """Ensure FeelerType validation fails with a invalid experimental data."""
    spec = observation_pb2.FeelerType()
    spec.count = 2
    spec.distance.minimum = 1
    spec.distance.maximum = 5
    spec.yaw_angles.extend([-2, 2])
    data = spec.experimental_data.add()
    data.minimum = 4
    data.maximum = 4
    with self.assertRaisesWithLiteralMatch(
        specs.InvalidSpecError,
        'observations/player/feeler/experimental_data[0] has '
        'invalid or missing range: [4.0, 4.0].'):
      specs.ProtobufValidator.check_spec(spec, 'observations/player/feeler')

  def test_check_feeler_type_mismatched_yaw_angles(self):
    """Ensure FeelerType validation fails with a invalid yaw angles."""
    spec = observation_pb2.FeelerType()
    spec.count = 2
    spec.distance.minimum = 1
    spec.distance.maximum = 5
    spec.yaw_angles.extend([-2, 2, 3])
    data = spec.experimental_data.add()
    data.minimum = 0
    data.maximum = 9
    with self.assertRaisesWithLiteralMatch(
        specs.InvalidSpecError,
        'observations/player/feeler has 3 yaw_angles that '
        'mismatch feeler count 2.'):
      specs.ProtobufValidator.check_spec(spec, 'observations/player/feeler')

  def test_check_joystick_type_valid(self):
    """Check valid JoystickType protos."""
    spec = action_pb2.JoystickType()
    spec.controlled_entity = 'player'
    spec.axes_mode = action_pb2.DELTA_PITCH_YAW
    specs.ProtobufValidator.check_spec(spec, 'actions/joystick')

    spec = action_pb2.JoystickType()
    spec.controlled_entity = 'player'
    spec.control_frame = 'camera'
    spec.axes_mode = action_pb2.DIRECTION_XZ
    specs.ProtobufValidator.check_spec(spec, 'actions/joystick')

  def test_check_joystick_type_no_axes_mode(self):
    """Ensure JoystickType validation fails with no joystick axes mode."""
    spec = action_pb2.JoystickType()
    spec.controlled_entity = 'player'
    with self.assertRaisesWithLiteralMatch(
        specs.InvalidSpecError, 'actions/joystick has undefined axes_mode.'):
      specs.ProtobufValidator.check_spec(spec, 'actions/joystick')

  def test_check_joystick_type_no_entity(self):
    """Ensure JoystickType validation fails with no controlled entity."""
    spec = action_pb2.JoystickType()
    spec.axes_mode = action_pb2.DELTA_PITCH_YAW
    with self.assertRaisesWithLiteralMatch(
        specs.InvalidSpecError, 'actions/joystick has no controlled_entity.'):
      specs.ProtobufValidator.check_spec(spec, 'actions/joystick')

  def test_check_joystick_type_invalid_control_frame(self):
    """Ensure JoystickType validation fails when no control frame is present."""
    spec = action_pb2.JoystickType()
    spec.controlled_entity = 'player'
    spec.axes_mode = action_pb2.DELTA_PITCH_YAW
    spec.control_frame = 'camera'
    with self.assertRaisesWithLiteralMatch(
        specs.InvalidSpecError,
        'actions/joystick has invalid control frame "camera". '
        'control_frame should only be set if axes_mode is '
        'DIRECTION_XZ, axes_mode is currently DELTA_PITCH_YAW.'):
      specs.ProtobufValidator.check_spec(spec, 'actions/joystick')

  def test_check_entity_field_type_valid(self):
    """Check valid EntityFieldType proto."""
    spec = observation_pb2.EntityFieldType()
    spec.category.enum_values.extend(['foo', 'bar'])
    specs.ProtobufValidator.check_spec(spec, 'observations/player')

    spec = observation_pb2.EntityFieldType()
    spec.number.minimum = 1
    spec.number.maximum = 2
    specs.ProtobufValidator.check_spec(spec, 'observations/player')

    spec = observation_pb2.EntityFieldType()
    spec.feeler.count = 1
    specs.ProtobufValidator.check_spec(spec, 'observations/player')

  def test_check_entity_field_type_no_type_set(self):
    """Ensure validation fails when EntityFieldType has no type."""
    spec = observation_pb2.EntityFieldType()
    with self.assertRaisesWithLiteralMatch(
        specs.InvalidSpecError,
        'observations/player type must have one of [category, number, '
        'feeler] set.'):
      specs.ProtobufValidator.check_spec(spec, 'observations/player')

  def test_check_entity_type_valid(self):
    """Check valid EntityType proto."""
    spec = observation_pb2.EntityType()
    specs.ProtobufValidator.check_spec(spec, 'observations/0')

    spec = observation_pb2.EntityType()
    spec.entity_fields.add().name = 'gaze'
    specs.ProtobufValidator.check_spec(spec, 'observations/0')

  @parameterized.named_parameters(
      ('ReservedNamePosition', 'position'),
      ('ReservedNameRotation', 'rotation'))
  def test_check_entity_type_reserved_name(self, name):
    """Ensure validation fails when a custom field has a reserved name."""
    spec = observation_pb2.EntityType()
    spec.entity_fields.add().name = name
    with self.assertRaisesWithLiteralMatch(
        specs.InvalidSpecError,
        f'observations/0/entity_field[0] has reserved name "{name}".'):
      specs.ProtobufValidator.check_spec(spec, 'observations/0')

  def test_check_entity_type_no_name(self):
    """Ensure validation fails when a custom field has no name."""
    spec = observation_pb2.EntityType()
    spec.entity_fields.add()
    with self.assertRaisesWithLiteralMatch(
        specs.InvalidSpecError, 'observations/0/entity_field[0] has no name.'):
      specs.ProtobufValidator.check_spec(spec, 'observations/0')

  def test_check_entity_type_duplicate_name(self):
    """Ensure validation fails when a custom field has a duplicate name."""
    spec = observation_pb2.EntityType()
    spec.entity_fields.add().name = 'foo'
    spec.entity_fields.add().name = 'foo'
    with self.assertRaisesWithLiteralMatch(
        specs.InvalidSpecError,
        'observations/0/entity_field[1] has name "foo" that already exists in '
        'observations/0'):
      specs.ProtobufValidator.check_spec(spec, 'observations/0')

  def test_check_action_type_valid(self):
    """Check valid ActionType proto."""
    spec = action_pb2.ActionType()
    spec.name = 'jump'
    spec.category.enum_values.extend(['false', 'true'])
    specs.ProtobufValidator.check_spec(spec, 'actions/jump')

  def test_check_action_type_no_type_set(self):
    """Ensure validation fails when ActionType has no type."""
    spec = action_pb2.ActionType()
    spec.name = 'jump'
    with self.assertRaisesWithLiteralMatch(
        specs.InvalidSpecError, 'actions/jump action_types must have one of '
        '[category, number, joystick] set.'):
      specs.ProtobufValidator.check_spec(spec, 'actions/jump')

  def test_check_action_spec_valid(self):
    """Check valid ActionSpec proto."""
    spec = action_pb2.ActionSpec()
    spec.actions.add().name = 'jump'
    specs.ProtobufValidator.check_spec(spec, 'actions')

  def test_check_action_spec_empty(self):
    spec = action_pb2.ActionSpec()
    with self.assertRaisesWithLiteralMatch(specs.InvalidSpecError,
                                           'actions is empty.'):
      specs.ProtobufValidator.check_spec(spec, 'actions')

  def test_check_action_spec_no_name(self):
    """Ensure validation fails when an ActionType field has no name."""
    spec = action_pb2.ActionSpec()
    spec.actions.add()
    with self.assertRaisesWithLiteralMatch(specs.InvalidSpecError,
                                           'actions/actions[0] has no name.'):
      specs.ProtobufValidator.check_spec(spec, 'actions')

  def test_check_action_spec_duplicate_name(self):
    """Ensure validation fails when an ActionType field has a duplicate name."""
    spec = action_pb2.ActionSpec()
    spec.actions.add().name = 'jump'
    spec.actions.add().name = 'jump'
    with self.assertRaisesWithLiteralMatch(
        specs.InvalidSpecError,
        'actions/actions[1] has duplicate name "jump".'):
      specs.ProtobufValidator.check_spec(spec, 'actions')

  def test_check_observation_spec_empty(self):
    spec = observation_pb2.ObservationSpec()
    with self.assertRaisesWithLiteralMatch(
        specs.InvalidSpecError,
        'observations must contain at least one non-camera entity.'):
      specs.ProtobufValidator.check_spec(spec, 'observations')

  def test_check_brain_spec_empty(self):
    spec = brain_pb2.BrainSpec()
    with self.assertRaisesWithLiteralMatch(
        specs.InvalidSpecError,
        'brain must have an observation spec and action spec.'):
      specs.ProtobufValidator.check_spec(spec, 'brain')

  def test_check_spec_unknown_proto(self):
    """Ensure spec validation fails when an unsupported proto is checked."""
    spec = brain_pb2.Brain()
    with self.assertRaisesWithLiteralMatch(
        specs.InvalidSpecError, 'Validator not found for Brain at "brain".'):
      specs.ProtobufValidator.check_spec(spec, 'brain')

  def test_check_unknown_proto(self):
    """Ensure data validation fails when an unsupported proto is checked."""
    data = brain_pb2.Brain()
    with self.assertRaisesWithLiteralMatch(
        specs.TypingError, 'Validator not found for Brain at "brain".'):
      specs.ProtobufValidator.check_data(data, brain_pb2.BrainSpec(), 'brain',
                                         True)

  def test_check_category(self):
    """Validate a category value that is in range."""
    spec = primitives_pb2.CategoryType()
    spec.enum_values.extend(['rose', 'lilly'])
    data = primitives_pb2.Category()
    data.value = 1
    specs.ProtobufValidator.check_data(data, spec, 'observations/player/item',
                                       True)

  @parameterized.named_parameters(
      ('BelowRange', -1),
      ('AboveRange', 2))
  def test_check_category_out_of_range(self, value):
    """Ensure validation fails when a category value is out of range."""
    spec = primitives_pb2.CategoryType()
    spec.enum_values.extend(['rose', 'lilly'])
    data = primitives_pb2.Category()
    data.value = value
    with self.assertRaisesWithLiteralMatch(
        specs.TypingError,
        f'observations/player/item category has value {value} '
        f'that is out of the specified range [0, 1] (rose, lilly).'):
      specs.ProtobufValidator.check_data(data, spec, 'observations/player/item',
                                         True)

  def test_check_number_valid(self):
    """Check a valid number."""
    spec = primitives_pb2.NumberType()
    spec.minimum = 2
    spec.maximum = 9
    data = primitives_pb2.Number()
    data.value = 2
    specs.ProtobufValidator.check_data(data, spec, 'observations/player/spirit',
                                       True)

  @parameterized.named_parameters(
      ('BelowRange', 1.0),
      ('AboveRange', 10.0))
  def test_check_number_out_of_range(self, value):
    """Ensure validation fails with a number out of range."""
    spec = primitives_pb2.NumberType()
    spec.minimum = 2
    spec.maximum = 9
    data = primitives_pb2.Number()
    data.value = value
    with self.assertRaisesWithLiteralMatch(
        specs.TypingError,
        f'observations/player/spirit number has value {value} '
        'that is out of the specified range [2.0, 9.0].'):
      specs.ProtobufValidator.check_data(data, spec,
                                         'observations/player/spirit', True)

  @staticmethod
  def _create_feeler_spec_and_data():
    """Create a valid feeler spec and data.

    Returns:
      (spec, data) where spec is a FeelerType proto and data is a Feeler proto.
    """
    spec = observation_pb2.FeelerType()
    spec.count = 2
    spec.distance.minimum = 0
    spec.distance.maximum = 42
    spec.yaw_angles.extend([-2, 2])
    # Categorical value with 3 potential values, one-hot encoded.
    number_of_categories = 3
    for _ in range(0, number_of_categories):
      experimental_data = spec.experimental_data.add()
      experimental_data.minimum = 0
      experimental_data.maximum = 1

    data = observation_pb2.Feeler()
    for distance_value, categorical_value in ((2, 0), (5, 2)):
      measurement = data.measurements.add()
      measurement.distance.value = distance_value
      for category in range(0, number_of_categories):
        experimental_data = measurement.experimental_data.add()
        experimental_data.value = 1 if categorical_value == category else 0
    return (spec, data)

  def test_check_feeler(self):
    """Check a valid feeler."""
    spec, data = ProtobufValidatorTest._create_feeler_spec_and_data()
    specs.ProtobufValidator.check_data(data, spec, 'observations/player/feeler',
                                       True)

  def test_check_feeler_invalid_measurements(self):
    """Ensure feeler validation fails with a measurement count mismatch."""
    spec, data = ProtobufValidatorTest._create_feeler_spec_and_data()
    del data.measurements[1]  # Remove the second feeler.

    with self.assertRaisesWithLiteralMatch(
        specs.TypingError, 'observations/player/feeler feeler has an invalid '
        'number of measurements 1 vs. expected 2.'):
      specs.ProtobufValidator.check_data(data, spec,
                                         'observations/player/feeler', True)

  def test_check_feeler_invalid_distance(self):
    """Ensure feeler validation fails with distance out of range."""
    spec, data = ProtobufValidatorTest._create_feeler_spec_and_data()
    data.measurements[1].distance.value = 43

    with self.assertRaisesWithLiteralMatch(
        specs.TypingError,
        'observations/player/feeler/measurements[1]/distance '
        'number has value 43.0 that is out of the specified range '
        '[0.0, 42.0].'):
      specs.ProtobufValidator.check_data(data, spec,
                                         'observations/player/feeler', True)

  def test_check_feeler_invalid_experimental_data(self):
    """Ensure feeler validation fails with mismatched categorical data."""
    spec, data = ProtobufValidatorTest._create_feeler_spec_and_data()
    del data.measurements[0].experimental_data[2]

    with self.assertRaisesWithLiteralMatch(
        specs.TypingError, 'observations/player/feeler/measurements[0] '
        'feeler contains 2 experimental_data vs. '
        'expected 3 experimental_data.'):
      specs.ProtobufValidator.check_data(data, spec,
                                         'observations/player/feeler', True)

  def test_check_feeler_experimental_data_out_of_range(self):
    """Ensure feeler validation fails with out of range categorical data."""
    spec, data = ProtobufValidatorTest._create_feeler_spec_and_data()
    data.measurements[0].experimental_data[1].value = 2

    with self.assertRaisesWithLiteralMatch(
        specs.TypingError,
        'observations/player/feeler/measurements[0]/experimental_data[1] '
        'number has value 2.0 that is out of the specified range [0.0, 1.0].'):
      specs.ProtobufValidator.check_data(data, spec,
                                         'observations/player/feeler', True)

  def test_check_entity_field_valid(self):
    """Check a valid EntityField."""
    data = observation_pb2.EntityField()
    data.category.value = 1
    spec = observation_pb2.EntityFieldType()
    spec.category.enum_values.extend(['false', 'true'])
    specs.ProtobufValidator.check_data(data, spec,
                                       'observations/player/shades_on', True)

  def test_check_entity_field_mismatched_type(self):
    """Ensure validation fails for EntityField with a mismatched type."""
    data = observation_pb2.EntityField()
    data.number.value = 1
    spec = observation_pb2.EntityFieldType()
    spec.category.enum_values.extend(['false', 'true'])
    with self.assertRaisesWithLiteralMatch(
        specs.TypingError,
        'observations/player/shades_on/value entity field "number" does not '
        'match the spec type "category".'):
      specs.ProtobufValidator.check_data(data, spec,
                                         'observations/player/shades_on', True)

  @staticmethod
  def _create_entity_spec_and_data():
    """Create a valid entity spec and data.

    Returns:
      (spec, data) where spec is an EntityType proto and data is an Entity
        proto.
    """
    data = observation_pb2.Entity()
    data.position.CopyFrom(primitives_pb2.Position())
    data.rotation.CopyFrom(primitives_pb2.Rotation())
    data.entity_fields.add()
    data.entity_fields.add()
    spec = observation_pb2.EntityType()
    spec.position.CopyFrom(primitives_pb2.PositionType())
    spec.rotation.CopyFrom(primitives_pb2.RotationType())
    spec.entity_fields.add()
    spec.entity_fields.add()
    return spec, data

  def test_check_entity_valid(self):
    """Check a valid Entity."""
    spec, data = ProtobufValidatorTest._create_entity_spec_and_data()
    specs.ProtobufValidator.check_data(data, spec, 'observations/player', True)

  def test_check_entity_optional_field_mismatch(self):
    """Ensure validation fails for Entity with mismatched optional fields."""
    spec, data = ProtobufValidatorTest._create_entity_spec_and_data()
    data.ClearField('position')
    with self.assertRaisesWithLiteralMatch(
        specs.TypingError,
        'observations/player entity does not have "position" but spec has '
        '"position".'):
      specs.ProtobufValidator.check_data(data, spec, 'observations/player',
                                         True)

    spec, data = ProtobufValidatorTest._create_entity_spec_and_data()
    spec.ClearField('rotation')
    with self.assertRaisesWithLiteralMatch(
        specs.TypingError,
        'observations/player entity has "rotation" but spec does not have '
        '"rotation".'):
      specs.ProtobufValidator.check_data(data, spec, 'observations/player',
                                         True)

  def test_check_entity_field_mismatch(self):
    """Ensure validation fails for Entity with mismatched fields."""
    spec, data = ProtobufValidatorTest._create_entity_spec_and_data()
    del data.entity_fields[1]
    with self.assertRaisesWithLiteralMatch(
        specs.TypingError,
        'observations/player entity contains 1 entity_fields vs. '
        'expected 2 entity_fields.'):
      specs.ProtobufValidator.check_data(data, spec, 'observations/player',
                                         True)

  def test_check_action_valid(self):
    """Check a valid Action."""
    data = action_pb2.Action()
    data.category.value = 1
    spec = action_pb2.ActionType()
    spec.category.enum_values.extend(['foo', 'bar'])
    specs.ProtobufValidator.check_data(data, spec, 'actions/shout', True)

  def test_check_action_value_mismatched_type(self):
    """Ensure validation fails for Action with a mismatched type."""
    data = action_pb2.Action()
    data.number.value = 1
    spec = action_pb2.ActionType()
    spec.category.enum_values.extend(['foo', 'bar'])
    with self.assertRaisesWithLiteralMatch(
        specs.TypingError, 'actions/shout/action action "number" does not '
        'match the spec action_types "category".'):
      specs.ProtobufValidator.check_data(data, spec, 'actions/shout', True)

  def test_check_action_data_valid(self):
    """Check a valid ActionData."""
    data = action_pb2.ActionData(
        source=action_pb2.ActionData.HUMAN_DEMONSTRATION)
    data.actions.add()
    spec = action_pb2.ActionSpec()
    spec.actions.add()
    specs.ProtobufValidator.check_data(data, spec, 'actions', True)

  def test_check_action_data_no_source(self):
    """Check ActionData with no source."""
    data = action_pb2.ActionData()
    data.actions.add()
    spec = action_pb2.ActionSpec()
    spec.actions.add()
    with self.assertRaisesWithLiteralMatch(
        specs.TypingError, 'ActionData action data\'s source is unknown.'):
      specs.ProtobufValidator.check_data(data, spec, 'ActionData', True)

  def test_check_action_data_mismatched_actions(self):
    """Ensure validation fails when the number of actions mismatch."""
    data = action_pb2.ActionData(
        source=action_pb2.ActionData.HUMAN_DEMONSTRATION)
    spec = action_pb2.ActionSpec()
    spec.actions.add()
    with self.assertRaisesWithLiteralMatch(
        specs.TypingError,
        'ActionData actions contains 0 actions vs. expected 1 actions.'):
      specs.ProtobufValidator.check_data(data, spec, 'ActionData', True)

  @staticmethod
  def _create_observation_spec_and_data():
    """Create a valid observation spec and data.

    Returns:
      (spec, data) where spec is an ObservationSpec proto and data is an
        ObservationData proto.
    """
    data = observation_pb2.ObservationData()
    data.player.entity_fields.add()
    data.global_entities.add()
    spec = observation_pb2.ObservationSpec()
    spec.player.entity_fields.add()
    spec.global_entities.add()
    return (spec, data)

  def test_check_observation_valid(self):
    """Check a valid Observation."""
    spec, data = ProtobufValidatorTest._create_observation_spec_and_data()
    specs.ProtobufValidator.check_data(data, spec, 'observations', True)

  def test_check_observation_mismatched_optional_entity(self):
    """Ensure Observation validation fails with a mismatched optional entity."""
    spec, data = ProtobufValidatorTest._create_observation_spec_and_data()
    data.camera.entity_fields.add()
    with self.assertRaisesWithLiteralMatch(
        specs.TypingError, 'observations entity has "camera" but spec does not '
        'have "camera".'):
      specs.ProtobufValidator.check_data(data, spec, 'observations', True)

  def test_check_observation_mismatched_global_entities(self):
    """Ensure Observation validation fails with a mismatched global entities."""
    spec, data = ProtobufValidatorTest._create_observation_spec_and_data()
    data.global_entities.add()
    with self.assertRaisesWithLiteralMatch(
        specs.TypingError,
        'observations observations contains 2 global_entities '
        'vs. expected 1 global_entities.',
    ):
      specs.ProtobufValidator.check_data(data, spec, 'observations', True)

  def test_check_joystick_valid(self):
    """Check a valid Joystick."""
    data = action_pb2.Joystick()
    data.x_axis = 0.707
    data.y_axis = -0.707
    specs.ProtobufValidator.check_data(data, action_pb2.JoystickType(),
                                       'left_stick', True)

  @parameterized.named_parameters(
      ('BelowRange', -2.0),
      ('AboveRange', 1.5))
  def test_check_joystick_out_of_range(self, value):
    """Ensure Joystick validation fails with out of range values."""
    data = action_pb2.Joystick()
    data.x_axis = value
    with self.assertRaisesWithLiteralMatch(
        specs.TypingError,
        f'left_stick joystick x_axis value {value} is out of '
        'range [-1.0, 1.0].'):
      specs.ProtobufValidator.check_data(data, action_pb2.JoystickType(),
                                         'left_stick', True)


class ProtobufNodeTest(parameterized.TestCase):
  """Test specs.ProtobufNode."""

  def test_construct(self):
    """Construct a ProtobufNode."""
    spec = observation_pb2.ObservationSpec()
    node = specs.ProtobufNode('foo', spec, 'fooey')
    self.assertEqual(node.name, 'foo')
    self.assertEqual(node.proto, spec)
    self.assertEqual(node.proto_field_name, 'fooey')
    self.assertCountEqual(node.children, [])
    self.assertIsNone(node.parent)

  def test_add_remove_children(self):
    """Test adding children to and removing children from a ProtobufNode."""
    spec = observation_pb2.ObservationSpec()
    # Add bish and bash as children of foo.
    foo = specs.ProtobufNode('foo', spec, 'fee')
    bish = specs.ProtobufNode('bish', spec, 'bishy')
    bash = specs.ProtobufNode('bash', spec, 'bashy')
    self.assertEqual(foo.add_children([bish, bash]), foo)
    self.assertCountEqual(foo.children, [bish, bash])
    self.assertEqual(foo.child_by_proto_field_name('bishy'), bish)
    self.assertEqual(foo.child_by_proto_field_name('bashy'), bash)
    self.assertEqual(bish.parent, foo)
    self.assertEqual(bash.parent, foo)

    # Add bosh to bar and move bash to bar.
    bar = specs.ProtobufNode('bar', spec, 'bee')
    bosh = specs.ProtobufNode('bosh', spec, 'boshy')
    self.assertEqual(bar.add_children([bash, bosh]), bar)
    self.assertCountEqual(bar.children, [bash, bosh])
    self.assertCountEqual(foo.children, [bish])
    self.assertEqual(bar.child_by_proto_field_name('boshy'), bosh)
    self.assertEqual(foo.child_by_proto_field_name('bishy'), bish)
    self.assertEqual(bash.parent, bar)
    self.assertEqual(bosh.parent, bar)
    self.assertEqual(bish.parent, foo)

    # Remove bosh from bar.
    bosh.remove_from_parent()
    self.assertIsNone(bosh.parent)
    self.assertCountEqual(bar.children, [bash])

  def test_get_path(self):
    """Get the path of a node relative to the root of a tree."""
    spec = observation_pb2.ObservationSpec()
    foo = specs.ProtobufNode('foo', spec, '')
    bar = specs.ProtobufNode('bar', spec, '')
    foo.add_children([bar])
    baz = specs.ProtobufNode('baz', spec, '')
    bar.add_children([baz])
    self.assertEqual(foo.path, 'foo')
    self.assertEqual(bar.path, 'foo/bar')
    self.assertEqual(baz.path, 'foo/bar/baz')

  def test_infer_path_components_from_spec_with_name(self):
    """Test constructing path components from a proto with a name."""
    spec = action_pb2.ActionType()
    spec.name = 'throttle'
    self.assertEqual(
        ('throttle', '', 'throttle'),
        specs.ProtobufNode._infer_path_components_from_spec(spec, None, None))
    self.assertEqual(
        ('throttle', 'actions', 'actions/throttle'),
        specs.ProtobufNode._infer_path_components_from_spec(spec, None,
                                                            'actions'))
    self.assertEqual(
        ('gas', 'actions', 'actions/gas'),
        specs.ProtobufNode._infer_path_components_from_spec(spec, 'gas',
                                                            'actions'))

  def test_infer_path_components_from_spec_no_name(self):
    """Test constructing path components from a proto without a name."""
    spec = observation_pb2.ObservationSpec()
    self.assertEqual(
        ('ObservationSpec', '', 'ObservationSpec'),
        specs.ProtobufNode._infer_path_components_from_spec(spec, None, None))
    self.assertEqual(
        ('ObservationSpec', 'brain', 'brain/ObservationSpec'),
        specs.ProtobufNode._infer_path_components_from_spec(spec, None,
                                                            'brain'))
    self.assertEqual(
        ('observations', 'brain', 'brain/observations'),
        specs.ProtobufNode._infer_path_components_from_spec(
            spec, 'observations', 'brain'))

  @mock.patch.object(specs.ProtobufValidator, 'check_spec')
  @mock.patch.object(specs.ProtobufNode, 'add_children')
  @mock.patch.object(specs.ProtobufNode, '_from_observation_spec')
  @mock.patch.object(specs.ProtobufNode, '_from_action_spec')
  def test_from_spec_brain_spec_calls_protobuf_validator(
      self, from_action_spec, from_observation_spec, add_children, check_spec):
    """Ensure from_spec() calls check_spec() and add_children()."""
    mock_action_node = mock.Mock()
    mock_observation_node = mock.Mock()
    from_action_spec.return_value = mock_action_node
    from_observation_spec.return_value = mock_observation_node
    observation_spec = observation_pb2.ObservationSpec()
    action_spec = action_pb2.ActionSpec()
    text_format.Parse(_OBSERVATION_SPEC, observation_spec)
    text_format.Parse(_ACTION_SPEC, action_spec)
    spec = brain_pb2.BrainSpec(
        observation_spec=observation_spec, action_spec=action_spec)
    specs.ProtobufNode.from_spec(spec)
    check_spec.assert_has_calls([mock.call(spec, 'BrainSpec')])
    from_action_spec.assert_has_calls([
        mock.call(spec.action_spec, 'action_spec', 'BrainSpec', 'action_spec')
    ])
    from_observation_spec.assert_has_calls([
        mock.call(spec.observation_spec, 'observation_spec', 'BrainSpec',
                  'observation_spec')
    ])
    add_children.assert_has_calls(
        [mock.call([mock_observation_node, mock_action_node])])

  @mock.patch.object(specs.ProtobufValidator, 'check_spec')
  def test_from_spec_observation_spec_calls_protobuf_validator(
      self, check_spec):
    """Ensure from_spec() calls ProtobufValidator.check_spec()."""
    spec = observation_pb2.ObservationSpec()
    text_format.Parse(_OBSERVATION_SPEC, spec)
    specs.ProtobufNode.from_spec(spec)
    check_spec.assert_has_calls([
        mock.call(spec, 'ObservationSpec'),
        mock.call(spec.player, 'ObservationSpec/player'),
        mock.call(spec.player.position, 'ObservationSpec/player/position'),
        mock.call(spec.player.rotation, 'ObservationSpec/player/rotation'),
        mock.call(spec.player.entity_fields[0],
                  'ObservationSpec/player/panache'),
        mock.call(spec.player.entity_fields[0].number,
                  'ObservationSpec/player/panache'),
        mock.call(spec.player.entity_fields[1],
                  'ObservationSpec/player/favorite_poison'),
        mock.call(spec.player.entity_fields[1].category,
                  'ObservationSpec/player/favorite_poison'),
        mock.call(spec.player.entity_fields[2],
                  'ObservationSpec/player/feeler'),
        mock.call(spec.player.entity_fields[2].feeler,
                  'ObservationSpec/player/feeler'),
        mock.call(spec.camera, 'ObservationSpec/camera'),
        mock.call(spec.camera.position, 'ObservationSpec/camera/position'),
        mock.call(spec.camera.rotation, 'ObservationSpec/camera/rotation'),
        mock.call(spec.global_entities[0], 'ObservationSpec/0'),
        mock.call(spec.global_entities[0].rotation,
                  'ObservationSpec/0/rotation'),
        mock.call(spec.global_entities[0].entity_fields[0],
                  'ObservationSpec/0/pizzazz'),
        mock.call(spec.global_entities[0].entity_fields[0].number,
                  'ObservationSpec/0/pizzazz'),
        mock.call(spec.global_entities[1], 'ObservationSpec/1'),
        mock.call(spec.global_entities[1].entity_fields[0],
                  'ObservationSpec/1/chutzpah'),
        mock.call(spec.global_entities[1].entity_fields[0].number,
                  'ObservationSpec/1/chutzpah'),
    ], any_order=True)

  @mock.patch.object(specs.ProtobufValidator, 'check_spec')
  def test_from_spec_action_spec_calls_protobuf_validator(self,
                                                          check_spec):
    """Ensure from_spec() calls ProtobufValidator.check_spec()."""
    spec = action_pb2.ActionSpec()
    text_format.Parse(_ACTION_SPEC, spec)
    specs.ProtobufNode.from_spec(spec)
    check_spec.assert_has_calls([
        mock.call(spec, 'ActionSpec'),
        mock.call(spec.actions[0], 'ActionSpec/what_do'),
        mock.call(spec.actions[0].category, 'ActionSpec/what_do'),
        mock.call(spec.actions[1], 'ActionSpec/trouble'),
        mock.call(spec.actions[1].number, 'ActionSpec/trouble'),
        mock.call(spec.actions[2], 'ActionSpec/left_stick'),
        mock.call(spec.actions[2].joystick, 'ActionSpec/left_stick'),
        mock.call(spec.actions[3], 'ActionSpec/right_stick'),
        mock.call(spec.actions[3].joystick, 'ActionSpec/right_stick'),
    ], any_order=True)

  @staticmethod
  def _create_protobuf_node_tree():
    """Create a test ProtobufNode tree."""
    obs = observation_pb2.ObservationSpec()
    return specs.ProtobufNode('observations', obs, '').add_children([
        specs.ProtobufNode('player', obs.player, 'player').add_children([
            specs.ProtobufNode('position', obs.player.position, 'position')]),
        specs.ProtobufNode('camera', obs.camera, 'camera').add_children([
            specs.ProtobufNode('rotation', obs.camera.rotation, 'rotation')])])

  def test_protobuf_node_equal(self):
    """Test equality and inequality of two ProtobufNode trees."""
    observations = ProtobufNodeTest._create_protobuf_node_tree()
    other_observations = ProtobufNodeTest._create_protobuf_node_tree()
    self.assertTrue(observations.__eq__(other_observations))
    self.assertFalse(observations.__ne__(other_observations))
    other_observations.children[-1].remove_from_parent()
    self.assertFalse(observations.__eq__(other_observations))
    self.assertTrue(observations.__ne__(other_observations))

  def test_protobuf_node_string(self):
    """Test conversion of ProtobufNode to a string."""
    observations = ProtobufNodeTest._create_protobuf_node_tree()
    self.assertEqual(
        'observations: (proto=(ObservationSpec, : ), children=['
        'player: (proto=(EntityType, player: ), children=['
        'position: (proto=(PositionType, position: ), children=[])]), '
        'camera: (proto=(EntityType, camera: ), children=['
        'rotation: (proto=(RotationType, rotation: ), children=[])])])'
        '', str(observations))

  def test_protobuf_node_as_nest(self):
    """Test conversion from a ProtobufNode instance tree to a nest."""
    observations = ProtobufNodeTest._create_protobuf_node_tree()
    player_position = observations.children[0].children[0]
    camera_rotation = observations.children[1].children[0]

    self.assertEqual(
        {'observations': {'player': {'position': player_position},
                          'camera': {'rotation': camera_rotation}}},
        observations.as_nest())
    self.assertEqual(
        {'player': {'position': player_position},
         'camera': {'rotation': camera_rotation}},
        observations.as_nest(include_self=False))

  def test_observation_spec_to_protobuf_nodes(self):
    """Test conversion from an ObservationSpec to ProtobufNode instances."""
    spec = observation_pb2.ObservationSpec()
    text_format.Parse(_OBSERVATION_SPEC, spec)
    observations = specs.ProtobufNode.from_spec(spec)
    expected = specs.ProtobufNode('ObservationSpec', spec, '').add_children([
        specs.ProtobufNode('player', spec.player, 'player').add_children([
            specs.ProtobufNode('position', spec.player.position, 'position'),
            specs.ProtobufNode('rotation', spec.player.rotation, 'rotation'),
            specs.ProtobufNode('panache', spec.player.entity_fields[0].number,
                               'entity_fields[0]'),
            specs.ProtobufNode('favorite_poison',
                               spec.player.entity_fields[1].category,
                               'entity_fields[1]'),
            specs.ProtobufNode('feeler',
                               spec.player.entity_fields[2].feeler,
                               'entity_fields[2]'),
        ]),
        specs.ProtobufNode('camera', spec.camera, 'camera').add_children([
            specs.ProtobufNode('position', spec.camera.position, 'position'),
            specs.ProtobufNode('rotation', spec.camera.rotation, 'rotation'),
        ]),
        specs.ProtobufNode(
            'global_entities', spec.global_entities,
            'global_entities').add_children([
                specs.ProtobufNode(
                    '0', spec.global_entities[0],
                    'global_entities[0]').add_children([
                        specs.ProtobufNode(
                            'rotation',
                            spec.global_entities[0].rotation,
                            'rotation'),
                        specs.ProtobufNode(
                            'pizzazz',
                            spec.global_entities[0].entity_fields[0].number,
                            'entity_fields[0]'),
                    ]),
                specs.ProtobufNode(
                    '1', spec.global_entities[1],
                    'global_entities[1]').add_children([
                        specs.ProtobufNode(
                            'chutzpah',
                            spec.global_entities[1].entity_fields[0].number,
                            'entity_fields[0]'),
                    ]),
            ]),
    ])
    self.assertEqual(str(expected), str(observations))

  def test_action_spec_to_protobuf_nodes(self):
    """Test conversion from an ActionSpec to ProtobufNode instances."""
    spec = action_pb2.ActionSpec()
    text_format.Parse(_ACTION_SPEC, spec)
    actions = specs.ProtobufNode.from_spec(spec)
    expected = specs.ProtobufNode(
        'ActionSpec', spec, '').add_children([
            specs.ProtobufNode('what_do', spec.actions[0].category,
                               'actions[0]'),
            specs.ProtobufNode('trouble', spec.actions[1].number,
                               'actions[1]'),
            specs.ProtobufNode('left_stick', spec.actions[2].joystick,
                               'actions[2]'),
            specs.ProtobufNode('right_stick', spec.actions[3].joystick,
                               'actions[3]'),
        ])
    self.assertEqual(str(expected), str(actions))

  def test_to_tfa_tensor_spec_invalid_type(self):
    """Ensure TensorSpec conversion from an invalid ProtobufNode fails."""
    node = specs.ProtobufNode('invalid', action_pb2.ActionSpec(), '')
    with self.assertRaisesWithLiteralMatch(
        specs.InvalidSpecError,
        'Unable to convert ActionSpec at "invalid" to TensorSpec.'):
      node.to_tfa_tensor_spec()

  def test_category_type_to_tfa_tensor_spec(self):
    """Test conversion from CategoryType ProtobufNode to BoundedTensorSpec."""
    spec = primitives_pb2.CategoryType()
    spec.enum_values.extend(['foo', 'bar', 'baz'])
    node = specs.ProtobufNode('test', spec, '')
    self.assertEqual(node.to_tfa_tensor_spec(),
                     tensor_spec.BoundedTensorSpec((1,), tf.int32, 0, 2,
                                                   name='test'))

  def test_number_type_to_tfa_tensor_spec(self):
    """Test conversion from NumberType ProtobufNode to BoundedTensorSpec."""
    spec = primitives_pb2.NumberType()
    spec.minimum = 1
    spec.maximum = 10
    node = specs.ProtobufNode('test', spec, '')
    self.assertEqual(node.to_tfa_tensor_spec(),
                     tensor_spec.BoundedTensorSpec((1,), tf.float32, 1, 10,
                                                   name='test'))

  def test_position_type_to_tfa_tensor_spec(self):
    """Test conversion from PositionType ProtobufNode to BoundedTensorSpec."""
    node = specs.ProtobufNode('test', primitives_pb2.PositionType(), '')
    self.assertEqual(node.to_tfa_tensor_spec(),
                     tensor_spec.TensorSpec((3,), tf.float32, name='test'))

  def test_rotation_type_to_tfa_tensor_spec(self):
    """Test conversion from RotationType ProtobufNode to BoundedTensorSpec."""
    node = specs.ProtobufNode('test', primitives_pb2.RotationType(), '')
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
    node = specs.ProtobufNode('test', spec, '')
    self.assertEqual(node.to_tfa_tensor_spec(),
                     tensor_spec.BoundedTensorSpec(
                         (2, 3,), tf.float32, minimum=10, maximum=100,
                         name='test'))

  def test_joystick_type_to_tfa_tensor_spec(self):
    """Test conversion from JoystickType ProtobufNode to BoundedTensorSpec."""
    node = specs.ProtobufNode('test', action_pb2.JoystickType(), '')
    self.assertEqual(node.to_tfa_tensor_spec(),
                     tensor_spec.BoundedTensorSpec(
                         (2,), tf.float32, minimum=-1, maximum=1, name='test'))

  def test_observation_data_to_protobuf_nest(self):
    """Test conversion from ObservationData to a protobuf nest."""
    mapped = []  # List of proto, name tuples that have been mapped.
    spec = observation_pb2.ObservationSpec()
    text_format.Parse(_OBSERVATION_SPEC, spec)
    data = observation_pb2.ObservationData()
    text_format.Parse(_OBSERVATION_DATA, data)
    nest = specs.ProtobufNode.from_spec(spec).data_to_proto_nest(
        data, mapper=lambda p, n: mapped.append((p, n)) or p)
    expected = {
        'ObservationSpec': {
            'player': {
                'position': data.player.position,
                'rotation': data.player.rotation,
                'panache': data.player.entity_fields[0].number,
                'favorite_poison': data.player.entity_fields[1].category,
                'feeler': data.player.entity_fields[2].feeler
            },
            'camera': {
                'position': data.camera.position,
                'rotation': data.camera.rotation,
            },
            'global_entities': {
                '0': {
                    'rotation': data.global_entities[0].rotation,
                    'pizzazz': data.global_entities[0].entity_fields[0].number,
                },
                '1': {
                    'chutzpah': data.global_entities[1].entity_fields[0].number,
                },
            },
        }
    }
    self.assertEqual(nest, expected)
    # Verify the mapper was applied.
    self.assertCountEqual(
        mapped,
        [(data.player.position, 'ObservationSpec/player/position'),
         (data.player.rotation, 'ObservationSpec/player/rotation'),
         (data.player.entity_fields[0].number,
          'ObservationSpec/player/panache'),
         (data.player.entity_fields[1].category,
          'ObservationSpec/player/favorite_poison'),
         (data.player.entity_fields[2].feeler,
          'ObservationSpec/player/feeler'),
         (data.camera.position, 'ObservationSpec/camera/position'),
         (data.camera.rotation, 'ObservationSpec/camera/rotation'),
         (data.global_entities[0].rotation,
          'ObservationSpec/global_entities/0/rotation'),
         (data.global_entities[0].entity_fields[0].number,
          'ObservationSpec/global_entities/0/pizzazz'),
         (data.global_entities[1].entity_fields[0].number,
          'ObservationSpec/global_entities/1/chutzpah')])

  def test_action_data_to_protobuf_nest(self):
    """Test conversion from ActionData to a protobuf nest."""
    mapped = []  # List of proto, name tuples that have been mapped.
    spec = action_pb2.ActionSpec()
    text_format.Parse(_ACTION_SPEC, spec)
    data = action_pb2.ActionData()
    text_format.Parse(_ACTION_DATA, data)
    nest = specs.ProtobufNode.from_spec(spec).data_to_proto_nest(
        data, mapper=lambda p, n: mapped.append((p, n)) or p)
    expected = {
        'ActionSpec': {
            'what_do': data.actions[0].category,
            'trouble': data.actions[1].number,
            'left_stick': data.actions[2].joystick,
            'right_stick': data.actions[3].joystick,
        },
    }
    self.assertEqual(nest, expected)
    # Verify the mapper was applied.
    self.assertEqual(
        mapped,
        [(data.actions[0].category, 'ActionSpec/what_do'),
         (data.actions[1].number, 'ActionSpec/trouble'),
         (data.actions[2].joystick, 'ActionSpec/left_stick'),
         (data.actions[3].joystick, 'ActionSpec/right_stick')])

  @mock.patch.object(specs.ProtobufValidator, 'check_data')
  def test_observation_data_to_protobuf_nest_calls_validator(self, check_data):
    """Verify all ObservationData nodes are validated against the spec."""
    spec = observation_pb2.ObservationSpec()
    text_format.Parse(_OBSERVATION_SPEC, spec)
    data = observation_pb2.ObservationData()
    text_format.Parse(_OBSERVATION_DATA, data)
    specs.ProtobufNode.from_spec(spec).data_to_proto_nest(data)
    # Check the subset of calls that represent all paths to protos.
    check_data.assert_has_calls([
        mock.call(data, spec, 'ObservationSpec', True),
        mock.call(data.player, spec.player, 'ObservationSpec/player', False),
        mock.call(data.player.position, spec.player.position,
                  'ObservationSpec/player/position', False),
        mock.call(data.player.rotation, spec.player.rotation,
                  'ObservationSpec/player/rotation', False),
        mock.call(data.player.entity_fields[0], spec.player.entity_fields[0],
                  'ObservationSpec/player/panache', False),
        mock.call(data.player.entity_fields[0].number,
                  spec.player.entity_fields[0].number,
                  'ObservationSpec/player/panache', False),
        mock.call(data.player.entity_fields[1], spec.player.entity_fields[1],
                  'ObservationSpec/player/favorite_poison', False),
        mock.call(data.player.entity_fields[1].category,
                  spec.player.entity_fields[1].category,
                  'ObservationSpec/player/favorite_poison', False),
        mock.call(data.player.entity_fields[2], spec.player.entity_fields[2],
                  'ObservationSpec/player/feeler', False),
        mock.call(data.player.entity_fields[2].feeler,
                  spec.player.entity_fields[2].feeler,
                  'ObservationSpec/player/feeler', False),
        mock.call(data.global_entities[0].rotation,
                  spec.global_entities[0].rotation,
                  'ObservationSpec/global_entities/0/rotation', False),
        mock.call(data.global_entities[0].entity_fields[0],
                  spec.global_entities[0].entity_fields[0],
                  'ObservationSpec/global_entities/0/pizzazz', False),
        mock.call(data.global_entities[0].entity_fields[0].number,
                  spec.global_entities[0].entity_fields[0].number,
                  'ObservationSpec/global_entities/0/pizzazz', False),
    ], any_order=True)

  @mock.patch.object(specs.ProtobufValidator, 'check_data')
  def test_action_data_to_protobuf_nest_calls_validator(self, check_data):
    """Verify all ActionData nodes are validated against the spec."""
    spec = action_pb2.ActionSpec()
    text_format.Parse(_ACTION_SPEC, spec)
    data = action_pb2.ActionData()
    text_format.Parse(_ACTION_DATA, data)
    specs.ProtobufNode.from_spec(spec).data_to_proto_nest(data)
    check_data.assert_has_calls([
        mock.call(data.actions[0], spec.actions[0],
                  'ActionSpec/what_do', False),
        mock.call(data.actions[0].category, spec.actions[0].category,
                  'ActionSpec/what_do', False),
        mock.call(data.actions[1].number, spec.actions[1].number,
                  'ActionSpec/trouble', False),
        mock.call(data.actions[2].joystick, spec.actions[2].joystick,
                  'ActionSpec/left_stick', False),
        mock.call(data.actions[3].joystick, spec.actions[3].joystick,
                  'ActionSpec/right_stick', False),
    ], any_order=True)


class SpecsTest(parameterized.TestCase):

  def test_spec_base_get_tfa_spec(self):
    """Convert from a spec proto to TF Agents TensorSpec nest."""
    spec = observation_pb2.ObservationSpec()
    spec.player.position.CopyFrom(primitives_pb2.PositionType())
    nest = specs.SpecBase(spec).tfa_spec
    expected_position_spec = tensor_spec.TensorSpec(
        shape=(3,), dtype=tf.float32, name='position')
    want = {'player': {'position': expected_position_spec}}
    self.assertEqual(want, nest)

  def test_spec_base_get_proto(self):
    """Test accessing the protobuf from a SpecBase."""
    spec = observation_pb2.ObservationSpec()
    spec.player.position.CopyFrom(primitives_pb2.PositionType())
    self.assertEqual(spec, specs.SpecBase(spec).proto)

  def test_spec_base_get_proto_nest(self):
    """Test accessing a nest of spec protos from a SpecBase."""
    spec = observation_pb2.ObservationSpec()
    spec.player.position.CopyFrom(primitives_pb2.PositionType())
    nest = specs.SpecBase(spec).spec_nest
    want = {'player': {'position': spec.player.position}}
    self.assertEqual(want, nest)

  def test_observation_data_to_nest(self):
    """Tests conversion from an ObservationData to a tf-agents nest."""
    observation_spec = observation_pb2.ObservationSpec()
    text_format.Parse(_OBSERVATION_SPEC, observation_spec)
    observation_data = observation_pb2.ObservationData()
    text_format.Parse(_OBSERVATION_DATA, observation_data)
    value = specs.ObservationSpec(observation_spec).tfa_value(observation_data)
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
    text_format.Parse(_ACTION_SPEC, action_spec)
    action_data = action_pb2.ActionData()
    text_format.Parse(_ACTION_DATA, action_data)
    value = specs.ActionSpec(action_spec).tfa_value(action_data)
    # Convert np arrays to list to allow comparison with want.
    value = tf.nest.map_structure(list, value)
    want = {
        'trouble': [1500.0],
        'what_do': [1],
        'left_stick': [0.0, 1.0],
        'right_stick': [-1.0, 0.0]
    }
    self.assertEqual(want, value)

  def test_brain_spec(self):
    brain_spec_pb = brain_pb2.BrainSpec()
    text_format.Parse(_OBSERVATION_SPEC, brain_spec_pb.observation_spec)
    text_format.Parse(_ACTION_SPEC, brain_spec_pb.action_spec)

    brain_spec = specs.BrainSpec(brain_spec_pb)
    self.assertIsInstance(brain_spec.observation_spec,
                          specs.ObservationSpec)
    self.assertIsInstance(brain_spec.action_spec,
                          specs.ActionSpec)

  def test_empty_brain_spec(self):
    empty_brain_spec = brain_pb2.BrainSpec()
    with self.assertRaisesWithLiteralMatch(
        specs.InvalidSpecError,
        'BrainSpec must have an observation spec and action spec.'):
      specs.BrainSpec(empty_brain_spec)

  @parameterized.named_parameters(
      ('IllegalEntity', 'Joystick(s) reference invalid entities: '
       'joy_bar --> [\'bar\'], joy_foo --> [\'foo\'].', """
       actions {
         name: "joy_foo"
         joystick {
           axes_mode: DELTA_PITCH_YAW
           controlled_entity: "foo"
         }
       }
       actions {
         name: "joy_bar"
         joystick {
           axes_mode: DELTA_PITCH_YAW
           controlled_entity: "bar"
         }
       }
       """, """
       player {
         position {}
         rotation {}
       }
       """), ('MissingPlayer',
              'Missing entity player referenced by joysticks [\'joy\'].', """
       actions {
         name: "joy"
         joystick {
           axes_mode: DELTA_PITCH_YAW
           controlled_entity: "player"
         }
       }
       """, """
       camera {
         position {}
         rotation {}
       }
       global_entities {
         rotation { }
         entity_fields {
           name: "despair",
           number {
            minimum: -100.0
            maximum: 0.0
           }
         }
       }
       """),
      ('MissingPlayerRotation',
       'Entity player referenced by joysticks [\'joy\'] has no rotation.', """
       actions {
         name: "joy"
         joystick {
           axes_mode: DELTA_PITCH_YAW
           controlled_entity: "player"
         }
       }
       """, """
       player {
         position {}
       }
       camera {
         position {}
         rotation {}
       }
       """), ('MissingCamera',
              'Missing entity camera referenced by joysticks [\'joy\'].', """
       actions {
         name: "joy"
         joystick {
           axes_mode: DIRECTION_XZ
           controlled_entity: "player"
           control_frame: "camera"
         }
       }
       """, """
       player {
         position {}
         rotation {}
       }
       """))
  def test_bad_brain_spec(self, expected_error, action, observation):
    brain_spec_pb = brain_pb2.BrainSpec()
    text_format.Parse(action, brain_spec_pb.action_spec)
    text_format.Parse(observation, brain_spec_pb.observation_spec)
    with self.assertRaisesWithLiteralMatch(specs.InvalidSpecError,
                                           expected_error):
      _ = specs.BrainSpec(brain_spec_pb)

  def test_known_fields(self):
    """Ensure that specs.py knows about all fields.

    If this test fails, someone has changed the proto and specs.py
    needs to be updated to reflect and test that change.
    """
    act_spec = action_pb2.ActionSpec().DESCRIPTOR
    act_data = action_pb2.ActionData().DESCRIPTOR
    obs_spec = observation_pb2.ObservationSpec().DESCRIPTOR
    obs_data = observation_pb2.ObservationData().DESCRIPTOR

    fields = set()
    def _find_fields(proto_descriptor):
      for name, fd in proto_descriptor.fields_by_name.items():
        if (proto_descriptor.full_name, name) in fields:
          continue
        fields.add((proto_descriptor.full_name, name))
        if fd.message_type:
          _find_fields(fd.message_type)

    _find_fields(act_spec)
    _find_fields(act_data)
    _find_fields(obs_spec)
    _find_fields(obs_data)

    self.assertEqual(
        fields, {
            ('falken.proto.Action', 'category'),
            ('falken.proto.Action', 'joystick'),
            ('falken.proto.Action', 'number'),
            ('falken.proto.ActionData', 'actions'),
            ('falken.proto.ActionData', 'source'),
            ('falken.proto.ActionSpec', 'actions'),
            ('falken.proto.ActionType', 'category'),
            ('falken.proto.ActionType', 'name'),
            ('falken.proto.ActionType', 'number'),
            ('falken.proto.EntityField', 'category'),
            ('falken.proto.EntityField', 'feeler'),
            ('falken.proto.ActionType', 'joystick'),
            ('falken.proto.EntityField', 'number'),
            ('falken.proto.EntityFieldType', 'category'),
            ('falken.proto.EntityFieldType', 'feeler'),
            ('falken.proto.EntityFieldType', 'name'),
            ('falken.proto.EntityFieldType', 'number'),
            ('falken.proto.Category', 'value'),
            ('falken.proto.CategoryType', 'enum_values'),
            ('falken.proto.Entity', 'entity_fields'),
            ('falken.proto.Entity', 'position'),
            ('falken.proto.Entity', 'rotation'),
            ('falken.proto.EntityType', 'entity_fields'),
            ('falken.proto.EntityType', 'position'),
            ('falken.proto.EntityType', 'rotation'),
            ('falken.proto.Feeler', 'measurements'),
            ('falken.proto.FeelerMeasurement', 'distance'),
            ('falken.proto.FeelerMeasurement', 'experimental_data'),
            ('falken.proto.FeelerType', 'count'),
            ('falken.proto.FeelerType', 'distance'),
            ('falken.proto.FeelerType', 'yaw_angles'),
            ('falken.proto.FeelerType', 'experimental_data'),
            ('falken.proto.FeelerType', 'thickness'),
            ('falken.proto.Joystick', 'x_axis'),
            ('falken.proto.Joystick', 'y_axis'),
            ('falken.proto.JoystickType', 'axes_mode'),
            ('falken.proto.JoystickType', 'controlled_entity'),
            ('falken.proto.JoystickType', 'control_frame'),
            ('falken.proto.Number', 'value'),
            ('falken.proto.NumberType', 'maximum'),
            ('falken.proto.NumberType', 'minimum'),
            ('falken.proto.ObservationData', 'camera'),
            ('falken.proto.ObservationData', 'global_entities'),
            ('falken.proto.ObservationData', 'player'),
            ('falken.proto.ObservationSpec', 'camera'),
            ('falken.proto.ObservationSpec', 'global_entities'),
            ('falken.proto.ObservationSpec', 'player'),
            ('falken.proto.Position', 'x'),
            ('falken.proto.Position', 'y'),
            ('falken.proto.Position', 'z'),
            ('falken.proto.Rotation', 'w'),
            ('falken.proto.Rotation', 'x'),
            ('falken.proto.Rotation', 'y'),
            ('falken.proto.Rotation', 'z'),
        })


class DataProtobufGeneratorTest(absltest.TestCase):
  """Tests for DataProtobufGenerator."""

  _GENERATED_OBSERVATION_DATA = """
  player {
    position {
    }
    rotation {
      w: 1.0
    }
    entity_fields {
      number {
      }
    }
    entity_fields {
      category {
      }
    }
    entity_fields {
      feeler {
        measurements {
          distance {
          }
          experimental_data {
          }
        }
        measurements {
          distance {
          }
          experimental_data {
          }
        }
        measurements {
          distance {
          }
          experimental_data {
          }
        }
      }
    }
  }
  global_entities {
    rotation {
      w: 1.0
    }
    entity_fields {
      number {
      }
    }
  }
  global_entities {
    entity_fields {
      number {
      }
    }
  }
  camera {
    position {
    }
    rotation {
      w: 1.0
    }
  }
  """

  _GENERATED_ACTION_DATA = """
  actions {
    category {
    }
  }
  actions {
    number {
      value: 1000.0
    }
  }
  actions {
    joystick {
    }
  }
  actions {
    joystick {
    }
  }
  source: HUMAN_DEMONSTRATION
  """

  # Number of random data protos to generate per test.
  _RANDOM_NUMBER_ATTEMPTS = 10

  def test_observation_from_spec(self):
    """Test generation of an ObservationData proto."""
    spec = observation_pb2.ObservationSpec()
    text_format.Parse(_OBSERVATION_SPEC, spec)
    data_protos = specs.DataProtobufGenerator.from_spec_node(
        specs.ProtobufNode.from_spec(spec))

    expected = observation_pb2.ObservationData()
    text_format.Parse(DataProtobufGeneratorTest._GENERATED_OBSERVATION_DATA,
                      expected)
    self.assertCountEqual(data_protos, [expected])

  def test_action_from_spec(self):
    """Test generation of an ActionData proto."""
    spec = action_pb2.ActionSpec()
    text_format.Parse(_ACTION_SPEC, spec)
    data_protos = specs.DataProtobufGenerator.from_spec_node(
        specs.ProtobufNode.from_spec(spec))

    expected = action_pb2.ActionData()
    text_format.Parse(DataProtobufGeneratorTest._GENERATED_ACTION_DATA,
                      expected)
    self.assertCountEqual(data_protos, [expected])

  def test_observation_from_spec_calls_modify_data_proto(self):
    """Ensure modify_data_proto is called for each observation data proto."""
    modified = []  # List of modified (type(data_proto), spec_proto) tuples.
    add_to_modified = lambda data, spec: modified.append((type(data), spec))

    spec = observation_pb2.ObservationSpec()
    text_format.Parse(_OBSERVATION_SPEC, spec)
    _ = specs.DataProtobufGenerator.from_spec_node(
        specs.ProtobufNode.from_spec(spec),
        modify_data_proto=add_to_modified)

    expected = [
        (observation_pb2.ObservationData, spec),
        (observation_pb2.Entity, spec.player),
        (primitives_pb2.Position, spec.player.position),
        (primitives_pb2.Rotation, spec.player.rotation),
        (primitives_pb2.Number, spec.player.entity_fields[0].number),
        (primitives_pb2.Category, spec.player.entity_fields[1].category),
        (observation_pb2.Feeler, spec.player.entity_fields[2].feeler),
        (observation_pb2.Entity, spec.camera),
        (primitives_pb2.Position, spec.camera.position),
        (primitives_pb2.Rotation, spec.camera.rotation),
        (observation_pb2.Entity, spec.global_entities[0]),
        (primitives_pb2.Rotation, spec.global_entities[0].rotation),
        (primitives_pb2.Number,
         spec.global_entities[0].entity_fields[0].number),
        (observation_pb2.Entity, spec.global_entities[1]),
        (primitives_pb2.Number,
         spec.global_entities[1].entity_fields[0].number),
    ]
    self.assertCountEqual(modified, expected)

  def test_action_from_spec_calls_modify_data_proto(self):
    """Ensure modify_data_proto is called for each action data proto."""
    modified = []  # List of modified (type(data_proto), spec_proto) tuples.
    add_to_modified = lambda data, spec: modified.append((type(data), spec))
    spec = action_pb2.ActionSpec()
    text_format.Parse(_ACTION_SPEC, spec)
    _ = specs.DataProtobufGenerator.from_spec_node(
        specs.ProtobufNode.from_spec(spec),
        modify_data_proto=add_to_modified)

    expected = [
        (action_pb2.ActionData, spec),
        (primitives_pb2.Category, spec.actions[0].category),
        (primitives_pb2.Number, spec.actions[1].number),
        (action_pb2.Joystick, spec.actions[2].joystick),
        (action_pb2.Joystick, spec.actions[3].joystick),
    ]
    self.assertCountEqual(modified, expected)

  def test_randomize_observation_data(self):
    """Ensure randomization does not change an ObservationData proto."""
    data = observation_pb2.ObservationData()
    specs.DataProtobufGenerator.randomize_leaf_data_proto(
        data, observation_pb2.ObservationSpec())
    self.assertEqual(data, observation_pb2.ObservationData())

  def test_randomize_action_data(self):
    """Ensure randomization does not change an ActionData proto."""
    data = action_pb2.ActionData()
    specs.DataProtobufGenerator.randomize_leaf_data_proto(
        data, action_pb2.ActionSpec())
    self.assertEqual(data, action_pb2.ActionData())

  def test_randomize_entity_data(self):
    """Ensure randomization does not change an Entity proto."""
    data = observation_pb2.Entity()
    specs.DataProtobufGenerator.randomize_leaf_data_proto(
        data, observation_pb2.EntityType())
    self.assertEqual(data, observation_pb2.Entity())

  def _assert_between(self, value, minimum, maximum):
    """Assert value is >= minimum and <= maximum.

    Args:
      value: Value to check.
      minimum: Minimum of the range.
      maximum: Maixmum of the range.
    """
    self.assertGreaterEqual(value, minimum)
    self.assertLessEqual(value, maximum)

  def test_randomize_category_proto(self):
    """Randomize a Category proto."""
    spec = primitives_pb2.CategoryType()
    spec.enum_values.extend(['yo', 'hey', 'sup'])
    unique_values = set()
    for _ in range(DataProtobufGeneratorTest._RANDOM_NUMBER_ATTEMPTS):
      data = primitives_pb2.Category()
      specs.DataProtobufGenerator.randomize_leaf_data_proto(data, spec)
      unique_values.add(data.value)
      self._assert_between(data.value, 0, len(spec.enum_values) - 1)
    self.assertGreater(len(unique_values), 1)

  def test_randomize_number_proto(self):
    """Randomize a Number proto."""
    spec = primitives_pb2.NumberType()
    spec.minimum = 10.0
    spec.maximum = 100.0
    unique_values = set()
    for _ in range(DataProtobufGeneratorTest._RANDOM_NUMBER_ATTEMPTS):
      data = primitives_pb2.Number()
      specs.DataProtobufGenerator.randomize_leaf_data_proto(data, spec)
      unique_values.add(data.value)
      self._assert_between(data.value, spec.minimum, spec.maximum)
    self.assertGreater(len(unique_values), 1)

  def test_randomize_joystick_proto(self):
    """Randomize a Joystick proto."""
    spec = action_pb2.JoystickType()
    unique_values = set()
    for _ in range(DataProtobufGeneratorTest._RANDOM_NUMBER_ATTEMPTS):
      data = action_pb2.Joystick()
      specs.DataProtobufGenerator.randomize_leaf_data_proto(data, spec)
      unique_values.add((data.x_axis, data.y_axis))
      self._assert_between(data.x_axis, -1.0, 1.0)
      self._assert_between(data.y_axis, -1.0, 1.0)
    self.assertGreater(len(unique_values), 1)

  def test_randomize_position_proto(self):
    """Randomize a Position proto."""
    spec = primitives_pb2.PositionType()
    unique_values = set()
    for _ in range(DataProtobufGeneratorTest._RANDOM_NUMBER_ATTEMPTS):
      data = primitives_pb2.Position()
      specs.DataProtobufGenerator.randomize_leaf_data_proto(data, spec)
      unique_values.add((data.x, data.y, data.z))
      self._assert_between(data.x, -1.0, 1.0)
      self._assert_between(data.y, -1.0, 1.0)
      self._assert_between(data.z, -1.0, 1.0)
    self.assertGreater(len(unique_values), 1)

  def test_randomize_rotation_proto(self):
    """Randomize a Rotation proto."""
    spec = primitives_pb2.RotationType()
    unique_values = set()
    for _ in range(DataProtobufGeneratorTest._RANDOM_NUMBER_ATTEMPTS):
      data = primitives_pb2.Rotation()
      specs.DataProtobufGenerator.randomize_leaf_data_proto(data, spec)
      unique_values.add((data.x, data.y, data.z, data.w))
      self._assert_between(data.x, -1.0, 1.0)
      self._assert_between(data.y, -1.0, 1.0)
      self._assert_between(data.z, -1.0, 1.0)
      self._assert_between(data.w, -1.0, 1.0)
    self.assertGreater(len(unique_values), 1)

  def test_randomize_feeler_proto(self):
    """Randomize a Feeler proto."""
    spec = observation_pb2.FeelerType()
    spec.count = 3
    spec.distance.minimum = 5.0
    spec.distance.maximum = 10.0
    experimental_data = spec.experimental_data.add()
    experimental_data.minimum = 1.0
    experimental_data.maximum = 2.0
    experimental_data = spec.experimental_data.add()
    experimental_data.minimum = 3.0
    experimental_data.maximum = 4.0

    unique_values = set()
    for _ in range(DataProtobufGeneratorTest._RANDOM_NUMBER_ATTEMPTS):
      data = observation_pb2.Feeler()
      for _ in range(spec.count):
        measurement = data.measurements.add()
        for _ in range(len(spec.experimental_data)):
          _ = measurement.experimental_data.add()
      specs.DataProtobufGenerator.randomize_leaf_data_proto(data, spec)
      flattened_feeler = []
      for measurement in data.measurements:
        flattened_feeler.append(measurement.distance.value)
        self._assert_between(measurement.distance.value, spec.distance.minimum,
                             spec.distance.maximum)

        for i, experimental_data in enumerate(measurement.experimental_data):
          flattened_feeler.append(experimental_data.value)
          self._assert_between(experimental_data.value,
                               spec.experimental_data[i].minimum,
                               spec.experimental_data[i].maximum)
      unique_values.add(tuple(flattened_feeler))
    self.assertGreater(len(unique_values), 1)

if __name__ == '__main__':
  absltest.main()
