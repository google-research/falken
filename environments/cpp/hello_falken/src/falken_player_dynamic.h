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

#ifndef HELLO_FALKEN_PLAYER_H_
#define HELLO_FALKEN_PLAYER_H_

#include "falken/actions.h"
#include "falken/brain.h"
#include "falken/episode.h"
#include "falken/observations.h"
#include "falken/service.h"
#include "falken/session.h"

namespace hello_falken {

class Ship;
class Goal;

// This variant of the FalkenPlayer sets the BrainSpec's observation and action
// attributes at runtime for the BrainSpec.
// Functionally, it is identical to the FalkenPlayer in falken_player.h/cc.
class FalkenPlayer {
 public:
  // Initializes Falken for use in this session
  // Returns false if the initialization failed.
  // Optionally provide brain ID & snapshot ID pair to start with the snapshot.
  bool Init(const char* brain_id, const char* snapshot_id);

  // Updates Falken with new informaion from the player and/or
  // updates the ship with new input from Falken.
  // Returns true if a Reset is requested.
  bool Update(Ship& ship, Goal& goal, bool human_control,
    bool force_evaluation);

  // Completes the current episode and starts a new one.
  void Reset(bool success);

  // Safely disconnects from Falken and cleans up associated resources.
  void Shutdown();

 private:
  void StartEvaluationSession(bool forced_evaluation);
  void StartInferenceSession();
  void StopSession();

  std::shared_ptr<falken::Service> service_;
  std::shared_ptr<falken::BrainBase> brain_;
  std::shared_ptr<falken::Session> session_;
  std::shared_ptr<falken::Episode> episode_;

  const int kMaxSteps = 500;
  bool eval_complete_ = false;
};

}  // namespace hello_falken

#endif /* HELLO_FALKEN_PLAYER_H_ */
