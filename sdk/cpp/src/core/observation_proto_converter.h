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

#ifndef FALKEN_SDK_CORE_OBSERVATION_PROTO_CONVERTER_H_
#define FALKEN_SDK_CORE_OBSERVATION_PROTO_CONVERTER_H_

#include "src/core/protos.h"
#include "falken/observations.h"

namespace falken {

class ObservationProtoConverter {
 public:
  static proto::ObservationSpec ToObservationSpec(
      const ObservationsBase& observation_base);
  static proto::ObservationData ToObservationData(
      const ObservationsBase& observation_base);
  static void FromObservationSpec(
      const proto::ObservationSpec& observation_spec,
      ObservationsBase& observation_base);
  static bool FromObservationData(
      const proto::ObservationData& observation_data,
      ObservationsBase& observations_base);
  // Verify that an ObservationSpec is the same as the given ObservationsBase.
  // Note: This assumes they are sorted by name since entities in protos do not
  // have names.
  static bool VerifyObservationSpecIntegrity(
      const proto::ObservationSpec& observation_spec,
      const ObservationsBase& observations_base);
  // Verify that an ObservationData is the same as the given ObservationsBase.
  // Note: This assumes they are sorted by name since entities in protos do not
  // have names.
  static bool VerifyObservationDataIntegrity(
      const proto::ObservationData& observation_data,
      const ObservationsBase& observations_base);
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_OBSERVATION_PROTO_CONVERTER_H_
