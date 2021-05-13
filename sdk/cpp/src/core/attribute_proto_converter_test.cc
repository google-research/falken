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

#include "src/core/attribute_proto_converter.h"

#include <array>

#include "src/core/protos.h"
#include "falken/attribute_base.h"
#include "falken/joystick_attribute.h"
#include "falken/log.h"
#include "falken/types.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"

namespace {

using ::testing::ElementsAreArray;
using ::testing::StrEq;

void PopulateFeelerProto(falken::proto::Feeler& feeler_proto) {
  feeler_proto.add_measurements()->mutable_distance()->set_value(1.1f);
  feeler_proto.add_measurements()->mutable_distance()->set_value(2.2f);
  feeler_proto.add_measurements()->mutable_distance()->set_value(3.3f);
  feeler_proto.mutable_measurements(0)->add_experimental_data()->set_value(0);
  feeler_proto.mutable_measurements(0)->add_experimental_data()->set_value(1);
  feeler_proto.mutable_measurements(0)->add_experimental_data()->set_value(0);
  feeler_proto.mutable_measurements(1)->add_experimental_data()->set_value(1);
  feeler_proto.mutable_measurements(1)->add_experimental_data()->set_value(0);
  feeler_proto.mutable_measurements(1)->add_experimental_data()->set_value(0);
  feeler_proto.mutable_measurements(2)->add_experimental_data()->set_value(0);
  feeler_proto.mutable_measurements(2)->add_experimental_data()->set_value(0);
  feeler_proto.mutable_measurements(2)->add_experimental_data()->set_value(1);
}

TEST(AttributeProtoConverterTest, TestToNumber) {
  falken::AttributeContainer attribute_container;
  falken::NumberAttribute<float> attribute(attribute_container,
                                           "float_attribute", 0.0f, 100.0f);
  attribute.set_value(50.0f);
  falken::proto::Number number =
      falken::AttributeProtoConverter::ToNumber(attribute);
  falken::proto::NumberType number_type =
      falken::AttributeProtoConverter::ToNumberType(attribute);
  EXPECT_EQ(number.value(), 50.0f);
  EXPECT_EQ(number_type.minimum(), 0.0f);
  EXPECT_EQ(number_type.maximum(), 100.0f);
}

TEST(AttributeProtoConverterTest, TestFromNumber) {
  falken::proto::NumberType number_type_proto;
  number_type_proto.set_minimum(50.0f);
  number_type_proto.set_maximum(100.0f);
  falken::proto::Number number_proto;
  number_proto.set_value(75.0f);
  falken::AttributeContainer attribute_container;
  falken::NumberAttribute<float> attribute(attribute_container,
                                           "float_attribute", 50.0f, 100.0f);
  EXPECT_TRUE(
      falken::AttributeProtoConverter::FromNumber(number_proto, attribute));
  EXPECT_EQ(attribute.number_minimum(), number_type_proto.minimum());
  EXPECT_EQ(attribute.number_maximum(), number_type_proto.maximum());
  EXPECT_EQ(attribute.number(), number_proto.value());

  falken::AttributeProtoConverter::FromNumberType("new", number_type_proto,
                                                  attribute_container);
  auto* new_attribute = attribute_container.attribute("new");
  ASSERT_NE(new_attribute, nullptr);
  EXPECT_THAT(new_attribute->name(), StrEq("new"));
  EXPECT_EQ(new_attribute->number_minimum(), number_type_proto.minimum());
  EXPECT_EQ(new_attribute->number_maximum(), number_type_proto.maximum());
}

TEST(AttributeProtoConverterTest, TestFromNumberOutOfRange) {
  falken::proto::NumberType number_type_proto;
  number_type_proto.set_minimum(50.0f);
  number_type_proto.set_maximum(100.0f);
  falken::proto::Number number_proto;
  number_proto.set_value(150.0f);
  falken::AttributeContainer attribute_container;
  falken::NumberAttribute<float> attribute(attribute_container,
                                           "float_attribute", 50.0f, 100.0f);
  std::shared_ptr<falken::SystemLogger> logger = falken::SystemLogger::Get();
  logger->set_abort_on_fatal_error(false);
  EXPECT_FALSE(
      falken::AttributeProtoConverter::FromNumber(number_proto, attribute));
}

TEST(AttributeProtoConverterTest, TestToCategory) {
  falken::AttributeContainer attribute_container;
  falken::CategoricalAttribute attribute(
      attribute_container, "categorical_attribute", {"zero", "one", "two"});
  attribute.set_value(1);
  falken::proto::Category category =
      falken::AttributeProtoConverter::ToCategory(attribute);
  falken::proto::CategoryType category_type =
      falken::AttributeProtoConverter::ToCategoryType(attribute);
  EXPECT_EQ(category.value(), 1);
  EXPECT_THAT(category_type.enum_values(),
              ElementsAreArray({"zero", "one", "two"}));
}

TEST(AttributeProtoConverterTest, TestFromCategory) {
  falken::proto::CategoryType category_type_proto;
  category_type_proto.add_enum_values("one");
  category_type_proto.add_enum_values("two");
  category_type_proto.add_enum_values("three");
  falken::proto::Category category_proto;
  category_proto.set_value(1);
  falken::AttributeContainer attribute_container;
  falken::CategoricalAttribute attribute(
      attribute_container, "categorical_attribute", {"one", "two", "three"});
  EXPECT_TRUE(
      falken::AttributeProtoConverter::FromCategory(category_proto, attribute));
  std::vector<std::string> category_values;
  EXPECT_THAT(
      falken::ConvertStringVector(attribute.category_values(), category_values),
      ElementsAreArray(category_type_proto.enum_values()));
  EXPECT_EQ(attribute.category(), category_proto.value());

  falken::AttributeProtoConverter::FromCategoryType("new", category_type_proto,
                                                    attribute_container);
  auto* new_attribute = attribute_container.attribute("new");
  ASSERT_NE(new_attribute, nullptr);
  EXPECT_THAT(new_attribute->name(), StrEq("new"));
  std::vector<std::string> new_category_values;
  EXPECT_THAT(falken::ConvertStringVector(new_attribute->category_values(),
                                          new_category_values),
              ElementsAreArray(category_type_proto.enum_values()));
}

TEST(AttributeProtoConverterTest, TestFromCategoryWrongCategory) {
  falken::proto::CategoryType category_type_proto;
  category_type_proto.add_enum_values("one");
  category_type_proto.add_enum_values("two");
  category_type_proto.add_enum_values("three");
  falken::proto::Category category_proto;
  category_proto.set_value(1);
  falken::AttributeContainer attribute_container;
  falken::PositionAttribute attribute(attribute_container,
                                      "position_attribute");
  EXPECT_FALSE(
      falken::AttributeProtoConverter::FromCategory(category_proto, attribute));
}

TEST(AttributeProtoConverterTest, TestToBool) {
  falken::AttributeContainer attribute_container;
  falken::BoolAttribute attribute(attribute_container, "bool");
  attribute.set_value(true);
  falken::proto::Category category =
      falken::AttributeProtoConverter::ToCategory(attribute);
  falken::proto::CategoryType category_type =
      falken::AttributeProtoConverter::ToCategoryType(attribute);
  EXPECT_EQ(category.value(), 1);
  EXPECT_THAT(category_type.enum_values(), ElementsAreArray({"false", "true"}));
}

TEST(AttributeProtoConverterTest, TestFromBool) {
  falken::proto::CategoryType category_type_proto;
  category_type_proto.add_enum_values("false");
  category_type_proto.add_enum_values("true");
  falken::proto::Category category_proto;
  category_proto.set_value(1);
  falken::AttributeContainer attribute_container;
  falken::BoolAttribute attribute(attribute_container, "bool");
  EXPECT_TRUE(
      falken::AttributeProtoConverter::FromCategory(category_proto, attribute));
  std::vector<std::string> bool_values({"false", "true"});
  EXPECT_THAT(bool_values, ElementsAreArray(category_type_proto.enum_values()));
  EXPECT_TRUE(attribute.value());

  falken::AttributeProtoConverter::FromCategoryType("new", category_type_proto,
                                                    attribute_container);
  auto* new_attribute = attribute_container.attribute("new");
  ASSERT_NE(new_attribute, nullptr);
  EXPECT_THAT(new_attribute->name(), StrEq("new"));
  EXPECT_THAT(bool_values, ElementsAreArray(category_type_proto.enum_values()));
}

TEST(AttributeProtoConverterTest, TestToFeeler) {
  falken::AttributeContainer attribute_container;
  int number_of_feelers = 3;
  float distance = 4.0f;
  float fov = 1.0f;
  falken::FeelersAttribute feelers(attribute_container, "feeler_attribute",
                                   number_of_feelers, distance, fov, 0.5f,
                                   {"zero", "one", "two"});
  feelers.feelers_distances()[0].set_value(0.5f);
  feelers.feelers_distances()[1].set_value(1.5f);
  feelers.feelers_distances()[2].set_value(2.5f);
  feelers.feelers_ids()[0].set_value(2);
  feelers.feelers_ids()[1].set_value(0);
  feelers.feelers_ids()[2].set_value(1);
  falken::proto::Feeler feeler_proto =
      falken::AttributeProtoConverter::ToFeeler(feelers);
  EXPECT_EQ(feelers.feelers_distances()[0].value(),
            feeler_proto.measurements(0).distance().value());
  EXPECT_EQ(feelers.feelers_distances()[1].value(),
            feeler_proto.measurements(1).distance().value());
  EXPECT_EQ(feelers.feelers_distances()[2].value(),
            feeler_proto.measurements(2).distance().value());
  EXPECT_EQ(feeler_proto.measurements(0).experimental_data(2).value(), 1);
  EXPECT_EQ(feeler_proto.measurements(0).experimental_data(0).value(), 0);
  EXPECT_EQ(feeler_proto.measurements(0).experimental_data(1).value(), 0);
}

TEST(AttributeProtoConverterTest, TestToFeelerType) {
  falken::AttributeContainer attribute_container;
  int number_of_feelers = 3;
  float distance = 4.0f;
  float thickness = 5.0f;
  float fov = 1.0f;
  std::array<float, 5> yaws = {-0.5, 0, 0.5};
  falken::FeelersAttribute feelers(attribute_container, "feeler_attribute",
                                   number_of_feelers, distance, fov, thickness);
  falken::proto::FeelerType feeler_type_proto =
      falken::AttributeProtoConverter::ToFeelerType(feelers);
  for (int i = 0; i < feeler_type_proto.yaw_angles().size(); ++i) {
    EXPECT_EQ(feeler_type_proto.yaw_angles(i), yaws[i]);
  }
  for (int i = 0; i < feeler_type_proto.experimental_data().size(); ++i) {
    EXPECT_EQ(feeler_type_proto.experimental_data(i).maximum(), 1);
    EXPECT_EQ(feeler_type_proto.experimental_data(i).minimum(), 0);
  }
  EXPECT_EQ(feeler_type_proto.count(), number_of_feelers);
  EXPECT_EQ(feeler_type_proto.thickness(), thickness);
  EXPECT_EQ(feeler_type_proto.distance().maximum(), distance);
  EXPECT_EQ(feeler_type_proto.distance().minimum(), 0.0f);
}

TEST(AttributeProtoConverterTest, TestFromFeeler) {
  falken::proto::Feeler feeler_proto;
  PopulateFeelerProto(feeler_proto);
  falken::proto::FeelerType feeler_type_proto;
  float fov = 1.5f;
  feeler_type_proto.add_yaw_angles(-fov / 2);
  falken::AttributeContainer attribute_container;
  falken::FeelersAttribute feelers(attribute_container, "feeler_attribute", 3,
                                   4.0f, fov, 0.5f, {"zero", "one", "two"});
  EXPECT_TRUE(
      falken::AttributeProtoConverter::FromFeeler(feeler_proto, feelers));
  EXPECT_EQ(feelers.feelers_distances()[0].value(),
            feeler_proto.measurements(0).distance().value());
  EXPECT_EQ(feelers.feelers_distances()[1].value(),
            feeler_proto.measurements(1).distance().value());
  EXPECT_EQ(feelers.feelers_distances()[2].value(),
            feeler_proto.measurements(2).distance().value());
  EXPECT_EQ(feelers.feelers_ids()[0].value(), 1);
  EXPECT_EQ(feelers.feelers_ids()[1].value(), 0);
  EXPECT_EQ(feelers.feelers_ids()[2].value(), 2);
}

TEST(AttributeProtoConverterTest, TestFromFeelerDifferentMeasurementSizes) {
  falken::proto::Feeler feeler_proto;
  PopulateFeelerProto(feeler_proto);
  feeler_proto.mutable_measurements(0)->add_experimental_data()->set_value(0);
  falken::proto::FeelerType feeler_type_proto;
  float fov = 1.5f;
  feeler_type_proto.add_yaw_angles(-fov / 2);
  falken::AttributeContainer attribute_container;
  falken::FeelersAttribute feelers(attribute_container, "feeler_attribute", 4,
                                   4.0f, fov, 0.5f, {"zero", "one", "two"});
  EXPECT_FALSE(
      falken::AttributeProtoConverter::FromFeeler(feeler_proto, feelers));
}

TEST(AttributeProtoConverterTest, TestFromFeelerDistanceOutOfRange) {
  falken::proto::Feeler feeler_proto;
  feeler_proto.add_measurements()->mutable_distance()->set_value(5.0f);
  feeler_proto.add_measurements()->mutable_distance()->set_value(0.0f);
  feeler_proto.add_measurements()->mutable_distance()->set_value(0.0f);
  falken::proto::FeelerType feeler_type_proto;
  float fov = 1.5f;
  feeler_type_proto.add_yaw_angles(-fov / 2);
  falken::AttributeContainer attribute_container;
  falken::FeelersAttribute feelers(attribute_container, "feeler_attribute", 3,
                                   4.0f, fov, 0.5f, {"zero", "one", "two"});
  std::shared_ptr<falken::SystemLogger> logger = falken::SystemLogger::Get();
  logger->set_abort_on_fatal_error(false);
  EXPECT_FALSE(
      falken::AttributeProtoConverter::FromFeeler(feeler_proto, feelers));
}

TEST(AttributeProtoConverterTest, TestFromFeelerDifferentCategorySizes) {
  falken::proto::Feeler feeler_proto;
  PopulateFeelerProto(feeler_proto);
  falken::proto::FeelerType feeler_type_proto;
  float fov = 1.5f;
  feeler_type_proto.add_yaw_angles(-fov / 2);
  falken::AttributeContainer attribute_container;
  falken::FeelersAttribute feelers(attribute_container, "feeler_attribute", 3,
                                   4.0f, fov, 0.5f, {"zero", "one"});
  EXPECT_FALSE(
      falken::AttributeProtoConverter::FromFeeler(feeler_proto, feelers));
}

TEST(AttributeProtoConverterTest, TestFromFeelerCategoryOutOfRange) {
  falken::proto::Feeler feeler_proto;
  PopulateFeelerProto(feeler_proto);
  feeler_proto.mutable_measurements(0)->mutable_experimental_data(1)->set_value(
      2);
  falken::proto::FeelerType feeler_type_proto;
  float fov = 1.5f;
  feeler_type_proto.add_yaw_angles(-fov / 2);
  falken::AttributeContainer attribute_container;
  falken::FeelersAttribute feelers(attribute_container, "feeler_attribute", 3,
                                   4.0f, fov, 0.5f, {"zero", "one", "two"});
  std::shared_ptr<falken::SystemLogger> logger = falken::SystemLogger::Get();
  logger->set_abort_on_fatal_error(false);
  EXPECT_FALSE(
      falken::AttributeProtoConverter::FromFeeler(feeler_proto, feelers));
}

TEST(AttributeProtoConverterTest, TestFromFeelerRepeatedCategory) {
  falken::proto::Feeler feeler_proto;
  PopulateFeelerProto(feeler_proto);
  feeler_proto.mutable_measurements(0)->mutable_experimental_data(0)->set_value(
      1);
  falken::proto::FeelerType feeler_type_proto;
  float fov = 1.5f;
  feeler_type_proto.add_yaw_angles(-fov / 2);
  falken::AttributeContainer attribute_container;
  falken::FeelersAttribute feelers(attribute_container, "feeler_attribute", 3,
                                   4.0f, fov, 0.5f, {"zero", "one", "two"});
  EXPECT_FALSE(
      falken::AttributeProtoConverter::FromFeeler(feeler_proto, feelers));
}

TEST(AttributeProtoConverterTest, TestFromFeelerType) {
  falken::proto::NumberType one_hot_id_type;
  one_hot_id_type.set_minimum(0.0f);
  one_hot_id_type.set_maximum(1.0f);
  falken::proto::FeelerType feeler_type_proto;
  feeler_type_proto.set_count(4);
  feeler_type_proto.set_thickness(3.0f);
  float fov = 1.5f;
  feeler_type_proto.add_yaw_angles(-fov * 0.5);
  feeler_type_proto.add_yaw_angles(-fov * 0.25);
  feeler_type_proto.add_yaw_angles(fov * 0.25);
  feeler_type_proto.add_yaw_angles(fov * 0.5);
  auto* distance = feeler_type_proto.mutable_distance();
  distance->set_minimum(0.0f);
  distance->set_maximum(10.0f);
  // One experimental_data per id, for each of {"zero", "one", "two"}.
  *feeler_type_proto.add_experimental_data() = one_hot_id_type;
  *feeler_type_proto.add_experimental_data() = one_hot_id_type;
  *feeler_type_proto.add_experimental_data() = one_hot_id_type;

  falken::AttributeContainer attribute_container;
  falken::AttributeProtoConverter::FromFeelerType("new", feeler_type_proto,
                                                  attribute_container);
  auto* new_attribute = attribute_container.attribute("new");
  ASSERT_NE(new_attribute, nullptr);
  EXPECT_THAT(new_attribute->name(), StrEq("new"));
  EXPECT_EQ(new_attribute->feelers_distances().size(),
            feeler_type_proto.count());
  EXPECT_EQ(new_attribute->feelers_thickness(), feeler_type_proto.thickness());
  ASSERT_EQ(new_attribute->feelers_ids().size(), feeler_type_proto.count());
  EXPECT_THAT(new_attribute->feelers_ids()[0].category_values(),
              ElementsAreArray({"0", "1", "2"}));
}

TEST(AttributeProtoConverterTest, TestToJoystick) {
  falken::AttributeContainer attribute_container;
  falken::JoystickAttribute attribute(
      attribute_container,
      "joystick",
      falken::kAxesModeDirectionXZ,
      falken::kControlledEntityPlayer,
      falken::kControlFrameCamera);
  attribute.set_x_axis(0.5f);
  attribute.set_y_axis(-0.25f);
  falken::proto::Joystick joystick =
      falken::AttributeProtoConverter::ToJoystick(attribute);

  EXPECT_THAT(joystick.x_axis(), testing::FloatEq(0.5f));
  EXPECT_THAT(joystick.y_axis(), testing::FloatEq(-0.25f));
}

TEST(AttributeProtoConverterTest, TestToJoystickType) {
  falken::AttributeContainer attribute_container;
  falken::JoystickAttribute attribute(
      attribute_container,
      "joystick",
      falken::kAxesModeDirectionXZ,
      falken::kControlledEntityPlayer,
      falken::kControlFrameCamera);
  attribute.set_x_axis(0.5f);
  attribute.set_y_axis(-0.25f);
  falken::proto::JoystickType j =
      falken::AttributeProtoConverter::ToJoystickType(attribute);

  EXPECT_THAT(j.axes_mode(), falken::proto::JoystickAxesMode::DIRECTION_XZ);
  EXPECT_THAT(j.controlled_entity(), "player");
  EXPECT_THAT(j.control_frame(), "camera");
}

TEST(AttributeProtoConverterTest, TestFromJoystick) {
  falken::proto::Joystick j;
  j.set_x_axis(0.5f);
  j.set_y_axis(-0.25f);

  falken::AttributeContainer attribute_container;
  falken::JoystickAttribute attribute(
      attribute_container,
      "joystick",
      falken::kAxesModeDirectionXZ,
      falken::kControlledEntityCamera,
      falken::kControlFrameWorld);

  EXPECT_TRUE(falken::AttributeProtoConverter::FromJoystick(j, attribute));
  EXPECT_THAT(attribute.joystick_x_axis(), testing::FloatEq(0.5f));
  EXPECT_THAT(attribute.joystick_y_axis(), testing::FloatEq(-0.25f));

  // Test out of range errors.

  std::shared_ptr<falken::SystemLogger> logger = falken::SystemLogger::Get();
  logger->set_abort_on_fatal_error(false);

  j.set_x_axis(1.5f);
  EXPECT_FALSE(falken::AttributeProtoConverter::FromJoystick(j, attribute));
  j.set_x_axis(-1.5f);
  EXPECT_FALSE(falken::AttributeProtoConverter::FromJoystick(j, attribute));
  j.set_x_axis(0.5f);
  EXPECT_TRUE(falken::AttributeProtoConverter::FromJoystick(j, attribute));
  j.set_y_axis(1.5f);
  EXPECT_FALSE(falken::AttributeProtoConverter::FromJoystick(j, attribute));
  j.set_y_axis(-1.5f);
  EXPECT_FALSE(falken::AttributeProtoConverter::FromJoystick(j, attribute));
}

TEST(AttributeProtoConverterTest, TestFromJoystickType) {
  falken::proto::JoystickType j;
  j.set_axes_mode(falken::proto::JoystickAxesMode::DELTA_PITCH_YAW);
  j.set_controlled_entity("player");
  j.set_control_frame("camera");

  falken::AttributeContainer attribute_container;
  falken::AttributeProtoConverter::FromJoystickType(
      "joystick", j, attribute_container);

  falken::AttributeBase *attribute = attribute_container.attribute("joystick");
  ASSERT_NE(attribute, nullptr);
  EXPECT_EQ(attribute->joystick_axes_mode(), falken::kAxesModeDeltaPitchYaw);
  EXPECT_EQ(attribute->joystick_controlled_entity(),
              falken::kControlledEntityPlayer);
  EXPECT_EQ(attribute->joystick_control_frame(), falken::kControlFrameCamera);
}



TEST(AttributeProtoConverterTest, TestToPosition) {
  falken::AttributeContainer attribute_container;
  falken::PositionAttribute attribute(attribute_container,
                                      "position_attribute");
  falken::Position position({1.0f, 2.0f, 3.0f});
  attribute.set_value(position);
  falken::proto::Position position_proto =
      falken::AttributeProtoConverter::ToPosition(attribute);
  EXPECT_EQ(position_proto.x(), position.x);
  EXPECT_EQ(position_proto.y(), position.y);
  EXPECT_EQ(position_proto.z(), position.z);
}

TEST(AttributeProtoConverterTest, TestFromPosition) {
  falken::proto::Position position_proto;
  position_proto.set_x(1.0f);
  position_proto.set_y(2.0f);
  position_proto.set_z(3.0f);
  falken::AttributeContainer attribute_container;
  falken::PositionAttribute attribute(attribute_container,
                                      "position_attribute");
  EXPECT_TRUE(
      falken::AttributeProtoConverter::FromPosition(position_proto, attribute));
  EXPECT_EQ(attribute.position().x, position_proto.x());
  EXPECT_EQ(attribute.position().y, position_proto.y());
  EXPECT_EQ(attribute.position().z, position_proto.z());
}

TEST(AttributeProtoConverterTest, TestToRotation) {
  falken::AttributeContainer attribute_container;
  falken::RotationAttribute attribute(attribute_container,
                                      "rotation_attribute");
  falken::Rotation rotation({1.0f, 1.0f, 1.0f, 0.0f});
  attribute.set_value(rotation);
  falken::proto::Rotation rotation_proto =
      falken::AttributeProtoConverter::ToRotation(attribute);
  EXPECT_EQ(rotation_proto.w(), rotation.w);
  EXPECT_EQ(rotation_proto.x(), rotation.x);
  EXPECT_EQ(rotation_proto.y(), rotation.y);
  EXPECT_EQ(rotation_proto.z(), rotation.z);
}

TEST(AttributeProtoConverterTest, TestFromRotation) {
  falken::proto::Rotation rotation_proto;
  rotation_proto.set_w(1.0f);
  rotation_proto.set_x(1.0f);
  rotation_proto.set_y(1.0f);
  rotation_proto.set_z(0.0f);
  falken::AttributeContainer attribute_container;
  falken::RotationAttribute attribute(attribute_container,
                                      "rotation_attribute");
  EXPECT_TRUE(
      falken::AttributeProtoConverter::FromRotation(rotation_proto, attribute));
  EXPECT_EQ(attribute.rotation().w, rotation_proto.w());
  EXPECT_EQ(attribute.rotation().x, rotation_proto.x());
  EXPECT_EQ(attribute.rotation().y, rotation_proto.y());
  EXPECT_EQ(attribute.rotation().z, rotation_proto.z());
}

}  // namespace
