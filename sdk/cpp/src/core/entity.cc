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

#include "falken/entity.h"

#include <string.h>

#include <algorithm>
#include <string>

#include "src/core/attribute_internal.h"
#include "src/core/entity_internal.h"
#include "src/core/globals.h"
#include "src/core/log.h"
#include "absl/memory/memory.h"

namespace falken {

static const AttributeBase::Type kObservationsValidTypes[] = {
    falken::AttributeBase::Type::kTypeFloat,
    falken::AttributeBase::Type::kTypeCategorical,
    falken::AttributeBase::Type::kTypeBool,
    falken::AttributeBase::Type::kTypePosition,
    falken::AttributeBase::Type::kTypeRotation,
    falken::AttributeBase::Type::kTypeFeelers,
    falken::AttributeBase::Type::kTypeUnknown,  // List terminator.
};

namespace {

static const char kEntityTypeName[] = "Entity";

Vector<EntityBase*>::const_iterator FindEntityIteratorByName(
    const Vector<EntityBase*>& entities, const char* name,
    bool log_error) {
  return FindItemIteratorByName(entities, name, log_error,
                                kEntityTypeName);
}

EntityBase* FindEntityByName(const Vector<EntityBase*>& entities,
                             const char* name, bool log_error) {
  return FindItemByName(entities, name, log_error, kEntityTypeName);
}

}  // namespace

// Private data for the EntityBase class.
struct EntityBase::EntityBaseData {
  // Construct entity data with a set of attributes.
  EntityBaseData(EntityContainer* container_, std::string name_)
      : container(container_), name(name_) {}
  // Construct entity data from another one, using a different container.
  EntityBaseData(EntityContainer* container_, const EntityBaseData& other_)
      : container(container_), name(other_.name) {}
  // Construct entity data from another one, using the same container.
  EntityBaseData(EntityBaseData&& other_)
      : container(other_.container), name(std::move(other_.name)) {
    other_.container = nullptr;
  }

  EntityContainer* container;
  std::string name;
};

EntityContainer::EntityContainer() : data_(new EntityContainerData()) {}

EntityContainer::EntityContainer(EntityContainer&& other) = default;

EntityContainer::EntityContainer(
    const std::set<std::string>& entities_to_ignore,
    const EntityContainer& other)
    : data_(new EntityContainerData()) {
  data_->allocated_entities.reserve(other.entities().size());
  for (const EntityBase* entity_base : other.entities()) {
    if (entities_to_ignore.find(std::string(entity_base->name())) ==
        entities_to_ignore.end()) {
      data_->allocated_entities.emplace_back(EntityBase(*this, *entity_base));
    }
  }
}

EntityContainer::~EntityContainer() {
  FALKEN_LOCK_GLOBAL_MUTEX();
  for (EntityBase* entity : data_->entities) {
    entity->ClearContainer();
  }
}

EntityBase::EntityBase(EntityContainer& container, const char* name)
    : AttributeContainer(kObservationsValidTypes, "Observations"),
      FALKEN_UNCONSTRAINED(position),
      FALKEN_UNCONSTRAINED(rotation),
      data_(new EntityBaseData(&container, name)) {
  container.AddEntity(this);
}

EntityBase::EntityBase(EntityContainer& container, const EntityBase& other)
    : AttributeContainer({"position", "rotation"}, other),
      position(*this, other.position),
      rotation(*this, other.rotation),
      data_(new EntityBaseData(&container, *other.data_)) {
  container.AddEntity(this);
}

EntityBase::EntityBase(EntityBase&& other)
    : AttributeContainer({"position", "rotation"}, other),
      position(*this, other.position),
      rotation(*this, other.rotation) {
  other.data_->container->RemoveEntity(&other);
  data_ = absl::make_unique<EntityBaseData>(std::move(*other.data_));
  data_->container->AddEntity(this);
}

EntityBase::~EntityBase() {
  FALKEN_LOCK_GLOBAL_MUTEX();
  if (data_ && data_->container) {
    data_->container->RemoveEntity(this);
  }
}

const char* EntityBase::name() const { return data_->name.c_str(); }

void EntityBase::ClearContainer() { data_->container = nullptr; }

const Vector<EntityBase*>& EntityContainer::entities() const {
  return data_->entities;
}

EntityBase* EntityContainer::entity(const char* name) const {
  return FindEntityByName(data_->entities, name, true);
}

void EntityContainer::RemoveEntity(EntityBase* entity) {
  auto it = FindEntityIteratorByName(data_->entities, entity->name(), false);
  if (it == data_->entities.end()) {
    LogError("Unable to remove entity %s as it is not found in the container.",
             entity->name());
    return;
  }
  data_->entities.erase(it);
}

void EntityContainer::AddEntity(EntityBase* entity) {
  if (FindEntityByName(data_->entities, entity->name(), false)) {
    LogError("Failed to add entity '%s' to the container as an entity with the "
             "same name is already present. Please change the entity name or "
             "use another container.", entity->name());
    return;
  }
  data_->entities.insert(
      std::upper_bound(data_->entities.begin(), data_->entities.end(), entity,
                       [](const EntityBase* lhs, const EntityBase* rhs) {
                         return strcmp(lhs->name(), rhs->name()) < 0;
                       }),
      entity);
}

}  // namespace falken
