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

#include "src/core/entity_proto_converter.h"

#include <string.h>

#include <string>
#include <vector>

#include "src/core/assert.h"
#include "src/core/attribute_proto_converter.h"
#include "src/core/entity_internal.h"
#include "src/core/log.h"
#include "src/core/protos.h"
#include "falken/types.h"

namespace falken {

proto::EntityFieldType* EntityProtoConverter::ToEntityFieldType(
    const AttributeBase& attribute, proto::EntityType& entity_type) {
  proto::EntityFieldType* entity_field_type = entity_type.add_entity_fields();
  entity_field_type->set_name(attribute.name());
  return entity_field_type;
}

void EntityProtoConverter::ToCategoryType(const AttributeBase& attribute,
                                          proto::EntityType& entity_type) {
  *ToEntityFieldType(attribute, entity_type)->mutable_category() =
      AttributeProtoConverter::ToCategoryType(attribute);
}

proto::EntityType EntityProtoConverter::ToEntityType(
    const EntityBase& entity_base) {
  proto::EntityType entity_type;
  for (const AttributeBase* attribute_base : entity_base.attributes()) {
    switch (attribute_base->type()) {
      case AttributeBase::Type::kTypeUnknown:
        LogError("Unknown Attribute type. Ignoring '%s'.",
                 attribute_base->name());
        break;
      case AttributeBase::Type::kTypeFeelers:
        *ToEntityFieldType(*attribute_base, entity_type)->mutable_feeler() =
            AttributeProtoConverter::ToFeelerType(*attribute_base);
        break;
      case AttributeBase::Type::kTypePosition:
        if (strcmp(attribute_base->name(), "position") != 0) {
          LogWarning("A position attribute already exists. Ignoring '%s'.",
                     attribute_base->name());
        } else {
          FALKEN_DEV_ASSERT(!entity_type.has_position());
          entity_type.mutable_position();
        }
        break;
      case AttributeBase::Type::kTypeRotation:
        if (strcmp(attribute_base->name(), "rotation") != 0) {
          LogWarning("A rotation attribute was already parsed. Ignoring '%s'.",
                     attribute_base->name());
        } else {
          FALKEN_DEV_ASSERT(!entity_type.has_rotation());
          entity_type.mutable_rotation();
        }
        break;
      case AttributeBase::Type::kTypeFloat:
        *ToEntityFieldType(*attribute_base, entity_type)->mutable_number() =
            AttributeProtoConverter::ToNumberType(*attribute_base);
        break;
      case AttributeBase::Type::kTypeBool:
        ToCategoryType(*attribute_base, entity_type);
        break;
      case AttributeBase::Type::kTypeCategorical:
        ToCategoryType(*attribute_base, entity_type);
        break;
      default:
        LogError("Invalid entity attribute. Ignoring '%s'.",
                 attribute_base->name());
        break;
    }
  }
  return entity_type;
}

void EntityProtoConverter::ToCategory(const AttributeBase& attribute,
                                      proto::Entity& entity) {
  *(entity.add_entity_fields()->mutable_category()) =
      AttributeProtoConverter::ToCategory(attribute);
}

proto::Entity EntityProtoConverter::ToEntity(const EntityBase& entity_base) {
  proto::Entity entity;
  for (const AttributeBase* attribute_base : entity_base.attributes()) {
    switch (attribute_base->type()) {
      case AttributeBase::Type::kTypeUnknown:
        LogError("Unknown Attribute type. Ignoring '%s'.",
                 attribute_base->name());
        break;
      case AttributeBase::Type::kTypeFeelers: {
        proto::EntityField* entity_field = entity.add_entity_fields();
        proto::Feeler* feeler = entity_field->mutable_feeler();
        *feeler = AttributeProtoConverter::ToFeeler(*attribute_base);
        break;
      }

      break;
      case AttributeBase::Type::kTypePosition:
        if (strcmp(attribute_base->name(), "position") != 0) {
          LogWarning("A position attribute already exists. Ignoring '%s'.",
                     attribute_base->name());
        } else {
          FALKEN_DEV_ASSERT(!entity.has_position());
          proto::Position* position = entity.mutable_position();
          *position = AttributeProtoConverter::ToPosition(*attribute_base);
        }
        break;
      case AttributeBase::Type::kTypeRotation:
        if (strcmp(attribute_base->name(), "rotation") != 0) {
          LogWarning("A rotation attribute already exists. Ignoring '%s'.",
                     attribute_base->name());
        } else {
          FALKEN_DEV_ASSERT(!entity.has_rotation());
          proto::Rotation* rotation = entity.mutable_rotation();
          *rotation = AttributeProtoConverter::ToRotation(*attribute_base);
        }
        break;
      case AttributeBase::Type::kTypeFloat: {
        proto::EntityField* attribute = entity.add_entity_fields();
        proto::Number* number = attribute->mutable_number();
        *number = AttributeProtoConverter::ToNumber(*attribute_base);
        break;
      }
      case AttributeBase::Type::kTypeBool:
        ToCategory(*attribute_base, entity);
        break;
      case AttributeBase::Type::kTypeCategorical: {
        ToCategory(*attribute_base, entity);
        break;
      }
      default:
        LogError("Invalid entity attribute type. Ignoring '%s'.",
                 attribute_base->name());
        break;
    }
  }
  return entity;
}

void EntityProtoConverter::FromEntityType(const proto::EntityType& entity_type,
                                          EntityBase& entity_base) {
  for (const proto::EntityFieldType& entity_field_type :
       entity_type.entity_fields()) {
    AttributeProtoConverter::FromEntityFieldType(
        entity_field_type, entity_base);
  }
}

void EntityProtoConverter::FromEntityType(const proto::EntityType& entity_type,
                                          const std::string& entity_name,
                                          EntityContainer& entity_container) {
  entity_container.data_->allocated_entities.emplace_back(
      EntityBase(entity_container, entity_name.c_str()));
  EntityProtoConverter::FromEntityType(
      entity_type, entity_container.data_->allocated_entities.back());
}

bool EntityProtoConverter::FromEntity(const proto::Entity& entity,
                                      EntityBase& entity_base) {
  if (!VerifyEntityIntegrity(entity, entity_base)) {
    LogError("Failed to parse the entity %s. %s.", entity_base.name(),
             kContactFalkenTeamBug);
    return false;
  }

  bool parsed = true;
  // Convert position and rotation.
  parsed = AttributeProtoConverter::FromPosition(entity.position(),
                                                 entity_base.position);
  parsed = AttributeProtoConverter::FromRotation(entity.rotation(),
                                                 entity_base.rotation) &&
           parsed;

  // Convert attributes.
  const size_t num_entity_fields = entity.entity_fields_size();
  size_t entity_base_index = 0;
  for (size_t i = 0; i < num_entity_fields; ++i) {
    // Skip position and rotation attributes as they're not part of the
    // attributes message in the proto.
    auto* attribute_base = entity_base.attributes()[entity_base_index];
    while (attribute_base == &entity_base.position ||
           attribute_base == &entity_base.rotation) {
      attribute_base = entity_base.attributes()[++entity_base_index];
    }

    const proto::EntityField& entity_field = entity.entity_fields(i);
    // Keep parsing even if we find a wrong action to fully log every error
    // found.
    parsed =
        AttributeProtoConverter::FromEntityField(entity_field,
                                                 *attribute_base) &&
        parsed;
    ++entity_base_index;
  }
  return parsed;
}

bool EntityProtoConverter::VerifyEntityTypeIntegrity(
    const proto::EntityType& entity_type, const EntityBase& entity_base) {
  // We subtract 2 from the entity_base since they are position and rotation,
  // which are embedded in the EntityType class instead of the attributes array.
  const size_t num_attributes_entity_base = entity_base.attributes().size() - 2;
  if (entity_type.entity_fields().size() != num_attributes_entity_base) {
    std::string entity_type_attributes;
    for (const proto::EntityFieldType& entity_field_type :
         entity_type.entity_fields()) {
      entity_type_attributes += entity_field_type.name() + ", ";
    }
    if (!entity_type_attributes.empty()) {
      // Removing extra ", " added by for loop.
      entity_type_attributes =
          entity_type_attributes.substr(0, entity_type_attributes.size() - 2);
    }
    std::string entity_base_attributes;
    for (const AttributeBase* attribute_base : entity_base.attributes()) {
      if (attribute_base == &entity_base.position ||
          attribute_base == &entity_base.rotation) {
        continue;
      }
      entity_base_attributes += std::string(attribute_base->name()) + ", ";
    }
    if (!entity_base_attributes.empty()) {
      entity_base_attributes =
          entity_base_attributes.substr(0, entity_base_attributes.size() - 2);
    }

    LogWarning(
        "Entity '%s' is different from the one in the service. The service "
        "expects %d attribute(s) called [%s] while the application defined "
        "entity '%s' has %d attribute(s) called [%s].",
        entity_base.name(), entity_type.entity_fields_size(),
        entity_type_attributes.c_str(), entity_base.name(),
        num_attributes_entity_base, entity_base_attributes.c_str());
    return false;
  }
  bool success = true;
  for (const proto::EntityFieldType& entity_field_type :
       entity_type.entity_fields()) {
    const AttributeBase* attribute_base =
        entity_base.attribute(entity_field_type.name().c_str());
    if (!attribute_base ||
        !AttributeProtoConverter::CompareEntityFieldTypeToAttributeBase(
            entity_field_type, *attribute_base)) {
      success = false;
      LogWarning(
          "Attribute '%s' in EntityType is different in given EntityBase or "
          "it does not exists.",
          entity_field_type.name().c_str());
    }
  }
  return success;
}

bool EntityProtoConverter::VerifyEntityIntegrity(
    const proto::Entity& entity, const EntityBase& entity_base) {
  // We subtract 2 from the entity_base since they are position and rotation,
  // which are embedded in the Entity class instead of the attributes array.
  const size_t num_attributes_entity_base = entity_base.attributes().size() - 2;
  if (entity.entity_fields().size() != num_attributes_entity_base) {
    LogWarning(
        "Entity '%s' is different from the one in the service. In the service "
        "the entity has '%d' attributes while the local entity has '%d' "
        "attributes.",
        entity_base.name(), entity.entity_fields_size(),
        num_attributes_entity_base);
    return false;
  }
  bool success = true;
  size_t entity_base_index = 0;
  for (const proto::EntityField& entity_field : entity.entity_fields()) {
    // Skip position and rotation attributes as they're not part of the
    // attributes message in the proto.
    auto* attribute_base = entity_base.attributes()[entity_base_index];
    while (attribute_base == &entity_base.position ||
           attribute_base == &entity_base.rotation) {
      attribute_base = entity_base.attributes()[++entity_base_index];
    }

    if (!attribute_base ||
        !AttributeProtoConverter::CompareEntityFieldToAttributeBase(
            entity_field, *attribute_base)) {
      success = false;
      LogWarning(
          "The Attribute '%d' in the entity differs from the one in the "
          "service or does not exists.",
          entity_base_index);
    }
    ++entity_base_index;
  }
  return success;
}

}  // namespace falken
