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

#ifndef FALKEN_SDK_CORE_SESSION_INTERNAL_H_
#define FALKEN_SDK_CORE_SESSION_INTERNAL_H_

#include <memory>
#include <string>
#include <vector>

#include "src/core/child_resource_map.h"
#include "src/core/protos.h"
#include "falken/session.h"

namespace falken {

// Private data for the Session class.
struct Session::SessionData {
  SessionData(const std::weak_ptr<BrainBase>& brain_,
              uint32_t total_steps_per_episode_, const char* id_, Type type_,
              uint64_t creation_time_)
      : brain(brain_),
        id(id_),
        total_steps_per_episode(total_steps_per_episode_),
        active_session(total_steps_per_episode > 0),
        type(type_),
        creation_time(creation_time_),
        training_progress(0) {
    switch (type) {
      case kTypeInvalid:
        training_state = falken::Session::TrainingState::kTrainingStateInvalid;
        break;
      case kTypeInteractiveTraining:
        training_state = falken::Session::TrainingState::kTrainingStateTraining;
        break;
      case kTypeInference:
        training_state = falken::Session::TrainingState::kTrainingStateComplete;
        break;
      case kTypeEvaluation:
        training_state =
            falken::Session::TrainingState::kTrainingStateEvaluating;
        break;
    }
  }

  // Brain associated with this session.
  std::shared_ptr<BrainBase> brain;
  // Unique ID of the session.
  const std::string id;
  // Maximum number of steps in each episode created by this session.
  const uint32_t total_steps_per_episode;
  // Whether the session is still active / open.
  bool active_session;
  // Type of session.
  Type type;
  // When the session was created (in milliseconds since the Unix epoch).
  int64_t creation_time;
  // Last training state of the session reported by the service.
  TrainingState training_state;
  // Last training progress value reported by the service.
  float training_progress;
  // Weak pointer to the session object.
  std::weak_ptr<Session> weak_this;
  // Keep track of created brains using this service so we can retrieve
  // shared_ptr's for shared resources.
  ChildResourceMap<Episode> created_episodes;
  std::vector<proto::Episode> episodes;
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_SESSION_INTERNAL_H_
