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

#include "src/core/action_proto_converter.h"

#include <google/protobuf/text_format.h>
#include <google/protobuf/util/message_differencer.h>
#include "falken/actions.h"
#include "falken/log.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"

namespace {

using MessageDifferencer = google::protobuf::util::MessageDifferencer;

struct TestAction : public falken::ActionsBase {
  TestAction(falken::AttributeContainer& attribute_container, const char* name)
      : FALKEN_NUMBER(health, 10.0f, 50.0f),
        FALKEN_BOOL(sprint),
        FALKEN_CATEGORICAL(weapons, {"shotgun", "pistol"}),
        FALKEN_JOYSTICK_DIRECTION_XZ(joy_direction_xz,
                                     falken::kControlledEntityPlayer,
                                     falken::kControlFrameCamera),
        FALKEN_JOYSTICK_DELTA_PITCH_YAW(joy_delta_pitch_yaw,
                                        falken::kControlledEntityCamera) {}

  falken::NumberAttribute<float> health;
  falken::BoolAttribute sprint;
  falken::CategoricalAttribute weapons;
  falken::JoystickAttribute joy_direction_xz;
  falken::JoystickAttribute joy_delta_pitch_yaw;
};

TEST(ActionProtoConverterTest, VerifyActionSpecIntegrity) {
  falken::AttributeContainer attribute_container;
  TestAction test_action(attribute_container, "TestAction");

  falken::proto::ActionSpec expected_action_spec;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        actions:
        [ {
          name: "health"
          number { minimum: 10 maximum: 50 }
          }
          , {
            name: "sprint"
            category { enum_values: "false" enum_values: "true" }
          }
          , {
            name: "weapons"
            category { enum_values: "shotgun" enum_values: "pistol" }
          }
          , {
            name: "joy_direction_xz"
            joystick {
              axes_mode: DIRECTION_XZ
              controlled_entity: "player"
              control_frame: "camera"
            }
          }
          , {
            name: "joy_delta_pitch_yaw"
            joystick {
              axes_mode: DELTA_PITCH_YAW
              controlled_entity: "camera"
            }
          }
        ]
      )",
      &expected_action_spec);

  EXPECT_TRUE(falken::ActionProtoConverter::VerifyActionSpecIntegrity(
      expected_action_spec, test_action));
}

TEST(ActionProtoConverterTest, VerifyActionSpecIntegrityDifferentSize) {
  falken::AttributeContainer attribute_container;
  TestAction test_action(attribute_container, "TestAction");

  falken::proto::ActionSpec expected_action_spec;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        actions:
        [ {
          name: "health"
          number { minimum: 10 maximum: 50 }
          }
          , {
            name: "sprint"
            category { enum_values: "false" enum_values: "true" }
          } ]
      )",
      &expected_action_spec);

  EXPECT_FALSE(falken::ActionProtoConverter::VerifyActionSpecIntegrity(
      expected_action_spec, test_action));
}

TEST(ActionProtoConverterTest, VerifyActionSpecIntegrityNonexistentAttribute) {
  falken::AttributeContainer attribute_container;
  TestAction test_action(attribute_container, "TestAction");

  falken::proto::ActionSpec expected_action_spec;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        actions:
        [ {
          name: "dog"
          number { minimum: 10 maximum: 50 }
          }
          , {
            name: "sprint"
            category { enum_values: "false" enum_values: "true" }
          }
          , {
            name: "weapons"
            category { enum_values: "shotgun" enum_values: "pistol" }
          }
          , {
            name: "joy_direction_xz"
            joystick {
              axes_mode: DIRECTION_XZ
              controlled_entity: "player"
              control_frame: "camera"
            }
          }
          , {
            name: "joy_delta_pitch_yaw"
            joystick {
              axes_mode: DELTA_PITCH_YAW
              controlled_entity: "camera"
            }
          }
        ]
      )",
      &expected_action_spec);

  EXPECT_FALSE(falken::ActionProtoConverter::VerifyActionSpecIntegrity(
      expected_action_spec, test_action));
}

TEST(ActionProtoConverterTest, VerifyActionSpecIntegrityAttribtueMismatch) {
  falken::AttributeContainer attribute_container;
  TestAction test_action(attribute_container, "TestAction");

  falken::proto::ActionSpec expected_action_spec;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        actions:
        [ {
          name: "health"
          number { minimum: 1 maximum: 50 }
          }
          , {
            name: "sprint"
            category { enum_values: "false" enum_values: "true" }
          }
          , {
            name: "weapons"
            category { enum_values: "shotgun" enum_values: "pistol" }
          }
          , {
            name: "joy_direction_xz"
            joystick {
              axes_mode: DIRECTION_XZ
              controlled_entity: "player"
              control_frame: "camera"
            }
          }
          , {
            name: "joy_delta_pitch_yaw"
            joystick {
              axes_mode: DELTA_PITCH_YAW
              controlled_entity: "camera"
            }
          }
        ]
      )",
      &expected_action_spec);

  EXPECT_FALSE(falken::ActionProtoConverter::VerifyActionSpecIntegrity(
      expected_action_spec, test_action));
}

TEST(ActionProtoConverterTest, TestToActionSpec) {
  falken::AttributeContainer attribute_container;
  TestAction test_action(attribute_container, "TestAction");
  falken::proto::ActionSpec action_spec =
      falken::ActionProtoConverter::ToActionSpec(test_action);

  falken::proto::ActionSpec expected_action_spec;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        actions:
        [ {
            name: "health"
            number { minimum: 10 maximum: 50 }
          }
          , {
            name: "joy_delta_pitch_yaw"
            joystick {
              axes_mode: DELTA_PITCH_YAW
              controlled_entity: "camera"
            }
          }
          , {
            name: "joy_direction_xz"
            joystick {
              axes_mode: DIRECTION_XZ
              controlled_entity: "player"
              control_frame: "camera"
            }
          }
          , {
            name: "sprint"
            category { enum_values: "false" enum_values: "true" }
          }
          , {
            name: "weapons"
            category { enum_values: "shotgun" enum_values: "pistol" }
          }

        ]
      )",
      &expected_action_spec);

  MessageDifferencer diff;
  std::string output;
  diff.ReportDifferencesToString(&output);
  EXPECT_TRUE(diff.Compare(action_spec, expected_action_spec))
      << "Difference is: " << output;
}

TEST(ActionProtoConverterTest, TestToActionData) {
  falken::AttributeContainer attribute_container;
  TestAction test_action(attribute_container, "TestAction");
  test_action.weapons.set_category(1);
  test_action.health.set_value(25.5f);
  test_action.sprint.set_value(true);
  test_action.joy_delta_pitch_yaw.set_x_axis(1.0f);
  test_action.joy_delta_pitch_yaw.set_y_axis(0.5f);
  test_action.joy_direction_xz.set_x_axis(-0.5f);
  test_action.joy_direction_xz.set_y_axis(-1.0f);
  test_action.set_source(
      falken::ActionsBase::Source::kSourceHumanDemonstration);
  falken::proto::ActionData action_data =
      falken::ActionProtoConverter::ToActionData(test_action);

  falken::proto::ActionData expected_action_data;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        actions:
        [ { number: { value: 25.5 } }
          , { joystick: { x_axis: 1.0 y_axis: 0.5 } }
          , { joystick: { x_axis: -0.5 y_axis: -1.0 } }
          , { category: { value: 1 } }
          , { category: { value: 1 } }
          ]
        source: 2
      )",
      &expected_action_data);

  MessageDifferencer diff;
  std::string output;
  diff.ReportDifferencesToString(&output);
  EXPECT_TRUE(diff.Compare(action_data, expected_action_data))
      << "Difference is: " << output;
}

TEST(ActionProtoConverterTest, TestFromActionData) {
  falken::AttributeContainer attribute_container;
  TestAction test_action(attribute_container, "TestAction");
  test_action.health.set_value(10.0f);
  test_action.weapons.set_value(0);
  test_action.sprint.set_value(false);
  test_action.joy_delta_pitch_yaw.set_x_axis(-1.0f);
  test_action.joy_delta_pitch_yaw.set_y_axis(-1.0f);
  test_action.joy_direction_xz.set_x_axis(-1.0f);
  test_action.joy_direction_xz.set_y_axis(-1.0f);
  falken::proto::ActionData action_data;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        actions:
        [ { number: { value: 40.0 } }
          , { joystick: { x_axis: 0.5 y_axis: 0.25 } }
          , { joystick: { x_axis: -0.25 y_axis: -0.5 } }
          , { category: { value: 1 } }
          , { category: { value: 1 } }]
        source: 2
      )",
      &action_data);
  EXPECT_TRUE(
      falken::ActionProtoConverter::FromActionData(action_data, test_action));
  EXPECT_EQ(test_action.health.value(), 40.0f);
  EXPECT_EQ(test_action.weapons.value(), 1);
  EXPECT_TRUE(test_action.sprint.value());
  EXPECT_EQ(test_action.joy_delta_pitch_yaw.x_axis(), 0.5f);
  EXPECT_EQ(test_action.joy_delta_pitch_yaw.y_axis(), 0.25f);
  EXPECT_EQ(test_action.joy_direction_xz.x_axis(), -0.25f);
  EXPECT_EQ(test_action.joy_direction_xz.y_axis(), -0.5f);
  EXPECT_EQ(test_action.source(),
            falken::ActionsBase::Source::kSourceHumanDemonstration);
}

TEST(ActionProtoConverterTest, TestFromActionDataDifferentSize) {
  falken::AttributeContainer attribute_container;
  TestAction test_action(attribute_container, "TestAction");
  test_action.health.set_value(10.0f);
  test_action.weapons.set_value(0);
  test_action.sprint.set_value(false);
  falken::proto::ActionData action_data;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        actions:
        [ { number: { value: 40.0 } }
          , { category: { value: 1 } } ]
        source: 2
      )",
      &action_data);
  EXPECT_FALSE(
      falken::ActionProtoConverter::FromActionData(action_data, test_action));
}

TEST(ActionProtoConverterTest, TestValueOutOfRangeFromActionData) {
  falken::AttributeContainer attribute_container;
  TestAction test_action(attribute_container, "TestAction");
  test_action.health.set_value(10.0f);
  test_action.weapons.set_value(0);
  test_action.sprint.set_value(true);
  falken::proto::ActionData action_data;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        actions:
        [ { number: { value: 60.0 } }
          , { category: { value: 5 } }
          , { category: { value: 2 } }]
        source: 2
      )",
      &action_data);
  std::shared_ptr<falken::SystemLogger> logger =
      falken::SystemLogger::Get();
  logger->set_abort_on_fatal_error(false);
  EXPECT_FALSE(
      falken::ActionProtoConverter::FromActionData(action_data, test_action));
  EXPECT_EQ(test_action.health.value(), 10.0f);
  EXPECT_EQ(test_action.weapons.value(), 0);
  EXPECT_TRUE(test_action.sprint.value());
  EXPECT_EQ(test_action.source(),
            falken::ActionsBase::Source::kSourceHumanDemonstration);
}

TEST(ActionProtoConverterTest, TestMissingActionFromActionData) {
  falken::AttributeContainer attribute_container;
  TestAction test_action(attribute_container, "TestAction");
  test_action.health.set_value(10.0f);
  test_action.weapons.set_value(0);
  test_action.sprint.set_value(true);
  falken::proto::ActionData action_data;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        actions:
        [ { number: { value: 40.0 } }]
        source: 2
      )",
      &action_data);
  EXPECT_FALSE(
      falken::ActionProtoConverter::FromActionData(action_data, test_action));
  EXPECT_EQ(test_action.health.value(), 10.0f);
  EXPECT_EQ(test_action.weapons.value(), 0);
  EXPECT_TRUE(test_action.sprint.value());
}

}  // namespace
