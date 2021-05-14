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

// Define the supported environments of the API that the Core can connect to.
// This file provides the standard methods used by ABSL flags to parse and error
// check the environments from a flag. It is used automatically by ABSL_FLAG.
#ifndef FALKEN_SDK_CORE_SERVICE_ENVIRONMENT_H_
#define FALKEN_SDK_CORE_SERVICE_ENVIRONMENT_H_

#include <string>

#include "src/core/macros.h"

namespace falken {
namespace core {

// Configure default values for service connections.
#if !defined(FALKEN_CONNECTION_DEFAULT_ADDRESS)
#define FALKEN_CONNECTION_DEFAULT_ADDRESS [::]:50051
#endif  // !defined(FALKEN_CONNECTION_DEFAULT_ADDRESS)
#if !defined(FALKEN_CONNECTION_DEFAULT_SSL_TARGET_NAME)
#define FALKEN_CONNECTION_DEFAULT_SSL_TARGET_NAME localhost
#endif  // !defined(FALKEN_CONNECTION_DEFAULT_SSL_TARGET_NAME)

#if !defined(FALKEN_CONNECTION_LOCAL_ADDRESS)
#define FALKEN_CONNECTION_LOCAL_ADDRESS FALKEN_CONNECTION_DEFAULT_ADDRESS
#endif  // !defined(FALKEN_CONNECTION_LOCAL_ADDRESS)
#if !defined(FALKEN_CONNECTION_LOCAL_SSL_TARGET_NAME)
#define FALKEN_CONNECTION_LOCAL_SSL_TARGET_NAME \
  FALKEN_CONNECTION_DEFAULT_SSL_TARGET_NAME
#endif  // !defined(FALKEN_CONNECTION_LOCAL_SSL_TARGET_NAME)

#if !defined(FALKEN_CONNECTION_DEV_ADDRESS)
#define FALKEN_CONNECTION_DEV_ADDRESS FALKEN_CONNECTION_DEFAULT_ADDRESS
#endif  // !defined(FALKEN_CONNECTION_DEV_ADDRESS)
#if !defined(FALKEN_CONNECTION_DEV_SSL_TARGET_NAME)
#define FALKEN_CONNECTION_DEV_SSL_TARGET_NAME \
  FALKEN_CONNECTION_DEFAULT_SSL_TARGET_NAME
#endif  // !defined(FALKEN_CONNECTION_DEV_SSL_TARGET_NAME)

#if !defined(FALKEN_CONNECTION_PROD_ADDRESS)
#define FALKEN_CONNECTION_PROD_ADDRESS FALKEN_CONNECTION_DEFAULT_ADDRESS
#endif  // !defined(FALKEN_CONNECTION_PROD_ADDRESS)
#if !defined(FALKEN_CONNECTION_PROD_SSL_TARGET_NAME)
#define FALKEN_CONNECTION_PROD_SSL_TARGET_NAME \
  FALKEN_CONNECTION_DEFAULT_SSL_TARGET_NAME
#endif  // !defined(FALKEN_CONNECTION_PROD_SSL_TARGET_NAME)

// Expand connection values into strings.
#define FALKEN_CONNECTION_LOCAL_ADDRESS_STRING \
  FALKEN_EXPAND_STRINGIFY(FALKEN_CONNECTION_LOCAL_ADDRESS)
#define FALKEN_CONNECTION_LOCAL_SSL_TARGET_NAME_STRING \
  FALKEN_EXPAND_STRINGIFY(FALKEN_CONNECTION_LOCAL_SSL_TARGET_NAME)
#define FALKEN_CONNECTION_DEV_ADDRESS_STRING \
  FALKEN_EXPAND_STRINGIFY(FALKEN_CONNECTION_DEV_ADDRESS)
#define FALKEN_CONNECTION_DEV_SSL_TARGET_NAME_STRING \
  FALKEN_EXPAND_STRINGIFY(FALKEN_CONNECTION_DEV_SSL_TARGET_NAME)
#define FALKEN_CONNECTION_PROD_ADDRESS_STRING \
  FALKEN_EXPAND_STRINGIFY(FALKEN_CONNECTION_PROD_ADDRESS)
#define FALKEN_CONNECTION_PROD_SSL_TARGET_NAME_STRING \
  FALKEN_EXPAND_STRINGIFY(FALKEN_CONNECTION_PROD_SSL_TARGET_NAME)

// Expands to an initializer for a ServiceEnvironmentSettings struct.
#define FALKEN_SERVICE_ENVIRONMENT_INIT_SETTINGS(                    \
    enum_name, enum_value, name, grpc_address, grpc_ssl_target_name) \
  ServiceEnvironmentSettings(                                        \
      name, GrpcChannelParameters(grpc_address, "", grpc_ssl_target_name))

// Expands to a ServiceEnvironment enum member.
#define FALKEN_SERVICE_ENVIRONMENT_INIT_ENUM(                        \
    enum_name, enum_value, name, grpc_address, grpc_ssl_target_name) \
  enum_name = enum_value

// Parameters for each ServiceEnvironment and the associated
// ServiceEnvironmentSettings.
// clang-format off
#define FALKEN_SERVICE_ENVIRONMENT_PARAMS(X)                            \
  X(kUndefined, 0, "", "", ""),                                         \
  X(kLocal, 1, "local",                                                 \
    FALKEN_CONNECTION_LOCAL_ADDRESS_STRING,                             \
    FALKEN_CONNECTION_LOCAL_SSL_TARGET_NAME_STRING),                    \
  X(kDev, 2, "dev",                                                     \
    FALKEN_CONNECTION_DEV_ADDRESS_STRING,                               \
    FALKEN_CONNECTION_DEV_SSL_TARGET_NAME_STRING),                      \
  X(kProd, 3, "prod",                                                   \
    FALKEN_CONNECTION_PROD_ADDRESS_STRING,                              \
    FALKEN_CONNECTION_PROD_SSL_TARGET_NAME_STRING),                     \
// clang-format on

// The supported environments for the API.
enum class ServiceEnvironment {
  FALKEN_SERVICE_ENVIRONMENT_PARAMS(FALKEN_SERVICE_ENVIRONMENT_INIT_ENUM)
};

// Parameters used to connect create a gRPC channel.
struct GrpcChannelParameters {
  GrpcChannelParameters() {}
  GrpcChannelParameters(const char* _address, const char* _ssl_certificate,
                        const char* _ssl_target_name)
      : address(_address),
        ssl_certificate(_ssl_certificate),
        ssl_target_name(_ssl_target_name) {}

  std::string address;
  std::string ssl_certificate;
  std::string ssl_target_name;

  // Whether the instance is empty.
  bool IsEmpty() const {
    return address.empty() && ssl_certificate.empty() &&
        ssl_target_name.empty();
  }
};

// Default settings of each environment.
struct ServiceEnvironmentSettings {
  ServiceEnvironmentSettings(
      const char* _name, const GrpcChannelParameters& _grpc_channel_parameters)
      : name(_name), grpc_channel_parameters(_grpc_channel_parameters) {}

  const char* name;
  GrpcChannelParameters grpc_channel_parameters;
};

// Conversion between the service environment enum values and the environment
// name.
ServiceEnvironment ServiceEnvironmentFromName(const std::string& name);
std::string ServiceEnvironmentToName(ServiceEnvironment env);

// Get the GRPC channel parameters for the specified service environment.
const GrpcChannelParameters& ServiceEnvironmentToGrpcChannelParameters(
    ServiceEnvironment env);
// Lookup the service environment based upon the server address.
ServiceEnvironment ServiceEnvironmentFromGrpcChannelParameters(
    const GrpcChannelParameters& params);

}  // namespace core
}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_SERVICE_ENVIRONMENT_H_
