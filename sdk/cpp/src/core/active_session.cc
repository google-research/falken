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

#include "src/core/active_session.h"

#include <functional>
#include <memory>
#include <mutex>  // NOLINT(build/c++11)
#include <sstream>
#include <string>

#include "src/core/status_macros.h"
#include "src/core/statusor.h"
#include "src/core/action_proto_converter.h"
#include "src/core/assert.h"
#include "src/core/callback.h"
#include "src/core/falken_core.h"
#include "src/core/grpc_utils.h"
#include "src/core/logger_base.h"
#include "src/core/model.h"
#include "src/core/protos.h"
#include "falken/brain_spec.h"
#include "falken/session.h"
#include "src/core/scheduler.h"
#include "src/core/temp_file.h"
#include "src/core/unpack_model.h"
#include "src/core/uuid4.h"
#include "absl/status/status.h"
#include "absl/time/clock.h"
#include "absl/time/time.h"
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

using absl::Status;
using falken::common::StatusOr;

class SharedAsyncQueueData {
 public:
  using AsyncSubmitReturnValue = common::StatusOr<proto::SessionInfo>;

  void SetLatestEpisodeSubmitReturnStatus(AsyncSubmitReturnValue&& status_or);

  AsyncSubmitReturnValue ScheduleCallbackAndReturn(
      std::unique_ptr<callback::Callback>& callback_ptr,
      bool evaluation_session);

  void StopBackgroundTasks(bool synchronous_stop);

  void ResetTrainingStateIfTrainingCompleted();

 private:
  std::mutex mutex_;
  std::unique_ptr<AsyncSubmitReturnValue> latest_async_return_value_;
  Scheduler scheduler_;
};

namespace {

const absl::Duration kUploadInterval = absl::Seconds(5);

Session::TrainingState SessionInfoStateToTrainingState(
    decltype(proto::SessionInfo().state()) input_state) {
  Session::TrainingState output_state;
  switch (input_state) {
    case proto::SessionInfo::TRAINING_STATE_UNSPECIFIED:
      output_state = Session::kTrainingStateInvalid;
      break;
    case proto::SessionInfo::TRAINING:
      output_state = Session::kTrainingStateTraining;
      break;
    case proto::SessionInfo::COMPLETED:
      output_state = Session::kTrainingStateComplete;
      break;
    case proto::SessionInfo::EVALUATING:
      output_state = Session::kTrainingStateEvaluating;
      break;
    default:
      output_state = Session::kTrainingStateInvalid;
      break;
  }
  return output_state;
}

StatusOr<proto::SessionInfo> SubmitAndLoadModel(
    ActiveSession* session, const proto::SubmitEpisodeChunksRequest& request) {
  FALKEN_ASSIGN_OR_RETURN(proto::SessionInfo session_info,
                          FalkenCore::Get().SubmitEpisodeChunks(request));
  FALKEN_RETURN_IF_ERROR(session->LoadModel(session_info.model_id()));
  return session_info;
}

void BackgroundThreadTask(std::recursive_mutex* core_mutex,
                          ActiveSession* session,
                          proto::SubmitEpisodeChunksRequest& request_message,
                          const std::string& episode_id, Session* session_ptr,
                          bool completing_episode) {
  auto retval = SubmitAndLoadModel(session, request_message);

  std::lock_guard<std::recursive_mutex> lock(*core_mutex);
  ActiveEpisode::UpdateSessionState(retval, episode_id, session_ptr,
                                    completing_episode);

  session->AsyncTasksSharedHandler()->SetLatestEpisodeSubmitReturnStatus(
      std::move(retval));
}

};  // namespace

SharedAsyncQueueData::AsyncSubmitReturnValue
SharedAsyncQueueData::ScheduleCallbackAndReturn(
    std::unique_ptr<callback::Callback>& callback_ptr,
    bool evaluation_session) {
  std::lock_guard<std::mutex> lock(mutex_);
  scheduler_.Schedule(callback_ptr);
  if (!latest_async_return_value_) {
    proto::SessionInfo default_session;
    if (evaluation_session) {
      default_session.set_state(proto::SessionInfo::EVALUATING);
    } else {
      default_session.set_state(proto::SessionInfo::TRAINING);
    }
    default_session.set_training_progress(0.0);
    return default_session;
  }
  return *latest_async_return_value_;
}

void SharedAsyncQueueData::StopBackgroundTasks(bool synchronous_stop) {
  // No need to take the mutex, scheduler is thread safe. In fact,
  // if you grab the mutex here, you get a deadlock if a task
  // was getting executed by the scheduler.
  scheduler_.CancelAllAndShutdownWorkerThread(synchronous_stop);
}

std::string ActiveEpisode::GetEpisodeId() const {
  std::lock_guard<std::recursive_mutex> lock(core_mutex_);
  return episode_id_;
}

// Google's style guide disallows using globals with complex init / destruction.
// We use the fix suggested in go/cpptips/110.md.
// This will never run the destructor, but let the OS remove the data from
// memory at program exit.
std::map<std::string, ActiveSession*>& GetSessionMap() {
  static std::map<std::string, ActiveSession*>* const session_map =
      new std::map<std::string, ActiveSession*>();
  return *session_map;
}

// Once a session is added into the map, memory handling for the session is
// done from Session map functions only (or the OS at program exit).
std::string AddSessionToMap(std::unique_ptr<ActiveSession> session) {
  std::string session_name = session->session_proto().name();
  GetSessionMap()[session_name] = session.release();
  return session_name;
}

ActiveSession* GetSessionFromMap(absl::string_view session_name) {
  std::map<std::string, ActiveSession*>& session_map = GetSessionMap();
  return session_map[std::string(session_name)];
}

void RemoveSessionFromMap(absl::string_view session_name) {
  ActiveSession* active_session = GetSessionFromMap(session_name);
  if (active_session != nullptr) {
    delete active_session;
    GetSessionMap().erase(std::string(session_name));
  }
}

absl::Status ActiveSession::LoadModelFromSnapshot(
    const std::string& snapshot_id) {
  FALKEN_ASSIGN_OR_RETURN(proto::Model model,
                          FalkenCore::Get().GetModelFromSnapshot(
                              session_proto_.brain_id(), snapshot_id));
  return SelectModel(model);
}

absl::Status ActiveSession::LoadModel(const std::string& model_id) {
  if (model_id == current_model_id_) return absl::OkStatus();
  if (model_id.empty()) {
    return absl::InternalError(
        FormatString("Service returned empty model id after returning "
                     "non-empty model ID '%s'",
                     current_model_id_.c_str()));
  }
  // We need to use the lock-less version of GetModel to be able to release
  // the lock around the slow call to GetModel from the service
  FALKEN_ASSIGN_OR_RETURN(proto::Model model,
                          FalkenCore::Get().GetModel(session_proto_, model_id));
  return SelectModel(model);
}

absl::Status ActiveSession::SelectModel(const proto::Model& model) {
  std::string model_id = model.model_id();
  std::string model_subdir =
      model_id + "_" + std::to_string(absl::ToUnixMillis(absl::Now()));
  FALKEN_RETURN_IF_ERROR(
      UnpackModel(model.serialized_model(), scratch_directory_, model_subdir));
  std::string model_path =
      flatbuffers::ConCatPathFileName(scratch_directory_, model_subdir);

  auto status = Model::CreateModel(brain_spec_, model_path);
  TempFile::Delete(*SystemLogger::Get(), model_subdir);
  if (!status.ok()) return status.status();

  std::unique_lock<std::recursive_mutex> lock(core_mutex_);
  model_ = std::move(status.ValueOrDie());
  current_model_id_ = model_id;

  return absl::OkStatus();
}

std::shared_ptr<Model>  // read warning below before updating this
ActiveSession::GetModel() const {
  // This is a public method returning a copy of an internal member, and it
  // assumes that the copy operation of model_ can be executed atomically. If
  // that's not the case you need to acquire the mutex here.

  return model_;
}

std::string ActiveSession::GetModelId() const {
  std::lock_guard<std::recursive_mutex> lock(core_mutex_);
  return current_model_id_;
}

const proto::Session ActiveSession::session_proto() const {
  std::lock_guard<std::recursive_mutex> lock(core_mutex_);
  return session_proto_;
}

ActiveEpisode::ActiveEpisode(ActiveEpisode&& episode)
    : core_mutex_(episode.core_mutex_) {
  // here I should usually take both mutexes, but in this case they are one and
  // the same core mutex used for all FalkenCore, ActiveSessions and
  // ActiveEpisodes
  std::lock_guard<std::recursive_mutex> lock(core_mutex_);
  model_ = std::move(episode.model_);
  model_id_ = std::move(episode.model_id_);
  shared_async_queue_data_ = std::move(episode.shared_async_queue_data_);
  chunk_.Swap(&episode.chunk_);
  episode_id_.swap(episode.episode_id_);
  std::swap(session_, episode.session_);
  latest_upload_time_ = episode.latest_upload_time_;
}

ActiveEpisode::ActiveEpisode(
    std::recursive_mutex& core_mutex, ActiveSession& session,
    std::shared_ptr<Model> model, const std::string& model_id,
    const std::shared_ptr<SharedAsyncQueueData>& shared_async_queue_data)
    : core_mutex_(core_mutex),
      session_(&session),
      model_(model),
      model_id_(model_id),
      shared_async_queue_data_(shared_async_queue_data) {
  episode_id_ = RandUUID4(session.session_proto().name());
  chunk_.set_episode_state(proto::EpisodeState::IN_PROGRESS);
  chunk_.set_episode_id(episode_id_);
  chunk_.set_chunk_id(0);

  latest_upload_time_ = absl::Now();
}

absl::Status ActiveEpisode::Step(BrainSpecBase& brain_spec, proto::Step&& step,
                                 Session* session_ptr) {
  // need to guard chunk_, queued_step and model_ and model_id_
  std::lock_guard<std::recursive_mutex> lock(core_mutex_);

  // If a new model is available, use it.
  UpdateModelFromSession();

  const auto step_call_timestamp_ = absl::Now();
  if ((step_call_timestamp_ - latest_upload_time_) > kUploadInterval) {
    latest_upload_time_ = step_call_timestamp_;
    TriggerAsyncUploadToServiceProcess(session_ptr, false);
  }

  if (chunk_.episode_state() != proto::EpisodeState::IN_PROGRESS) {
    return absl::InternalError("Can't call step on a closed episode.");
  }
  auto& queued_step = *chunk_.add_steps();
  queued_step = std::move(step);
  // If a human demonstration was provided, do not perform inference and reset
  // the training state as the service will restart training.
  if (queued_step.has_action() &&
      queued_step.action().source() == proto::ActionData::HUMAN_DEMONSTRATION) {
    shared_async_queue_data_->ResetTrainingStateIfTrainingCompleted();
    return absl::OkStatus();
  }

  // Try to perform inference...
  if (!model_) {
    queued_step.mutable_action()->set_source(proto::ActionData::NO_SOURCE);
    // Since there is no model set the action source in the developer facing
    // brain object to none.
    brain_spec.actions_base().set_source(ActionsBase::kSourceNone);
    return absl::OkStatus();
  }
  FALKEN_RETURN_IF_ERROR(model_->RunModel(brain_spec));

  *queued_step.mutable_action() =
      ActionProtoConverter::ToActionData(brain_spec.actions_base());
  queued_step.mutable_action()->set_source(proto::ActionData::BRAIN_ACTION);
  // Since we generated an action from a model set the action source in the
  // developer facing to brain action.
  brain_spec.actions_base().set_source(ActionsBase::kSourceBrainAction);

  // The system currently uses the same model for every step in a chunk, but
  // that could change in the future, so we want to stop execution should that
  // behavior change as we'll need to revisit the associated chunk code.
  FALKEN_DEV_ASSERT(chunk_.model_id().empty() ||
                    chunk_.model_id() == model_id_);
  chunk_.set_model_id(model_id_);

  return absl::OkStatus();
}

void ActiveEpisode::CreateChunkSubmissionsRequest(
    proto::SubmitEpisodeChunksRequest& dst_request) {
  const auto& session_proto = session_->session_proto();
  dst_request.set_project_id(session_proto.project_id());
  dst_request.set_brain_id(session_proto.brain_id());
  dst_request.set_session_id(session_proto.name());

  proto::EpisodeChunk chunk;
  if (FlushChunk(&chunk)) {
    *dst_request.add_chunks() = std::move(chunk);
  }
}

void ActiveEpisode::UpdateModelFromSession() {
  // Evaluation sessions need to use the same model throughout an episode,
  // so they don't update the model here.
  if (session_->session_proto().session_type() !=
      proto::SessionType::EVALUATION) {
    auto session_model_id = session_->GetModelId();
    if (model_id_ != session_model_id) {
      // update this episode's model
      model_id_ = session_model_id;
      model_ = session_->GetModel();
    }
  }
}

common::StatusOr<proto::SessionInfo>
ActiveEpisode::TriggerAsyncUploadToServiceProcess(Session* session_ptr,
                                                  bool completing_episode) {
  proto::SubmitEpisodeChunksRequest submit_chunk_request;
  CreateChunkSubmissionsRequest(submit_chunk_request);

  // C++11 does not have capture-by-move for chunk data, so we need to use bind
  // to emulate the feature. Notice that it's safe to hold a copy of session ptr
  // because it outlives the task
  auto async_callback = std::bind(BackgroundThreadTask, &core_mutex_, session_,
                                  std::move(submit_chunk_request), episode_id_,
                                  session_ptr, completing_episode);
  auto callback_ptr = std::unique_ptr<callback::Callback>(
      new callback::CallbackStdFunction(std::function<void()>(async_callback)));
  return shared_async_queue_data_->ScheduleCallbackAndReturn(
      callback_ptr, session_ptr->type() == Session::kTypeEvaluation);
}

StatusOr<proto::SessionInfo> ActiveEpisode::Close(proto::EpisodeState state,
                                                  Session* session_ptr) {
  if (state == proto::EpisodeState::UNSPECIFIED ||
      state == proto::EpisodeState::IN_PROGRESS) {
    return absl::InvalidArgumentError(
        "Cannot close an episode with UNSPECIFIED or IN_PROGRESS");
  }
  if (!chunk_.steps_size() && chunk_.chunk_id() == 0) {
    return absl::FailedPreconditionError("Cannot close an empty episode.");
  }
  chunk_.set_episode_state(state);

  return TriggerAsyncUploadToServiceProcess(session_ptr, true);
}

void SharedAsyncQueueData::ResetTrainingStateIfTrainingCompleted() {
  std::lock_guard<std::mutex> lock(mutex_);
  // will cause the system to assume TRAINING/EVALUATING until new data is
  // received
  if (latest_async_return_value_ && latest_async_return_value_->ok() &&
      (latest_async_return_value_->ValueOrDie().state() ==
       proto::SessionInfo::COMPLETED)) {
    latest_async_return_value_.reset();
  }
}

void SharedAsyncQueueData::SetLatestEpisodeSubmitReturnStatus(
    AsyncSubmitReturnValue&& status_or) {
  std::lock_guard<std::mutex> lock(mutex_);
  latest_async_return_value_ =
      absl::make_unique<AsyncSubmitReturnValue>(std::move(status_or));
}

std::string ActiveEpisode::GetModelId() const {
  std::lock_guard<std::recursive_mutex> lock(core_mutex_);
  return model_id_;
}

proto::EpisodeChunk ActiveEpisode::chunk() {
  std::lock_guard<std::recursive_mutex> lock(core_mutex_);
  return chunk_;
}

bool ActiveEpisode::FlushChunk(proto::EpisodeChunk* output_chunk) {
  std::lock_guard<std::recursive_mutex> lock(core_mutex_);
  if (chunk_.episode_state() == proto::EpisodeState::IN_PROGRESS &&
      chunk_.steps().empty()) {
    return false;
  }

  chunk_.Swap(output_chunk);
  chunk_.Clear();
  chunk_.set_chunk_id(output_chunk->chunk_id() + 1);
  chunk_.set_episode_state(proto::EpisodeState::IN_PROGRESS);
  chunk_.set_episode_id(episode_id_);
  return true;
}

void ActiveEpisode::UpdateSessionState(
    const falken::common::StatusOr<proto::SessionInfo>& session_info_or,
    const std::string& episode_id, Session* session, bool completed_episode) {
  if (session_info_or.ok()) {
    proto::SessionInfo info = session_info_or.ValueOrDie();
    if (completed_episode) {
      LogVerbose("Successfully completed episode %s, model is %s.",
                 episode_id.c_str(), info.model_id().c_str());
    } else {
      LogVerbose(
          "Connected to the service to upload observations/actions and "
          "download model for episode %s, model is %s.",
          episode_id.c_str(), info.model_id().c_str());
    }
    auto training_state = SessionInfoStateToTrainingState(info.state());
    session->set_training_state(training_state);
    session->set_training_progress(info.training_progress());
  } else {
    if (completed_episode) {
      LogError("Failed to complete episode %s: %s", episode_id.c_str(),
               session_info_or.ToString().c_str());
    } else {
      LogError("Failed to upload observations/actions during episode %s: %s",
               episode_id.c_str(), session_info_or.ToString().c_str());
    }
  }
}

ActiveSession::ActiveSession(std::recursive_mutex& core_mutex,
                             const falken::BrainSpecBase& brain_spec,
                             const proto::Session& session_proto,
                             const std::string& scratch_directory,
                             const std::string& starting_snapshot_id)
    : core_mutex_(core_mutex),
      scratch_directory_(scratch_directory),
      session_proto_(session_proto),
      brain_spec_(brain_spec),
      shared_async_queue_data_(std::make_shared<SharedAsyncQueueData>()) {}

StatusOr<ActiveSession*> ActiveSession::Create(
    std::recursive_mutex& core_mutex, const falken::BrainSpecBase& brain_spec,
    const proto::Session& session_proto, const std::string& scratch_directory,
    const std::string& starting_snapshot_id) {
  std::unique_ptr<ActiveSession> new_active_session(
      new ActiveSession(core_mutex, brain_spec, session_proto,
                        scratch_directory, starting_snapshot_id));
  FALKEN_RETURN_IF_ERROR(new_active_session->Initialize());

  ActiveSession* active_session = new_active_session.get();
  AddSessionToMap(::std::move(new_active_session));
  return active_session;
}

absl::Status ActiveSession::Initialize() {
  // We only support resuming from one snapshot right now.
  if (session_proto_.starting_snapshot_ids_size() > 1) {
    return absl::Status(absl::StatusCode::kUnimplemented,
                        "Unable to start a session from multiple snapshots");
  } else if (session_proto_.starting_snapshot_ids_size() == 1) {
    // If we're only resuming from a snapshot, load the associated model.
    FALKEN_RETURN_IF_ERROR(
        LoadModelFromSnapshot(session_proto_.starting_snapshot_ids(0)));
  }
  return absl::OkStatus();
}

ActiveEpisode* ActiveSession::CreateEpisode() {
  ActiveEpisode episode(core_mutex_, *this, model_, current_model_id_,
                        shared_async_queue_data_);
  auto key = episode.GetEpisodeId();
  std::lock_guard<std::recursive_mutex> lock(core_mutex_);
  auto it =
      episodes_.emplace_hint(episodes_.find(key), key, std::move(episode));
  // Return the address of the episode that was just inserted.
  return &it->second;
}

ActiveEpisode* ActiveSession::GetEpisode(const std::string& episode_id) {
  std::lock_guard<std::recursive_mutex> lock(core_mutex_);
  auto result = episodes_.find(episode_id);
  if (result == episodes_.cend()) {
    return nullptr;
  }
  return &result->second;
}

void ActiveSession::StopBackgroundTasks(bool synchronous_stop) {
  // Don't take the mutex here, the shared_async_queue_data object is thread
  // safe.
  shared_async_queue_data_->StopBackgroundTasks(synchronous_stop);
}

}  // namespace core
}  // namespace falken
