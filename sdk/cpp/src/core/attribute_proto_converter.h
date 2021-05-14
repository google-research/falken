//  Copyright 2021 Google LLC
//
//  Licensed under the Apache License, Version 2.0 (the "License");
//  you may not use this file except in compliance with the License.
//  You may obtain a copy of the License at
//
//       http://www.apache.org/licenses/LICENSE-2.0
//
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.

#ifndef FALKEN_SDK_CORE_ATTRIBUTE_PROTO_CONVERTER_H_
#define FALKEN_SDK_CORE_ATTRIBUTE_PROTO_CONVERTER_H_

#include "src/core/protos.h"
#include "falken/attribute.h"

namespace falken {

class AttributeProtoConverter {
 public:
  // Convert a number attribute to proto.
  static proto::Number ToNumber(const AttributeBase& attribute);

  // Get a number attribute from a proto.
  static bool FromNumber(const proto::Number& number,
                         AttributeBase& output_attribute);

  // Construct an attribute from a number type and add it to the container.
  static void FromNumberType(const char* name, const proto::NumberType& number,
                             AttributeContainer& container);

  // Convert the required constraints of a number attribute to proto.
  static proto::NumberType ToNumberType(const AttributeBase& attribute);

  // Convert a categorical value attribute to proto.
  static proto::Category ToCategory(const AttributeBase& attribute);

  // Get a categorical value attribute from a proto.
  static bool FromCategory(const proto::Category& category,
                           AttributeBase& output_attribute);

  // Construct an attribute from a category type and add it to the container.
  static void FromCategoryType(const char* name,
                               const proto::CategoryType& category,
                               AttributeContainer& container);

  // Convert the available values for a categorical value attribute to proto.
  static proto::CategoryType ToCategoryType(const AttributeBase& attribute);

  // Convert Feeler value to a proto.
  static proto::Feeler ToFeeler(const AttributeBase& attribute);

  // Get a Feeler value attribute from a proto.
  static bool FromFeeler(const proto::Feeler& feeler,
                         AttributeBase& output_attribute);

  // Construct an attribute from a feeler type and add it to the container.
  static void FromFeelerType(const char* name, const proto::FeelerType& feeler,
                             AttributeContainer& container);

  // Convert the available values for a Joystick value attribute to proto.
  static proto::FeelerType ToFeelerType(const AttributeBase& attribute);

  // Convert Feeler value to a proto.
  static proto::Joystick ToJoystick(const AttributeBase& attribute);

  // Get a Joystick value attribute from a proto.
  static bool FromJoystick(const proto::Joystick& joystick,
                           AttributeBase& output_attribute);

  // Construct an attribute from a feeler type and add it to the container.
  static void FromJoystickType(const char* name,
                               const proto::JoystickType& joystick,
                               AttributeContainer& container);

  // Convert the available values for a Joystick value attribute to proto.
  static proto::JoystickType ToJoystickType(const AttributeBase& attribute);

  // Convert the attribute's position to proto.
  static proto::Position ToPosition(const AttributeBase& attribute);

  // Get the attribute's position from a proto.
  static bool FromPosition(const proto::Position& position,
                           AttributeBase& output_attribute);

  // Convert the attribute's rotation to proto.
  static proto::Rotation ToRotation(const AttributeBase& attribute);

  // Get the attribute's rotation from a proto.
  static bool FromRotation(const proto::Rotation& rotation,
                           AttributeBase& output_attribute);
  // Add an AttributeBase for the given attribute container.
  static void FromEntityFieldType(
      const proto::EntityFieldType& entity_field_type,
      AttributeContainer& attribute_container);
  // Modify given AttributeBase based on the provided attribute.
  // Return false if there's a mismatch between attributes.
  static bool FromEntityField(const proto::EntityField& entity_field,
                              AttributeBase& output_attribute);
  // Add an AttributeBase for the given attribute container.
  static void FromActionType(const proto::ActionType& action_type,
                             AttributeContainer& attribute_container);
  // Modify given attribute_base based on the provided action.
  // Return false if there's a mismatch between attributes.
  static bool FromAction(const proto::Action& action,
                         AttributeBase& output_attribute);

  // Compare a proto type to an attribute.
  static bool Compare(const proto::NumberType& number,
                      const AttributeBase& attribute);
  static bool Compare(const proto::CategoryType& category,
                      const AttributeBase& attribute);
  static bool Compare(const proto::FeelerType& feeler,
                      const AttributeBase& attribute);
  static bool Compare(const proto::JoystickType& joystick,
                      const AttributeBase& attribute);

  // Verifies if a given AttributeBase has the same characteristics as the given
  // ActionType.
  static bool CompareActionTypeToAttributeBase(
      const proto::ActionType& action_type, const AttributeBase& attribute);
  // Verifies if a given AttributeBase has the same characteristics as the given
  // EntityFieldType.
  static bool CompareEntityFieldTypeToAttributeBase(
      const proto::EntityFieldType& entity_field_type,
      const AttributeBase& attribute);
  // Verifies if a given AttributeBase has the same characteristics as the given
  // EntityFieldType.
  static bool CompareEntityFieldToAttributeBase(
      const proto::EntityField& entity_field,
      const AttributeBase& attribute_base);
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_ATTRIBUTE_PROTO_CONVERTER_H_
