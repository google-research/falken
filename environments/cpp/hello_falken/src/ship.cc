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

#include "ship.h"

#include "render.h"

namespace hello_falken {

// Ship and goal sizes relative to the smallest screen dimension.
const float Ship::kSize = 0.0625f;
const float Goal::kSize = 0.1042f;

void Ship::SetControls(float steering, float throttle) {
  this->steering = steering;
  this->throttle = throttle;
}

void Ship::Update(const Renderer& renderer, float delta_time) {
  // The max acceleration applied by the throttle
  static const float kMaxThrottle = renderer.AbsoluteValue(104.17f);
  // the max accelerationa applied by steering
  static const float kMaxSteering = 2000.f;
  // The max velocity of the ship
  static const float kMaxVelocity = renderer.AbsoluteValue(1.25f);
  // The rate at which ship velocity decays
  static const float kVelocityDecay = 3.f;
  // The max angular velocity of the ship
  static const float kMaxAngularVelocity = 300.f;
  // The rate at which ship angular velocity decays
  static const float kAngularDecay = 5.f;

  // Apply steering
  angular_velocity += steering * kMaxSteering * delta_time;
  // Decay gradually slows rotation
  angular_velocity -= angular_velocity * kAngularDecay * delta_time;
  // Ensure we don't exceed our max angular velocity
  angular_velocity =
      Clamp(angular_velocity, -kMaxAngularVelocity, kMaxAngularVelocity);
  // Apply angular veloicty to rotation
  rotation += angular_velocity * delta_time;

  // Apply thrust
  float playerAcceleration = throttle * kMaxThrottle * delta_time;
  Vec2 impulse(DegreesToRadians(rotation));
  impulse *= playerAcceleration * delta_time;
  velocity += impulse;
  // Decay gradually slows the ship down
  velocity -= velocity * kVelocityDecay * delta_time;
  // Ensure we don't exceed our max velocity
  float velocity_mag_sq = velocity.MagnitudeSquared();
  if (velocity_mag_sq > (kMaxVelocity * kMaxVelocity)) {
    float scale = kMaxVelocity / sqrtf(velocity_mag_sq);
    velocity *= scale;
  }
  // Apply velocity to position
  position += velocity * delta_time;

  // Ensure the ship stays inside the screen.
  float safe_width = renderer.SafeX(renderer.AbsoluteValue(kSize));
  position.x = Clamp(position.x, -safe_width, safe_width);
  float safe_height = renderer.SafeY(renderer.AbsoluteValue(kSize));
  position.y = Clamp(position.y, -safe_height, safe_height);
}

void Ship::Reset(const Renderer& renderer) {
  position.Randomize(renderer.SafeX(renderer.AbsoluteValue(kSize)),
                     renderer.SafeY(renderer.AbsoluteValue(kSize)));
  rotation = RandomInRange(0.f, 360.f);
  steering = 0.f;
  throttle = 0.f;
  velocity.x = 0.f;
  velocity.y = 0.f;
  angular_velocity = 0.f;
}

void Goal::Reset(const Renderer& renderer) {
  position.Randomize(renderer.SafeX(renderer.AbsoluteValue(kSize)),
                     renderer.SafeY(renderer.AbsoluteValue(kSize)));
}

}  // namespace hello_falken
