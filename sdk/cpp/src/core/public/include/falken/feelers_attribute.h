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

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_FEELERS_ATTRIBUTE_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_FEELERS_ATTRIBUTE_H_

#include <utility>

#include "falken/allocator.h"
#include "falken/attribute_base.h"
#include "falken/config.h"
#include "falken/types.h"

namespace falken {

/// @brief Construct a feeler attribute.
///
/// fov_coverage defines the range (in radians) in which feelers are going to
/// be placed. The range goes from -fov_coverage/2 to fov_coverage/2. Each
/// feeler is equally spaced by an angle of
/// fov_coverage / (number_of_feelers - 1).
/// Feeler 0 will be placed in -fov_coverage/2 whereas Feeler N will be
/// placed in fov_coverage/2. For example:
/// @code{.cpp}
/// struct Container : AttributeContainer {
///   Container() :
///     FALKEN_FEELERS(value, 14, 1.0f, M_PI/2.0f, 1.574f,
///     {"zero", "one", "two"}) {}
/// };
/// @endcode
/// This feeler will place the feelers between -PI/4 and PI/4.
/// Feeler 0 will be placed at -PI/4 radians and feeler 13 at PI/4 radians.
/// For more information, see @see FeelersAttribute.
#define FALKEN_FEELERS(member_name, number_of_feelers, feeler_length, \
                       fov_coverage, feeler_thickness, ...)           \
  member_name(*this, #member_name, number_of_feelers, feeler_length,  \
              fov_coverage, feeler_thickness, __VA_ARGS__)

/// Feelers sense and collect data from the world around an entity.
class FALKEN_EXPORT FeelersAttribute : public AttributeBase {
 public:
  /// Construct a feelers attribute.
  ///
  /// @details Given that the feeler categories are not stored in the service as
  ///     strings but as enum values instead, when a brain is loaded, generic
  ///     names will be retrieved. For instance, if the categories were
  ///     {"floor", "wall", "carpet"}, the mapping between stored and retrieved
  ///     values would be {"carpet": "0", "floor": "1", "wall": "2"}, since all
  ///     attributes are stored in alphabetical order.
  ///
  /// @param container Container where to add the new feelers attribute.
  /// @param name Feelers attribute name.
  /// @param number_of_feelers Number of feelers that are attached to an entity.
  /// @param feeler_length Maximum distance for the feelers.
  /// @param fov_coverage Field of view angle in radians.
  /// @param feeler_thickness Thickness value for spherical raycast.
  ///     This parameter should be set to 0 if ray casts have no volume.
  /// @param ids Categories for the feelers.
  FeelersAttribute(
      AttributeContainer& container, const char* name, int number_of_feelers,
      float feeler_length, float fov_coverage, float feeler_thickness,
      const std::vector<std::string>& ids = std::vector<std::string>());

  /// Construct a feelers attribute.
  ///
  /// @deprecated Use the overload without <code>record_distances</code>
  /// instead.
  ///
  /// @param container Container where to add the new feelers attribute.
  /// @param name Feelers attribute name.
  /// @param number_of_feelers Number of feelers that are attached to an entity.
  /// @param feeler_length Maximum distance for the feelers.
  /// @param fov_coverage Field of view angle in radians.
  /// @param feeler_thickness Thickness value for spherical raycast.
  ///     This parameter should be set to 0 if ray casts have no volume.
  /// @param record_distances Whether distances should be recorded. This
  ///     parameter can't be false if ids is empty.
  /// @param ids Categories for the feelers. This parameter can't be empty if
  ///     record_distances is set to false.
  FALKEN_DEPRECATED FeelersAttribute(
      AttributeContainer& container, const char* name, int number_of_feelers,
      float feeler_length, float fov_coverage, float feeler_thickness,
      bool record_distances,
      const std::vector<std::string>& ids = std::vector<std::string>());
  /// Copy a feelers attribute and migrate it to a new container.
  ///
  /// @param container Container where to add the new feelers attribute.
  /// @param other Attribute to copy.
  FeelersAttribute(AttributeContainer& container,
                   const FeelersAttribute& other);
  /// Move a feelers attribute and migrate it to a new container.
  ///
  /// @param container Container where to add the new feelers attribute.
  /// @param other Attribute to move.
  FeelersAttribute(AttributeContainer& container, FeelersAttribute&& other);
  /// Move a feelers attribute.
  FeelersAttribute(FeelersAttribute&& other);

  /// Get feeler length value.
  ///
  /// @return Length of the feeler.
  float length() const;

  /// Get feeler radius value.
  ///
  /// @deprecated Use thickness() instead of radius. This will be removed in the
  /// future.
  /// @return Radius of the feeler.
  FALKEN_DEPRECATED float radius() const;

  /// Get feeler thickness value.
  ///
  /// @return Thickness of the feeler.
  float thickness() const;

  /// Get the angle between feeler 0 and feeler N. The angle is in radians.
  ///
  /// @return Field of view angle value in radians.
  float fov_angle() const;

  /// @brief Get feeler distances values.
  ///

  /// Index 0 refers to the feeler placed at -fov_coverage/2. Each feeler
  /// is equally spaced by an angle of fov_coverage / (number_of_feelers - 1).
  ///
  /// @return Distances of the feeler.
  FixedSizeVector<NumberAttribute<float>>& distances();

  /// @brief Get feeler distances values.
  ///
  /// Index 0 refers to the feeler placed at -fov_coverage/2. Each feeler
  /// is equally spaced by an angle of fov_coverage / (number_of_feelers - 1).
  ///
  /// @return Distances of the feeler.
  const FixedSizeVector<NumberAttribute<float>>& distances() const;

  /// @brief Get feeler IDs values.
  ///
  /// Index 0 refers to the feeler placed at -fov_coverage/2.
  ///
  /// @return IDs of the feeler.
  FixedSizeVector<CategoricalAttribute>& ids();

  /// Get feeler IDs values.
  ///
  /// @return IDs of the feeler.
  const FixedSizeVector<CategoricalAttribute>& ids() const;

#if !defined(SWIG) && !defined(FALKEN_CSHARP)
  // Copying attributes is not supported.
  FeelersAttribute& operator=(const FeelersAttribute& other) = delete;
#else
  // Copy attribute values but the container is intact since
  // we can't have more than one attribute with the same name
  // in a container.
  FeelersAttribute& operator=(const FeelersAttribute& other) = default;
#endif  // !defined(SWIG) && !defined(FALKEN_CSHARP)

  FALKEN_DEFINE_NEW_DELETE
};


}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_FEELERS_ATTRIBUTE_H_
