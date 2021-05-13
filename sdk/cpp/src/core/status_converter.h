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

#ifndef FALKEN_SDK_CORE_STATUS_CONVERTER_H_
#define FALKEN_SDK_CORE_STATUS_CONVERTER_H_

#include "absl/status/status.h"
#if defined(__APPLE__)
#include "grpc/include/grpcpp/grpcpp.h"
#else
#include "grpc/include/grpcpp/grpcpp.h"
#endif

namespace falken {
namespace core {

// Convert a grpc::Status along with it's payload to absl::Status.
absl::Status MakeStatusFromGrpcStatus(const grpc::Status& status);

}  // namespace core
}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_STATUS_CONVERTER_H_
