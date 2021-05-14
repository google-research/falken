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

#ifndef FALKEN_SDK_CORE_ENTITY_PROTO_CONVERTER_H_
#define FALKEN_SDK_CORE_ENTITY_PROTO_CONVERTER_H_

#include "src/core/protos.h"
#include "falken/entity.h"

namespace falken {

class EntityProtoConverter {
 public:
  // Convert a given EntityBase to an EntityType.
  static proto::EntityType ToEntityType(const EntityBase& entity_base);
  // Convert a given EntityBase to an Entity.
  static proto::Entity ToEntity(const EntityBase& entity_base);
  static void FromEntityType(const proto::EntityType& entity_type,
                             EntityBase& entity_base);
  // Parse an EntityType by allocating an entity base in the entity container.
  static void FromEntityType(const proto::EntityType& entity_type,
                             const std::string& entity_name,
                             EntityContainer& entity_container);
  // Convert a given Entity to an EntityBase.
  static bool FromEntity(const proto::Entity& entity, EntityBase& entity_base);

  // Verify that a given EntityBase has the same attributes in the given
  // EntityType.
  static bool VerifyEntityTypeIntegrity(const proto::EntityType& entity_type,
                                        const EntityBase& entity_base);
  // Verify that a given EntityBase has the same attributes in the given
  // Entity.
  static bool VerifyEntityIntegrity(const proto::Entity& entity,
                                    const EntityBase& entity_base);

 private:
  static proto::EntityFieldType* ToEntityFieldType(
      const AttributeBase& attribute, proto::EntityType& entity_type);
  static void ToCategoryType(const AttributeBase& attribute,
                             proto::EntityType& entity_type);
  static void ToCategory(const AttributeBase& attribute, proto::Entity& entity);
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_ENTITY_PROTO_CONVERTER_H_
