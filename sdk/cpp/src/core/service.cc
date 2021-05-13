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

#include "falken/service.h"

#include <string.h>

#include <algorithm>
#include <memory>
#include <set>
#include <typeinfo>

#include "src/core/assert.h"
#include "src/core/brain_spec_proto_converter.h"
#include "src/core/child_resource_map.h"
#include "src/core/falken_core.h"
#include "src/core/globals.h"
#include "src/core/log.h"
#include "src/core/protos.h"
#include "falken/log.h"
#include "src/core/stdout_logger.h"

namespace falken {

// No-lint b/c we are fine with this being destroyed on exit.
static ChildResourceMap<Service> services_; // NOLINT

struct Service::ServiceData {
  ServiceData() : logger(SystemLogger::Get()) {}

  std::weak_ptr<Service> weak_this;
  // Keep track of created brains using this service so we can retrieve
  // shared_ptr's for shared resources.
  ChildResourceMap<BrainBase> created_brains;
  std::shared_ptr<SystemLogger> logger;
};

Service::Service() : service_data_(new Service::ServiceData) {}

Service::~Service() = default;

std::shared_ptr<Service> Service::Connect(const char* project_id,
                                          const char* api_key,
                                          const char* json_config) {
  // Use a single system logger instance until we have created a service object.
  std::shared_ptr<SystemLogger> logger = SystemLogger::Get();
  // Try loading the default config, ignore any errors as we'll try configuring
  // again after setting the API key and project ID.
  auto& core = core::FalkenCore::Get();
  grpc::ClientContext context;
  core.ConfigureContext(&context);

  // Optionally overload the base configuration.
  if (json_config && !core.SetJsonConfig(json_config)) {
    return std::shared_ptr<Service>();
  }
  if (api_key && strlen(api_key)) core.SetApiKey(api_key);
  if (project_id && strlen(project_id)) core.SetProjectId(project_id);

  // Try configuring the gRPC context to check for any errors.
  auto configured_context = core.ConfigureContext(&context);
  if (!configured_context.ok()) {
    LogError("Service connection failed: %s",
             configured_context.status().ToString().c_str());
    return std::shared_ptr<Service>();
  }
  auto service_ptr = services_.LookupChild(core.GetProjectId().c_str());
  if (service_ptr) {
    return service_ptr;
  }
  service_ptr = std::shared_ptr<Service>(new Service());
  services_.AddChild(service_ptr, service_ptr->WeakThis(),
                     core.GetProjectId().c_str());
  return service_ptr;
}

bool Service::SetTemporaryDirectory(const char* temporary_directory) {
  StandardOutputErrorLogger stdout_logger;
  return core::TempFile::SetSystemTemporaryDirectory(
      stdout_logger, std::string(temporary_directory));
}

String Service::GetTemporaryDirectory() {
  return String(core::TempFile::GetSystemTemporaryDirectory().c_str());
}

std::shared_ptr<BrainBase> Service::GetBrain(const char* brain_id,
                                             const char* snapshot_id) {
  std::shared_ptr<BrainBase> brain_ptr = LookupBrain(brain_id,
                                                     typeid(BrainBase).name());
  if (brain_ptr) {
    return brain_ptr;
  }

  falken::common::StatusOr<proto::Brain> brain_or =
      core::FalkenCore::Get().GetBrain(brain_id);
  if (!brain_or.ok()) {
    LogError("Failed to fetch brain %s: %s", brain_id,
             brain_or.status().ToString().c_str());
    return std::shared_ptr<BrainBase>();
  }
  proto::Brain falken_brain = brain_or.ValueOrDie();
  std::unique_ptr<BrainSpecBase> brain_spec =
      BrainSpecProtoConverter::FromBrainSpec(falken_brain.brain_spec());
  if (!brain_spec) {
    return std::shared_ptr<BrainBase>();
  }
  brain_ptr = std::shared_ptr<BrainBase>(new BrainBase(
      WeakThis(), std::move(brain_spec), falken_brain.brain_id().c_str(),
      falken_brain.display_name().c_str(), snapshot_id));
  AddBrain(brain_ptr, typeid(BrainBase).name());
  return brain_ptr;
}

std::shared_ptr<BrainBase> Service::LoadBrain(const char* brain_id,
                                              const char* snapshot_id) {
  return GetBrain(brain_id, snapshot_id);
}

std::shared_ptr<BrainBase> Service::CreateBrain(
    const char* display_name, const BrainSpecBase& brain_spec) {
  const String brain_id = CreateBrainInternal(display_name, brain_spec);
  if (brain_id.empty()) {
    return std::shared_ptr<BrainBase>();
  }
  std::unique_ptr<BrainSpecBase> allocated_brain_spec(
      new BrainSpecBase(brain_spec));
  std::shared_ptr<BrainBase> brain_ptr(
      new BrainBase(WeakThis(), std::move(allocated_brain_spec),
                    brain_id.c_str(), display_name, nullptr));
  AddBrain(brain_ptr, typeid(BrainBase).name());
  return brain_ptr;
}

Vector<std::shared_ptr<BrainBase>> Service::ListBrains() {
  Vector<std::shared_ptr<BrainBase>> brains;
  falken::common::StatusOr<std::vector<proto::Brain>> brain_protos_or =
      core::FalkenCore::Get().ListBrains();
  if (brain_protos_or.ok()) {
    std::vector<proto::Brain>& brain_protos = brain_protos_or.ValueOrDie();
    for (const auto& falken_brain : brain_protos) {
      std::shared_ptr<BrainBase> brain_ptr = LookupBrain(
          falken_brain.brain_id().c_str(), typeid(BrainBase).name());
      if (brain_ptr) {
        brains.push_back(brain_ptr);
      } else {
        std::unique_ptr<BrainSpecBase> brain_spec =
            BrainSpecProtoConverter::FromBrainSpec(falken_brain.brain_spec());
        if (brain_spec) {
          brain_ptr = std::shared_ptr<BrainBase>(
              new BrainBase(WeakThis(), std::move(brain_spec),
                            falken_brain.brain_id().c_str(),
                            falken_brain.display_name().c_str(), nullptr));
          AddBrain(brain_ptr, typeid(BrainBase).name());
          brains.push_back(brain_ptr);
        }
      }
    }
  }
  return brains;
}

std::weak_ptr<Service>& Service::WeakThis() {
  return service_data_->weak_this;
}

void Service::AddBrain(const std::shared_ptr<BrainBase>& brain,
                                    const char* type_id) {
  service_data_->created_brains.AddChild(brain, brain->WeakThis(), brain->id(),
                                         type_id);
}

std::shared_ptr<BrainBase> Service::LookupBrain(
    const char* brain_id, const char* type_id) {
  return service_data_->created_brains.LookupChild(brain_id, type_id);
}

String Service::CreateBrainInternal(const char* display_name,
                                    const BrainSpecBase& brain_spec) {
  falken::common::StatusOr<proto::Brain> falken_brain =
      core::FalkenCore::Get().CreateBrain(
          display_name, BrainSpecProtoConverter::ToBrainSpec(brain_spec));
  return falken_brain.ok() ? falken_brain.ValueOrDie().brain_id().c_str()
                           : String();
}

bool Service::GetAndVerifyBrain(const char* brain_id,
                                const BrainSpecBase& brain_spec,
                                String* display_name) const {
  falken::common::StatusOr<proto::Brain> brain_or =
      core::FalkenCore::Get().GetBrain(brain_id);
  if (!brain_or.ok()) {
    LogError("Failed to fetch brain %s: %s", brain_id,
             brain_or.status().ToString().c_str());
    return false;
  }
  proto::Brain falken_brain = brain_or.ValueOrDie();
  *display_name = falken_brain.display_name().c_str();  // NOLINT
  // Do not use Brain's "MatchesBrainSpec" since that will generate a
  // copy to the falken's brain spec proto.
  return BrainSpecProtoConverter::VerifyBrainSpecIntegrity(
      falken_brain.brain_spec(), brain_spec);
}

}  // namespace falken
