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

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_UNCONSTRAINED_ATTRIBUTE_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_UNCONSTRAINED_ATTRIBUTE_H_

#include <utility>

#include "falken/allocator.h"
#include "falken/attribute_base.h"

namespace falken {

// Construct a unconstrained attribute member of a class using the name of the
// member variable as the name label for the attribute.
//
// For example:
// struct Container : AttributeContainer {
//   Container() :
//     FALKEN_UNCONSTRAINED(position) {}
//   PositionAttribute position;
// };
#define FALKEN_UNCONSTRAINED(member_name) member_name(*this, #member_name)

/// Attribute without constraints / bounds.
///
/// T is the C++ type of the value owned by this attribute.
/// TYPE is the type enumeration of this attribute, see AttributeBase::Type
/// for more information.
template <typename T, AttributeBase::Type TYPE>
class UnconstrainedAttribute : public AttributeBase {
 public:
  /// Construct an unconstrained attribute.
  ///
  /// @param container Container where to add the new unconstrained attribute.
  /// @param name Unconstrained attribute name.
  UnconstrainedAttribute(AttributeContainer& container, const char* name)
      : AttributeBase(container, name, TYPE) {}
  /// Copy an unconstrained attribute and migrate it to a new container.
  ///
  /// @param container Container where to add the new unconstrained attribute.
  /// @param other Attribute to copy.
  UnconstrainedAttribute(AttributeContainer& container,
                         const UnconstrainedAttribute& other)
      : AttributeBase(container, other) {}
  /// Move an unconstrained attribute and migrate it to a new container.
  ///
  /// @param container Container where to add the new unconstrained attribute.
  /// @param other Attribute to move.
  UnconstrainedAttribute(AttributeContainer& container,
                         UnconstrainedAttribute&& other)
      : AttributeBase(container, std::move(other)) {}
  /// Move an unconstrained attribute.
  UnconstrainedAttribute(UnconstrainedAttribute&& other)
      : AttributeBase(std::move(other)) {}

  /// Set attribute value.
  ///
  /// @param value Attribute value.
  void set_value(const T& value);

  /// Set attribute value by casting value's type to unconstrained attribute.
  ///
  /// @param value Attribute value.
  /// @return Attribute.
  UnconstrainedAttribute<T, TYPE>& operator=(const T& value) {
    set_value(value);
    return *this;
  }

#if !defined(SWIG) && !defined(FALKEN_CSHARP)
  /// Copy assignment operator is deleted.
  UnconstrainedAttribute& operator=(const UnconstrainedAttribute& other) =
      delete;
#else
  UnconstrainedAttribute& operator=(const UnconstrainedAttribute& other) =
      default;
#endif  // !defined(SWIG) && !defined(FALKEN_CSHARP)

  /// Get attribute value.
  ///
  /// @return Value of the attribute.
  T value() const;

  /// Get attribute value by casting unconstrained attribute to value's type.
  ///
  /// @return Value of the attribute.
  operator T() const { return value(); }  // NOLINT

  FALKEN_DEFINE_NEW_DELETE
};

template <>
inline void UnconstrainedAttribute<float, AttributeBase::kTypeFloat>::set_value(
    const float& value) {
  set_number(value);
}

template <>
inline float UnconstrainedAttribute<float, AttributeBase::kTypeFloat>::value()
    const {
  return number();
}

template <>
inline void UnconstrainedAttribute<int, AttributeBase::kTypeFloat>::set_value(
    const int& value) {
  set_number(static_cast<float>(value));
}

template <>
inline int UnconstrainedAttribute<int, AttributeBase::kTypeFloat>::value()
    const {
  return static_cast<int>(number());
}

template <>
inline void UnconstrainedAttribute<bool, AttributeBase::kTypeBool>::set_value(
    const bool& value) {
  set_boolean(value);
}

template <>
inline bool UnconstrainedAttribute<bool, AttributeBase::kTypeBool>::value()
    const {
  return boolean();
}

template <>
inline void
UnconstrainedAttribute<Position, AttributeBase::kTypePosition>::set_value(
    const Position& value) {
  set_position(value);
}

template <>
inline Position
UnconstrainedAttribute<Position, AttributeBase::kTypePosition>::value() const {
  return position();
}

template <>
inline void
UnconstrainedAttribute<Rotation, AttributeBase::kTypeRotation>::set_value(
    const Rotation& value) {
  set_rotation(value);
}

template <>
inline Rotation
UnconstrainedAttribute<Rotation, AttributeBase::kTypeRotation>::value() const {
  return rotation();
}

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_UNCONSTRAINED_ATTRIBUTE_H_
