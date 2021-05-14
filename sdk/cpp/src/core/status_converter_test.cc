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

#include <string>
#include <vector>

#include "google/protobuf/any.pb.h"  // NOLINT
#include "google/rpc/code.pb.h"  // NOLINT
#include "google/rpc/status.pb.h"  // NOLINT
#include "gtest/gtest.h"
#include "absl/strings/string_view.h"

TEST(StatusConverter, ConvertGrpcStatusOk) {
  auto status = falken::core::MakeStatusFromGrpcStatus(
      grpc::Status(grpc::StatusCode::OK, "Hello"));
  EXPECT_TRUE(status.ok());
  EXPECT_EQ(status.code(), absl::StatusCode::kOk);
  // absl::Status removes the message when constructed with
  // absl::StatusCode::kOk.
  EXPECT_EQ(status.message(), "");
}

TEST(StatusConverter, ConvertGrpcStatusFailed) {
  auto status = falken::core::MakeStatusFromGrpcStatus(
      grpc::Status(grpc::StatusCode::NOT_FOUND, "Cheese not found"));
  EXPECT_FALSE(status.ok());
  EXPECT_EQ(status.code(), absl::StatusCode::kNotFound);
  EXPECT_EQ(status.message(), "Cheese not found");
}

namespace {

// Create a google::rpc:Status protobuf that chains two google::rpc::Status
// protobufs with the specified codes and messages.
static google::rpc::Status CreateRpcStatusProto(
    google::rpc::Code outer_code, const std::string& outer_message,
    google::rpc::Code inner_code, const std::string& inner_message) {
  google::rpc::Status outer_details;
  outer_details.set_code(outer_code);
  outer_details.set_message(outer_message);
  google::rpc::Status inner_details;
  inner_details.set_code(google::rpc::Code::OK);
  inner_details.set_message(inner_message);
  std::string serialized_inner_details;
  inner_details.SerializeToString(&serialized_inner_details);
  google::protobuf::Any& nested_inner_details = *outer_details.add_details();
  nested_inner_details.set_type_url("google.rpc.Status");
  nested_inner_details.set_value(serialized_inner_details);
  return outer_details;
}

}  // namespace

TEST(StatusConverter, ConvertGrpcStatusOkWithPayload) {
  google::rpc::Status rpc_status_proto =
      CreateRpcStatusProto(google::rpc::Code::OK, "Frontend is ok",
                           google::rpc::Code::OK, "Backend is ok");
  std::string serialized_rpc_status;
  rpc_status_proto.SerializeToString(&serialized_rpc_status);
  auto status = falken::core::MakeStatusFromGrpcStatus(grpc::Status(
      grpc::StatusCode::OK, "Welcome to the jungle", serialized_rpc_status));
  EXPECT_TRUE(status.ok());
  EXPECT_EQ(status.code(), absl::StatusCode::kOk);
  // absl::Status removes the message and ignores the payload when constructed
  // with absl::StatusCode::kOk.
  EXPECT_EQ(status.message(), "");
  int number_of_payloads = 0;
  status.ForEachPayload(
      [&number_of_payloads](absl::string_view, const absl::Cord&) {
        number_of_payloads++;
      });
  EXPECT_EQ(number_of_payloads, 0);
}

TEST(StatusConverter, ConvertGrpcStatusFailedWithPayload) {
  google::rpc::Status rpc_status_proto = CreateRpcStatusProto(
      google::rpc::Code::OK, "Frontend is ok",
      google::rpc::Code::DEADLINE_EXCEEDED, "Backend is kaput");
  std::string serialized_rpc_status;
  rpc_status_proto.SerializeToString(&serialized_rpc_status);
  auto status = falken::core::MakeStatusFromGrpcStatus(grpc::Status(
      grpc::StatusCode::DEADLINE_EXCEEDED,
      "Timed out while connecting to the service", serialized_rpc_status));
  EXPECT_FALSE(status.ok());
  EXPECT_EQ(status.code(), absl::StatusCode::kDeadlineExceeded);
  EXPECT_EQ(status.message(), "Timed out while connecting to the service");
  int number_of_payloads = 0;
  status.ForEachPayload([&number_of_payloads, &serialized_rpc_status](
                            absl::string_view url, const absl::Cord& payload) {
    EXPECT_EQ(url, google::rpc::Status::GetDescriptor()->full_name());
    EXPECT_EQ(payload, serialized_rpc_status);
    number_of_payloads++;
  });
  EXPECT_EQ(number_of_payloads, 1);
}
