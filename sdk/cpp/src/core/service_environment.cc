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

#include "src/core/service_environment.h"

#include <memory>
#include <vector>

#include "src/core/log.h"
#include "src/core/local_grpc_roots_pem.h"
#include "src/core/public_grpc_roots_pem.h"
#include "absl/base/macros.h"

namespace falken {
namespace core {

// gRPC channel parameters per environment.
std::vector<ServiceEnvironmentSettings>& GetServiceEnvironmentSettings() {
  static std::unique_ptr<std::vector<ServiceEnvironmentSettings>>
      settings;  // NOLINT
  if (!settings) {
    settings.reset(new std::vector<ServiceEnvironmentSettings>({
        FALKEN_SERVICE_ENVIRONMENT_PARAMS(
            FALKEN_SERVICE_ENVIRONMENT_INIT_SETTINGS)
    }));
  }
  return *settings;
}

ServiceEnvironment ServiceEnvironmentFromName(const std::string& name) {
  auto& all_settings = GetServiceEnvironmentSettings();
  for (int i = 0; i < all_settings.size(); ++i) {
    if (name == all_settings[i].name) {
      return static_cast<ServiceEnvironment>(i);
    }
  }
  return ServiceEnvironment::kUndefined;
}

std::string ServiceEnvironmentToName(ServiceEnvironment environment) {
  return GetServiceEnvironmentSettings()[static_cast<int>(environment)].name;
}

// Returns an SSL certificate so internal developers can connect to local
// gRPC endpoints.
static const char* GetLocalCert() {
  static const char* local_cert = nullptr;
  if (local_cert == nullptr) {
    local_cert = reinterpret_cast<const char*>(local_grpc_roots_pem_data);
    LogVerbose("Loaded local cert (%s) of size: %zd",
               local_grpc_roots_pem_filename,
               local_grpc_roots_pem_size);
  }
  return local_cert;
}

static const char* GetPublicCert() {
  // On the first call, load the default cert from the compile-time-copied
  // grpc/etc/roots.pem file.
  static const char* public_cert = nullptr;
  if (public_cert == nullptr) {
    public_cert = reinterpret_cast<const char*>(public_grpc_roots_pem_data);
    LogVerbose("Loaded public cert (%s) of size: %zd",
               public_grpc_roots_pem_filename, public_grpc_roots_pem_size);
  }
  return public_cert;
}

const GrpcChannelParameters& ServiceEnvironmentToGrpcChannelParameters(
    ServiceEnvironment environment) {
  auto& params = GetServiceEnvironmentSettings()[static_cast<int>(environment)]
                     .grpc_channel_parameters;
  if (params.ssl_certificate.empty()) {
    if (environment == ServiceEnvironment::kLocal) {
      params.ssl_certificate = GetLocalCert();
    } else if (environment == ServiceEnvironment::kDev ||
               environment == ServiceEnvironment::kProd) {
      params.ssl_certificate = GetPublicCert();
    }
  }
  return params;
}

ServiceEnvironment ServiceEnvironmentFromGrpcChannelParameters(
    const GrpcChannelParameters& params) {
  auto& all_settings = GetServiceEnvironmentSettings();
  for (int i = 0; i < all_settings.size(); ++i) {
    const auto& settings = all_settings[i];
    if (params.address == settings.grpc_channel_parameters.address) {
      return static_cast<ServiceEnvironment>(i);
    }
  }
  return ServiceEnvironment::kUndefined;
}

}  // namespace core
}  // namespace falken
