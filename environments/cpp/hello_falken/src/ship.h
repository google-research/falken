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

#ifndef HELLO_FALKEN_SHIP_H_
#define HELLO_FALKEN_SHIP_H_

#include "math_utils.h"
#include "render.h"

namespace hello_falken {

class Ship {
 public:
  Vec2 position;
  float rotation = 0.f;
  static const float kSize;

  // Sets new values for steering and throttle
  void SetControls(float steering, float throttle);
  // Updates the position and orientation of the ship
  void Update(const Renderer& renderer, float delta_time);
  // Moves ship to random position and rotation
  // Zeroes out steering, throttle, and velocity
  void Reset(const Renderer& renderer);

  float GetSteering() const { return steering; }
  float GetThrottle() const { return throttle; }

  Vec2 GetForward() const { return Vec2(DegreesToRadians(rotation)); }
  Vec2 GetRight() const {
    Vec2 forward = GetForward();
    return Vec2(forward.y, -forward.x);
  }

 private:
  float steering = 0.f;
  float throttle = 0.f;
  Vec2 velocity;
  float angular_velocity = 0.f;
};

class Goal {
 public:
  Vec2 position;
  static const float kSize;

  // Moves goal to random position
  void Reset(const Renderer& renderer);
};

}  // namespace hello_falken

#endif /* HELLO_FALKEN_SHIP_H_ */
