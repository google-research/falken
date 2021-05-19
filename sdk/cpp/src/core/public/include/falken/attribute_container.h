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

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_ATTRIBUTE_CONTAINER_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_ATTRIBUTE_CONTAINER_H_

#include <memory>
#include <set>
#include <string>
#include <vector>

#include "falken/allocator.h"
#include "falken/attribute_base.h"
#include "falken/config.h"
#include "falken/types.h"

namespace falken {

class ActionProtoConverter;
class ActionsBase;
class AttributeBase;
class AttributeProtoConverter;
class AttributeTest;

/// Container for attributes.
class FALKEN_EXPORT AttributeContainer {
  friend class ActionProtoConverter;
  friend class ActionsBase;
  friend class AttributeBase;
  friend class AttributeProtoConverter;
  friend class AttributeTest;
  friend class Episode;

 public:
  AttributeContainer();
  /// Copy constructor is deleted.
  AttributeContainer(const AttributeContainer& other) = delete;
  /// Copy assignment operator is deleted.
  AttributeContainer& operator=(const AttributeContainer& other) = delete;
  /// Copy attributes from a given container except the ones listed.
  ///
  /// @param attributes_to_ignore Names of the attributes to ignore.
  /// @param other Container to copy.
  AttributeContainer(const std::set<std::string>& attributes_to_ignore,
                     const AttributeContainer& other);
  /// Move attributes from a given container except the ones listed.
  ///
  /// @param attributes_to_ignore Names of the attributes to ignore.
  /// @param other Container to move.
  AttributeContainer(const std::set<std::string>& attributes_to_ignore,
                     AttributeContainer&& other);
  virtual ~AttributeContainer();

  /// Get attributes.
  ///
  /// @return Attributes.
  const Vector<AttributeBase*>& attributes() const;

  /// Get an attribute by name.
  ///
  /// @param name Attribute name.
  /// @return Attribute.
  AttributeBase* attribute(const char* name) const;

  FALKEN_DEFINE_NEW_DELETE

 protected:
  /// Construct a container receiving the supported attributes types list.
  explicit AttributeContainer(const AttributeBase::Type* valid_types,
                              const char* container_name);

  /// Add an attribute to the container.
  ///
  /// @param attribute Attribute to be added.
  void AddAttribute(AttributeBase* attribute);

  /// Remove a given attribute from the container.
  ///
  /// @param attribute Attribute to be removed.
  void RemoveAttribute(AttributeBase* attribute);

  /// Remove all attributes from the container.
  void ClearAttributes();

  /// Set the modification flag for the container.
  ///
  /// @param modified Flag boolean value.
  void set_modified(bool modified);
  /// Check if any attributes have been modified in the container.
  ///
  /// @return true if any attributes have been modified, false otherwise.
  bool modified() const;
  /// Checks if any of the attributes within the container have not been
  /// updated, and adds a list of the unset attributes to the vector it receives
  /// as argument
  bool HasUnmodifiedAttributes(
      std::vector<std::string>& unset_attribute_names) const;

 private:
  // Reset all modified state of the attributes within the container
  void reset_attributes_dirty_flags();

  /// Return true if all the attributtes have had their values set
  bool all_attributes_are_set() const;

  // Copy from a given AttributeContainer its attributes by allocating
  // memory for them.
  void CopyAndAllocateAttributes(
      const std::set<std::string>& attributes_to_ignore,
      const AttributeContainer& other);

  std::string GetAttributeNamesString() const;

  FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_START
  // Private data.
  struct AttributeContainerData;
  std::unique_ptr<AttributeContainerData> attribute_container_data_;
  FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_END
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_ATTRIBUTE_CONTAINER_H_
