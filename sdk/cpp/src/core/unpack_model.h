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

#ifndef FALKEN_SDK_CORE_UNPACK_MODEL_H_
#define FALKEN_SDK_CORE_UNPACK_MODEL_H_

#include "src/core/protos.h"
#include "absl/status/status.h"

namespace falken {
namespace core {

// Unpacks a model to a directory from a Falken::Model proto.
absl::Status UnpackModel(const proto::SerializedModel& model,
                         const std::string& output_dir,
                         const std::string& model_subdir);

}  // namespace core
}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_UNPACK_MODEL_H_
