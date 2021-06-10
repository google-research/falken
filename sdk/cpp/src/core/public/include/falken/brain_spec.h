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

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_BRAIN_SPEC_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_BRAIN_SPEC_H_

#include <memory>

#include "falken/actions.h"
#include "falken/allocator.h"
#include "falken/config.h"
#include "falken/observations.h"

namespace falken {

/// @brief Brain specification that can be built at runtime.
///
/// A brain specification describes observations (@see ObservationBase) and
/// actions (@see ActionsBase). Observations allow you to define how Falken’s AI
/// perceives your game both while it is playing and while it is “watching” a
/// human play. Falken’s observations are based an entity/attribute model, where
/// an entity is simply a container for attributes, each of which have a
/// corresponding name, type, and value. Actions allow you to define how
/// Falken’s AI interacts with your game and how it learns from humans who play
/// it.
///
/// Using {@code BrainSpecBase} allows you to define the brain specification at
/// runtime, whereas using {@code BrainSpec} is useful in cases where the brain
/// specification is defined at compilation time. Usage example:
/// @code{.cpp}
/// struct MyObservations : public falken::ObservationsBase {
///  public:
///   MyObservations() : FALKEN_NUMBER(health, 1.0f, 3.0f) {}
///
///   falken::NumberAttribute<float> health;
/// };
///
/// struct MyActions : public falken::ActionsBase {
///  public:
///   MyActions() : FALKEN_NUMBER(speed, 5.0f, 10.0f) {}
///
///   falken::NumberAttribute<float> speed;
/// };
///
/// void CreateBrainExample() {
///   // ...
///   MyObservations observations;
///   MyActions actions;
///   falken::BrainSpecBase brain_spec_base(&observations, &actions);
///   std::unique_ptr<falken::BrainBase> brain_base =
///       service->CreateBrain("my_brain", brain_spec_base);
///   // ...
/// }
/// @endcode
///
/// The example below sets observations and actions at runtime:
///
/// @code{.cpp}
/// void CreateBrainDynamicExample() {
///   //...
///.  falken::ObservationsBase observations;
///   falken::AttributeBase health(observations, "health", 1.0f, 3.0f);
///   falken::ActionsBase actions;
///   falken::AttributeBase speed(actions, "speed", 5.0f, 10.0f);
///   falken::BrainSpecBase brain_spec_base(&observations, &actions);
///   falken::BrainBase brain_ =
///     service_->CreateBrain("my_brain", brain_spec_base);
/// @endcode
///
/// NOTE: When a brain is created at runtime, all the attributes provided
/// will be copied to internal objects. This means that changes applied to
/// external attributes will not affect the contents of the brain.
/// Following the example above, this change will not have any effect
/// in the brain.
///
/// @code{.cpp}
/// speed.set_number(7.0f);
/// @endcode

/// See {@code BrainSpec} for an example using a templated class.
class FALKEN_EXPORT BrainSpecBase {
  friend class BrainSpecProtoConverter;

 public:
  /// Construct brain specification from observations and actions.
  ///
  /// @param observations_base Observations specs.
  /// @param actions_base Actions specs.
  BrainSpecBase(ObservationsBase* observations_base, ActionsBase* actions_base);
  /// Copy constructor.
  BrainSpecBase(const BrainSpecBase& other);
  /// Move constructor.
  BrainSpecBase(BrainSpecBase&& other);
  virtual ~BrainSpecBase();

  /// Get mutable observations base in the brain specs.
  ///
  /// @return Mutable observations base in the brain specs.
  ObservationsBase& observations_base();
  /// Get observations base in the brain specs.
  ///
  /// @return Observations base in the brain specs.
  const ObservationsBase& observations_base() const;
  /// Get mutable actions base in the brain specs.
  ///
  /// @return Mutable actions base in the brain specs.
  ActionsBase& actions_base();
  /// Get actions base in the brain specs.
  ///
  /// @return Actions base in the brain specs.
  const ActionsBase& actions_base() const;

  FALKEN_DEFINE_NEW_DELETE

 private:
  // Allocate memory for observations and actions.
  BrainSpecBase();

  FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_START
  // Private data.
  struct BrainSpecData;
  std::unique_ptr<BrainSpecData> brain_spec_data_;
  FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_END
};

/// Templated brain specification. Usage example:
/// @code{.cpp}
/// struct MyObservations : public falken::ObservationsBase {
///  public:
///   MyObservations() : FALKEN_NUMBER(health, 1.0f, 3.0f) {}
///
///   falken::NumberAttribute<float> health;
/// };
///
/// struct MyActions : public falken::ActionsBase {
///  public:
///   MyActions() : FALKEN_NUMBER(speed, 5.0f, 10.0f) {}
///
///   falken::NumberAttribute<float> speed;
/// };
///
/// using MyTemplateBrainSpec = falken::BrainSpec<MyObservations, MyActions>;
///
/// void CreateBrainExample() {
///   // ...
///   std::unique_ptr<falken::Brain<MyTemplateBrainSpec>> brain =
///       service->CreateBrain<MyTemplateBrainSpec>("my_brain");
///   // ...
/// }
/// @endcode
template <typename ObservationsClass, typename ActionsClass>
struct BrainSpec : public BrainSpecBase {
  BrainSpec() : BrainSpecBase(&observations, &actions) {}
  ~BrainSpec() override = default;

  /// Brain observation specs.
  ObservationsClass observations;
  /// Brain action specs.
  ActionsClass actions;
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_BRAIN_SPEC_H_
