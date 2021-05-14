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

#include "falken/primitives.h"

#include <cmath>

namespace falken {

Rotation Rotation::operator*(const Rotation& rhs) {
  Rotation result;
  result.w = w * rhs.w - x * rhs.x - y * rhs.y - z * rhs.z;
  result.x = w * rhs.x + x * rhs.w + y * rhs.z - z * rhs.y;
  result.y = w * rhs.y - x * rhs.z + y * rhs.w + z * rhs.x;
  result.z = w * rhs.z + x * rhs.y - y * rhs.x + z * rhs.w;
  return result;
}

Rotation Rotation::FromDirectionVector(const Vector3& direction) {
  return FromDirectionVector(direction.x, direction.y, direction.z);
}

Rotation Rotation::FromDirectionVector(float x_, float y_, float z_) {
  float pitch = std::asin(-y_);
  float yaw = std::atan2(x_, z_);
  return FromEulerAngles(0.0f, pitch, yaw);
}

Rotation Rotation::FromEulerAngles(const EulerAngles& angles) {
  return FromEulerAngles(angles.roll, angles.pitch, angles.yaw);
}

Rotation Rotation::FromEulerAngles(float roll, float pitch, float yaw) {
  float halfYaw = yaw * 0.5f;
  float sinYaw = std::sin(halfYaw);
  float cosYaw = std::cos(halfYaw);
  float halfPitch = pitch * 0.5f;
  float sinPitch = std::sin(halfPitch);
  float cosPitch = std::cos(halfPitch);
  float halfRoll = roll * 0.5f;
  float sinRoll = std::sin(halfRoll);
  float cosRoll = std::cos(halfRoll);

  // Create Quaternion representation of the Euler rotations.
  Rotation x_quat(sinRoll, 0.0f, 0.0f, cosRoll);
  Rotation y_quat(0.0f, sinPitch, 0.0f, cosPitch);
  Rotation z_quat(0.0f, 0.0f, sinYaw, cosYaw);

  // Convert to Quaternion using YXZ conversion.
  return y_quat * x_quat * z_quat;
}

EulerAngles Rotation::ToEulerAngles(const Rotation& rotation) {
  EulerAngles angles;

  angles.roll = asin(2 * (rotation.x * rotation.w - rotation.y * rotation.z));
  angles.pitch =
      std::atan2(2 * (rotation.x * rotation.z + rotation.y * rotation.w),
                 (rotation.w * rotation.w - rotation.x * rotation.x -
                  rotation.y * rotation.y + rotation.z * rotation.z));
  angles.yaw = atan2(2 * (rotation.x * rotation.y + rotation.z * rotation.w),
                     (rotation.w * rotation.w - rotation.x * rotation.x +
                      rotation.y * rotation.y - rotation.z * rotation.z));
  return angles;
}

}  // namespace falken
