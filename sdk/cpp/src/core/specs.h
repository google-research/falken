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

#ifndef FALKEN_SDK_CORE_SPECS_H_
#define FALKEN_SDK_CORE_SPECS_H_

#include <map>
#include <string>

#include "src/core/protos.h"
#include "src/core/statusor.h"

namespace falken {
namespace common {

// Check that the brain spec describes valid action and observation spaces.
absl::Status CheckValid(const proto::BrainSpec& spec);

// Check that the action spec describes a valid action space.
absl::Status CheckValid(const proto::ActionSpec& spec);

// Check that the observation spec describes a valid observation space space.
absl::Status CheckValid(const proto::ObservationSpec& spec);

// Typecheck data against spec.
absl::Status Typecheck(const proto::ObservationSpec& spec,
                       const proto::ObservationData& data);
absl::Status Typecheck(const proto::ActionSpec& spec,
                       const proto::ActionData& data);

}  // namespace common
}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_SPECS_H_
