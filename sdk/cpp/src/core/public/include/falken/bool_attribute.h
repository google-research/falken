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

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_BOOL_ATTRIBUTE_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_BOOL_ATTRIBUTE_H_

#include <utility>

#include "falken/allocator.h"
#include "falken/attribute_base.h"
#include "falken/config.h"

namespace falken {

// Construct a bool attribute member of a class using the name
// of the member variable as the name label for the attribute.
//
// For example:
// struct Container : AttributeContainer {
//   Container() :
//     FALKEN_BOOL(value) {}
//   BoolAttribute value;
// };
#define FALKEN_BOOL(member_name) member_name(*this, #member_name)

/// Bool attribute.
class FALKEN_EXPORT BoolAttribute : public AttributeBase {
 public:
  /// Construct a boolean attribute.
  ///
  /// @param container Container where to add the new boolean attribute.
  /// @param name Boolean attribute name.
  BoolAttribute(AttributeContainer& container, const char* name);
  /// Copy a boolean attribute and migrate it to a new container.
  ///
  /// @param container Container where to add the new boolean attribute.
  /// @param attribute Attribute to copy.
  BoolAttribute(AttributeContainer& container, const BoolAttribute& attribute);
  /// Move a boolean attribute and migrate it to a new container.
  ///
  /// @param container Container where to add the new boolean attribute.
  /// @param attribute Attribute to move.
  BoolAttribute(AttributeContainer& container, BoolAttribute&& attribute);
  /// Move a boolean attribute.
  BoolAttribute(BoolAttribute&& attribute);

  /// Set attribute value.
  ///
  /// @param value Attribute value.
  /// @return true if the attribute was successfully set, false otherwise.
  bool set_value(bool value);

  /// Set attribute value by casting value's type to boolean attribute.
  ///
  /// @param value Attribute value.
  /// @return Attribute.
  BoolAttribute& operator=(bool value);

  /// Get attribute value.
  ///
  /// @return Value of the attribute.
  bool value() const;

  /// Get attribute value by casting boolean attribute to value's type.
  ///
  /// @return Value of the attribute.
  operator bool() const;  // NOLINT

#if defined(SWIG) || defined(FALKEN_CSHARP)
  BoolAttribute& operator=(const BoolAttribute& attribute) = default;
#endif  // defined(SWIG) || defined(FALKEN_CSHARP)

  FALKEN_DEFINE_NEW_DELETE
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_BOOL_ATTRIBUTE_H_
