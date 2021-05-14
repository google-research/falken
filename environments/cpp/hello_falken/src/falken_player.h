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

  struct Actions : public falken::ActionsBase {
    Actions()
        : FALKEN_JOYSTICK_DELTA_PITCH_YAW(
              steering, falken::kControlledEntityPlayer),
          FALKEN_NUMBER(throttle, -1.0f, 1.0f) {}

    falken::JoystickAttribute steering;
    falken::NumberAttribute<float> throttle;
  };

  struct Observations : public falken::ObservationsBase {
    Observations() : FALKEN_ENTITY(goal) { }

    falken::EntityBase goal;
  };

  using BrainSpec = falken::BrainSpec<Observations, Actions>;

  std::shared_ptr<falken::Service> service_;
  std::shared_ptr<falken::Brain<BrainSpec>> brain_;
  std::shared_ptr<falken::Session> session_;
  std::shared_ptr<falken::Episode> episode_;

  const int kMaxSteps = 500;
  bool eval_complete_ = false;
};

}  // namespace hello_falken

#endif /* HELLO_FALKEN_PLAYER_H_ */
