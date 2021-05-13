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

#ifndef FALKEN_SDK_CORE_ACTIVE_SESSION_H_
#define FALKEN_SDK_CORE_ACTIVE_SESSION_H_

#include <map>
#include <memory>
#include <mutex>  // NOLINT(build/c++11)

#include "src/core/statusor.h"
#include "src/core/model.h"
#include "src/core/protos.h"
#include "falken/session.h"
#include "src/core/scheduler.h"
#include "absl/status/status.h"
#include "absl/time/time.h"

#if defined(__APPLE__)
#include "grpc/include/grpcpp/channel.h"
#else
#include "grpc/include/grpcpp/grpcpp.h"
#endif

namespace falken {

class BrainSpecBase;

namespace core {

class ActiveSession;
class SharedAsyncQueueData;

class ActiveEpisode {
 public:
  using EpisodeCompletionCallback =
      std::function<void(const falken::common::StatusOr<proto::SessionInfo>&)>;

  ActiveEpisode(ActiveEpisode&& episode);

  absl::Status Step(BrainSpecBase& brain_spec, proto::Step&& step,
                    Session* session_ptr);

  falken::common::StatusOr<proto::SessionInfo> Close(proto::EpisodeState state,
                                                     Session* session_ptr);

  // Return the automatically generated ID of this episode.
  std::string GetEpisodeId() const;

  proto::EpisodeChunk chunk();

  // Returns the current model ID.
  std::string GetModelId() const;

  static void UpdateSessionState(
      const falken::common::StatusOr<proto::SessionInfo>& session_info_or,
      const std::string& episode_id, Session* session, bool completed_episode);

 private:
  std::recursive_mutex& core_mutex_;

  std::string episode_id_;
  ActiveSession* session_;
  proto::EpisodeChunk chunk_;
  // Current model. This could be shared between multiple episodes.
  std::shared_ptr<Model> model_;
  // Current model id.
  std::string model_id_;

  std::shared_ptr<SharedAsyncQueueData> shared_async_queue_data_;

  absl::Time latest_upload_time_;

  explicit ActiveEpisode(
      std::recursive_mutex& core_mutex, ActiveSession& session,
      std::shared_ptr<Model> model, const std::string& model_id,
      const std::shared_ptr<SharedAsyncQueueData>& shared_async_queue_data);

  // If there is data in the episode, write it out to chunk and reset
  // internal storage of episode.
  bool FlushChunk(proto::EpisodeChunk* output_chunk);

  // Moves the current contents of chunks into the dst_request proto
  // request structure
  void CreateChunkSubmissionsRequest(
      proto::SubmitEpisodeChunksRequest& dst_request);

  // For session types other than evaluation, updates the model from the parent
  // session. Notice that it does not download a model, it just updates the
  // model from the one stored in the session.
  void UpdateModelFromSession();

  // Creates a callback method with and queues it in the ActiveSession shared
  // scheduler. If an episode completion callback is given, executes that after
  // uploading chunks to the service.
  common::StatusOr<proto::SessionInfo> TriggerAsyncUploadToServiceProcess(
      Session* session_ptr, bool completing_episode);

  // ActiveSession is allowed access to the private constructor.
  friend class ActiveSession;
};

class ActiveSession {
 public:
  // Construct and initialize an active session.
  static falken::common::StatusOr<ActiveSession*> Create(
      std::recursive_mutex& core_mutex, const falken::BrainSpecBase& brain_spec,
      const proto::Session& session_proto, const std::string& scratch_directory,
      const std::string& starting_snapshot_id);

  ActiveEpisode* CreateEpisode();

  // Returns episode or nullptr if no one is found.
  ActiveEpisode* GetEpisode(const std::string& episode_id);

  // Returns the current model.
  std::shared_ptr<Model> GetModel() const;

  // Returns the current model ID.
  std::string GetModelId() const;

  const proto::Session session_proto() const;

  // Calls GetModel on the API service and loads the model.
  absl::Status LoadModel(const std::string& model_id);

  // Ensures that any further background tasks finish or get cancelled
  void StopBackgroundTasks(bool synchronous_stop);

  SharedAsyncQueueData* AsyncTasksSharedHandler() {
    return shared_async_queue_data_.get();
  }

 private:
  std::recursive_mutex& core_mutex_;

  // Scratch directory that Falken can write to during a session.
  std::string scratch_directory_;

  // Current session.
  proto::Session session_proto_;

  // Current model.
  std::shared_ptr<Model> model_;

  // Map from episodes to IDs.
  std::map<std::string, ActiveEpisode> episodes_;

  // ID of the current model.
  std::string current_model_id_;

  // Brain spec.
  const falken::BrainSpecBase& brain_spec_;

  std::shared_ptr<SharedAsyncQueueData> shared_async_queue_data_;

  explicit ActiveSession(std::recursive_mutex& core_mutex,
                         const falken::BrainSpecBase& brain_spec,
                         const proto::Session& session_proto,
                         const std::string& scratch_directory,
                         const std::string& starting_snapshot_id);

  // Try to initialize the session.
  absl::Status Initialize();

  // Fetch the model associated with the specified snapshot, cache and
  // start using it in this session.
  absl::Status LoadModelFromSnapshot(const std::string& snapshot_id);

  // Cache the specified model and start using it in this session.
  absl::Status SelectModel(const proto::Model& model);

  friend class ActiveEpisode;
};

// These functions keep track of ActiveSession objects. Once a session is added
// with AddSessionToMap, memory handling for the session is done from
// these functions only (or the OS at program exit).
std::string AddSessionToMap(std::unique_ptr<ActiveSession> session);
ActiveSession* GetSessionFromMap(absl::string_view session_name);
void RemoveSessionFromMap(absl::string_view session_name);

}  // namespace core
}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_ACTIVE_SESSION_H_
