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

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_ENTITY_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_ENTITY_H_

#include <memory>
#include <set>
#include <string>
#include <vector>

#include "falken/allocator.h"
#include "falken/attribute.h"
#include "falken/config.h"

namespace falken {

class EntityBase;

/// Container for entities.
class FALKEN_EXPORT EntityContainer {
  friend class EntityBase;
  friend class EntityProtoConverter;

 public:
  /// Default constructor.
  EntityContainer();
  /// Remove all entities from this container and destruct.
  ~EntityContainer();

  /// Copy constructor is deleted.
  EntityContainer(const EntityContainer& other) = delete;
  /// Copy assignment operator is deleted.
  EntityContainer& operator=(const EntityContainer& other) = delete;
  /// Move constructor.
  EntityContainer(EntityContainer&& other);
  /// Allocate entities from a given container except the ones listed.
  ///
  /// @param entities_to_ignore Names of entities to ignore.
  /// @param other Original container.
  EntityContainer(const std::set<std::string>& entities_to_ignore,
                  const EntityContainer& other);

  /// Get entities in this container.
  ///
  /// @return Entities in this container.
  const Vector<EntityBase*>& entities() const;
  /// Get an entity by name.
  ///
  /// @details Given that the entities names are not stored in the service as
  ///     strings but as enum values instead, when a brain is loaded, generic
  ///     names will be retrieved. For instance, if the names were
  ///     {"enemy", "player", "sidekick"}, the mapping between stored and
  ///     retrieved values would be {"enemy": "entity_0", "player": "entity_1",
  ///     "sidekick": "entity_2"}, since all attributes are stored in
  ///     alphabetical order.
  ///
  /// @param name Entity name.
  /// @return Entity.
  EntityBase* entity(const char* name) const;

  FALKEN_DEFINE_NEW_DELETE

 protected:
  /// Remove a given entity from the container.
  ///
  /// @param entity Entity to be removed.
  void RemoveEntity(EntityBase* entity);
  /// Add an entity to the container.
  ///
  /// @param entity Entity to be added.
  void AddEntity(EntityBase* entity);

 private:
  FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_START
  // Private data.
  struct EntityContainerData;
  std::unique_ptr<EntityContainerData> data_;
  FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_END
};

/// Observations of an in-game entity.
class FALKEN_EXPORT EntityBase : public AttributeContainer {
  friend class EntityProtoConverter;
  friend class EntityContainer;

 public:
  /// Construct an entity with a set of attributes.
  ///
  /// @param container Container where to add the new entity.
  /// @param name Entity name.
  EntityBase(EntityContainer& container, const char* name);
  /// Remove the entity from the container and destruct.
  ~EntityBase() override;

  /// Copy constructor is deleted.
  EntityBase(const EntityBase& other) = delete;
  /// Copy assignment operator is deleted.
  EntityBase& operator=(const EntityBase& other) = delete;
  /// Construct an entity from another one.
  ///
  /// @param container Container where to add the new entity.
  /// @param other Original entity.
  EntityBase(EntityContainer& container, const EntityBase& other);
  /// Move constructor.
  EntityBase(EntityBase&& other);

  /// Get the entity name.
  ///
  /// @return Name of the entity.
  const char* name() const;

  /// Position of the entity in world space.
  PositionAttribute position;  // NOLINT
  /// Rotation of the entity in world space.
  RotationAttribute rotation;  // NOLINT

  FALKEN_DEFINE_NEW_DELETE

 private:
  // Clear container.
  void ClearContainer();

  FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_START
  // Private data.
  struct EntityBaseData;
  std::unique_ptr<EntityBaseData> data_;
  FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_END
};
}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_ENTITY_H_
