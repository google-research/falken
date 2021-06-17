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
from learner.brains import data_protobuf_generator
from learner.brains import specs
from learner.brains import specs_test

import common.generate_protos  # pylint: disable=unused-import

import action_pb2
import observation_pb2
import primitives_pb2


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
    text_format.Parse(specs_test._OBSERVATION_SPEC, spec)
    data_protos = data_protobuf_generator.DataProtobufGenerator.from_spec_node(
        specs.ProtobufNode.from_spec(spec))

    expected = observation_pb2.ObservationData()
    text_format.Parse(DataProtobufGeneratorTest._GENERATED_OBSERVATION_DATA,
                      expected)
    self.assertCountEqual(data_protos, [expected])

  def test_action_from_spec(self):
    """Test generation of an ActionData proto."""
    spec = action_pb2.ActionSpec()
    text_format.Parse(specs_test._ACTION_SPEC, spec)
    data_protos = data_protobuf_generator.DataProtobufGenerator.from_spec_node(
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
    text_format.Parse(specs_test._OBSERVATION_SPEC, spec)
    _ = data_protobuf_generator.DataProtobufGenerator.from_spec_node(
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
    text_format.Parse(specs_test._ACTION_SPEC, spec)
    _ = data_protobuf_generator.DataProtobufGenerator.from_spec_node(
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
    data_protobuf_generator.DataProtobufGenerator.randomize_leaf_data_proto(
        data, observation_pb2.ObservationSpec())
    self.assertEqual(data, observation_pb2.ObservationData())

  def test_randomize_action_data(self):
    """Ensure randomization does not change an ActionData proto."""
    data = action_pb2.ActionData()
    data_protobuf_generator.DataProtobufGenerator.randomize_leaf_data_proto(
        data, action_pb2.ActionSpec())
    self.assertEqual(data, action_pb2.ActionData())

  def test_randomize_entity_data(self):
    """Ensure randomization does not change an Entity proto."""
    data = observation_pb2.Entity()
    data_protobuf_generator.DataProtobufGenerator.randomize_leaf_data_proto(
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
      data_protobuf_generator.DataProtobufGenerator.randomize_leaf_data_proto(
          data, spec)
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
      data_protobuf_generator.DataProtobufGenerator.randomize_leaf_data_proto(
          data, spec)
      unique_values.add(data.value)
      self._assert_between(data.value, spec.minimum, spec.maximum)
    self.assertGreater(len(unique_values), 1)

  def test_randomize_joystick_proto(self):
    """Randomize a Joystick proto."""
    spec = action_pb2.JoystickType()
    unique_values = set()
    for _ in range(DataProtobufGeneratorTest._RANDOM_NUMBER_ATTEMPTS):
      data = action_pb2.Joystick()
      data_protobuf_generator.DataProtobufGenerator.randomize_leaf_data_proto(
          data, spec)
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
      data_protobuf_generator.DataProtobufGenerator.randomize_leaf_data_proto(
          data, spec)
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
      data_protobuf_generator.DataProtobufGenerator.randomize_leaf_data_proto(
          data, spec)
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
      data_protobuf_generator.DataProtobufGenerator.randomize_leaf_data_proto(
          data, spec)
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
