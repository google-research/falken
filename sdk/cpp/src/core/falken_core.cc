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

#include "src/core/falken_core.h"

#include <memory>
#include <mutex>  // NOLINT(build/c++11)
#include <string>
#include <utility>

#include "src/core/status_macros.h"
#include "src/core/statusor.h"
#include "src/core/action_proto_converter.h"
#include "src/core/active_session.h"
#include "src/core/assert.h"
#include "src/core/falken_core_options.h"
#include "src/core/grpc_utils.h"
#include "src/core/log.h"
#include "src/core/protos.h"
#include "falken/brain_spec.h"
#include "src/core/status_converter.h"
#include "src/core/uuid4.h"
#include "absl/status/status.h"
#include "absl/synchronization/mutex.h"
#include "flatbuffers/util.h"

#if defined(__APPLE__)
#include "grpc/include/grpcpp/client_context.h"
#include "grpc/include/grpcpp/create_channel.h"
#include "grpc/include/grpcpp/grpcpp.h"
#include "grpc/include/grpcpp/security/credentials.h"
#else
#include "grpc/include/grpcpp/grpcpp.h"
#endif

namespace falken {
namespace core {

// Protos used by the core library.
using absl::Status;
using falken::common::StatusOr;

namespace {

StatusOr<ActiveEpisode*> GetEpisode(const proto::Session& session,
                                    const std::string& episode_id) {
  ActiveSession* active_session = GetSessionFromMap(session.name());
  if (!active_session) {
    return absl::Status(absl::StatusCode::kInvalidArgument,
                        "Invalid session name.");
  }
  ActiveEpisode* active_episode = active_session->GetEpisode(episode_id);
  if (!active_episode) {
    return absl::Status(absl::StatusCode::kInvalidArgument,
                        "Invalid episode id.");
  }
  return active_episode;
}

}  // namespace

FalkenCore::FalkenCore() {
  SetServiceEnvironment(ServiceEnvironment::kProd);
  SetSessionScratchDirectory(std::string());
}

bool FalkenCore::SetJsonConfig(const char* json_config) {
  LogDebug("Set JSON config");
  loaded_json_config_ = true;
  return FalkenCoreOption::SetOptionsFromJson(this, GetFalkenCoreOptions(),
                                              json_config);
}

std::string FalkenCore::GetJsonConfig() const {
  return FalkenCoreOption::GetOptionsAsJson(*this, GetFalkenCoreOptions());
}

bool FalkenCore::LoadJsonConfig(const char* filename) {
  std::string json;
  bool default_filename = filename == nullptr;
  filename = filename ? filename : "falken_config.json";
  if (default_filename) {
    LogVerbose("No JSON config file path set, trying default path %s",
               filename);
  } else {
    LogVerbose("Loading JSON config from %s", filename);
  }
  if (!flatbuffers::LoadFile(filename, false, &json)) {
    if (!default_filename) {
      LogWarning("Failed to load JSON config file %s", filename);
    } else {
      LogVerbose("No config found at default location %s", filename);
    }
    return false;
  } else {
    LogDebug("Successfully loaded JSON config file %s", filename);
  }
  return SetJsonConfig(json.c_str());
}

proto::grpc_gen::FalkenService::Stub* FalkenCore::GetService() {
  std::lock_guard<std::recursive_mutex> lock(mutex_);
  if (!stub_ || requested_service_grpc_channel_params_.address !=
                    connected_service_grpc_channel_params_.address) {
    LogVerbose(
        "FalkenCore::GetService() connecting to new channel '%s' --> '%s'",
        connected_service_grpc_channel_params_.address.c_str(),
        requested_service_grpc_channel_params_.address.c_str());
    stub_ = CreateChannel(requested_service_grpc_channel_params_);
    connected_service_grpc_channel_params_ =
        requested_service_grpc_channel_params_;
    if (stub_) {
      LogVerbose("FalkenCore::GetService() connected to '%s'",
                 requested_service_grpc_channel_params_.address.c_str());
    }
  }
  if (!stub_) {
    LogError(
        "Unable to connect to FalkenPrivateService using the address "
        "%s. Check if the address is correct. %s.",
        requested_service_grpc_channel_params_.address.c_str(),
        kContactFalkenTeam);
    return nullptr;
  }
  return stub_.get();
}

falken::common::StatusOr<grpc::ClientContext*> FalkenCore::ConfigureContext(
    grpc::ClientContext* context) {
  std::chrono::system_clock::time_point deadline =
      std::chrono::system_clock::now() +
      std::chrono::milliseconds(timeout_millis_);
  static bool log_initialized = false;
  // This uses FalkenCore::Log() to initialize the log sink.
  if (!log_initialized) {
    LogDebug("Configuring Falken Context");
    log_initialized = true;
  }
  if (!loaded_json_config_) {
    LoadJsonConfig();
    // Don't try loading the default configuration again.
    loaded_json_config_ = true;
  }
  context->set_deadline(deadline);
  if (GetApiKey().empty() || GetProjectId().empty()) {
    return absl::UnauthenticatedError(
        "Must set API key and project ID before calling Falken APIs. If you "
        "don't have them or the error persist please contact falken support "
        "team.");
  } else {
    context->AddMetadata(grpc::string(kApiKeyMetadataKey), api_key_);
  }
  return context;
}

// If the supplied gRPC status is an error, convert to an absl::Status,
// log an error and return the status. If the gRPC status is ok, call
// the supplied function and return the return value.
template <typename T>
static StatusOr<T> ParseResultIfStatusOk(
    const char* rpc_name, grpc::Status&& status,
    const std::function<T()>& parse_result) {
  if (!status.ok()) {
    LogError("%s failed with status: %s.", rpc_name,
             status.error_message().c_str());
    return MakeStatusFromGrpcStatus(status);
  }
  return parse_result();
}

StatusOr<proto::Brain> FalkenCore::CreateBrain(
    const std::string& display_name, const proto::BrainSpec& brain_spec) {
  grpc::ClientContext context;
  FALKEN_ASSIGN_OR_RETURN(auto configured_context, ConfigureContext(&context));
  proto::CreateBrainRequest request;
  request.set_project_id(GetProjectId());
  *request.mutable_brain_spec() = brain_spec;
  request.set_display_name(display_name);

  proto::Brain brain;
  return ParseResultIfStatusOk<proto::Brain>(
      "CreateBrain",
      FalkenCore::GetService()->CreateBrain(configured_context, request,
                                            &brain),
      [&brain]() { return brain; });
}

StatusOr<proto::Brain> FalkenCore::GetBrain(const std::string& brain_id) {
  grpc::ClientContext context;
  FALKEN_ASSIGN_OR_RETURN(auto configured_context, ConfigureContext(&context));
  proto::GetBrainRequest request;
  request.set_project_id(GetProjectId());
  request.set_brain_id(brain_id);

  proto::Brain brain;
  return ParseResultIfStatusOk<proto::Brain>(
      "GetBrain",
      FalkenCore::GetService()->GetBrain(configured_context, request, &brain),
      [&brain]() { return brain; });
}

falken::common::StatusOr<std::vector<proto::Brain>> FalkenCore::ListBrains() {
  proto::ListBrainsRequest request;
  proto::ListBrainsResponse response;

  request.set_project_id(GetProjectId());
  const int kPageSize = 1000;
  request.set_page_size(kPageSize);

  std::vector<proto::Brain> brains;
  do {
    grpc::ClientContext context;
    FALKEN_ASSIGN_OR_RETURN(auto configured_context,
                            ConfigureContext(&context));
    grpc::Status status = FalkenCore::GetService()->ListBrains(
        configured_context, request, &response);
    if (!status.ok()) {
      return MakeStatusFromGrpcStatus(status);
    }
    brains.insert(brains.end(), response.brains().begin(),
                  response.brains().end());
    request.set_page_token(response.next_page_token());
  } while (response.brains_size() > 0);

  return brains;
}

void FalkenCore::SetSessionScratchDirectory(const std::string& scratch) {
  scratch_dir_ = absl::make_unique<TempFile>(
      *SystemLogger::Get(), "falken_scratch", true /* create_directory */);
  scratch_dir_->SetTemporaryDirectory(scratch);
}

const std::string& FalkenCore::GetSessionScratchDirectory() const {
  return scratch_dir_->GetTemporaryDirectory();
}

StatusOr<proto::Session> FalkenCore::CreateSession(
    BrainSpecBase& brain_spec, const proto::SessionSpec& session_spec) {
  proto::CreateSessionRequest request;
  *request.mutable_spec() = session_spec;
  request.set_project_id(GetProjectId());
  proto::Session session;

  grpc::ClientContext context;
  FALKEN_ASSIGN_OR_RETURN(auto configured_context, ConfigureContext(&context));
  grpc::Status session_status = FalkenCore::GetService()->CreateSession(
      configured_context, request, &session);

  if (!session_status.ok()) {
    return MakeStatusFromGrpcStatus(session_status);
  }

  std::lock_guard<std::recursive_mutex> lock(mutex_);

  if (!scratch_dir_->Create()) {
    return absl::InternalError(
        "Unable to create temporary scratch directory "
        "under " +
        scratch_dir_->GetTemporaryDirectory());
  }

  auto created_session =
      ActiveSession::Create(mutex_, brain_spec, session, scratch_dir_->path(),
                            session_spec.snapshot_id());
  if (!created_session.ok()) return created_session.status();

  return session;
}

StatusOr<int> FalkenCore::GetSessionCount(const std::string& brain_id) {
  proto::GetSessionCountRequest request;
  request.set_project_id(GetProjectId());
  request.set_brain_id(brain_id);
  proto::GetSessionCountResponse response;

  grpc::ClientContext context;
  FALKEN_ASSIGN_OR_RETURN(auto configured_context, ConfigureContext(&context));
  return ParseResultIfStatusOk<int>(
      "GetSessionCount",
      FalkenCore::GetService()->GetSessionCount(configured_context, request,
                                                &response),
      [&response]() { return response.session_count(); });
}

falken::common::StatusOr<proto::Session> FalkenCore::GetSession(
    const std::string& brain_id, const std::string& session_id) {
  proto::GetSessionRequest request;
  request.set_project_id(GetProjectId());
  request.set_brain_id(brain_id);
  request.set_session_id(session_id);
  proto::Session session;

  grpc::ClientContext context;
  FALKEN_ASSIGN_OR_RETURN(auto configured_context, ConfigureContext(&context));
  return ParseResultIfStatusOk<proto::Session>(
      "GetSession",
      FalkenCore::GetService()->GetSession(configured_context, request,
                                           &session),
      [&session]() { return session; });
}

falken::common::StatusOr<proto::Session> FalkenCore::GetSession(
    const std::string& brain_id, int session_index) {
  proto::GetSessionByIndexRequest request;
  request.set_project_id(GetProjectId());
  request.set_brain_id(brain_id);
  request.set_session_index(session_index);
  proto::Session session;

  grpc::ClientContext context;
  FALKEN_ASSIGN_OR_RETURN(auto configured_context, ConfigureContext(&context));
  return ParseResultIfStatusOk<proto::Session>(
      "GetSessionByIndex",
      FalkenCore::GetService()->GetSessionByIndex(configured_context, request,
                                                  &session),
      [&session]() { return session; });
}

falken::common::StatusOr<std::vector<proto::Session>> FalkenCore::ListSessions(
    const std::string& brain_id) {
  proto::ListSessionsRequest request;
  proto::ListSessionsResponse response;

  request.set_project_id(GetProjectId());
  request.set_brain_id(brain_id);
  const int kPageSize = 100;
  request.set_page_size(kPageSize);

  std::vector<proto::Session> sessions;
  do {
    grpc::ClientContext context;
    FALKEN_ASSIGN_OR_RETURN(auto configured_context,
                            ConfigureContext(&context));
    grpc::Status status = FalkenCore::GetService()->ListSessions(
        configured_context, request, &response);
    if (!status.ok()) {
      return MakeStatusFromGrpcStatus(status);
    }
    sessions.insert(sessions.end(), response.sessions().begin(),
                    response.sessions().end());
    request.set_page_token(response.next_page_token());
  } while (response.sessions_size() > 0);

  return sessions;
}

StatusOr<std::string> FalkenCore::StopSession(const proto::Session& session,
                                              bool synchronous_stop) {
  std::unique_lock<std::recursive_mutex> lock(mutex_);
  ActiveSession* active_session = GetSessionFromMap(session.name());
  if (!active_session) {
    return absl::Status(absl::StatusCode::kInvalidArgument,
                        "Unable to stop the session named " + session.name() +
                            ". Invalid session name. Check the session name. " +
                            kContactFalkenTeam);
  }

  // Release the lock to allow active background tasks to be flushed, and the
  // remaining ones to be cancelled. This is not fully thread safe, since a
  // background thread could be started before we take back the lock, but if
  // the user side is single-threaded, then this is safe.
  lock.unlock();
  active_session->StopBackgroundTasks(synchronous_stop);
  lock.lock();

  proto::StopSessionResponse session_resp;
  proto::StopSessionRequest request;
  *request.mutable_session() = active_session->session_proto();
  request.set_project_id(active_session->session_proto().project_id());

  grpc::ClientContext context;
  FALKEN_ASSIGN_OR_RETURN(auto configured_context, ConfigureContext(&context));
  return ParseResultIfStatusOk<std::string>(
      "StopSession",
      FalkenCore::GetService()->StopSession(configured_context, request,
                                            &session_resp),
      [&session, &session_resp]() {
        RemoveSessionFromMap(session.name());
        return session_resp.snapshot_id();
      });
}

StatusOr<std::vector<proto::Episode>> FalkenCore::GetSessionEpisodes(
    const std::string& brain_id, const std::string& session_id) {
  proto::ListEpisodeChunksResponse resp;
  proto::ListEpisodeChunksRequest request;

  request.set_project_id(GetProjectId());
  request.set_brain_id(brain_id);
  request.set_session_id(session_id);

  // Retrieve one chunk at a time to minimize the chances that we request
  // more data than we are allowed to request over gRPC.
  // b/156519662 is required to guarantee that chunks are never too large.
  request.set_page_size(1);
  std::vector<proto::EpisodeChunk> episode_chunks;
  do {
    grpc::ClientContext context;
    FALKEN_ASSIGN_OR_RETURN(auto configured_context,
                            ConfigureContext(&context));
    grpc::Status session_status = FalkenCore::GetService()->ListEpisodeChunks(
        configured_context, request, &resp);
    if (!session_status.ok()) {
      return MakeStatusFromGrpcStatus(session_status);
    }
    for (const auto& chunk : resp.episode_chunks()) {
      episode_chunks.push_back(chunk);
    }
    request.set_page_token(resp.next_page_token());
  } while (resp.episode_chunks_size() > 0);

  // Combine EpisodeChunks into developer-friendly Episodes
  std::vector<proto::Episode> episodes;
  std::string current_episode_id = "";
  proto::Episode* current_episode = nullptr;
  for (const auto& chunk : episode_chunks) {
    if (chunk.episode_id() != current_episode_id) {
      episodes.push_back(proto::Episode());
      current_episode = &(episodes.back());
      current_episode->set_episode_id(chunk.episode_id());
      current_episode_id = chunk.episode_id();
    }
    if (current_episode != nullptr) {
      current_episode->mutable_steps()->MergeFrom(chunk.steps());
      current_episode->set_final_state(chunk.episode_state());
    }
  }

  return episodes;
}

StatusOr<proto::SessionInfo> FalkenCore::SubmitEpisodeChunks(
    const proto::SubmitEpisodeChunksRequest& request) {
  proto::SessionInfo session_info;
  proto::SubmitEpisodeChunksResponse resp;
  grpc::ClientContext context;
  FALKEN_ASSIGN_OR_RETURN(auto configured_context, ConfigureContext(&context));
  return ParseResultIfStatusOk<proto::SessionInfo>(
      "SubmitEpisodeChunks",
      FalkenCore::GetService()->SubmitEpisodeChunks(configured_context, request,
                                                    &resp),
      [&resp]() { return resp.session_info(); });
}

StatusOr<proto::Model> FalkenCore::GetModel(const proto::Session& session,
                                            const std::string& model_id) {
  proto::GetModelRequest request;
  request.set_project_id(GetProjectId());
  request.set_brain_id(session.brain_id());
  request.set_model_id(model_id);
  return GetModel(request);
}

StatusOr<proto::Model> FalkenCore::GetModel(
    const proto::GetModelRequest& request) {
  grpc::ClientContext context;
  FALKEN_ASSIGN_OR_RETURN(auto configured_context, ConfigureContext(&context));
  proto::Model model;
  return ParseResultIfStatusOk<proto::Model>(
      "GetModel",
      FalkenCore::GetService()->GetModel(configured_context, request, &model),
      [&model]() { return model; });
}

StatusOr<proto::Model> FalkenCore::GetModelFromSnapshot(
    const std::string& brain_id, const std::string& snapshot_id) {
  proto::GetModelRequest request;
  request.set_project_id(GetProjectId());
  request.set_brain_id(brain_id);
  request.set_snapshot_id(snapshot_id);
  return GetModel(request);
}

StatusOr<std::string> FalkenCore::CreateEpisode(const proto::Session& session) {
  std::lock_guard<std::recursive_mutex> lock(mutex_);
  ActiveSession* active_session = GetSessionFromMap(session.name());
  if (!active_session) {
    return absl::Status(absl::StatusCode::kInvalidArgument,
                        "Unable to create an episode for the session " +
                            session.name() +
                            ". Invalid session name. Check "
                            "the session name. " +
                            kContactFalkenTeam);
  }
  ActiveEpisode* episode = active_session->CreateEpisode();
  return episode->GetEpisodeId();
}

Status FalkenCore::StepEpisode(BrainSpecBase& brain_spec,
                               const proto::Session& session,
                               const std::string& episode_id,
                               proto::Step&& step,
                               Session* session_ptr) {
  std::lock_guard<std::recursive_mutex> lock(mutex_);
  FALKEN_ASSIGN_OR_RETURN(ActiveEpisode * episode,
                          GetEpisode(session, episode_id));
  return episode->Step(brain_spec, std::move(step), session_ptr);
}

// Closes the session with the appropriate state. State cannot be
// IN_PROGRESS or UNDEFINED.
StatusOr<proto::SessionInfo> FalkenCore::FinishEpisode(
    const proto::Session& session, const std::string& episode_id,
    const proto::EpisodeState state, Session* session_ptr) {
  std::lock_guard<std::recursive_mutex> lock(mutex_);
  FALKEN_ASSIGN_OR_RETURN(ActiveEpisode * episode,
                          GetEpisode(session, episode_id));
  return episode->Close(state, session_ptr);
}

proto::Session FalkenCore::ToSession(const std::string& session_name,
                                     const std::string& brain_id,
                                     const std::string& snapshot_id) {
  proto::Session session;
  if (!snapshot_id.empty()) {
    session.add_starting_snapshot_ids(snapshot_id);
  }
  session.set_project_id(GetProjectId());
  session.set_brain_id(brain_id);
  session.set_name(session_name);
  return session;
}

std::string FalkenCore::GetEpisodeModelId(const proto::Session& session,
                                          const std::string& episode_id) const {
  return GetEpisode(session, episode_id).ValueOrDie()->GetModelId();
}

}  // namespace core
}  // namespace falken
