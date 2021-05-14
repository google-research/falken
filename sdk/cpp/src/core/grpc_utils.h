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

#ifndef FALKEN_SDK_CORE_GRPC_UTILS_H_
#define FALKEN_SDK_CORE_GRPC_UTILS_H_

#include "src/core/protos.h"
#include "src/core/service_environment.h"

#include "grpc/include/grpcpp/grpcpp.h"
#include "grpc/include/grpcpp/security/credentials.h"

namespace falken {
namespace core {

std::unique_ptr<proto::grpc_gen::FalkenService::Stub> CreateChannel(
    const GrpcChannelParameters& param);

}  // namespace core
}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_GRPC_UTILS_H_
