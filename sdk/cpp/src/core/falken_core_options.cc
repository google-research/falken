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

#include "src/core/falken_core_options.h"

#include <ctype.h>

#include <algorithm>
#include <sstream>
#include <string>
#include <vector>

#include "src/core/falken_core.h"
#include "falken/log.h"
#include "absl/base/macros.h"

namespace falken {
namespace core {

namespace {

// Log level names.
static const char kDebugName[] = "debug";
static const char kVerboseName[] = "verbose";
static const char kInfoName[] = "info";
static const char kWarningName[] = "warning";
static const char kErrorName[] = "error";
static const char kFatalName[] = "fatal";

// Convert log level string to level.
LogLevel LogLevelFromName(const std::string& name) {
  static const struct {
    const char* name;
    LogLevel level;
  } kNameToLevel[] = {
      {kDebugName, kLogLevelDebug}, {kVerboseName, kLogLevelVerbose},
      {kInfoName, kLogLevelInfo},   {kWarningName, kLogLevelWarning},
      {kErrorName, kLogLevelError}, {kFatalName, kLogLevelFatal},
  };
  // Make the log level name lowercase.
  std::string name_lower = name;
  std::transform(name_lower.begin(), name_lower.end(), name_lower.begin(),
                 [](char c) { return tolower(c); });
  for (int i = 0; i < ABSL_ARRAYSIZE(kNameToLevel); ++i) {
    const auto& name_to_level = kNameToLevel[i];
    if (name_lower == name_to_level.name) {
      return name_to_level.level;
    }
  }
  LogWarning("Failed to find log level matching name %s", name.c_str());
  return kLogLevelInfo;
}

// Convert log level to string.
const char* LogLevelToName(LogLevel level) {
  switch (level) {
    case kLogLevelDebug:
      return kDebugName;
    case kLogLevelVerbose:
      return kVerboseName;
    case kLogLevelInfo:
      return kInfoName;
    case kLogLevelWarning:
      return kWarningName;
    case kLogLevelError:
      return kErrorName;
    case kLogLevelFatal:
      return kFatalName;
  }
  LogWarning("Failed to convert log level %d to name", static_cast<int>(level));
  return kInfoName;
}

}  // namespace

typedef OptionAccessor<GrpcChannelParameters> GrpcChannelParametersOption;

static const std::vector<GrpcChannelParametersOption>&
GetGrpcChannelParametersOptions() {
  static std::vector<GrpcChannelParametersOption> options;  // NOLINT
  if (options.empty()) {
    options.emplace_back(
        "address",
        [](GrpcChannelParameters* params,
           const GrpcChannelParametersOption& accessor, const std::string& path,
           const flexbuffers::Reference& value) -> bool {
          params->address = value.ToString();
          return true;
        },
        [](const GrpcChannelParameters& params,
           const GrpcChannelParametersOption& accessor, const std::string& path,
           flexbuffers::Builder* builder) {
          if (!params.address.empty()) {
            builder->String(accessor.name().c_str(), params.address.c_str());
          }
        });
    options.emplace_back(
        "ssl_certificate",
        [](GrpcChannelParameters* params,
           const GrpcChannelParametersOption& accessor, const std::string& path,
           const flexbuffers::Reference& value) -> bool {
          params->ssl_certificate = FlexbuffersStringListToString(value);
          return true;
        },
        [](const GrpcChannelParameters& params,
           const GrpcChannelParametersOption& accessor, const std::string& path,
           flexbuffers::Builder* builder) {
          if (!params.ssl_certificate.empty()) {
            builder->Vector(accessor.name().c_str(), [builder, params]() {
              std::stringstream ss(params.ssl_certificate);
              std::string line;
              while (std::getline(ss, line)) {
                builder->Add(line.c_str());
              }
            });
          }
        });
    options.emplace_back(
        "ssl_target_name",
        [](GrpcChannelParameters* params,
           const GrpcChannelParametersOption& accessor, const std::string& path,
           const flexbuffers::Reference& value) -> bool {
          params->ssl_target_name = value.ToString();
          return true;
        },
        [](const GrpcChannelParameters& params,
           const GrpcChannelParametersOption& accessor, const std::string& path,
           flexbuffers::Builder* builder) {
          if (!params.ssl_target_name.empty()) {
            builder->String(accessor.name().c_str(),
                            params.ssl_target_name.c_str());
          }
        });
  }
  return options;
}

const std::vector<FalkenCoreOption>& GetFalkenCoreOptions() {
  static std::vector<FalkenCoreOption> options;  // NOLINT
  if (options.empty()) {
    // Public configuration options.
    options.emplace_back(
        "api_key",
        [](FalkenCore* falken_core, const FalkenCoreOption& accessor,
           const std::string& path,
           const flexbuffers::Reference& value) -> bool {
          if (!value.IsString()) {
            LogError("Option %s should be a string", path.c_str());
            return false;
          }
          falken_core->SetApiKey(value.As<std::string>());
          return true;
        },
        [](const FalkenCore& falken_core, const FalkenCoreOption& accessor,
           const std::string& path, flexbuffers::Builder* builder) {
          if (!falken_core.GetApiKey().empty()) {
            builder->String(accessor.name().c_str(), "(hidden)");
          }
        });
    options.emplace_back(
        "project_id",
        [](FalkenCore* falken_core, const FalkenCoreOption& accessor,
           const std::string& path,
           const flexbuffers::Reference& value) -> bool {
          if (!value.IsString()) {
            LogError("Option %s should be a string", path.c_str());
            return false;
          }
          falken_core->SetProjectId(value.As<std::string>());
          return true;
        },
        [](const FalkenCore& falken_core, const FalkenCoreOption& accessor,
           const std::string& path, flexbuffers::Builder* builder) {
          builder->String(accessor.name().c_str(),
                          falken_core.GetProjectId().c_str());
        });
    // Internal configuration options.
    options.emplace_back(
        "api_call_timeout_milliseconds",
        [](FalkenCore* falken_core, const FalkenCoreOption& accessor,
           const std::string& path,
           const flexbuffers::Reference& value) -> bool {
          if (!value.IsInt()) {
            LogError("Option %s should be an integer", path.c_str());
            return false;
          }
          falken_core->SetApiCallTimeout(value.AsInt64());
          return true;
        },
        [](const FalkenCore& falken_core, const FalkenCoreOption& accessor,
           const std::string& path, flexbuffers::Builder* builder) {
          builder->Int(accessor.name().c_str(),
                       falken_core.GetApiCallTimeout());
        });
    options.emplace_back(
        "session_data_dir",
        [](FalkenCore* falken_core, const FalkenCoreOption& accessor,
           const std::string& path,
           const flexbuffers::Reference& value) -> bool {
          if (!value.IsString()) {
            LogError("Option %s should be a string", path.c_str());
            return false;
          }
          falken_core->SetSessionScratchDirectory(value.As<std::string>());
          return true;
        },
        [](const FalkenCore& falken_core, const FalkenCoreOption& accessor,
           const std::string& path, flexbuffers::Builder* builder) {
          builder->String(accessor.name().c_str(),
                          falken_core.GetSessionScratchDirectory().c_str());
        });
    options.emplace_back(
        "log_file",
        [](FalkenCore* falken_core, const FalkenCoreOption& accessor,
           const std::string& path,
           const flexbuffers::Reference& value) -> bool {
          if (!value.IsString()) {
            LogError("Option %s should be a string", path.c_str());
            return false;
          }
          SystemLogger::Get()->file_logger().set_filename(
              value.As<std::string>().c_str());
          return true;
        },
        [](const FalkenCore& falken_core, const FalkenCoreOption& accessor,
           const std::string& path, flexbuffers::Builder* builder) {
          builder->String(
              accessor.name().c_str(),
              SystemLogger::Get()->file_logger().filename().c_str());
        });
    options.emplace_back(
        "log_level",
        [](FalkenCore* falken_core, const FalkenCoreOption& accessor,
           const std::string& path,
           const flexbuffers::Reference& value) -> bool {
          if (!value.IsString()) {
            LogError("Option %s should be a string", path.c_str());
            return false;
          }
          SystemLogger::Get()->set_log_level(
              LogLevelFromName(value.As<std::string>().c_str()));
          return true;
        },
        [](const FalkenCore& falken_core, const FalkenCoreOption& accessor,
           const std::string& path, flexbuffers::Builder* builder) {
          builder->String(accessor.name().c_str(),
                          LogLevelToName(SystemLogger::Get()->log_level()));
        });
    options.emplace_back(
        "service",
        std::vector<FalkenCoreOption>({
            FalkenCoreOption(
                "environment",
                [](FalkenCore* falken_core, const FalkenCoreOption& accessor,
                   const std::string& path,
                   const flexbuffers::Reference& value) -> bool {
                  std::string string_value = value.As<std::string>();
                  ServiceEnvironment service_environment =
                      ServiceEnvironmentFromName(string_value);
                  if (service_environment == ServiceEnvironment::kUndefined) {
                    LogError(
                        "Option %s should be one of [local, "
                        "dev, prod], not %s",
                        path.c_str(), string_value.c_str());
                    return false;
                  }
                  falken_core->SetServiceEnvironment(service_environment);
                  return true;
                },
                [](const FalkenCore& falken_core,
                   const FalkenCoreOption& accessor, const std::string& path,
                   flexbuffers::Builder* builder) {
                  builder->String(accessor.name().c_str(),
                                  ServiceEnvironmentToName(
                                      falken_core.GetServiceEnvironment()));
                }),
            FalkenCoreOption(
                "connection",
                [](FalkenCore* falken_core, const FalkenCoreOption& accessor,
                   const std::string& path,
                   const flexbuffers::Reference& value) -> bool {
                  // Note: This is dangerously depending on the assumption that
                  // the environment parameter has been loaded on when this
                  // code is executed.
                  GrpcChannelParameters params =
                      falken_core->GetServiceGrpcChannelParameters();
                  if (!GrpcChannelParametersOption::SetOptions(
                          &params, GetGrpcChannelParametersOptions(),
                          value.AsMap()) ||
                      params.IsEmpty()) {
                    LogError("Option %s is empty", path.c_str());
                    return false;
                  }
                  falken_core->SetServiceGrpcChannelParameters(params);
                  return true;
                },
                [](const FalkenCore& falken_core,
                   const FalkenCoreOption& accessor, const std::string& path,
                   flexbuffers::Builder* builder) {
                  auto params = falken_core.GetServiceGrpcChannelParameters();
                  GrpcChannelParametersOption::GetOptions(
                      builder, params, GetGrpcChannelParametersOptions(),
                      &accessor.name(), &path);
                }),
        }));
  }
  return options;
}

}  // namespace core
}  // namespace falken
