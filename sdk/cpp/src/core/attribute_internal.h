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

#ifndef FALKEN_SDK_CORE_ATTRIBUTE_INTERNAL_H_
#define FALKEN_SDK_CORE_ATTRIBUTE_INTERNAL_H_

#include <sstream>
#include <utility>

#include "src/core/vector_search.h"
#include "src/core/log.h"
#include "falken/attribute_base.h"
#include "falken/attribute_container.h"
#include "falken/types.h"

namespace falken {

// Get the name of an item where T::name() returns the name.
template<typename T>
const char* ItemGetName(const T& item) {
  return item->name();
}

// Find an item in an array by name returning iterator.end() if the item isn't
// found.
template<typename T>
typename Vector<T*>::const_iterator FindItemIteratorByName(
    const Vector<T*>& items, const char* name, bool log_error,
    const char* item_type_name) {
  auto it = SearchSortedVectorByName<T*, ItemGetName<T*>>(items, name);
  if (it == items.end() && log_error) {
    std::stringstream found;
    found << "[";
    for (const auto& item : items) {
      found << ItemGetName<T*>(item);
      found << ", ";
    }
    found << "]";
    LogError("%s %s not found in container. Found %s", item_type_name, name,
             found.str().c_str());
  }
  return it;
}

// Find an item in an array by name, returning nullptr if it's not found.
template<typename T>
T* FindItemByName(const Vector<T*>& attributes, const char* name,
                  bool log_error, const char* item_type_name) {
  auto it = FindItemIteratorByName(attributes, name, log_error, item_type_name);
  return it != attributes.end() ? *it : nullptr;
}

// Pimpl struct to hold all Attribute Base private fields.
struct AttributeBase::AttributeBaseData {
  // Constructor.
  AttributeBaseData(AttributeContainer& container, Type type, const char* name)
      : container(&container),
        notify_container(this->container),
        name(name),
        type(type),
        dirty(false) {}

  AttributeBaseData(AttributeContainer& container, AttributeBaseData&& other)
      : container(&container),
        notify_container(this->container),
        type(other.type),
        category_values(std::move(other.category_values)),
        dirty(false) {}

  AttributeBaseData(AttributeContainer& container,
                    const AttributeBaseData& other)
      : container(&container),
        notify_container(this->container),
        name(other.name),
        type(other.type),
        category_values(other.category_values),
        dirty(false),
        clamp_values(other.clamp_values) {}

  // Copy constructor.
  AttributeBaseData(const AttributeBaseData& other)
      : container(other.container),
        notify_container(this->container),
        name(other.name),
        type(other.type),
        category_values(other.category_values),
        dirty(false),
        clamp_values(other.clamp_values) {}

  // Move constructor.
  AttributeBaseData(AttributeBaseData&& other)
      : container(other.container),
        notify_container(this->container),
        type(other.type),
        category_values(std::move(other.category_values)),
        dirty(false),
        clamp_values(other.clamp_values) {}

  // Keep reference to the container. If deletion of container happens
  // before this attribute is destroyed, this pointer will be set to null.
  AttributeContainer* container;
  // Used to notify the attribute container that the attribute has been
  // modified. This can be different to container_ in the case where a private
  // container is used to store composite attributes but an public container
  // needs to be notified of any changes.
  AttributeContainer* notify_container;

  String name;

  Type type;

  Vector<String> category_values;

  /// Indicates that the attribute has been written to. This variable is only
  /// used for simple attributes (number, category, etc). Attributes that are
  /// implemented as containers of other attributes, such as feelers and
  /// joystick, don't use this variable at all.
  bool dirty;

  bool clamp_values = false;
};

// Pimpl struct to hold all the Attribute Container private fields.
struct AttributeContainer::AttributeContainerData {
  explicit AttributeContainerData(const AttributeBase::Type* valid_types,
                                  const char* container_name = "")
      : modified(false),
        valid_types(valid_types),
        container_name(container_name) {}

  Vector<AttributeBase> allocated_attributes;
  // Attributes that this container has. They are sorted by name.
  Vector<AttributeBase*> attributes;
  // Whether attributes in the container have been modified.
  // Each attribute in the container holds a pointer to this flag.
  bool modified;
  // Local container that holds the supported types.
  const AttributeBase::Type* valid_types;
  // Container name.
  const char* container_name;
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_ATTRIBUTE_INTERNAL_H_
