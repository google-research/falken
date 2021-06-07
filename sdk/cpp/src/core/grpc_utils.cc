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

#include <string.h>

#include "src/core/client_info.h"
#include "src/core/log.h"
#include "src/core/service_environment.h"

namespace falken {
namespace core {

std::shared_ptr<grpc::Channel> CreateBaseChannel(
    const char* service_name, const GrpcChannelParameters& params) {
  if (params.address.empty()) {
    LogError("No %s service address specified.", service_name);
    return nullptr;
  }

  LogVerbose("Connecting to %s service address %s", service_name,
             params.address.c_str());

  std::shared_ptr<grpc::ChannelCredentials> credentials;
  if (params.ssl_certificate.empty()) {
    credentials = grpc::experimental::LocalCredentials(LOCAL_TCP);
    LogVerbose("Using local TCP credentials.");
  } else {
    grpc::SslCredentialsOptions ssl_options;
    ssl_options.pem_root_certs = params.ssl_certificate;
    credentials = grpc::SslCredentials(ssl_options);
    LogVerbose("Using SSL credentials.");
  }

  std::shared_ptr<grpc::Channel> channel;
  grpc::ChannelArguments channel_args;
  if (!params.ssl_target_name.empty()) {
    channel_args.SetSslTargetNameOverride(params.ssl_target_name);
    LogVerbose("Overriding SSL target name with %s",
               params.ssl_target_name.c_str());
  }
  channel_args.SetUserAgentPrefix(GetUserAgent());
  channel_args.SetInt(
      "grpc.max_receive_message_length", 50 * 1024 * 1024);

  channel = grpc::CreateCustomChannel(params.address, credentials,
                                      channel_args);
  if (!channel) {
    LogError("Failed to create channel to connect to %s", service_name);
  }
  return channel;
}

template <typename STUB_CLASS, typename STUB_FACTORY_FUNC>
std::unique_ptr<STUB_CLASS> CreateChannelStub(
    const char* service_name, const GrpcChannelParameters& params,
    STUB_FACTORY_FUNC factory_func) {
  auto channel = CreateBaseChannel(service_name, params);
  if (!channel) return nullptr;
  std::unique_ptr<STUB_CLASS> stub = factory_func(channel, grpc::StubOptions());
  if (!stub) {
    LogError("Failed to create stub to connect to %s", service_name);
  }
  return stub;
}

std::unique_ptr<proto::grpc_gen::FalkenService::Stub> CreateChannel(
    const GrpcChannelParameters& params) {
  return CreateChannelStub<proto::grpc_gen::FalkenService::Stub>(
      "Falken", params, proto::grpc_gen::FalkenService::NewStub);
}

}  // namespace core
}  // namespace falken
