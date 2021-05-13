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

#ifndef FALKEN_SDK_CORE_BRAIN_SPEC_PROTO_CONVERTER_H_
#define FALKEN_SDK_CORE_BRAIN_SPEC_PROTO_CONVERTER_H_

#include "src/core/action_proto_converter.h"
#include "src/core/observation_proto_converter.h"
#include "src/core/protos.h"
#include "falken/brain_spec.h"

namespace falken {

class BrainSpecProtoConverter final {
 public:
  // Convert a given BrainSpecBase to a BrainSpec proto.
  static proto::BrainSpec ToBrainSpec(const BrainSpecBase& brain_spec_base);
  // Convert a given BrainSpec to a BrainSpecBase.
  static std::unique_ptr<BrainSpecBase> FromBrainSpec(
      const proto::BrainSpec& brain_spec);
  // Compare the given BrainSpec to a dynamic BrainSpecBase, checking
  // that every attribute from the owned ObservationSpec and ActionSpec
  // is exactly the same as the ones that the templatized BrainSpec has.
  static bool VerifyBrainSpecIntegrity(const proto::BrainSpec& brain_spec,
                                       const BrainSpecBase& brain_spec_base);
  // Compare the given BrainSpec to a templatized BrainSpec, checking
  // that every attribute from the owned ObservationSpec and ActionSpec
  // is exactly the same as the ones that the templatized BrainSpec has.
  template <typename BrainSpecClass>
  static bool VerifyBrainSpecIntegrity(const proto::BrainSpec& brain_spec);
};

template <typename BrainSpecClass>
bool BrainSpecProtoConverter::VerifyBrainSpecIntegrity(
    const proto::BrainSpec& brain_spec) {
  BrainSpecClass template_brain_spec;
  return VerifyBrainSpecIntegrity(brain_spec, template_brain_spec);
}

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_BRAIN_SPEC_PROTO_CONVERTER_H_
