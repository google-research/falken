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

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_ROTATION_ATTRIBUTE_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_ROTATION_ATTRIBUTE_H_

#include <utility>

#include "falken/allocator.h"
#include "falken/config.h"
#include "falken/primitives.h"
#include "falken/unconstrained_attribute.h"

namespace falken {

/// Rotation attribute.
class FALKEN_EXPORT RotationAttribute
    : public UnconstrainedAttribute<Rotation, AttributeBase::kTypeRotation> {
 public:
  /// Construct a rotation attribute.
  ///
  /// @param container Container where to add the new rotation attribute.
  /// @param name Rotation attribute name.
  RotationAttribute(AttributeContainer& container, const char* name);
  /// Copy a rotation attribute and migrate it to a new container.
  ///
  /// @param container Container where to add the new rotation attribute.
  /// @param other Attribute to copy.
  RotationAttribute(AttributeContainer& container,
                    const RotationAttribute& other);
  /// Move a rotation attribute and migrate it to a new container.
  ///
  /// @param container Container where to add the new rotation attribute.
  /// @param other Attribute to move.
  RotationAttribute(AttributeContainer& container, RotationAttribute&& other);
  /// Move a rotation attribute.
  RotationAttribute(RotationAttribute&& other);

  /// Set attribute value.
  ///
  /// @param value Attribute value.
  void set_value(const Rotation& value);

  /// Set attribute value by casting value's type to rotation attribute.
  ///
  /// @param value Attribute value.
  /// @return Attribute.
  RotationAttribute& operator=(const Rotation& value);

#if !defined(SWIG) && !defined(FALKEN_CSHARP)
  /// Copy assignment operator is deleted.
  RotationAttribute& operator=(const RotationAttribute& other) = delete;
#else
  RotationAttribute& operator=(const RotationAttribute& other) = default;
#endif  // !defined(SWIG) && !defined(FALKEN_CSHARP)

  /// Get attribute value.
  ///
  /// @return Value of the attribute.
  const Rotation& value() const;

  /// Get attribute value by casting rotation attribute to value's type.
  ///
  /// @return Value of the attribute.
  operator Rotation() const;  // NOLINT

  FALKEN_DEFINE_NEW_DELETE
};


}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_ROTATION_ATTRIBUTE_H_
