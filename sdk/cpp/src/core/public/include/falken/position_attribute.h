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

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_POSITION_ATTRIBUTE_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_POSITION_ATTRIBUTE_H_

#include <utility>

#include "falken/allocator.h"
#include "falken/config.h"
#include "falken/primitives.h"
#include "falken/unconstrained_attribute.h"

namespace falken {

/// Position attribute.
class FALKEN_EXPORT PositionAttribute
    : public UnconstrainedAttribute<Position, AttributeBase::kTypePosition> {
 public:
  /// Construct a position attribute.
  ///
  /// @param container Container where to add the new position attribute.
  /// @param name Position attribute name.
  PositionAttribute(AttributeContainer& container, const char* name);
  /// Copy a position attribute and migrate it to a new container.
  ///
  /// @param container Container where to add the new position attribute.
  /// @param other Attribute to copy.
  PositionAttribute(AttributeContainer& container,
                    const PositionAttribute& other);
  /// Move a position attribute and migrate it to a new container.
  ///
  /// @param container Container where to add the new position attribute.
  /// @param other Attribute to move.
  PositionAttribute(AttributeContainer& container, PositionAttribute&& other);
  /// Move a position attribute.
  PositionAttribute(PositionAttribute&& other);

  /// Set attribute value.
  ///
  /// @param value Attribute value.
  void set_value(const Position& value);

  /// Set attribute value by casting value's type to position attribute.
  ///
  /// @param value Attribute value.
  /// @return Attribute.
  PositionAttribute& operator=(const Position& value);

#if !defined(SWIG) && !defined(FALKEN_CSHARP)
  /// Copy assignment operator is deleted.
  PositionAttribute& operator=(const PositionAttribute& other) = delete;
#else
  PositionAttribute& operator=(const PositionAttribute& other) = default;
#endif  // !defined(SWIG) && !defined(FALKEN_CSHARP)

  /// Get attribute value.
  ///
  /// @return Value of the attribute.
  const Position& value() const;

  /// Get attribute value by casting position attribute to value's type.
  ///
  /// @return Value of the attribute.
  operator Position() const;  // NOLINT

  FALKEN_DEFINE_NEW_DELETE
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_POSITION_ATTRIBUTE_H_
