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

#include "src/core/grpc_utils.h"

#include "src/core/service_environment.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "absl/time/time.h"

namespace {

TEST(GrpcUtils, CreateChannelTest) {
  auto stub =
      falken::core::CreateChannel(ServiceEnvironmentToGrpcChannelParameters(
          falken::core::ServiceEnvironment::kProd));
  EXPECT_TRUE(stub != nullptr);
}
}  // namespace
