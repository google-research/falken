// Copyright 2021 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include "src/core/specs.h"

#include <cstddef>
#include <utility>

#include <google/protobuf/descriptor.h>
#include <google/protobuf/text_format.h>
#include "src/core/protos.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "absl/status/status.h"

namespace {

using falken::common::CheckValid;
using falken::common::Typecheck;
using falken::proto::ActionData;
using falken::proto::ActionSpec;
using falken::proto::BrainSpec;
using falken::proto::ObservationData;
using falken::proto::ObservationSpec;

TEST(SpecsTest, TestCheckValidBrainSpec) {
  BrainSpec spec;
  // Valid observation spec.
  google::protobuf::TextFormat::ParseFromString(R"(
    observation_spec {
      player {
        position {}
        rotation {}
        entity_fields {
          name: "A"
          number { maximum: 1 }
        }
      }
      camera {
        position {}
        rotation {}
      }
      global_entities {
        position {}
        rotation {}
      }
      global_entities {
        position {}
        rotation {}
        entity_fields { category { enum_values: "E1" enum_values: "E2" } }
      }
    }
    action_spec {
      actions {
        name: "A1"
        category {
          enum_values: "A"
          enum_values: "B"
        }
      }
      actions {
        name: "A2"
        number {
          minimum: -1
          maximum: 1
        }
      }
      actions {
        name: "A3"
        joystick {
          axes_mode: DIRECTION_XZ
          control_frame: "camera"
          controlled_entity: "player"
        }
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(CheckValid(spec).ok());

  // Invalid reference.
  google::protobuf::TextFormat::ParseFromString(R"(
    observation_spec {
      player {
        position {}
        rotation {}
        entity_fields {
          name: "A"
          number { maximum: 1 }
        }
      }
    }
    action_spec {
      actions {
        name: "A"
        joystick {
          axes_mode: DIRECTION_XZ
          control_frame: "invalid"
          controlled_entity: "invalid"
        }
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // Missing camera reference.
  google::protobuf::TextFormat::ParseFromString(R"(
    observation_spec {
      player {
        position {}
        rotation {}
        entity_fields {
          name: "A"
          number { maximum: 1 }
        }
      }
    }
    action_spec {
      actions {
        name: "A"
        joystick {
          axes_mode: DIRECTION_XZ
          control_frame: "player"
          controlled_entity: "camera"
        }
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // control_frame shouldn't be specified
  google::protobuf::TextFormat::ParseFromString(R"(
    observation_spec {
      player {
        position {}
        rotation {}
        entity_fields {
          name: "A"
          number { maximum: 1 }
        }
      }
    }
    action_spec {
      actions {
        name: "A"
        joystick {
          axes_mode: DELTA_PITCH_YAW
          control_frame: "player"
          controlled_entity: "player"
        }
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // control_frame does not need to be be specified for directional.
  // missing control_Frame is interpreted as 'world'.
  google::protobuf::TextFormat::ParseFromString(R"(
    observation_spec {
      player {
        position {}
        rotation {}
        entity_fields {
          name: "A"
          number { maximum: 1 }
        }
      }
    }
    action_spec {
      actions {
        name: "A"
        joystick {
          axes_mode: DIRECTION_XZ
          controlled_entity: "player"
        }
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(CheckValid(spec).ok());
}

TEST(SpecsTest, TestCheckValidObservation) {
  ObservationSpec spec;

  // Valid observation spec.
  google::protobuf::TextFormat::ParseFromString(R"(
    player {
      position {}
      rotation {}
      entity_fields {
        name: "A"
        number { maximum: 1 }
      }
    }
    camera {
      position {}
      rotation {}
    }
    global_entities {
      position {}
      rotation {}
    }
    global_entities {
      position {}
      rotation {}
      entity_fields { category { enum_values: "E1" enum_values: "E2" } }
    }
  )",
                                      &spec);
  EXPECT_TRUE(CheckValid(spec).ok());

  // Empty observation spec.
  google::protobuf::TextFormat::ParseFromString(R"()", &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // Empty player entity.
  google::protobuf::TextFormat::ParseFromString(R"(
    player {}
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // Empty global entity.
  google::protobuf::TextFormat::ParseFromString(R"(
    global_entities {}
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // Reserved attribute name.
  google::protobuf::TextFormat::ParseFromString(R"(
    player {
      entity_fields {
        name: "position"
        number {
          maximum: 1
        }
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // Double attribute name.
  google::protobuf::TextFormat::ParseFromString(R"(
    player {
      entity_fields {
        name: "doubletrouble"
        number {
          maximum: 1
        }
      }
      entity_fields {
        name: "doubletrouble"
        number {
          maximum: 1
        }
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // Empty attribute
  google::protobuf::TextFormat::ParseFromString(R"(
    player {
      entity_fields {
        name: "empty"
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // Empty enum
  google::protobuf::TextFormat::ParseFromString(R"(
    player {
      entity_fields {
        name: "empty_enum"
        category {}
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // Empty range
  google::protobuf::TextFormat::ParseFromString(R"(
    player {
      entity_fields {
        name: "empty_range"
        number {
          minimum: 1
          maximum: 0
        }
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));
}

TEST(SpecsTest, TestCheckValidAction) {
  ActionSpec spec;

  // Valid action spec.
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      name: "A1"
      category {
        enum_values: "A"
        enum_values: "B"
      }
    }
    actions {
      name: "A2"
      number {
        minimum: -1
        maximum: 1
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(CheckValid(spec).ok());

  // Empty spec
  google::protobuf::TextFormat::ParseFromString(R"()", &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // Empty action
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      name: "A1"
    }
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // Unnamed action
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      number {
        maximum: 1
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // Same name twice
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      name: "A"
      number {
        maximum: 1
      }
    }
    actions {
      name: "A"
      number {
        maximum: 1
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // Empty enum value
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      name: "A"
      category {
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // Single enum value
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      name: "A"
      category {
        enum_values: "A"
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // Empty enum value
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      name: "A"
      category {
        enum_values: ""
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // Singleton number range
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      name: "A"
      number {
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // Empty number range
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      name: "A"
      number {
        maximum: 0
        minimum: 1
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // No axes_mode set.
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      name: "A"
      joystick {
        control_frame: "player"
        controlled_entity: "player"
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // No controlled_entity set.
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      name: "A"
      joystick {
        axes_mode: DIRECTION_XZ
        control_frame: "player"
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // Valid: No control frame set for DIRECTION axes_mode.
  // Interpreted as "world".
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      name: "A"
      joystick {
        axes_mode: DIRECTION_XZ
        controlled_entity: "player"
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(CheckValid(spec).ok());

  // Control frame set for non-DIRECTION axes_mode.
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      name: "A"
      joystick {
        axes_mode: DELTA_PITCH_YAW
        controlled_entity: "player"
        control_frame: "player"
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));
}

TEST(SpecsTest, TestTypecheckActionMismatch) {
  ActionSpec spec;
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      number {
        maximum: 10
      }
    }
  )",
                                      &spec);

  ActionData data;
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      category {
        value: 5
      }
    }
    source: BRAIN_ACTION
  )",
                                      &data);

  EXPECT_TRUE(absl::IsInvalidArgument(Typecheck(spec, data)));
}

TEST(SpecsTest, TestTypecheckActionNumberOutOfRange) {
  ActionSpec spec;
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      number {
        maximum: 10
      }
    }
  )",
                                      &spec);

  ActionData data;
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      number {
        value: 11
      }
    }
    source: BRAIN_ACTION
  )",
                                      &data);

  EXPECT_TRUE(absl::IsInvalidArgument(Typecheck(spec, data)));
}

TEST(SpecsTest, TestTypecheckActionCategoryOutOfRange) {
  ActionSpec spec;
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      category {
        enum_values: "A"
        enum_values: "B"
      }
    }
  )",
                                      &spec);

  ActionData data;
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      category {
        value: -1
      }
    }
    source: BRAIN_ACTION
  )",
                                      &data);

  EXPECT_TRUE(absl::IsInvalidArgument(Typecheck(spec, data)));
}

TEST(SpecsTest, TestTypecheckNumActionsMismatch) {
  ActionSpec spec;
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      number {
        maximum: 10
      }
    }
  )",
                                      &spec);

  ActionData data;
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      number {
        value: 5
      }
    }
    actions {
      number {
        value: 7
      }
    }
    source: BRAIN_ACTION
  )",
                                      &data);

  EXPECT_TRUE(absl::IsInvalidArgument(Typecheck(spec, data)));
}

TEST(SpecsTest, TestTypecheckActions) {
  ActionSpec spec;
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      number {
        maximum: 10
      }
    }
    actions {
      category {
        enum_values: "A"
        enum_values: "B"
      }
    }
  )",
                                      &spec);

  ActionData data;
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      number {
        value: 5
      }
    }
    actions {
      category {
        value: 1
      }
    }
    source: BRAIN_ACTION
  )",
                                      &data);

  EXPECT_TRUE(Typecheck(spec, data).ok());
}

TEST(SpecsTest, TestTypecheckEmptyActions) {
  ActionSpec spec;
  google::protobuf::TextFormat::ParseFromString(R"(
    actions {
      number {
        maximum: 10
      }
    }
    actions {
      category {
        enum_values: "A"
        enum_values: "B"
      }
    }
  )",
                                      &spec);

  ActionData empty_data_nosource;
  ActionData empty_data_human;
  empty_data_human.set_source(ActionData::BRAIN_ACTION);
  empty_data_nosource.set_source(ActionData::NO_SOURCE);

  EXPECT_TRUE(Typecheck(spec, empty_data_nosource).ok());
  EXPECT_TRUE(absl::IsInvalidArgument(Typecheck(spec, empty_data_human)));
}

TEST(SpecsTest, TestTypecheckPlayerMismatch) {
  ObservationSpec spec;
  google::protobuf::TextFormat::ParseFromString(R"(
    player {
    }
  )",
                                      &spec);

  ObservationData data;
  google::protobuf::TextFormat::ParseFromString(R"(
  )",
                                      &data);

  EXPECT_TRUE(absl::IsInvalidArgument(Typecheck(spec, data)));
}

TEST(SpecsTest, TestTypecheckNumberOutOfRange) {
  ObservationSpec spec;
  google::protobuf::TextFormat::ParseFromString(R"(
    global_entities {
      entity_fields {
        number {
          minimum: 0
          maximum: 10
        }
      }
    }
  )",
                                      &spec);

  ObservationData data;
  google::protobuf::TextFormat::ParseFromString(R"(
    global_entities {
      entity_fields {
        number {
          value: 0
        }
      }
    }
  )",
                                      &data);

  EXPECT_TRUE(absl::IsInvalidArgument(Typecheck(spec, data)));
}

TEST(SpecsTest, TestTypecheckInvalidRange) {
  ObservationSpec spec;
  google::protobuf::TextFormat::ParseFromString(R"(
    global_entities {
      entity_fields {
        number {
          minimum: 0
          maximum: 0
        }
      }
    }
  )",
                                      &spec);

  ObservationData data;
  google::protobuf::TextFormat::ParseFromString(R"(
    global_entities {
      entity_fields {
        number {
          value: 0
        }
      }
    }
  )",
                                      &data);

  EXPECT_TRUE(absl::IsInvalidArgument(Typecheck(spec, data)));
}

TEST(SpecsTest, TestTypecheckSingletonRange) {
  ObservationSpec spec;
  google::protobuf::TextFormat::ParseFromString(R"(
    global_entities {
      entity_fields {
        category {
          enum_values: "Singleton"
        }
      }
    }
  )",
                                      &spec);

  ObservationData data;
  google::protobuf::TextFormat::ParseFromString(R"(
    global_entities {
      entity_fields {
        category {
          value: 0
        }
      }
    }
  )",
                                      &data);

  EXPECT_TRUE(absl::IsInvalidArgument(Typecheck(spec, data)));
}

TEST(SpecsTest, TestTypecheckCategoryOutOfRange) {
  ObservationSpec spec;
  google::protobuf::TextFormat::ParseFromString(R"(
    global_entities {
      entity_fields {
        category {
          enum_values: "test1"
          enum_values: "test2"
        }
      }
    }
  )",
                                      &spec);

  ObservationData data;
  google::protobuf::TextFormat::ParseFromString(R"(
    global_entities {
      entity_fields {
        category {
          value: 2
        }
      }
    }
  )",
                                      &data);

  EXPECT_TRUE(absl::IsInvalidArgument(Typecheck(spec, data)));
}

TEST(SpecsTest, TestTypecheckAttributeMismatch) {
  ObservationSpec spec;
  google::protobuf::TextFormat::ParseFromString(R"(
    global_entities {
      entity_fields {
        number {
          maximum: 10
        }
      }
    }
  )",
                                      &spec);

  ObservationData data;
  google::protobuf::TextFormat::ParseFromString(R"(
    global_entities {
      entity_fields {
        category {
        }
      }
    }
  )",
                                      &data);

  EXPECT_TRUE(absl::IsInvalidArgument(Typecheck(spec, data)));
}

TEST(SpecsTest, TestTypecheckEntityMismatch) {
  ObservationSpec spec;
  google::protobuf::TextFormat::ParseFromString(R"(
    global_entities {
      position {
      }
    }
  )",
                                      &spec);

  ObservationData data;
  google::protobuf::TextFormat::ParseFromString(R"(
    global_entities {
      rotation {
      }
    }
  )",
                                      &data);

  EXPECT_TRUE(absl::IsInvalidArgument(Typecheck(spec, data)));
}

TEST(SpecsTest, TestTypecheckMismatchedNumEntities) {
  ObservationSpec spec;
  google::protobuf::TextFormat::ParseFromString(R"(
    global_entities {
    }
    global_entities {
    }
  )",
                                      &spec);

  ObservationData data;
  google::protobuf::TextFormat::ParseFromString(R"(
    global_entities {
    }
  )",
                                      &data);

  EXPECT_TRUE(absl::IsInvalidArgument(Typecheck(spec, data)));
}

TEST(SpecsTest, TestTypecheckSpecGlobalEntityAttributeOOR) {
  ObservationSpec spec;
  google::protobuf::TextFormat::ParseFromString(R"(
    player {
      position {}
      rotation {}
    }
    global_entities {
      position {}
      rotation {}
      entity_fields {
        name: "X"
        number {
          minimum: -1
          maximum: 1
        }
      }
    }
  )",
                                      &spec);

  ObservationData bad_data;
  google::protobuf::TextFormat::ParseFromString(R"(
    player {
      position {
        x: 1
        y: 2
        z: 3
      }
    }
    global_entities {
      entity_fields {
        number {
          value: -1.1
        }
      }
    }
  )",
                                      &bad_data);

  ObservationData ok_data;
  google::protobuf::TextFormat::ParseFromString(R"(
    player {
      position {
        x: 1
        y: 2
        z: 3
      }
      rotation {
        x: 1
        y: 2
        z: 3
        w: 4
      }
    }
    global_entities {
      position {
        x: 1
        y: 2
        z: 3
      }
      rotation {
        x: 1
        y: 2
        z: 3
        w: 4
      }
      entity_fields {
        number {
          value: -0.3
        }
      }
    }
  )",
                                      &ok_data);

  EXPECT_TRUE(absl::IsInvalidArgument(Typecheck(spec, bad_data)));
  EXPECT_TRUE(Typecheck(spec, ok_data).ok());
}

TEST(SpecsTest, TestTypecheckSpecEmpty) {
  ObservationSpec spec;
  google::protobuf::TextFormat::ParseFromString(R"(
  )",
                                      &spec);

  ObservationData data;
  google::protobuf::TextFormat::ParseFromString(R"(
  )",
                                      &data);

  EXPECT_TRUE(absl::IsInvalidArgument(Typecheck(spec, data)));
}

TEST(SpecsTest, TestCheckValidFeelerObservation) {
  ObservationSpec spec;

  google::protobuf::TextFormat::ParseFromString(R"(
    player {
      position {}
      rotation {}
      entity_fields {
        name: "feeler"
        feeler {
          count: 3
          distance { minimum: 0.0 maximum: 100.0 }
          yaw_angles: [ -10.0, 0, 10.0 ]
          experimental_data: { minimum: 0.0 maximum: 100.0 }
        }
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(CheckValid(spec).ok());
}

TEST(SpecsTest, TestCheckMismatchedCountFeelerObservation) {
  ObservationSpec spec;

  google::protobuf::TextFormat::ParseFromString(R"(
    player {
      position {}
      rotation {}
      entity_fields {
        name: "feeler"
        feeler {
          count: 5
          distance { minimum: 0.0 maximum: 100.0 }
          yaw_angles: [ -10.0, 0, 10.0 ]
          experimental_data: { minimum: 0.0 maximum: 100.0 }
        }
      }
    }
    global_entities { position {} }
    global_entities {
      rotation {}
      entity_fields { category { enum_values: "E1" enum_values: "E2" } }
    }
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));
}

TEST(SpecsTest, TestNoObservationSignalsGenerated) {
  BrainSpec spec;

  // No custom fields or joystick action.
  google::protobuf::TextFormat::ParseFromString(R"(
    observation_spec {
      player {
        position {}
        rotation {}
      }
    }
    action_spec {
      actions {
          name: "A1"
          category {
            enum_values: "A"
            enum_values: "B"
          }
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // Joystick action but no entity to steer towards.
  google::protobuf::TextFormat::ParseFromString(R"(
    observation_spec {
      player {
        position {}
        rotation {}
      }
    }
    action_spec {
      actions {
        name: "A"
        joystick {
          axes_mode: DELTA_PITCH_YAW
          controlled_entity: "player"
        }
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // Has entity, but the entity doesn't have a complete transform.
  google::protobuf::TextFormat::ParseFromString(R"(
    observation_spec {
      player {
        position {}
        rotation {}
      }
      global_entities {
        rotation {}
      }
    }
    action_spec {
      actions {
        name: "A"
        joystick {
          axes_mode: DELTA_PITCH_YAW
          controlled_entity: "player"
        }
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(absl::IsInvalidArgument(CheckValid(spec)));

  // Now there's a joystick action and enough info to generate signals.
  google::protobuf::TextFormat::ParseFromString(R"(
    observation_spec {
      player {
        position {}
        rotation {}
      }
      global_entities {
        position {}
        rotation {}
      }
    }
    action_spec {
      actions {
        name: "A"
        joystick {
          axes_mode: DELTA_PITCH_YAW
          controlled_entity: "player"
        }
      }
    }
  )",
                                      &spec);
  EXPECT_TRUE(CheckValid(spec).ok());
}

// Recursively inserts proto field names into a set starting from a root
// message.
void InsertFieldsIntoMap(const google::protobuf::Descriptor& descr,
                         std::set<std::string>* seen) {
  for (int i = 0; i < descr.field_count(); ++i) {
    const google::protobuf::FieldDescriptor& fieldDescr = *descr.field(i);
    auto name = fieldDescr.full_name();
    if (seen->find(name) != seen->end()) {
      continue;
    }
    seen->insert(name);
    if (fieldDescr.message_type()) {
      InsertFieldsIntoMap(*fieldDescr.message_type(), seen);
    }
  }
}

// Expands to a std::string that contains the full name of a proto field.
#define FALKEN_PROTO_FIELD_NAME(falken_proto, field_name) \
  (falken::proto::falken_proto::descriptor()->full_name() + "." + field_name)

// This test checks that no fields were added since the code was written.
// We need to check this since field additions should generally also cause
// changes in the translation code. They also call for new tests to be added.
// After new code has been added and tested, a new field can be added to the
// expected list of fields below.
TEST(SpecsTest, TestAllFieldsCovered) {
  ActionSpec aspec;
  ActionData adata;
  ObservationSpec ospec;
  ObservationData odata;
  std::set<std::string> seen;

  InsertFieldsIntoMap(*aspec.GetDescriptor(), &seen);
  InsertFieldsIntoMap(*adata.GetDescriptor(), &seen);
  InsertFieldsIntoMap(*ospec.GetDescriptor(), &seen);
  InsertFieldsIntoMap(*odata.GetDescriptor(), &seen);

  std::set<std::string> want = {
    FALKEN_PROTO_FIELD_NAME(Action, "category"),
    FALKEN_PROTO_FIELD_NAME(Action, "joystick"),
    FALKEN_PROTO_FIELD_NAME(Action, "number"),
    FALKEN_PROTO_FIELD_NAME(ActionData, "actions"),
    FALKEN_PROTO_FIELD_NAME(ActionData, "source"),
    FALKEN_PROTO_FIELD_NAME(ActionSpec, "actions"),
    FALKEN_PROTO_FIELD_NAME(ActionType, "category"),
    FALKEN_PROTO_FIELD_NAME(ActionType, "name"),
    FALKEN_PROTO_FIELD_NAME(ActionType, "joystick"),
    FALKEN_PROTO_FIELD_NAME(ActionType, "number"),
    FALKEN_PROTO_FIELD_NAME(EntityField, "category"),
    FALKEN_PROTO_FIELD_NAME(EntityField, "feeler"),
    FALKEN_PROTO_FIELD_NAME(EntityField, "number"),
    FALKEN_PROTO_FIELD_NAME(EntityFieldType, "category"),
    FALKEN_PROTO_FIELD_NAME(EntityFieldType, "feeler"),
    FALKEN_PROTO_FIELD_NAME(EntityFieldType, "name"),
    FALKEN_PROTO_FIELD_NAME(EntityFieldType, "number"),
    FALKEN_PROTO_FIELD_NAME(Category, "value"),
    FALKEN_PROTO_FIELD_NAME(CategoryType, "enum_values"),
    FALKEN_PROTO_FIELD_NAME(Entity, "entity_fields"),
    FALKEN_PROTO_FIELD_NAME(Entity, "position"),
    FALKEN_PROTO_FIELD_NAME(Entity, "rotation"),
    FALKEN_PROTO_FIELD_NAME(EntityType, "entity_fields"),
    FALKEN_PROTO_FIELD_NAME(EntityType, "position"),
    FALKEN_PROTO_FIELD_NAME(EntityType, "rotation"),
    FALKEN_PROTO_FIELD_NAME(Feeler, "measurements"),
    FALKEN_PROTO_FIELD_NAME(FeelerMeasurement, "distance"),
    FALKEN_PROTO_FIELD_NAME(FeelerMeasurement, "experimental_data"),
    FALKEN_PROTO_FIELD_NAME(FeelerType, "count"),
    FALKEN_PROTO_FIELD_NAME(FeelerType, "distance"),
    FALKEN_PROTO_FIELD_NAME(FeelerType, "yaw_angles"),
    FALKEN_PROTO_FIELD_NAME(FeelerType, "experimental_data"),
    FALKEN_PROTO_FIELD_NAME(FeelerType, "thickness"),
    FALKEN_PROTO_FIELD_NAME(Joystick, "x_axis"),
    FALKEN_PROTO_FIELD_NAME(Joystick, "y_axis"),
    FALKEN_PROTO_FIELD_NAME(JoystickType, "axes_mode"),
    FALKEN_PROTO_FIELD_NAME(JoystickType, "controlled_entity"),
    FALKEN_PROTO_FIELD_NAME(JoystickType, "control_frame"),
    FALKEN_PROTO_FIELD_NAME(Number, "value"),
    FALKEN_PROTO_FIELD_NAME(NumberType, "maximum"),
    FALKEN_PROTO_FIELD_NAME(NumberType, "minimum"),
    FALKEN_PROTO_FIELD_NAME(ObservationData, "global_entities"),
    FALKEN_PROTO_FIELD_NAME(ObservationData, "camera"),
    FALKEN_PROTO_FIELD_NAME(ObservationData, "player"),
    FALKEN_PROTO_FIELD_NAME(ObservationSpec, "global_entities"),
    FALKEN_PROTO_FIELD_NAME(ObservationSpec, "camera"),
    FALKEN_PROTO_FIELD_NAME(ObservationSpec, "player"),
    FALKEN_PROTO_FIELD_NAME(Position, "x"),
    FALKEN_PROTO_FIELD_NAME(Position, "y"),
    FALKEN_PROTO_FIELD_NAME(Position, "z"),
    FALKEN_PROTO_FIELD_NAME(Rotation, "w"),
    FALKEN_PROTO_FIELD_NAME(Rotation, "x"),
    FALKEN_PROTO_FIELD_NAME(Rotation, "y"),
    FALKEN_PROTO_FIELD_NAME(Rotation, "z"),
  };
  EXPECT_EQ(seen, want);
}

}  // namespace
