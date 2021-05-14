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

#include "src/core/status_converter.h"

#include "google/rpc/code.pb.h"  // NOLINT
#include "google/rpc/status.pb.h"  // NOLINT
#include "src/core/log.h"
#include "absl/strings/cord.h"

namespace falken {
namespace core {

absl::Status MakeStatusFromGrpcStatus(const grpc::Status& grpc_status) {
  const auto& message = grpc_status.error_message();
  auto status_code = static_cast<absl::StatusCode>(grpc_status.error_code());
  // absl::Status will ignore the message on construction if the status is ok.
  if (status_code == absl::StatusCode::kOk && !message.empty()) {
    LogWarning(
        "RPC message '%s' received for a successful "
        "operation will not be added to absl::Status",
        message.c_str());
  }
  absl::Status status(status_code, message);

  const auto& error_details = grpc_status.error_details();
  if (!error_details.empty()) {
    google::rpc::Status status_proto;
    if (status_proto.ParseFromString(grpc_status.error_details())) {
      // absl::Status will silently not store payloads if the status is ok so
      // log the payload instead.
      if (status_code == absl::StatusCode::kOk) {
        LogWarning(
            "RPC payload '%s' received for a successful "
            "operation will not be added to absl::Status",
            status_proto.DebugString().c_str());
      }
      status.SetPayload(status_proto.GetDescriptor()->full_name(),
                        absl::Cord(grpc_status.error_details()));
    } else {
      LogError(
          "Failed to parse error_details of "
          "google::rpc::Status (code=%d, message=%s)",
          static_cast<int>(grpc_status.error_code()),
          grpc_status.error_message().c_str());
    }
  }
  return status;
}

}  // namespace core
}  // namespace falken
