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

#include <stdint.h>

#include <cmath>
#include <set>
#include <string>

#include "src/core/protos.h"
#include "src/core/status_macros.h"
#include "src/core/statusor.h"
#include "absl/base/macros.h"
#include "absl/status/status.h"
#include "absl/strings/str_format.h"
#include "absl/strings/str_join.h"

namespace falken {
namespace common {

namespace {
using absl::InvalidArgumentError;
using absl::Status;

using falken::common::StatusOr;
using proto::Action;
using proto::ActionData;
using proto::ActionSpec;
using proto::ActionType;
using proto::BrainSpec;
using proto::Category;
using proto::CategoryType;
using proto::Entity;
using proto::EntityField;
using proto::EntityFieldType;
using proto::EntityType;
using proto::Feeler;
using proto::FeelerType;
using proto::Joystick;
using proto::JoystickAxesMode;
using proto::JoystickType;
using proto::Number;
using proto::NumberType;
using proto::ObservationData;
using proto::ObservationSpec;
using proto::Position;
using proto::PositionType;
using proto::Rotation;
using proto::RotationType;

constexpr float kDelta = 1e-10f;

absl::Status CheckValid(const EntityType& spec);

Status Typecheck(const CategoryType& spec, const Category& data) {
  if (spec.enum_values_size() < 2) {
    return InvalidArgumentError(
        "Category specifies less than two enum_values:\nspec: " +
        spec.DebugString());
  }

  if (data.value() < 0 || data.value() >= spec.enum_values().size()) {
    return InvalidArgumentError(
        "Category value " + std::to_string(data.value()) + " is out of " +
        "range [0, " + std::to_string(spec.enum_values().size() - 1) + "]");
  }
  return absl::OkStatus();
}

Status Typecheck(const NumberType& spec, const Number& data) {
  if (spec.minimum() == spec.maximum()) {
    return InvalidArgumentError("Invalid singleton range for NumberType: " +
                                spec.DebugString());
  }

  if (data.value() < spec.minimum() || data.value() > spec.maximum()) {
    return InvalidArgumentError("Number value " + std::to_string(data.value()) +
                                " is out of " + "range [" +
                                std::to_string(spec.minimum()) + ", " +
                                std::to_string(spec.maximum()));
  }
  return absl::OkStatus();
}

inline Status CheckJoystickAxes(const Joystick& data) {
  if (std::fabs(data.x_axis()) > 1 + kDelta) {
    return InvalidArgumentError(
        absl::StrFormat("Joystick x_axis out of range: %f", data.x_axis()));
  }
  if (std::fabs(data.y_axis()) > 1 + kDelta) {
    return InvalidArgumentError(
        absl::StrFormat("Joystick y_axis out of range: %f", data.y_axis()));
  }
  return absl::OkStatus();
}

Status Typecheck(const JoystickType& spec, const Joystick& data) {
  return CheckJoystickAxes(data);
}

Status Typecheck(const FeelerType& spec, const Feeler& data) {
  if (spec.count() != data.measurements_size()) {
    return InvalidArgumentError(
        "Feeler has " + std::to_string(data.measurements_size()) +
        " measurements, but the FeelerType spec requires " +
        std::to_string(spec.count()) + " measurements to be provided.");
  }
  if (spec.count() != spec.yaw_angles_size()) {
    return InvalidArgumentError(
        "FeelerType has " + std::to_string(spec.yaw_angles_size()) +
        " yaw angles, but a count of " + std::to_string(spec.count()) +
        " measurements to be provided.");
  }
  return absl::OkStatus();
}

Status Typecheck(const EntityFieldType& spec, const EntityField& data) {
  if (!spec.has_category() && !spec.has_number() && !spec.has_feeler()) {
    return InvalidArgumentError("EntityFieldType spec may not be empty.");
  }
  if (!data.has_category() && !data.has_number() && !data.has_feeler()) {
    return InvalidArgumentError("EntityField has no known type.");
  }
  if (spec.has_category() != data.has_category()) {
    return InvalidArgumentError(
        "EntityFieldType spec does not match data: \nspec: " +
        spec.DebugString() + "\ndata: " + data.DebugString());
  }
  if (spec.has_feeler() != data.has_feeler()) {
    return InvalidArgumentError(
        "EntityFieldType spec does not match data: \nspec: " +
        spec.DebugString() + "\ndata: " + data.DebugString());
  }

  if (spec.has_category()) {
    return Typecheck(spec.category(), data.category());
  }
  if (spec.has_number()) {
    return Typecheck(spec.number(), data.number());
  }
  if (spec.has_feeler()) {
    return Typecheck(spec.feeler(), data.feeler());
  }

  ABSL_ASSERT(false);  // Unreachable
  return absl::OkStatus();
}

Status Typecheck(const EntityType& spec, const Entity& data) {
  FALKEN_RETURN_IF_ERROR(CheckValid(spec));

  // Translate fixed entity fields.
  if (spec.has_position() != data.has_position() ||
      spec.has_rotation() != data.has_rotation()) {
    return InvalidArgumentError(
        "Entity type mismatch:\nspec: " + spec.DebugString() +
        "data: " + data.DebugString());
  }

  if (spec.entity_fields_size() != data.entity_fields_size()) {
    return InvalidArgumentError(
        "Custom entity_fields mismatch:\nspec: " + spec.DebugString() +
        "data: " + data.DebugString());
  }

  const std::set<std::string> forbidden_names = {"position", "rotation"};
  std::set<std::string> used_names;

  for (int i = 0; i < spec.entity_fields_size(); ++i) {
    const EntityFieldType& spec_field = spec.entity_fields(i);
    const EntityField& data_field = data.entity_fields(i);
    if (forbidden_names.count(spec_field.name()) != 0) {
      return InvalidArgumentError("Custom entity field with name \"" +
                                  spec_field.name() + "\" not allowed.");
    }

    if (used_names.count(spec_field.name()) != 0) {
      return InvalidArgumentError("Two custom entity fields with same name \"" +
                                  spec_field.name() + "\" not allowed.");
    }
    used_names.insert(spec_field.name());
    FALKEN_RETURN_IF_ERROR(Typecheck(spec_field, data_field));
  }

  return absl::OkStatus();
}

absl::Status Typecheck(const ActionType& spec, const Action& data) {
  // Check that the same type is set.
  std::map<ActionType::ActionTypesCase, Action::ActionCase> enum_map = {
      {ActionType::ACTION_TYPES_NOT_SET, Action::ACTION_NOT_SET},
      {ActionType::kCategory, Action::kCategory},
      {ActionType::kJoystick, Action::kJoystick},
      {ActionType::kNumber, Action::kNumber}};

  if (!enum_map.count(spec.action_types_case())) {
    return InvalidArgumentError("Unknown spec action type:\nspec:" +
                                spec.DebugString());
  }

  if (enum_map.find(spec.action_types_case())->second != data.action_case()) {
    return InvalidArgumentError(
        "Mismatch in action type between spec and data:\nspec:" +
        spec.DebugString() + "\ndata: " + data.DebugString());
  }

  switch (spec.action_types_case()) {
    case ActionType::ActionTypesCase::ACTION_TYPES_NOT_SET:
      return InvalidArgumentError("Action type not set:\nspec:\n" +
                                  spec.DebugString());
      break;
    case ActionType::ActionTypesCase::kCategory:
      return Typecheck(spec.category(), data.category());
      break;
    case ActionType::ActionTypesCase::kJoystick:
      return Typecheck(spec.joystick(), data.joystick());
      break;
    case ActionType::ActionTypesCase::kNumber:
      return Typecheck(spec.number(), data.number());
      break;
    default:
      return InvalidArgumentError("Unrecognized action type:\nspec\n" +
                                  spec.DebugString());
  }
}

absl::Status CheckValid(const FeelerType& spec) {
  if (spec.count() < 1) {
    return InvalidArgumentError(
        "Feeler must measure in at least one direction: " + spec.DebugString());
  }
  if (spec.count() != spec.yaw_angles_size()) {
    return InvalidArgumentError(
        "Feeler must specify a yaw angle for each FeelerMeasurement." +
        spec.DebugString());
  }
  if (spec.thickness() < 0.0f) {
    return InvalidArgumentError(
        "Feeler's thickness must be greater or equal than 0: " +
        spec.DebugString());
  }

  return absl::OkStatus();
}

absl::Status CheckValid(const CategoryType& spec) {
  if (spec.enum_values_size() == 0) {
    return InvalidArgumentError("Enum has no values: " + spec.DebugString());
  }
  if (spec.enum_values_size() == 1) {
    return InvalidArgumentError("Enum has only one possible value: " +
                                spec.DebugString());
  }
  std::set<std::string> vals;
  for (const std::string& val : spec.enum_values()) {
    if (val.empty()) {
      return InvalidArgumentError("CategoryType contains empty enum value: " +
                                  spec.DebugString());
    }
    if (vals.count(val) != 0) {
      return InvalidArgumentError("Duplicate enum value: \"" + val + "\" in " +
                                  spec.DebugString());
    }
    vals.insert(val);
  }
  return absl::OkStatus();
}

absl::Status CheckValid(const NumberType& spec) {
  if (std::isnan(spec.minimum()) || std::isnan(spec.maximum())) {
    return InvalidArgumentError("NumberType may not have NaN range boundary: " +
                                spec.DebugString());
  }
  if (spec.maximum() < spec.minimum()) {
    return InvalidArgumentError("NumberType range may not be empty: " +
                                spec.DebugString());
  }
  if (spec.maximum() == spec.minimum()) {
    return InvalidArgumentError(
        "Minimum and maximum may not be the same in NumberType range: " +
        spec.DebugString());
  }
  if (std::isinf(spec.minimum()) || std::isinf(spec.maximum())) {
    return InvalidArgumentError("NumberType may not have inf range boundary: " +
                                spec.DebugString());
  }
  return absl::OkStatus();
}

absl::Status CheckValid(const EntityFieldType& spec) {
  if (!spec.has_category() && !spec.has_number() && !spec.has_feeler()) {
    return InvalidArgumentError(
        "EntityFieldType has unknown or empty subtype: " + spec.DebugString());
  }
  if (spec.has_category()) {
    return CheckValid(spec.category());
  } else if (spec.has_number()) {
    return CheckValid(spec.number());
  } else if (spec.has_feeler()) {
    return CheckValid(spec.feeler());
  }

  ABSL_ASSERT(false);  // This should never happen.
  return absl::OkStatus();
}

absl::Status CheckValid(const EntityType& spec) {
  if (!spec.has_position() && !spec.has_rotation() &&
      !spec.entity_fields_size()) {
    return InvalidArgumentError(
        "Entity has neither position, rotation nor custom entity_fields: " +
        spec.DebugString());
  }
  if (!spec.has_position() || !spec.has_rotation()) {
    return InvalidArgumentError("EntityType spec must have position and "
                                "rotation.");
  }
  const std::set<std::string> reserved_names = {"position", "rotation"};

  std::set<std::string> used_names;
  for (const EntityFieldType& attr_spec : spec.entity_fields()) {
    if (reserved_names.count(attr_spec.name()) != 0) {
      return InvalidArgumentError("EntityFieldType has reserved name: \"" +
                                  attr_spec.name() + "\"");
    }
    if (used_names.count(attr_spec.name()) != 0) {
      return InvalidArgumentError("EntityFieldType has duplicate name: \"" +
                                  attr_spec.name() + "\" " +
                                  "in entity: " + attr_spec.DebugString());
    }
    used_names.insert(attr_spec.name());
    FALKEN_RETURN_IF_ERROR(CheckValid(attr_spec));
  }
  return absl::OkStatus();
}

absl::Status CheckValid(const JoystickType& spec) {
  if (spec.axes_mode() == proto::JoystickAxesMode::UNDEFINED) {
    return InvalidArgumentError("axes_mode not set in JoystickType");
  }
  bool directional = spec.axes_mode() == proto::JoystickAxesMode::DIRECTION_XZ;
  bool has_control_frame = !spec.control_frame().empty();

  if (!directional && has_control_frame) {
    return InvalidArgumentError(
        "Only DIRECTION_XZ mode joystick actions may have a control_frame set."
        "\nspec:\n" +
        spec.DebugString());
  }

  if (spec.controlled_entity().empty()) {
    return InvalidArgumentError("controlled_entity not set:\nspec:\n" +
                                spec.DebugString());
  }
  return absl::OkStatus();
}

absl::Status CheckValid(const ActionType& spec) {
  switch (spec.action_types_case()) {
    case ActionType::ACTION_TYPES_NOT_SET:
      return InvalidArgumentError("ActionType has unset subtype: " +
                                  spec.DebugString());
      break;
    case ActionType::kCategory:
      return CheckValid(spec.category());
      break;
    case ActionType::kJoystick:
      return CheckValid(spec.joystick());
      break;
    case ActionType::kNumber:
      return CheckValid(spec.number());
      break;
    default:
      return InvalidArgumentError("ActionType has unknown subtype: " +
                                  spec.DebugString());
  }
}

void AddReferences(const ActionType& action,
                   std::set<std::string>& references) {
  if (!action.has_joystick()) {
    return;
  }
  if (!action.joystick().control_frame().empty()) {
    references.insert(action.joystick().control_frame());
  }
  if (!action.joystick().controlled_entity().empty()) {
    references.insert(action.joystick().controlled_entity());
  }
}

// Checks that an entity is present with a rotation and position. The name is
// used for error reporting.
absl::Status CheckReferencedEntity(const std::string& name,
                                   const EntityType& entity) {
  // Make sure referenced entity has position and rotation. This implicitly
  // checks whether the entity was present in the parent proto.
  if (!entity.has_position()) {
    return absl::InvalidArgumentError(absl::StrFormat(
        "Referenced entity \"%s\" must have a position.", name));
  }
  if (!entity.has_rotation()) {
    return absl::InvalidArgumentError(absl::StrFormat(
        "Referenced entity \"%s\" must have a rotation.", name));
  }

  return absl::OkStatus();
}

bool HasCustomEntityField(const ObservationSpec& observation) {
  for (const auto& entity : observation.global_entities()) {
    if (entity.entity_fields_size()) {
      return true;
    }
  }

  return observation.player().entity_fields_size() != 0;
}

absl::Status CheckObservationSignalsCanBeGenerated(const BrainSpec& spec) {
  // Check if any custom entity fields are defined.
  if (HasCustomEntityField(spec.observation_spec())) {
    // Custom entity fields currently always generate observation signals.
    return absl::OkStatus();
  }

  // We now check whether egocentric signals can be generated from the spec.
  // This requires:
  // a) A joystick action to be present in the action spec.
  // b) Some global entities to be defined (otherwise there is no target for
  //    the egocentric signal).

  bool has_joystick = false;
  for (const auto& action : spec.action_spec().actions()) {
    if (action.has_joystick()) {
      has_joystick = true;
      break;
    }
  }
  if (!has_joystick) {
    return absl::InvalidArgumentError(
        "If there are no joystick actions present, observations must contain "
        "custom attributes. Please either add custom attributes to "
        "observations or add at least one joystick action and custom entity "
        "to the brain spec.");
  }

  bool has_entity_transform = false;
  for (const auto& entity : spec.observation_spec().global_entities()) {
    if (entity.has_position() && entity.has_rotation()) {
      has_entity_transform = true;
      break;
    }
  }
  if (!has_entity_transform) {
    return absl::InvalidArgumentError(
        "Please add custom attributes or custom entities to the observation.");
  }

  return absl::OkStatus();
}

std::set<std::string> GetReferences(const BrainSpec& spec) {
  std::set<std::string> references;
  for (const auto& action : spec.action_spec().actions()) {
    AddReferences(action, references);
  }
  return references;
}

absl::Status CheckReferences(const BrainSpec& spec) {
  // Collect references.
  std::set<std::string> references = GetReferences(spec);
  // Check if references entities are present with position and observation.
  const auto& observation = spec.observation_spec();
  for (const auto& ref : references) {
    if (ref == "player") {
      FALKEN_RETURN_IF_ERROR(
          CheckReferencedEntity("player", observation.player()));
    } else if (ref == "camera") {
      FALKEN_RETURN_IF_ERROR(
          CheckReferencedEntity("camera", observation.camera()));
    } else {
      return absl::InvalidArgumentError(absl::StrFormat(
          "Entity reference must be \"player\" or \"camera\", but is \"%s\"",
          ref));
    }
  }
  return absl::OkStatus();
}

}  // namespace

absl::Status CheckValid(const ObservationSpec& spec) {
  if (!spec.has_player() && !spec.global_entities_size()) {
    return InvalidArgumentError("Observation spec may not be empty.");
  }
  if (spec.has_player()) {
    FALKEN_RETURN_IF_ERROR(CheckValid(spec.player()));
  }
  for (const EntityType& entity : spec.global_entities()) {
    FALKEN_RETURN_IF_ERROR(CheckValid(entity));
  }
  return absl::OkStatus();
}

absl::Status CheckValid(const ActionSpec& spec) {
  std::set<std::string> used_names;
  if (!spec.actions_size()) {
    return InvalidArgumentError("No actions specified.");
  }
  for (const ActionType& action : spec.actions()) {
    if (used_names.count(action.name())) {
      return InvalidArgumentError("Duplicate action name: \"" + action.name() +
                                  "\" " + "in ActionSpec " +
                                  spec.DebugString());
    }
    if (action.name().empty()) {
      return InvalidArgumentError("Action name may not be empty.");
    }
    used_names.insert(action.name());
    FALKEN_RETURN_IF_ERROR(CheckValid(action));
  }
  return absl::OkStatus();
}

absl::Status CheckValid(const BrainSpec& spec) {
  FALKEN_RETURN_IF_ERROR(CheckValid(spec.action_spec()));
  FALKEN_RETURN_IF_ERROR(CheckValid(spec.observation_spec()));
  FALKEN_RETURN_IF_ERROR(CheckReferences(spec));
  FALKEN_RETURN_IF_ERROR(CheckObservationSignalsCanBeGenerated(spec));

  return absl::OkStatus();
}

Status Typecheck(const ObservationSpec& spec, const ObservationData& data) {
  if (spec.has_player() != data.has_player() ||
      spec.has_camera() != data.has_camera() ||
      spec.global_entities_size() != data.global_entities_size()) {
    return InvalidArgumentError(
        "Spec does not match data:\nspec: " + spec.DebugString() +
        "data: " + data.DebugString());
  }
  if (!spec.has_player() && !spec.global_entities_size()) {
    return InvalidArgumentError("ObservationSpec may not be empty.");
  }

  FALKEN_RETURN_IF_ERROR(Typecheck(spec.player(), data.player()));
  for (int i = 0; i < spec.global_entities_size(); ++i) {
    FALKEN_RETURN_IF_ERROR(
        Typecheck(spec.global_entities(i), data.global_entities(i)));
  }
  return absl::OkStatus();
}

absl::Status Typecheck(const ActionSpec& spec, const ActionData& data) {
  if (data.source() == proto::ActionData::SOURCE_UNKNOWN) {
    return InvalidArgumentError("ActionData source is unknown: " +
                                spec.DebugString());
  }
  if (!data.actions_size() && data.source() == proto::ActionData::NO_SOURCE) {
    return absl::OkStatus();
  }
  if (!spec.actions_size()) {
    return InvalidArgumentError("ActionSpec specifies no actions: " +
                                spec.DebugString());
  }

  if (spec.actions_size() != data.actions_size()) {
    return InvalidArgumentError(
        "Mismatch in number of actions between spec and data:\nspec:" +
        spec.DebugString() + "\ndata: " + data.DebugString());
  }
  for (int i = 0; i < spec.actions_size(); ++i) {
    FALKEN_RETURN_IF_ERROR(Typecheck(spec.actions(i), data.actions(i)));
  }

  return absl::OkStatus();
}

}  // namespace common
}  // namespace falken
