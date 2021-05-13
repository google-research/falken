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

#ifndef FALKEN_SDK_CORE_FALKEN_CORE_H_
#define FALKEN_SDK_CORE_FALKEN_CORE_H_

#include <stdint.h>

#include <memory>
#include <mutex>  // NOLINT(build/c++11)
#include <string>

#include "src/core/statusor.h"
#include "src/core/grpc_utils.h"
#include "src/core/protos.h"
#include "falken/log.h"
#include "falken/session.h"
#include "src/core/service_environment.h"
#include "src/core/temp_file.h"
#include "absl/memory/memory.h"
#include "absl/status/status.h"

namespace falken {

class BrainSpecBase;

namespace core {

// Key for the grpc sidechannel which is parsed by the Falken's service to
// authenticate requests.
static const char kApiKeyMetadataKey[] = "x-goog-api-key";

constexpr int64_t kDelayMillis = 30000;

// Singleton that implements the Core SDK functions by calling the Falken
// Private API.
class FalkenCore {
 public:
  using EpisodeCompletionCallback =
      std::function<void(const falken::common::StatusOr<proto::SessionInfo>&)>;

  static FalkenCore& Get() {
    static auto* const kInstance = new FalkenCore();
    return *kInstance;
  }

  // Configure the core using a JSON config in the following format:
  //
  // {
  //   // Public configuration options.
  //   // These options are publicly documented and used to configure the
  //   // service by a developer.
  //
  //   // API key string used to connect to the Falken service.
  //   // This defaults to an empty string so must be set via this configuration
  //   // or the SetApiKey() method.
  //   "api_key: "API_KEY",
  //
  //   // Project ID used to connect to the Falken service.
  //   // This defaults to an empty string so must be set via this configuration
  //   // or the SetProjectId() method.
  //   "project_id": "PROJECT_ID",
  //
  //   // Internal configuration options.
  //   // These options are for testing *only* and should not be exposed in
  //   // external documentation or used by external developers.
  //
  //   // Timeout for API calls to the Falken service. This defaults to
  //   // kDelayMillis (30s / 30000ms).
  //   "api_call_timeout_milliseconds": TIMEOUT,
  //
  //   // Path to a temporary directory for session data.
  //   // By default this is an empty string which causes the SDK to store
  //   // session data under the system temporary directory.
  //   "session_data_dir": "DIRECTORY",
  //
  //   // Path to a file to write logs.
  //   // If this is not specified logs are written to the system temporary
  //   // directory. If this is an empty string, logging to a file is disabled.
  //   // NOTE: This log file is shared across the entire SDK, the most recent
  //   // configuration of this value will set where the logs are written.
  //   "log_file": "PATH",
  //
  //   // Log verbosity configuration. This can be one of
  //   // ("debug", "verbose", "info", "warning", "error", "fatal") where
  //   // debug is the most verbose debugging and fatal is the least.
  //   // By default this is "info".
  //   "log_level": "LEVEL",
  //
  //   // Falken service connection configuration.
  //.  // IMPORTANT: Order matters.
  //   "service": {
  //     // ENV Can be "local" (an instance running localhost) , "dev"
  //     // the development instance of the service, or "prod" the production
  //     // instance of the service. This is an alias for the address to connect
  //     // to the Falken service that can be manually configured using the
  //     // "service_address" option. This defaults to "prod".
  //     "environment": "ENV",
  //     // Attributes of the service connection.
  //     "connection: {
  //       // Custom service address to connect to. This overrides
  //       // the value set by "environment" and defaults to the "prod" service
  //       "address": "ADDRESS",
  //       // SSL certificate string or string list used to authenticate the
  //       // connection to the service. If this isn't provided, connections to
  //       // the "local" environment use certs in the embedded data structure
  //       // local_grpc_roots. Authentication to other environments use certs
  //       // in the embedded data structure public_grpc_roots.
  //       "ssl_certificate": [
  //         "LINE0",
  //         "LINE1",
  //         // ...
  //         "LINEN"
  //       ],
  //       // SSL target name override for the gRPC channel. If this is a local
  //       // connection, ssl_certificate is empty and this value is empty this
  //       // defaults to kTestLocalPemCertName (test_cert_2).
  //       "ssl_target_name": "TARGET_NAME"
  //     }
  //   },
  //
  // }
  // This method is not thread safe, and should not be called when there
  // are active sessions.
  bool SetJsonConfig(const char* json_config);

  // Get the configuration as a JSON string.
  std::string GetJsonConfig() const;

  // Load the JSON configuration from a file.
  // This method is not thread safe, and should not be called when there
  // are active sessions.
  bool LoadJsonConfig(const char* filename = nullptr);

  // Specifies how long to wait for API calls before timing out.
  // These methods are not thread safe, and should not be called when there
  // are active sessions.
  void SetApiCallTimeout(int64_t timeout_millis) {
    timeout_millis_ = timeout_millis;
  }
  int64_t GetApiCallTimeout() const { return timeout_millis_; }

  // Set the service environment to connect to.
  // These methods are not thread safe, and should not be called when there
  // are active sessions.
  void SetServiceEnvironment(ServiceEnvironment env) {
    requested_service_grpc_channel_params_ =
        ServiceEnvironmentToGrpcChannelParameters(env);
  }
  ServiceEnvironment GetServiceEnvironment() const {
    return ServiceEnvironmentFromGrpcChannelParameters(
        requested_service_grpc_channel_params_);
  }

  // Set the service gRPC channel parameters.
  // These methods are not thread safe, and should not be called when there
  // are active sessions.
  void SetServiceGrpcChannelParameters(const GrpcChannelParameters& params) {
    requested_service_grpc_channel_params_ = params;
  }
  const GrpcChannelParameters& GetServiceGrpcChannelParameters() const {
    return requested_service_grpc_channel_params_;
  }

  // Set the key to use for all subsequent API calls.
  // These methods are not thread safe, and should not be called when there
  // are active sessions.
  void SetApiKey(absl::string_view api_key) { api_key_ = std::string(api_key); }
  const std::string& GetApiKey() const { return api_key_; }

  // Set the project ID to use for all subsequent API calls.
  // This method is not thread safe, and should not be called when there
  // are active sessions.
  void SetProjectId(absl::string_view project_id) {
    project_id_ = std::string(project_id);
  }

  // This method is not thread safe, and should not be called when there
  // are active sessions.
  const std::string& GetProjectId() const { return project_id_; }

  // Set scratch directory for sessions, if this is empty the system
  // temporary directory is used.
  // This method is not thread safe, and should not be called when there
  // are active sessions.
  void SetSessionScratchDirectory(const std::string& scratch);

  // This method is not thread safe, and should not be called when there
  // are active sessions.
  const std::string& GetSessionScratchDirectory() const;

  // Creates the Brain instance based on the supplied BrainSpec.
  falken::common::StatusOr<proto::Brain> CreateBrain(
      const std::string& display_name, const proto::BrainSpec& brain_spec);

  // Gives full details of a Brain from the ID.
  falken::common::StatusOr<proto::Brain> GetBrain(const std::string& brain_id);

  // Returns the Brains for this project.
  falken::common::StatusOr<std::vector<proto::Brain>> ListBrains();

  // Begins the process of training or running a brain.
  // Returns a session which can be Stepped and Stopped.
  falken::common::StatusOr<proto::Session> CreateSession(
      BrainSpecBase& brain_spec, const proto::SessionSpec& session_spec);

  // Returns the number of sessions associated with a brain.
  falken::common::StatusOr<int> GetSessionCount(const std::string& brain_id);

  // Returns a session proto from a session id.
  falken::common::StatusOr<proto::Session> GetSession(
      const std::string& brain_id, const std::string& session_id);

  // Returns a session proto from an index.
  falken::common::StatusOr<proto::Session> GetSession(
      const std::string& brain_id, int session_index);

  // Returns the Sessions created by the specified Brain.
  falken::common::StatusOr<std::vector<proto::Session>> ListSessions(
      const std::string& brain_id);

  // Terminates this session.
  // Returns a snapshot id that can be used for new sessions. Can be empty.
  falken::common::StatusOr<std::string> StopSession(
      const proto::Session& session, bool synchronous_stop);

  // Returns all Steps in all Episodes for the specified Session
  falken::common::StatusOr<std::vector<proto::Episode>> GetSessionEpisodes(
      const std::string& brain_id, const std::string& session_id);

  // Adds the given episode chunks to the session. Returns the SessionInfo if
  // successful.
  falken::common::StatusOr<proto::SessionInfo> SubmitEpisodeChunks(
      const proto::SubmitEpisodeChunksRequest& request);

  falken::common::StatusOr<proto::Model> GetModel(const proto::Session& session,
                                                  const std::string& model_id);

  falken::common::StatusOr<proto::Model> GetModel(
      const proto::GetModelRequest& request);

  falken::common::StatusOr<proto::Model> GetModelFromSnapshot(
      const std::string& brain_id, const std::string& snapshot_id);

  // DRAFT INTERFACE FOR EPISODE BASED ACCESS:

  // Create a new episode associated with a session and returns its id.
  falken::common::StatusOr<std::string> CreateEpisode(
      const proto::Session& session);

  // Requests an action from the server, given an observation.
  // If step.action is set, that same action is returned.
  absl::Status StepEpisode(BrainSpecBase& brain_spec,
                           const proto::Session& session,
                           const std::string& episode_id, proto::Step&& step,
                           Session* session_ptr);

  // Closes the session with the appropriate state. State cannot be
  // IN_PROGRESS or UNDEFINED.
  // Returns SessionInfo if available.
  falken::common::StatusOr<proto::SessionInfo> FinishEpisode(
      const proto::Session& session, const std::string& episode_id,
      const proto::EpisodeState state, Session* session_ptr);

  // Configure a GRPC client context.
  falken::common::StatusOr<grpc::ClientContext*> ConfigureContext(
      grpc::ClientContext* context);

  std::string GetEpisodeModelId(const proto::Session& session,
                                const std::string& episode_id) const;

  // Utility method to construct a session proto.
  proto::Session ToSession(const std::string& session_name,
                           const std::string& brain_id,
                           const std::string& snapshot_id);

 private:
  FalkenCore();

  // Non-blocking implementations for GetModel, meant to be used from
  // context that already owns the core mutex, to allow taking it more
  // than once and being able to release it around the call to the
  // GetModel service
  falken::common::StatusOr<proto::Model> GetModelImpl(
      std::unique_lock<std::recursive_mutex>& lock,
      const proto::Session& session, const std::string& model_id);
  falken::common::StatusOr<proto::Model> GetModelImpl(
      std::unique_lock<std::recursive_mutex>& lock,
      const proto::GetModelRequest& request);

  // protection against concurrent access from user facing and from
  // active session/episode
  std::recursive_mutex mutex_;

  // Whether a JSON config file has been loaded.
  // This is used to only load the configuration from the default search
  // location once.
  bool loaded_json_config_ = false;

  // Notice that the stub can change later if the connection is
  // reset to a different service address. Don't store the pointer to the
  // stub and instead call GetService() on each use.
  proto::grpc_gen::FalkenService::Stub* GetService();

  std::string api_key_;
  std::string project_id_;
  std::unique_ptr<TempFile> scratch_dir_;
  int64_t timeout_millis_ = kDelayMillis;
  std::string last_error_msg_;
  GrpcChannelParameters requested_service_grpc_channel_params_;
  GrpcChannelParameters connected_service_grpc_channel_params_;
  std::unique_ptr<proto::grpc_gen::FalkenService::Stub> stub_ = nullptr;

  // Required to give access to ActiveSession to lock-less GetModel methods.
  friend class ActiveSession;
};

}  // namespace core
}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_FALKEN_CORE_H_
