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

#include <string>
#include <vector>

#include "src/core/assert.h"
#include "src/core/attribute_proto_converter.h"
#include "src/core/log.h"
#include "src/core/protos.h"
#include "falken/actions.h"
#include "falken/attribute.h"
#include "absl/strings/str_join.h"

namespace falken {

// Defined in attribute.cc.
extern const char* AttributeBaseTypeToString(AttributeBase::Type type);

ActionsBase::Source FromActionSource(proto::ActionData::ActionSource source) {
  switch (source) {
    case proto::ActionData::SOURCE_UNKNOWN:
      return ActionsBase::Source::kSourceInvalid;
      break;
    case proto::ActionData::NO_SOURCE:
      return ActionsBase::Source::kSourceNone;
      break;
    case proto::ActionData::HUMAN_DEMONSTRATION:
      return ActionsBase::Source::kSourceHumanDemonstration;
      break;
    case proto::ActionData::BRAIN_ACTION:
      return ActionsBase::Source::kSourceBrainAction;
      break;
    default:
      break;
  }
  FALKEN_DEV_ASSERT(false);
  return ActionsBase::Source::kSourceInvalid;
}

std::string GetActionsNamesString(const proto::ActionSpec& actions_spec) {
  return absl::StrJoin(actions_spec.actions(), ", ",
                       [](std::string* out, const proto::ActionType a) {
                         out->append(a.name());
                       });
}

proto::ActionType* ActionProtoConverter::ToActionType(
    const AttributeBase& attribute, proto::ActionSpec& action_spec) {
  proto::ActionType* action_type = action_spec.add_actions();
  action_type->set_name(attribute.name());
  return action_type;
}

void ActionProtoConverter::ToCategoryType(const AttributeBase& attribute,
                                          proto::ActionSpec& action_spec) {
  *ToActionType(attribute, action_spec)->mutable_category() =
      AttributeProtoConverter::ToCategoryType(attribute);
}

void ActionProtoConverter::ToCategory(const AttributeBase& attribute,
                                      proto::ActionData& action_data) {
  *(action_data.add_actions()->mutable_category()) =
      AttributeProtoConverter::ToCategory(attribute);
}

static void LogInvalidType(const AttributeBase& attribute) {
  LogError(
      "Attribute type '%s' is not supported by actions. "
      "Ignoring attribute '%s'. Attribute type should be bool, float or "
      "categorical",
      AttributeBaseTypeToString(attribute.type()), attribute.name());
}

proto::ActionSpec ActionProtoConverter::ToActionSpec(
    const ActionsBase& action_base) {
  proto::ActionSpec action_spec;

  for (const AttributeBase* attribute_base : action_base.attributes()) {
    switch (attribute_base->type()) {
      case AttributeBase::Type::kTypeFloat:
        *ToActionType(*attribute_base, action_spec)->mutable_number() =
            AttributeProtoConverter::ToNumberType(*attribute_base);
        break;
      case AttributeBase::Type::kTypeBool:
        ToCategoryType(*attribute_base, action_spec);
        break;
      case AttributeBase::Type::kTypeCategorical:
        ToCategoryType(*attribute_base, action_spec);
        break;
      case AttributeBase::Type::kTypeJoystick:
        *ToActionType(*attribute_base, action_spec)->mutable_joystick() =
            AttributeProtoConverter::ToJoystickType(*attribute_base);
        break;
      default:
        LogInvalidType(*attribute_base);
        break;
    }
  }

  return action_spec;
}

proto::ActionData ActionProtoConverter::ToActionData(
    const ActionsBase& action_base) {
  proto::ActionData action_data;

  for (const AttributeBase* attribute_base : action_base.attributes()) {
    switch (attribute_base->type()) {
      case AttributeBase::Type::kTypeFloat:
        *action_data.add_actions()->mutable_number() =
            AttributeProtoConverter::ToNumber(*attribute_base);
        break;
      case AttributeBase::Type::kTypeBool:
        ToCategory(*attribute_base, action_data);
        break;
      case AttributeBase::Type::kTypeCategorical:
        ToCategory(*attribute_base, action_data);
        break;
      case AttributeBase::Type::kTypeJoystick:
        *action_data.add_actions()->mutable_joystick() =
            AttributeProtoConverter::ToJoystick(*attribute_base);
        break;
      default:
        LogInvalidType(*attribute_base);
        break;
    }
  }

  switch (action_base.source()) {
    case ActionsBase::Source::kSourceInvalid:
      LogError(
          "Action must have the action source set on each episode step. For "
          "example, if a human performed the action during the episode step "
          "set the source to \" human demonstration \", otherwise set the "
          "source to \" none \".");
      break;
    case ActionsBase::Source::kSourceNone:
      action_data.set_source(proto::ActionData::NO_SOURCE);
      break;

    case ActionsBase::Source::kSourceHumanDemonstration:
      action_data.set_source(proto::ActionData::HUMAN_DEMONSTRATION);
      break;

    case ActionsBase::Source::kSourceBrainAction:
      action_data.set_source(proto::ActionData::BRAIN_ACTION);
      break;
  }

  return action_data;
}

void ActionProtoConverter::FromActionSpec(const proto::ActionSpec& action_spec,
                                          ActionsBase& actions_base) {
  for (const proto::ActionType& action_type : action_spec.actions()) {
    AttributeProtoConverter::FromActionType(action_type, actions_base);
  }
}

bool ActionProtoConverter::FromActionData(const proto::ActionData& action_data,
                                          ActionsBase& actions_base) {
  const size_t num_attributes_action_data = action_data.actions().size();
  const size_t num_attributes_actions_base = actions_base.attributes().size();
  if (num_attributes_action_data != num_attributes_actions_base) {
    LogError(
        "Could not parse generated actions as the number of generated action "
        "attributes '%d' differs from the application defined number '%d'.",
        num_attributes_action_data, num_attributes_actions_base);
    return false;
  }
  bool parsed = true;
  for (size_t i = 0; i < num_attributes_action_data; ++i) {
    const proto::Action& action = action_data.actions()[i];
    // Keep parsing even if we find a wrong action to fully log every error
    // found.
    parsed = AttributeProtoConverter::FromAction(
                 action, *actions_base.attributes()[i]) &&
             parsed;
  }
  actions_base.set_source(FromActionSource(action_data.source()));
  return parsed;
}

bool ActionProtoConverter::VerifyActionSpecIntegrity(
    const proto::ActionSpec& action_spec, const ActionsBase& actions_base) {
  if (action_spec.actions().size() != actions_base.attributes().size()) {
    LogError(
        "Loaded brain's action specification contains '%d' attributes which "
        "mismatches the expected action specification's number of attributes "
        "'%d'.\nThe loaded brain's action specification is: '%s' while the "
        "developer specified attributes is: '%s'. Please create a new brain "
        "with the new action specifications.\n",
        action_spec.actions().size(), actions_base.attributes().size(),
        GetActionsNamesString(action_spec).c_str(),
        actions_base.GetAttributeNamesString().c_str());
    return false;
  }
  for (const proto::ActionType& action_type : action_spec.actions()) {
    const AttributeBase* attribute_base =
        actions_base.attribute(action_type.name().c_str());
    if (!attribute_base) {
      LogError(
          "Attribute '%s' wasn't found in the specified attributes. Please "
          "check that the attribute name is correct."
          "\nThe loaded brain's action specification is: '%s' while the "
          "developer specified attributes is: '%s'.\n",
          action_type.name().c_str(),
          GetActionsNamesString(action_spec).c_str(),
          actions_base.GetAttributeNamesString().c_str());
      return false;
    }
    if (!AttributeProtoConverter::CompareActionTypeToAttributeBase(
            action_type, *attribute_base)) {
      return false;
    }
  }
  return true;
}

}  // namespace falken
