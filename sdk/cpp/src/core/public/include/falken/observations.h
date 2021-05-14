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

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_OBSERVATIONS_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_OBSERVATIONS_H_

#include "falken/allocator.h"
#include "falken/config.h"
#include "falken/entity.h"

namespace falken {

// Construct an EntityBase member of a class using the name of the member
// variable as the name label for the attribute.
//
// For example:
//
// struct MyEntity : public falken::EntityBase {
//   MyEntity(falken::EntityContainer& container, const char* name) :
//     falken::EntityBase(container, name),
//     FALKEN_CATEGORICAL(category_value, {"one", "two"}) {}
//   falken::CategoricalAttribute category_value;
// };
//
// struct MyObservation : ObservationsBase {
//   MyObservation() :
//     FALKEN_ENTITY(value) {}
//   MyEntity value;
// };
#define FALKEN_ENTITY(member_name) \
  member_name(*this, #member_name)

/// @brief A set of observations.
///
/// Observations allow you to define how Falken’s AI perceives your game both
/// while it is playing and while it is “watching” a human play. Falken’s
/// Observations are based on the Entity/Attribute model, where an Entity is
/// simply a container for attributes, each of which have a corresponding name,
/// type, and value.
///
/// Attributes added to this object are observations of the player. Entities
/// added to this object are non-player entities that are perceived by the
/// player.
class FALKEN_EXPORT ObservationsBase : public EntityContainer,
                                       public EntityBase {
 public:
  /// Construct an observation.
  ObservationsBase();
  /// Copy an observation.
  ObservationsBase(const ObservationsBase& other);
  /// Move an observation.
  ObservationsBase(ObservationsBase&& other);

  FALKEN_DEFINE_NEW_DELETE
};

}  // namespace falken
#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_OBSERVATIONS_H_
