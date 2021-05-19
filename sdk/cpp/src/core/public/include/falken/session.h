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

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_SESSION_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_SESSION_H_

#include <map>
#include <memory>
#include <string>
#include <utility>
#include <vector>

#include "falken/allocator.h"
#include "falken/config.h"
#include "falken/types.h"

namespace falken {

class BrainBase;
class Episode;
class ServiceTest;

namespace core {
class ActiveEpisode;
};

/// A Session represents a period of time during which Falken was learning how
/// to play a game, playing a game, or both.
class FALKEN_EXPORT Session {
  friend class BrainBase;
  friend class Episode;
  friend class ServiceTest;
  friend class core::ActiveEpisode;

 public:
  /// Enum to indicate valid session types.
  enum Type {
    /// An invalid session.
    kTypeInvalid = 0,
    /// An interactive training session.
    kTypeInteractiveTraining = 1,
    /// A session that performs no training.
    kTypeInference = 2,
    /// A session that evaluates models trained in a previous session.
    kTypeEvaluation = 3,
  };
  /// Enum to indicate valid training states.
  enum TrainingState {
    /// Do not use. Internal usage only.
    kTrainingStateInvalid = 0,
    /// There is still training to be completed for this session.
    kTrainingStateTraining,
    /// There is no more work being done for this session.
    kTrainingStateComplete,
    /// Models are being deployed for online evaluation.
    kTrainingStateEvaluating
  };

  /// Stop a session if it's started. Remove reference from the created brain.
  ~Session();

  /// Start an episode if one hasn't been started.
  ///
  /// @return Started episode.
  std::shared_ptr<Episode> StartEpisode();

  /// Check is the session has been stopped.
  ///
  /// @return true if the session has been stopped, false otherwise.
  bool stopped() const;

  /// Wait for all submitted episodes to be processed and stop the session.
  ///
  /// @return A snapshot id that can be used for new sessions. Empty if a
  ///     failure occurs while stopping the session.
  String Stop();

  /// Get the brain that owns this session.
  ///
  /// If the brain was destroyed before this session, this method will assert.
  ///
  /// @return Brain that owns this session.
  BrainBase& brain() const;

  /// Get the session id.
  ///
  /// @return ID of the session.
  const char* id() const;

  /// Get the current session training state.
  ///
  /// @return Training state of the session.
  TrainingState training_state() const;

  /// Get the fraction of training time completed for the current session.
  ///
  /// @return Training progress for the session (a number between 0 and 1).
  float training_progress() const;

  /// Get the session type.
  ///
  /// @return Type of the session.
  Type type() const;

  /// Get the session creation time in milliseconds since the Unix epoch
  /// (see https://en.wikipedia.org/wiki/Unix_time).
  ///
  /// @return Creation time of the session in milliseconds.
  int64_t creation_time() const;

  /// Get session information as a human readable string.
  ///
  /// @return Human readable session information.
  String info() const;

  /// Get the number of episodes in the session.
  ///
  /// @return Number of episodes in the session.
  int GetEpisodeCount() const;

  /// Get a read-only episode by index in the session.
  ///
  /// @param index Episode index.
  /// @return Read-only episode.
  std::shared_ptr<Episode> GetEpisode(int index);

  FALKEN_DEFINE_NEW_DELETE

 private:
  // Start a session.
  Session(const std::weak_ptr<BrainBase>& brain,
          uint32_t total_steps_per_episode, const char* id, Type type,
          uint64_t timestamp);

  String Stop(bool synchronous_stop);

  // Get the session state that would be used for inference.
  // This is an opaque string that changes as the brain learns and ultimately
  // wrapped in a brain snapshot when the session is complete.
  String state() const;
  // Provides a weak_ptr form of this
  std::weak_ptr<Session>& WeakThis();
  // Adds an Episode to created_episodes_ list.
  void AddEpisode(const std::shared_ptr<Episode>& episode);
  // Retrieves an Episode from created_sessions_
  std::shared_ptr<Episode> LookupEpisode(const char* id) const;
  // Get the total number of steps in each episode of this session.
  uint32_t total_steps_per_episode() const;
  // Set the current session training state.
  void set_training_state(TrainingState state);
  /// Set the fraction of training time completed for the current session.
  void set_training_progress(float training_progress);

  FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_START
  // Private data.
  struct SessionData;
  std::unique_ptr<SessionData> data_;
  FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_END

  // Fetch and save session data.
  bool LoadSessionData() const;

  // Return whether the session is read-only.
  bool IsReadOnly() const;

  // Get the ID of the latest trained model in this session.
  std::string model_id() const;
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_SESSION_H_
