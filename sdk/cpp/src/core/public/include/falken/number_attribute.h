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

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_NUMBER_ATTRIBUTE_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_NUMBER_ATTRIBUTE_H_

#include <utility>

#include "falken/allocator.h"
#include "falken/attribute_base.h"

namespace falken {

// Construct a number attribute member of a class using the name of the member
// variable as the name label for the attribute.
//
// For example:
// struct Container : AttributeContainer {
//   Container() :
//     FALKEN_NUMBER(value, 0.0f, 1.0f) {}
//   NumberAttribute value;
// };
#define FALKEN_NUMBER(member_name, minimum, maximum) \
  member_name(*this, #member_name, minimum, maximum)

/// Number attribute.
template <typename T>
class NumberAttribute : public AttributeBase {
 public:
  /// Construct a number attribute.
  ///
  /// @param container Container where to add the new number attribute.
  /// @param name Number attribute name.
  /// @param minimum Lower bound value.
  /// @param maximum Upper bound value.
  NumberAttribute(AttributeContainer& container, const char* name, T minimum,
                  T maximum)
      : AttributeBase(container, name, minimum, maximum) {}
  /// Copy a number attribute and migrate it to a new container.
  ///
  /// @param container Container where to add the new number attribute.
  /// @param attribute Attribute to copy.
  NumberAttribute(AttributeContainer& container,
                  const NumberAttribute& attribute)
      : AttributeBase(container, attribute) {}
  /// Move a number attribute and migrate it to a new container.
  ///
  /// @param container Container where to add the new attribute.
  /// @param attribute Attribute to move.
  NumberAttribute(AttributeContainer& container, NumberAttribute&& attribute)
      : AttributeBase(container, std::move(attribute)) {}
  /// Move a number attribute.
  NumberAttribute(NumberAttribute&& attribute)
      : AttributeBase(std::move(attribute)) {}

  /// Set attribute value ensuring it is within the required constraints.
  ///
  /// @param value Attribute value.
  /// @return true if the attribute was successfully set, false otherwise.
  bool set_value(T value) { return set_number(static_cast<float>(value)); }

  /// Set attribute value by casting value's type to number attribute.
  ///
  /// @param value Attribute value.
  /// @return Attribute.
  NumberAttribute<T>& operator=(T value) {
    set_value(value);
    return *this;
  }

  /// Get attribute value.
  ///
  /// @return Value of the attribute.
  T value() const { return static_cast<T>(number()); }

  /// Get attribute value by casting number attribute to value's type.
  ///
  /// @return Value of the attribute.
  operator T() const { return value(); }  // NOLINT

  /// Get attribute lower bound.
  ///
  /// @return Lower bound of the attribute.
  T value_minimum() const { return static_cast<T>(number_minimum()); }

  /// Get attribute upper bound.
  ///
  /// @return Upper bound of the attribute.
  T value_maximum() const { return static_cast<T>(number_maximum()); }

#if defined(SWIG) || defined(FALKEN_CSHARP)
  NumberAttribute<T>& operator=(const NumberAttribute& other) = default;
#endif  // defined(SWIG) || defined(FALKEN_CSHARP)

  FALKEN_DEFINE_NEW_DELETE
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_NUMBER_ATTRIBUTE_H_
