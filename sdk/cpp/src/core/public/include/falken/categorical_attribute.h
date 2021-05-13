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

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_CATEGORICAL_ATTRIBUTE_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_CATEGORICAL_ATTRIBUTE_H_

#include <utility>

#include "falken/allocator.h"
#include "falken/attribute_base.h"
#include "falken/config.h"
#include "falken/types.h"

namespace falken {

// Construct a categorical attribute member of a class using the name
// of the member variable as the name label for the attribute.
//
// For example:
// struct Container : AttributeContainer {
//   Container() :
//     FALKEN_CATEGORICAL(value, {"off", "on"}) {}
//   CategoricalAttribute value;
// };
#define FALKEN_CATEGORICAL(member_name, ...) \
  member_name(*this, #member_name, __VA_ARGS__)

/// Categorical attribute.
class FALKEN_EXPORT CategoricalAttribute : public AttributeBase {
 public:
  /// Construct a categorical attribute.
  ///
  /// @param container Container where to add the new categorical attribute.
  /// @param name Number attribute name.
  /// @param category_values List of categories.
  CategoricalAttribute(AttributeContainer& container, const char* name,
                       const std::vector<std::string>& category_values);
  /// Copy a categorical attribute and migrate it to a new container.
  ///
  /// @param container Container where to add the new categorical attribute.
  /// @param attribute Attribute to copy.
  CategoricalAttribute(AttributeContainer& container,
                       const CategoricalAttribute& attribute);
  /// Move a categorical attribute and migrate it to a new container.
  ///
  /// @param container Container where to add the new categorical attribute.
  /// @param attribute Attribute to move.
  CategoricalAttribute(AttributeContainer& container,
                       CategoricalAttribute&& attribute);
  /// Move a categorical attribute.
  CategoricalAttribute(CategoricalAttribute&& attribute);

  /// Get attribute available values.
  ///
  /// @return Available values of the attribute.
  const Vector<String>& categories() const;

  /// Set attribute value ensuring it is within the required constraints.
  ///
  /// @param value Attribute value.
  /// @return true if the attribute was successfully set, false otherwise.
  bool set_value(int value);

  /// Set attribute value by casting value's type to categorical attribute.
  ///
  /// @param value Attribute value.
  /// @return Attribute.
  CategoricalAttribute& operator=(int value);

  /// Get attribute value.
  ///
  /// @return Value of the attribute.
  int value() const;

  /// Get attribute value by casting categorical attribute to value's type.
  ///
  /// @return Value of the attribute.
  operator int() const;  // NOLINT

#if defined(SWIG) || defined(FALKEN_CSHARP)
  CategoricalAttribute& operator=(const CategoricalAttribute& other) = default;
#endif  // defined(SWIG) || defined(FALKEN_CSHARP)

  FALKEN_DEFINE_NEW_DELETE
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_CATEGORICAL_ATTRIBUTE_H_
