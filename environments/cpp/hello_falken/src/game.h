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

#ifndef HELLO_FALKEN_GAME_H_
#define HELLO_FALKEN_GAME_H_

#include <memory>

#include "falken_player.h"
#include "render.h"
#include "ship.h"
#include "input_device.h"

namespace hello_falken {

class Game {
 public:
  // Creates a Game instance.
  Game();

  // Initializes the game and related subsystems.
  bool Init(const char* brain_id,
            const char* snapshot_id,
            bool vsync);
  // Ticks the simulation and performs rendering.
  void Update(float delta_time);
  // Destroys the game and related subsystems.
  void Shutdown();

 private:
  // Converts physical input into ship steering and throttle.
  void PlayerInput();
  // Updates ship physics and checks to see if the game is won.
  void UpdatePhysics(float delta_time);
  // Resets the ship and the goal to random positions.
  void Reset(bool success);

  Renderer renderer;
  FalkenPlayer falkenPlayer;
  Ship ship;
  Goal goal;
  std::unique_ptr<InputDevice> input_device;
  bool human_control = true;
  bool forced_evaluation = false;
  bool space_was_pressed = false;
  bool reset_was_pressed = false;
  bool initialized = false;
};

}  // namespace hello_falken

#endif /* HELLO_FALKEN_GAME_H_ */
