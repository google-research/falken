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

#include "game.h"

#include <assert.h>
#include <stdio.h>

#include <SDL.h>

#include "gamepad.h"
#include "keyboard.h"

namespace hello_falken {

Game::Game() {
#if defined(__ANDROID__)
  input_device.reset(new Gamepad());
#else
  input_device.reset(new Keyboard());
#endif
}

bool Game::Init(const char* brain_id, const char* snapshot_id, bool vsync) {
  assert(!initialized);

  if (!renderer.Init(vsync)) {
    SDL_Log("Failed to initialize renderer.");
    return false;
  }

  if (!falkenPlayer.Init(brain_id, snapshot_id)) {
    SDL_Log("Falken was unable to initialize correctly.");
    return false;
  }

  Reset(false);

  initialized = true;
  return true;
}

void Game::Update(float delta_time) {
  assert(initialized);

  // Perform standard input, physics, render sequence.
  PlayerInput();
  bool reset_requested =
      falkenPlayer.Update(ship, goal, human_control, forced_evaluation);
  if (reset_requested) {
    Reset(false);
  }

  UpdatePhysics(delta_time);
  renderer.Render(ship, goal);
}

void Game::Shutdown() {
  assert(initialized);

  falkenPlayer.Shutdown();
  renderer.Shutdown();

  initialized = false;
}

void Game::PlayerInput() {
  bool space_pressed = input_device->GetInputState(InputDevice::kChangeControl);
  if (space_pressed && space_pressed != space_was_pressed) {
    human_control = !human_control;
  }
  space_was_pressed = space_pressed;

  bool reset_pressed = input_device->GetInputState(InputDevice::kReset);
  if (reset_pressed && reset_pressed != reset_was_pressed) {
    Reset(false);
  }
  reset_was_pressed = reset_pressed;

  if (input_device->GetInputState(InputDevice::kForceEvaluation)) {
    forced_evaluation = true;
  }

  if (human_control) {
    float steering = 0.f;
    if (input_device->GetInputState(InputDevice::kGoLeft)) {
      steering += 1.f;
    }
    if (input_device->GetInputState(InputDevice::kGoRight)) {
      steering -= 1.f;
    }

    float throttle = 0.f;
    if (input_device->GetInputState(InputDevice::kGoUp)) {
      throttle += 1.f;
    }
    if (input_device->GetInputState(InputDevice::kGoDown)) {
      throttle -= 1.f;
    }

    ship.SetControls(steering, throttle);
  }
}

void Game::UpdatePhysics(float delta_time) {
  ship.Update(renderer, delta_time);

  Vec2 delta = goal.position - ship.position;
  float tolerance = renderer.AbsoluteValue(goal.kSize) * 0.5f;
  if (delta.MagnitudeSquared() <= (tolerance * tolerance)) {
    Reset(true);
  }
}

void Game::Reset(bool success) {
  ship.Reset(renderer);
  goal.Reset(renderer);
  falkenPlayer.Reset(success);
}

}  // namespace hello_falken
