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

#include <algorithm>
#include <iterator>
#include <sstream>

#include "src/core/assert.h"
#include "src/core/attribute_internal.h"
#include "src/core/log.h"
#include "src/core/protos.h"
#include "falken/attribute.h"
#include "falken/attribute_base.h"
#include "falken/types.h"
#include "absl/strings/str_format.h"

namespace falken {

// Defined in attribute.cc.
extern const char* AttributeBaseTypeToString(AttributeBase::Type type);

namespace {
const Vector<String>& GetBoolCategories() {
  static const Vector<String> kBoolCategories({"false", "true"});  // NOLINT
  return kBoolCategories;
}

const std::vector<std::string>& GetStdVectorBoolCategories() {
  static const std::vector<std::string> kBoolCategories(  // NOLINT
      {"false", "true"});                                 // NOLINT
  return kBoolCategories;
}
}  // namespace

std::string AttributeBaseDebugString(const AttributeBase& attribute_base) {
  constexpr const char* debug_string =
      "Attribute name: %s\n"
      "Attribute type: %s\n"
      "Attribute category_values: %s\n"
      "Attribute minimum value: %f\n"
      "Attribute maximum value: %f\n"
      "Attribute feelers number: %d\n"
      "Attribute feelers length: %f\n"
      "Attribute feelers thickness: %f\n"
      "Attribute feelers fov: %f\n"
      "Attribute feelers IDs: %s\n";
  std::stringstream category_names;
  for (const auto& category : attribute_base.category_values()) {
    category_names << category.c_str() << ", ";
  }
  std::stringstream feelers_category_names;
  if (attribute_base.type() == AttributeBase::kTypeFeelers &&
      !attribute_base.feelers_ids().empty()) {
    for (const auto& category :
         attribute_base.feelers_ids()[0].category_values()) {
      feelers_category_names << category.c_str() << ", ";
    }
  }
  return absl::StrFormat(debug_string, attribute_base.name(),
                         AttributeBaseTypeToString(attribute_base.type()),
                         category_names.str().c_str(),
                         attribute_base.type() == AttributeBase::kTypeFloat
                             ? attribute_base.number_minimum()
                             : 0.0f,
                         attribute_base.type() == AttributeBase::kTypeFloat
                             ? attribute_base.number_maximum()
                             : 0.0f,
                         attribute_base.type() != AttributeBase::kTypeFeelers
                             ? 0
                             : attribute_base.feelers_distances().size(),
                         attribute_base.type() != AttributeBase::kTypeFeelers
                             ? 0
                             : attribute_base.feelers_length(),
                         attribute_base.type() != AttributeBase::kTypeFeelers
                             ? 0
                             : attribute_base.feelers_thickness(),
                         attribute_base.type() != AttributeBase::kTypeFeelers
                             ? 0
                             : attribute_base.feelers_fov_angle(),
                         attribute_base.type() != AttributeBase::kTypeFeelers
                             ? std::string()
                             : feelers_category_names.str().c_str());
}

// Get a number attribute as a proto.
proto::Number AttributeProtoConverter::ToNumber(
    const AttributeBase& attribute) {
  proto::Number number;
  number.set_value(attribute.number());
  return number;
}

bool AttributeProtoConverter::FromNumber(const proto::Number& number,
                                         AttributeBase& output_attribute) {
  if (!output_attribute.set_number(number.value())) {
    LogError(
        "Failed to parse the received number %f into attribute '%s' with type "
        "'%s' and range = [%f, %f]. This could be caused because the service  "
        "sent an out of range value. %s.",
        number.value(), output_attribute.name(),
        AttributeBaseTypeToString(output_attribute.type()),
        output_attribute.number_minimum(), output_attribute.number_maximum(),
        kContactFalkenTeamBug);
    return false;
  }
  return true;
}

// Get the required constraints of a number attribute as a proto.
proto::NumberType AttributeProtoConverter::ToNumberType(
    const AttributeBase& attribute) {
  proto::NumberType number_type;
  number_type.set_minimum(attribute.number_minimum());
  number_type.set_maximum(attribute.number_maximum());
  return number_type;
}

void AttributeProtoConverter::FromNumberType(const char* name,
                                             const proto::NumberType& number,
                                             AttributeContainer& container) {
  container.attribute_container_data_->allocated_attributes.emplace_back(
      container, name, number.minimum(), number.maximum());
}

// Get a categorical value attribute as a proto.
proto::Category AttributeProtoConverter::ToCategory(
    const AttributeBase& attribute) {
  proto::Category category;
  switch (attribute.type()) {
    case AttributeBase::kTypeCategorical:
      category.set_value(attribute.category());
      break;
    case AttributeBase::kTypeBool:
      category.set_value(attribute.boolean() ? 1 : 0);
      break;
    default:
      FALKEN_DEV_ASSERT_MESSAGE(false,
                                "Attribute type should be Categorical "
                                "or Bool.");
      break;
  }
  return category;
}

bool AttributeProtoConverter::FromCategory(const proto::Category& category,
                                           AttributeBase& output_attribute) {
  bool parsed = false;
  switch (output_attribute.type()) {
    case AttributeBase::kTypeCategorical:
      parsed = output_attribute.set_category(category.value());
      break;
    case AttributeBase::kTypeBool: {
      int value = category.value();
      parsed = (value == 0 || value == 1) &&
               output_attribute.set_boolean(value != 0);
      break;
    }
    default:
      break;
  }
  if (!parsed) {
    LogError(
        "Failed to parse the received category value %d into the attribute "
        "'%s' which type is '%s'. The service may have sent a value  that is "
        "not a Bool or a Category. %s.",
        category.value(), output_attribute.name(),
        AttributeBaseTypeToString(output_attribute.type()),
        kContactFalkenTeamBug);
  }
  return parsed;
}

void AttributeProtoConverter::FromCategoryType(
    const char* name, const proto::CategoryType& category,
    AttributeContainer& container) {
  std::vector<std::string> enum_values(category.enum_values().begin(),
                                       category.enum_values().end());
  if (enum_values == GetStdVectorBoolCategories()) {
    container.attribute_container_data_->allocated_attributes.emplace_back(
        container, name, AttributeBase::kTypeBool);
  } else {
    container.attribute_container_data_->allocated_attributes.emplace_back(
        container, name, enum_values);
  }
}

// Get the available values for a categorical value attribute as a proto.
proto::CategoryType AttributeProtoConverter::ToCategoryType(
    const AttributeBase& attribute) {
  proto::CategoryType category_type;
  const Vector<String>* categories = nullptr;
  switch (attribute.type()) {
    case AttributeBase::kTypeCategorical: {
      categories = &attribute.category_values();
      break;
    }
    case AttributeBase::kTypeBool:
      categories = &GetBoolCategories();
      break;
    default:
      FALKEN_DEV_ASSERT_MESSAGE(false,
                                "Attribute type should be "
                                "Categorical or Bool.");
      return category_type;
  }
  category_type.mutable_enum_values()->Reserve(categories->size());
  for (const auto& category : *categories) {
    category_type.add_enum_values(category.c_str());
  }
  return category_type;
}

proto::Feeler AttributeProtoConverter::ToFeeler(
    const AttributeBase& attribute) {
  proto::Feeler feeler_proto;
  FALKEN_DEV_ASSERT(
      attribute.feelers_ids().empty() ||
      attribute.feelers_distances().empty() ||
      attribute.feelers_ids().size() == attribute.feelers_distances().size());

  for (int i = 0; i < attribute.feelers_distances().size(); ++i) {
    auto* measurement = feeler_proto.add_measurements();
    if (!attribute.feelers_distances().empty()) {
      measurement->mutable_distance()->set_value(
          attribute.feelers_distances()[i].value());
    }
    if (!attribute.feelers_ids().empty()) {
      // Add the one-hot encoded id to the experimental_data.
      for (int j = 0; j < attribute.number_of_feelers_ids(); ++j) {
        measurement->add_experimental_data()->set_value(
            attribute.feelers_ids()[i].value() == j ? 1 : 0);
      }
    }
  }
  return feeler_proto;
}

bool AttributeProtoConverter::FromFeeler(const proto::Feeler& feeler,
                                         AttributeBase& output_attribute) {
  int number_of_feelers = output_attribute.feelers_distances().size();
  if (feeler.measurements_size() != number_of_feelers) {
    LogError(
        "Failed to parse the received feeler with %d feelers into the "
        "attribute '%s' with %d feelers. Size mismatch.",
        feeler.measurements_size(), output_attribute.name(), number_of_feelers);
    return false;
  }

  for (int i = 0; i < number_of_feelers; ++i) {
    const auto& measurement = feeler.measurements(i);
    if (!output_attribute.feelers_distances().empty() &&
        !FromNumber(measurement.distance(),
                    output_attribute.feelers_distances()[i])) {
      LogError(
          "Failed to parse the received feeler distance with index %d into "
          "the attribute '%s'. %s.",
          i, output_attribute.name(), kContactFalkenTeamBug);
      return false;
    }
    if (!output_attribute.feelers_ids().empty()) {
      int number_of_ids = output_attribute.number_of_feelers_ids();
      // Decode the one-hot encoded category from the experimental_data.
      if (number_of_ids != measurement.experimental_data_size()) {
        LogError(
            "Failed to parse the received feeler categories with index '%d' "
            "and '%d' IDs into the attribute '%s' with %d IDs. Both should "
            "have the same size. Check if the attribute IDs were properly "
            "defined.",
            i, measurement.experimental_data_size(), output_attribute.name(),
            number_of_ids);
        return false;
      }
      // Decode the one-hot encoded id.
      int id_value = -1;
      for (int j = 0; j < number_of_ids; ++j) {
        if (static_cast<int>(measurement.experimental_data(j).value()) == 1) {
          if (id_value >= 0) {
            LogError(
                "Failed to parse feeler categories with index %d into the "
                "attribute '%s' as more than one category was set in the "
                "service. %s.",
                i, output_attribute.name(), kContactFalkenTeamBug);
            return false;
          }
          id_value = j;
        }
      }
      if (!output_attribute.feelers_ids()[i].set_value(id_value)) {
        LogError(
            "Failed to parse the received feeler IDs with index %d into "
            "the attribute '%s'. The service provided the out of range "
            "id value %d. %s.",
            i, output_attribute.name(), id_value, kContactFalkenTeamBug);
        return false;
      }
    }
  }
  return true;
}

void AttributeProtoConverter::FromFeelerType(const char* name,
                                             const proto::FeelerType& feeler,
                                             AttributeContainer& container) {
  std::vector<std::string> ids;
  if (feeler.experimental_data_size() > 0) {
    const int id_count = feeler.experimental_data_size();
    ids.resize(id_count);
    for (int i = 0; i < id_count; ++i) {
      ids[i] = std::to_string(i);
    }
  }
  container.attribute_container_data_->allocated_attributes.emplace_back(
      container, name, feeler.count(), feeler.distance().maximum(),
      -feeler.yaw_angles(0) * 2, feeler.thickness(), ids);
}

proto::FeelerType AttributeProtoConverter::ToFeelerType(
    const AttributeBase& attribute) {
  proto::FeelerType feeler_type_proto;
  auto number_type = feeler_type_proto.mutable_distance();
  number_type->set_minimum(0);
  number_type->set_maximum(attribute.feelers_length());
  feeler_type_proto.set_count(attribute.feelers_distances().size());
  feeler_type_proto.set_thickness(attribute.feelers_thickness());
  // Filling the yaw angles starting from the FOV divided by two and adding a
  // delta angle that depends on the FOV, the amount of feelers and the feeler
  // position.
  float start_angle = -attribute.feelers_fov_angle() / 2.0f;
  float angle_per_feeler =
      attribute.feelers_fov_angle() /
      static_cast<float>(attribute.feelers_distances().size() - 1);
  if (attribute.feelers_distances().size() == 1) {
    angle_per_feeler = 0.0f;
    start_angle = 0.0f;
  }
  for (int i = 0; i < attribute.feelers_distances().size(); ++i) {
    feeler_type_proto.add_yaw_angles(start_angle + (angle_per_feeler * i));
  }
  for (int i = 0; i < attribute.number_of_feelers_ids(); ++i) {
    auto id = feeler_type_proto.add_experimental_data();
    // Specify binary data because it is one-hot encoded.
    id->set_minimum(0);
    id->set_maximum(1);
  }
  return feeler_type_proto;
}

namespace {

const char* kControlledEntityPlayerId = "player";
const char* kControlledEntityCameraId = "camera";
const char* kControlFramePlayerId = "player";
const char* kControlFrameCameraId = "camera";
const char* kControlFrameWorldId = "";  // world is encoded as the empty string.

proto::JoystickAxesMode ToProtoEnum(falken::AxesMode m) {
  switch (m) {
    case kAxesModeDeltaPitchYaw:
      return proto::JoystickAxesMode::DELTA_PITCH_YAW;
      break;
    case kAxesModeDirectionXZ:
      return proto::JoystickAxesMode::DIRECTION_XZ;
      break;
    default:
      LogError("Encountered an invalid axes mode of %d during translation.", m);
      return proto::JoystickAxesMode::UNDEFINED;
  }
}

falken::AxesMode FromProtoEnum(proto::JoystickAxesMode m) {
  switch (m) {
    case proto::JoystickAxesMode::DELTA_PITCH_YAW:
      return kAxesModeDeltaPitchYaw;
      break;
    case proto::JoystickAxesMode::DIRECTION_XZ:
      return kAxesModeDirectionXZ;
      break;
    default:
      LogError("Encountered an invalid axes mode of %d during translation.", m);
      return kAxesModeInvalid;
  }
}

falken::ControlFrame FromControlFrameStringToEnum(const std::string& id) {
  if (id == kControlFramePlayerId) {
    return kControlFramePlayer;
  }

  if (id == kControlFrameWorldId) {
    return kControlFrameWorld;
  }
  if (id == kControlFrameCameraId) {
    return kControlFrameCamera;
  }
  LogError(
      "Encountered an invalid joystick control frame of %s during "
      "translation. %s",
      id.c_str(), kContactFalkenTeamBug);
  return kControlFrameWorld;
}

falken::ControlledEntity FromControlledEntityStringToEnum(
    const std::string& id) {
  if (id == kControlledEntityPlayerId) {
    return kControlledEntityPlayer;
  }
  if (id == kControlledEntityCameraId) {
    return kControlledEntityCamera;
  }
  LogError(
      "Encountered an invalid joystick controlled entity %s during "
      "translation. %s",
      id.c_str(), kContactFalkenTeamBug);
  return kControlledEntityPlayer;
}

std::string FromControlledEntityEnumToString(
    ControlledEntity controlled_entity) {
  std::string controlled_entity_string;
  switch (controlled_entity) {
    case kControlledEntityPlayer:
      controlled_entity_string = kControlledEntityPlayerId;
      return controlled_entity_string;
    case kControlledEntityCamera:
      controlled_entity_string = kControlledEntityCameraId;
      return controlled_entity_string;
    default:
      LogError(
          "Encountered an invalid controlled entity %d in a joystick "
          "attribute. Controlled entities should be kControlledEntityPlayer "
          "(0) or kControlledEntityCamera (1).",
          controlled_entity);
      return controlled_entity_string;
  }
}

std::string FromControlFrameToString(ControlFrame control_frame) {
  std::string control_frame_string = std::string();
  switch (control_frame) {
    case kControlFrameWorld:
      control_frame_string = kControlFrameWorldId;
      return control_frame_string;
    case kControlFrameCamera:
      control_frame_string = kControlFrameCameraId;
      return control_frame_string;
    case kControlFramePlayer:
      control_frame_string = kControlFramePlayerId;
      return control_frame_string;
    default:
      LogError(
          "Encountered an invalid control frame %d in a joystick "
          "attribute. Controlled entities should be kControlFrameWorld (0), "
          "kControlFramePlayer (1) or kControlFrameCamera (2).",
          control_frame);
      return control_frame_string;
  }
}
}  // namespace

// Convert Joystick value to a proto.
proto::Joystick AttributeProtoConverter::ToJoystick(
    const AttributeBase& attribute) {
  proto::Joystick joystick;
  joystick.set_x_axis(attribute.joystick_x_axis());
  joystick.set_y_axis(attribute.joystick_y_axis());
  return joystick;
}

// Get a Joystick value attribute from a proto.
bool AttributeProtoConverter::FromJoystick(const proto::Joystick& joystick,
                                           AttributeBase& output_attribute) {
  if (!output_attribute.set_joystick_x_axis(joystick.x_axis())) {
    LogError(
        "Failed to parse the received joystick x_axis value %f into joystick "
        "attribute '%s'. This could be caused because the service sent a "
        "value outside the allowed range [-1.0f, 1.0f].",
        joystick.x_axis(), output_attribute.name());
    return false;
  }
  if (!output_attribute.set_joystick_y_axis(joystick.y_axis())) {
     LogError(
        "Failed to parse the received joystick y_axis value %f into joystick "
        "attribute '%s'. This could be caused because the service sent a "
        "value outside the allowed range [-1.0f, 1.0f].",
        joystick.y_axis(), output_attribute.name());
    return false;
  }

  return true;
}

// Construct an attribute from a joystick type and add it to the container.
void AttributeProtoConverter::FromJoystickType(
    const char* name, const proto::JoystickType& joystick,
    AttributeContainer& container) {
  container.attribute_container_data_->allocated_attributes.emplace_back(
      container, name, FromProtoEnum(joystick.axes_mode()),
      FromControlledEntityStringToEnum(joystick.controlled_entity()),
      FromControlFrameStringToEnum(joystick.control_frame()));
}

// Convert the available values for a Joystick value attribute to proto.
proto::JoystickType AttributeProtoConverter::ToJoystickType(
    const AttributeBase& attribute) {
  proto::JoystickType joystick;
  joystick.set_axes_mode(ToProtoEnum(attribute.joystick_axes_mode()));
  joystick.set_controlled_entity(
      FromControlledEntityEnumToString(attribute.joystick_controlled_entity()));
  joystick.set_control_frame(
      FromControlFrameToString(attribute.joystick_control_frame()));
  return joystick;
}

// Get attribute's position as a proto.
proto::Position AttributeProtoConverter::ToPosition(
    const AttributeBase& attribute) {
  proto::Position position;
  position.set_x(attribute.position().x);
  position.set_y(attribute.position().y);
  position.set_z(attribute.position().z);
  return position;
}

bool AttributeProtoConverter::FromPosition(const proto::Position& position,
                                           AttributeBase& output_attribute) {
  return output_attribute.set_position(
      Position(position.x(), position.y(), position.z()));
}

// Get attribute's rotation as a proto.
proto::Rotation AttributeProtoConverter::ToRotation(
    const AttributeBase& attribute) {
  proto::Rotation rotation;
  rotation.set_x(attribute.rotation().x);
  rotation.set_y(attribute.rotation().y);
  rotation.set_z(attribute.rotation().z);
  rotation.set_w(attribute.rotation().w);
  return rotation;
}

bool AttributeProtoConverter::FromRotation(const proto::Rotation& rotation,
                                           AttributeBase& output_attribute) {
  return output_attribute.set_rotation(
      Rotation(rotation.x(), rotation.y(), rotation.z(), rotation.w()));
}

void AttributeProtoConverter::FromEntityFieldType(
    const proto::EntityFieldType& entity_field_type,
    AttributeContainer& attribute_container) {
  if (entity_field_type.has_number()) {
    FromNumberType(entity_field_type.name().c_str(), entity_field_type.number(),
                   attribute_container);
  } else if (entity_field_type.has_category()) {
    FromCategoryType(entity_field_type.name().c_str(),
                     entity_field_type.category(),
                     attribute_container);
  } else if (entity_field_type.has_feeler()) {
    FromFeelerType(entity_field_type.name().c_str(), entity_field_type.feeler(),
                   attribute_container);
  } else {
    LogWarning(
        "Failed to parse received entity_field type '%s' since it does not "
        "contain a supported type. Received attribute type should be one of "
        "Number, Categorical or Feeler. %s.",
        entity_field_type.name().c_str(), kContactFalkenTeamBug);
  }
}

bool AttributeProtoConverter::FromEntityField(
    const proto::EntityField& entity_field, AttributeBase& output_attribute) {
  bool parsed = false;
  if (entity_field.has_number()) {
    parsed = FromNumber(entity_field.number(), output_attribute);
  } else if (entity_field.has_category()) {
    parsed = FromCategory(entity_field.category(), output_attribute);
  } else if (entity_field.has_feeler()) {
    parsed = FromFeeler(entity_field.feeler(), output_attribute);
  } else {
    LogError(
        "Failed to parse received entity_field with unsupported type into "
        "the attribute '%s'. Type should be Number, Categorical or Feeler."
        "%s.",
        output_attribute.name(), kContactFalkenTeamBug);
  }
  return parsed;
}

void AttributeProtoConverter::FromActionType(
    const proto::ActionType& action_type,
    AttributeContainer& attribute_container) {
  if (action_type.has_number()) {
    FromNumberType(action_type.name().c_str(), action_type.number(),
                   attribute_container);
  } else if (action_type.has_category()) {
    FromCategoryType(action_type.name().c_str(), action_type.category(),
                     attribute_container);
  } else if (action_type.has_joystick()) {
    FromJoystickType(action_type.name().c_str(), action_type.joystick(),
                     attribute_container);
  } else {
    LogError(
        "Failed to parse de received ActionType '%s' since it does not contain "
        "a supported type. Supported types are Number, Categorical and "
        "Joystick. %s.",
        action_type.name().c_str(), kContactFalkenTeamBug);
  }
}

bool AttributeProtoConverter::FromAction(const proto::Action& action,
                                         AttributeBase& output_attribute) {
  bool parsed = false;
  if (action.has_number()) {
    parsed = FromNumber(action.number(), output_attribute);
  } else if (action.has_category()) {
    parsed = FromCategory(action.category(), output_attribute);
  } else if (action.has_joystick()) {
    parsed = FromJoystick(action.joystick(), output_attribute);
  } else {
    LogError(
        "Failed to parse the received action into the attribute '%s' since it "
        "does not contain a supported type. Supported types are Number, "
        "Categorical and Joystick. %s.",
        output_attribute.name(), kContactFalkenTeamBug);
  }
  return parsed;
}

bool AttributeProtoConverter::Compare(const proto::NumberType& number,
                                      const AttributeBase& attribute) {
  return attribute.type() == AttributeBase::kTypeFloat &&
         number.minimum() == attribute.number_minimum() &&
         number.maximum() == attribute.number_maximum();
}

bool AttributeProtoConverter::Compare(const proto::CategoryType& category,
                                      const AttributeBase& attribute) {
  Vector<String> enum_values;
  const auto& proto_enum_values = category.enum_values();
  enum_values.resize(proto_enum_values.size());
  std::transform(
      proto_enum_values.begin(), proto_enum_values.end(), enum_values.begin(),
      [](const std::string& str) -> String { return String(str.c_str()); });
  bool is_category_and_equal =
      attribute.type() == AttributeBase::kTypeCategorical &&
      attribute.category_values() == enum_values;
  bool is_bool_and_equal = attribute.type() == AttributeBase::kTypeBool &&
                           GetBoolCategories() == enum_values;
  return is_category_and_equal || is_bool_and_equal;
}

bool AttributeProtoConverter::Compare(const proto::FeelerType& feeler,
                                      const AttributeBase& attribute) {
  bool equal = true;
  if (attribute.type() != AttributeBase::kTypeFeelers) {
    LogWarning("%s is not a feelers attribute.", attribute.name());
    equal = false;
  }
  float proto_fov = -feeler.yaw_angles(0) * 2;
  if (attribute.feelers_fov_angle() != proto_fov) {
    LogWarning(
        "Feelers attribute %s FoV angle %f does not match the FoV angle "
        "%f reported by the service.",
        attribute.name(), attribute.feelers_fov_angle(), proto_fov);
    equal = false;
  }
  if (attribute.feelers_length() != feeler.distance().maximum()) {
    LogWarning(
        "Feelers attribute '%s' length %f does not match the length %f "
        "reported by the service.",
        attribute.name(), attribute.feelers_length(),
        feeler.distance().maximum());
    equal = false;
  }
  if (attribute.number_of_feelers_ids() != feeler.experimental_data_size()) {
    LogWarning(
        "Feelers attribute '%s' has %d possible IDs which does not match the "
        "%f IDs reported by the service.",
        attribute.name(), attribute.number_of_feelers_ids(),
        feeler.experimental_data_size());
    equal = false;
  }
  return equal;
}

bool AttributeProtoConverter::Compare(const proto::JoystickType& joystick,
                                      const AttributeBase& attribute) {
  bool equal = true;
  if (attribute.type() != AttributeBase::kTypeJoystick) {
    LogWarning(
        "Attribute '%s' is not a joystick, but the service reports that it is.",
        attribute.name());
    return false;
  }
  if (attribute.joystick_axes_mode() != FromProtoEnum(joystick.axes_mode())) {
    equal = false;
    LogWarning(
        "Mismatch on attribute '%s'. The service reports an axes_mode of %d "
        "but the attribute has axes_mode %d",
        attribute.name(), FromProtoEnum(joystick.axes_mode()),
        attribute.joystick_axes_mode());
  }
  if (attribute.joystick_controlled_entity() !=
      FromControlledEntityStringToEnum(joystick.controlled_entity())) {
    equal = false;
    LogWarning(
        "Mismatch on attribute '%s'. The service reports controlled_entity "
        "'%s' but the attribute has controlled_entity '%s'",
        attribute.name(), joystick.controlled_entity().c_str(),
        attribute.joystick_controlled_entity());
  }
  if (attribute.joystick_control_frame() !=
      FromControlFrameStringToEnum(joystick.control_frame())) {
    equal = false;
    LogWarning(
        "Mismatch on attribute '%s'. The service reports control_frame '%s' "
        "but the attribute has control_frame %s",
        attribute.name(), joystick.control_frame().c_str(),
        attribute.joystick_control_frame());
  }
  return equal;
}

bool AttributeProtoConverter::CompareActionTypeToAttributeBase(
    const proto::ActionType& action_type, const AttributeBase& attribute) {
  bool is_number_and_equal =
      action_type.has_number() && Compare(action_type.number(), attribute);
  bool is_category_or_bool_and_equal =
      action_type.has_category() && Compare(action_type.category(), attribute);
  bool is_joystick_and_equal =
      action_type.has_joystick() && Compare(action_type.joystick(), attribute);
  if (!(is_number_and_equal || is_category_or_bool_and_equal ||
        is_joystick_and_equal)) {
    LogWarning(
        "Action specification mismatch. The received action "
        "specification is different from the expected one.\n "
        "Received specification is:\n%s\nExpected is:\n%s\n",
        action_type.DebugString().c_str(),
        AttributeBaseDebugString(attribute).c_str());
    return false;
  }
  return true;
}

bool AttributeProtoConverter::CompareEntityFieldTypeToAttributeBase(
    const proto::EntityFieldType& entity_field_type,
    const AttributeBase& attribute) {
  bool is_number_and_equal = entity_field_type.has_number() &&
                             Compare(entity_field_type.number(), attribute);
  bool is_category_or_bool_and_equal =
      entity_field_type.has_category() &&
      Compare(entity_field_type.category(), attribute);
  bool is_feeler_and_equal = entity_field_type.has_feeler() &&
                             Compare(entity_field_type.feeler(), attribute);
  if (!(is_number_and_equal || is_category_or_bool_and_equal ||
        is_feeler_and_equal)) {
    LogWarning(
        "Type mismatch. Received type doesn't match with the attribute "
        "expected type."
        "\nReceived type is:\n%s\nExpected type is:\n%s\n",
        entity_field_type.DebugString().c_str(),
        AttributeBaseDebugString(attribute).c_str());
    return false;
  }
  return true;
}

bool AttributeProtoConverter::CompareEntityFieldToAttributeBase(
    const proto::EntityField& entity_field,
    const AttributeBase& attribute_base) {
  bool is_number_and_equal = entity_field.has_number() &&
                             attribute_base.type() == AttributeBase::kTypeFloat;
  bool is_category_and_equal =
      entity_field.has_category() &&
      (attribute_base.type() == AttributeBase::kTypeCategorical ||
       attribute_base.type() == AttributeBase::kTypeBool);
  bool is_feeler_and_equal =
      entity_field.has_feeler() &&
      attribute_base.type() == AttributeBase::kTypeFeelers &&
      entity_field.feeler().measurements_size() ==
          attribute_base.number_of_feelers() &&
      entity_field.feeler().measurements(0).experimental_data_size() ==
          attribute_base.number_of_feelers_ids();
  if (!is_number_and_equal && !is_category_and_equal && !is_feeler_and_equal) {
    LogWarning(
        "Attribute mismatch. Received attribute is different from the expected."
        "\nReceived is:\n%s\nExpected is:\n%s\n",
        entity_field.DebugString().c_str(),
        AttributeBaseDebugString(attribute_base).c_str());
    return false;
  }
  return true;
}

}  // namespace falken
