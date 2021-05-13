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

#include "src/core/brain_spec_proto_converter.h"

#include <memory>

namespace falken {

proto::BrainSpec BrainSpecProtoConverter::ToBrainSpec(
    const BrainSpecBase& brain_spec_base) {
  proto::BrainSpec brain_spec;
  *brain_spec.mutable_observation_spec() =
      ObservationProtoConverter::ToObservationSpec(
          brain_spec_base.observations_base());
  *brain_spec.mutable_action_spec() =
      ActionProtoConverter::ToActionSpec(brain_spec_base.actions_base());
  return brain_spec;
}

std::unique_ptr<BrainSpecBase> BrainSpecProtoConverter::FromBrainSpec(
    const proto::BrainSpec& brain_spec) {
  std::unique_ptr<BrainSpecBase> allocated_brain_spec(new BrainSpecBase());
  ActionProtoConverter::FromActionSpec(brain_spec.action_spec(),
                                       allocated_brain_spec->actions_base());
  ObservationProtoConverter::FromObservationSpec(
      brain_spec.observation_spec(), allocated_brain_spec->observations_base());
  return allocated_brain_spec;
}

bool BrainSpecProtoConverter::VerifyBrainSpecIntegrity(
    const proto::BrainSpec& brain_spec, const BrainSpecBase& brain_spec_base) {
  const proto::ObservationSpec& observation_spec =
      brain_spec.observation_spec();
  const proto::ActionSpec& action_spec = brain_spec.action_spec();
  return ObservationProtoConverter::VerifyObservationSpecIntegrity(
             observation_spec, brain_spec_base.observations_base()) &&
         ActionProtoConverter::VerifyActionSpecIntegrity(action_spec,
             brain_spec_base.actions_base());
}

}  // namespace falken
