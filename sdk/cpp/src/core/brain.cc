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

#include "falken/brain.h"

#include <algorithm>
#include <memory>
#include <utility>

#include "src/core/assert.h"
#include "src/core/brain_spec_proto_converter.h"
#include "src/core/child_resource_map.h"
#include "src/core/falken_core.h"
#include "src/core/globals.h"
#include "falken/service.h"
#include "falken/session.h"
#include "falken/types.h"
#include "absl/time/clock.h"
#include "absl/time/time.h"

namespace falken {

namespace {

Session::Type FromSessionType(proto::SessionType session_type) {
  Session::Type type;
  switch (session_type) {
    case proto::SessionType::SESSION_TYPE_UNSPECIFIED:
      type = Session::kTypeInvalid;
      break;
    case proto::SessionType::INTERACTIVE_TRAINING:
      type = Session::kTypeInteractiveTraining;
      break;
    case proto::SessionType::INFERENCE:
      type = Session::kTypeInference;
      break;
    case proto::SessionType::EVALUATION:
      type = Session::kTypeEvaluation;
      break;
    default:
      type = Session::kTypeInvalid;
      break;
  }
  return type;
}

const char* SessionTypeToString(Session::Type type) {
  switch (type) {
    case Session::Type::kTypeInvalid:
      return "Invalid";
    case Session::Type::kTypeInteractiveTraining:
      return "\"Interactive Training\" "
             "(falken::Session::Type::kTypeInteractiveTraining)";
    case Session::Type::kTypeInference:
      return "\"Inference\" (falken::Session::Type::kTypeInference)";
    case Session::Type::kTypeEvaluation:
      return "\"Evaluation\" (falken::Session::Type::kTypeEvaluation)";
    default:
      return "Type does not exist";
  }
}

}  // namespace

struct BrainBase::BrainData {
  // Constructors
  BrainData(const std::shared_ptr<Service>& service,
            BrainSpecBase* brain_spec_base, String id, String display_name,
            String snapshot_id)
      : service(service),
        brain_spec_base(brain_spec_base),
        id(id),
        display_name(display_name),
        snapshot_id(snapshot_id) {}

  BrainData(const std::shared_ptr<Service>& service,
            std::unique_ptr<BrainSpecBase>& allocated_brain_spec_base,
            String id, String display_name, String snapshot_id)
      : service(service),
        allocated_brain_spec_base(std::move(allocated_brain_spec_base)),
        brain_spec_base(this->allocated_brain_spec_base.get()),
        id(id),
        display_name(display_name),
        snapshot_id(snapshot_id) {}

  std::weak_ptr<BrainBase> weak_this;
  // Keep track of created brains using this service so we can retrieve
  // shared_ptr's for shared resources.
  ChildResourceMap<Session> created_sessions;
  std::shared_ptr<Service> service;
  // Allocation when creating a dynamic BrainSpecBase. Mutually exclusive with
  // brain_spec_base_.
  std::unique_ptr<BrainSpecBase> allocated_brain_spec_base;
  // Pointer to a brain spec base. Used for inherited classes from Brain class.
  BrainSpecBase* brain_spec_base;

  String id;
  String display_name;
  // Snapshot id that this brain is using to create sessions.
  // Will be updated when a session finishes and returns a valid snapshot id.
  String snapshot_id;
};

BrainBase::BrainBase(const std::weak_ptr<Service>& service,
                     BrainSpecBase* brain_spec, const char* id,
                     const char* display_name, const char* snapshot_id)
    : brain_data_(
          std::make_unique<BrainData>(service.lock(), brain_spec, id,
                                      display_name ? display_name : String(),
                                      snapshot_id ? snapshot_id : String())) {
  FALKEN_ASSERT(brain_data_->brain_spec_base);
}

BrainBase::BrainBase(const std::weak_ptr<Service>& service,
                     std::unique_ptr<BrainSpecBase> allocated_brain_spec,
                     const char* id, const char* display_name,
                     const char* snapshot_id)
    : brain_data_(
          std::make_unique<BrainData>(service.lock(), allocated_brain_spec, id,
                                      display_name ? display_name : String(),
                                      snapshot_id ? snapshot_id : String())) {}

BrainBase::~BrainBase() {
}

Service& BrainBase::service() const {
  FALKEN_ASSERT_MESSAGE(brain_data_->service,
                        "Associated service has been destroyed for brain %s.",
                        info().c_str());
  return *brain_data_->service;
}

const char* BrainBase::id() const { return brain_data_->id.c_str(); }

const char* BrainBase::display_name() const {
  return brain_data_->display_name.c_str();
}

void BrainBase::UpdateSnapshotId(const char* snapshot_id) {
  brain_data_->snapshot_id = snapshot_id;
}

// Gets a weak_ptr form of this
std::weak_ptr<BrainBase>& BrainBase::WeakThis() {
  return brain_data_->weak_this;
}

void BrainBase::AddSession(const std::shared_ptr<Session>& session) {
  brain_data_->created_sessions.AddChild(session, session->WeakThis(),
                                         session->id(),
                                         (session->IsReadOnly() ? "r" : "rw"));
}

std::shared_ptr<Session> BrainBase::LookupSession(const char* id,
                                                  bool read_only) const {
  return brain_data_->created_sessions.LookupChild(id,
                                                   (read_only ? "r" : "rw"));
}

std::string BrainBase::SessionToKey(const char* id, bool read_only) const {
  return std::string(id) + "/" + (read_only ? "r" : "rw");
}

String BrainBase::info() const {
  return brain_data_->display_name + " (" + brain_data_->id + ")";
}

String BrainBase::BrainInfo() const { return info(); }

const BrainSpecBase& BrainBase::brain_spec_base() const {
  FALKEN_ASSERT(brain_data_->brain_spec_base);
  return *brain_data_->brain_spec_base;
}

BrainSpecBase& BrainBase::brain_spec_base() {
  FALKEN_ASSERT(brain_data_->brain_spec_base);
  return *brain_data_->brain_spec_base;
}

const char* BrainBase::snapshot_id() const {
  return brain_data_->snapshot_id.c_str();
}

std::shared_ptr<Session> BrainBase::StartSession(
    falken::Session::Type type, uint32_t max_steps_per_episode) {
  if (!brain_data_->service) {
    LogError(
        "StartSession failed for brain %s: It's not possible to start a "
        "session as the associated service has been destroyed.",
        info().c_str());
    return std::shared_ptr<Session>();
  }
  proto::SessionSpec session_spec;
  switch (type) {
    case Session::kTypeInvalid:
      LogError(
          "StartSession failed for brain %s since the requested session type "
          "is invalid. Valid session types are %s, %s and %s.",
          info().c_str(),
          SessionTypeToString(Session::kTypeInteractiveTraining),
          SessionTypeToString(Session::kTypeInference),
          SessionTypeToString(Session::kTypeEvaluation));
      return nullptr;
    case Session::kTypeInteractiveTraining:
      session_spec.set_session_type(proto::SessionType::INTERACTIVE_TRAINING);
      break;
    case Session::kTypeInference:
      session_spec.set_session_type(proto::SessionType::INFERENCE);
      break;
    case Session::kTypeEvaluation:
      session_spec.set_session_type(proto::SessionType::EVALUATION);
      break;
  }
  if (!brain_data_->snapshot_id.empty()) {
    session_spec.set_snapshot_id(snapshot_id());
  }
  auto& falken_core = core::FalkenCore::Get();
  session_spec.set_project_id(falken_core.GetProjectId());
  session_spec.set_brain_id(id());
  session_spec.set_max_steps_per_episode(max_steps_per_episode);
  falken::common::StatusOr<proto::Session> session_or =
      falken_core.CreateSession(brain_spec_base(), session_spec);
  if (!session_or.ok()) {
    LogError("Failed to create a new session for brain %s: %s. %s.",
             info().c_str(), session_or.ToString().c_str(), kContactFalkenTeam);
    return std::shared_ptr<Session>();
  }
  proto::Session session_proto = session_or.ValueOrDie();
  if (!session_proto.starting_snapshot_ids().empty()) {
    brain_data_->snapshot_id =
        session_proto.starting_snapshot_ids()[0].c_str();  // NOLINT
  }
  std::shared_ptr<Session> session(new Session(
      brain_data_->weak_this, max_steps_per_episode,
      session_proto.name().c_str(), type, absl::ToUnixMillis(absl::Now())));
  AddSession(session);
  return session;
}

int BrainBase::GetSessionCount() const {
  if (!brain_data_->service) {
    LogError(
        "GetSessionCount failed for brain %s: It's not possible to get the "
        "requested session count as the associated service has been destroyed.",
        info().c_str());
    return 0;
  }
  falken::common::StatusOr<int> count_or =
      core::FalkenCore::Get().GetSessionCount(id());
  if (!count_or.ok()) {
    LogError("Failed to retrieve session count for brain %s: %s. %s.",
             info().c_str(), count_or.ToString().c_str(), kContactFalkenTeam);
    return 0;
  }
  return count_or.ValueOrDie();
}

std::shared_ptr<Session> BrainBase::GetSession(int index) {
  if (!brain_data_->service) {
    LogError(
        "GetSession failed for brain %s: It's not possible to get the "
        "requested session as the associated service has been destroyed.",
        info().c_str());
    return std::shared_ptr<Session>();
  }

  falken::common::StatusOr<proto::Session> session_or =
      core::FalkenCore::Get().GetSession(id(), index);
  if (!session_or.ok()) {
    LogError("Failed to retrieve session with index %d for brain %s: %s. %s.",
             index, info().c_str(), session_or.ToString().c_str(),
             kContactFalkenTeam);
    return std::shared_ptr<Session>();
  }
  proto::Session session_proto = session_or.ValueOrDie();

  std::shared_ptr<Session> session = LookupSession(session_proto.name().c_str(),
                                                   true);
  if (session) {
    return session;
  }

  session = std::shared_ptr<Session>(
      new Session(brain_data_->weak_this, 0, session_proto.name().c_str(),
                  FromSessionType(session_proto.session_type()),
                  absl::ToUnixMillis(absl::Now())));
  AddSession(session);
  return session;
}

std::shared_ptr<Session> BrainBase::GetSession(const char* session_id) {
  if (!brain_data_->service) {
    LogError(
        "GetSession failed for brain %s: It's not possible to get the "
        "requested session as the associated service has been destroyed.",
        info().c_str());
    return std::shared_ptr<Session>();
  }

  std::shared_ptr<Session> session = LookupSession(session_id, true);
  if (session) {
    return session;
  }

  falken::common::StatusOr<proto::Session> session_or =
      core::FalkenCore::Get().GetSession(id(), session_id);
  if (!session_or.ok()) {
    LogError("Failed to retrieve session with id %s for brain %s: %s. %s.",
             session_id, info().c_str(), session_or.ToString().c_str(),
             kContactFalkenTeam);
    return std::shared_ptr<Session>();
  }
  proto::Session session_proto = session_or.ValueOrDie();

  session = std::shared_ptr<Session>(
      new Session(brain_data_->weak_this, 0, session_proto.name().c_str(),
                  FromSessionType(session_proto.session_type()),
                  absl::ToUnixMillis(absl::Now())));
  AddSession(session);
  return session;
}

Vector<std::shared_ptr<Session>> BrainBase::ListSessions() {
  Vector<std::shared_ptr<Session>> sessions;
  falken::common::StatusOr<std::vector<proto::Session>> sessions_or =
      core::FalkenCore::Get().ListSessions(brain_data_->id.c_str());
  if (sessions_or.ok()) {
    const std::vector<proto::Session>& proto_sessions =
        sessions_or.ValueOrDie();
    for (const auto& session_proto : proto_sessions) {
      std::shared_ptr<Session> session_ptr =
          LookupSession(session_proto.name().c_str(), true);
      if (session_ptr) {
        sessions.push_back(session_ptr);
      } else {
        std::shared_ptr<Session> session(new Session(
            brain_data_->weak_this, 0, session_proto.name().c_str(),
            FromSessionType(session_proto.session_type()),
            absl::ToUnixMillis(absl::Now())));
        AddSession(session);
        sessions.push_back(session);
      }
    }
  }
  return sessions;
}

bool BrainBase::MatchesBrainSpec(const BrainSpecBase& brain_spec) const {
  return MatchesBrainSpec(brain_spec_base(), brain_spec);
}

bool BrainBase::MatchesBrainSpec(const BrainSpecBase& brain_spec,
                                 const BrainSpecBase& other_brain_spec) {
  return BrainSpecProtoConverter::VerifyBrainSpecIntegrity(
      BrainSpecProtoConverter::ToBrainSpec(brain_spec), other_brain_spec);
}

}  // namespace falken
