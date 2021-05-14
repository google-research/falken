// Copyright 2021 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include "falken/brain_spec.h"

#include <memory>
#include <utility>

#include "src/core/assert.h"
#include "src/core/log.h"
#include "absl/memory/memory.h"

namespace falken {

struct BrainSpecBase::BrainSpecData {
  // Constructor
  BrainSpecData(ObservationsBase* observations_base, ActionsBase* actions_base)
      : observations_base(observations_base), actions_base(actions_base) {}

  // Default constructor.
  BrainSpecData()
      : allocated_observations_base(absl::make_unique<ObservationsBase>()),
        allocated_actions_base(absl::make_unique<ActionsBase>()),
        observations_base(allocated_observations_base.get()),
        actions_base(allocated_actions_base.get()) {}

  // Copy constructor.
  BrainSpecData(const BrainSpecData& other)
      : allocated_observations_base(
            absl::make_unique<ObservationsBase>(*other.observations_base)),
        allocated_actions_base(
            absl::make_unique<ActionsBase>(*other.actions_base)),
        observations_base(allocated_observations_base.get()),
        actions_base(allocated_actions_base.get()) {}

  // Move constructor.
  BrainSpecData(BrainSpecData&& other)
      : allocated_observations_base(
            std::move(other.allocated_observations_base)),
        allocated_actions_base(std::move(other.allocated_actions_base)),
        observations_base(allocated_observations_base.get()),
        actions_base(allocated_actions_base.get()) {}

  std::unique_ptr<ObservationsBase> allocated_observations_base;
  std::unique_ptr<ActionsBase> allocated_actions_base;

  ObservationsBase* observations_base;
  ActionsBase* actions_base;
};

BrainSpecBase::BrainSpecBase(ObservationsBase* observations_base,
                             ActionsBase* actions_base)
    : brain_spec_data_(
          std::make_unique<BrainSpecData>(observations_base, actions_base)) {
  FALKEN_ASSERT(brain_spec_data_->observations_base);
  FALKEN_ASSERT(brain_spec_data_->actions_base);
}

BrainSpecBase::BrainSpecBase(const BrainSpecBase& other)
    : brain_spec_data_(
          std::make_unique<BrainSpecData>(*other.brain_spec_data_)) {}

BrainSpecBase::BrainSpecBase(BrainSpecBase&& other)
    : brain_spec_data_(
          std::make_unique<BrainSpecData>(std::move(*other.brain_spec_data_))) {
}

BrainSpecBase::BrainSpecBase()
    : brain_spec_data_(std::make_unique<BrainSpecData>()) {}

BrainSpecBase::~BrainSpecBase() = default;

ObservationsBase& BrainSpecBase::observations_base() {
  return *brain_spec_data_->observations_base;
}

const ObservationsBase& BrainSpecBase::observations_base() const {
  return *brain_spec_data_->observations_base;
}

ActionsBase& BrainSpecBase::actions_base() {
  return *brain_spec_data_->actions_base;
}

const ActionsBase& BrainSpecBase::actions_base() const {
  return *brain_spec_data_->actions_base;
}

}  // namespace falken
