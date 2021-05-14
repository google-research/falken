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

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_PRIMITIVES_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_PRIMITIVES_H_

namespace falken {

/// Generic 3D vector.
struct Vector3 {
  Vector3() {}
  /// Construct a Vector3 from XYZ values.
  ///
  /// @param x_ X coordinate.
  /// @param y_ Y coordinate.
  /// @param z_ Z coordinate.
  Vector3(float x_, float y_, float z_) : x(x_), y(y_), z(z_) {}

  /// x coordinate.
  float x = 0.0f;
  /// y coordinate.
  float y = 0.0f;
  /// z coordinate.
  float z = 0.0f;
};

/// 3D vector that represents the position.
struct Position : public Vector3 {
  Position() {}
  /// Construct a Position from XYZ values.
  ///
  /// @param x_ X coordinate.
  /// @param y_ Y coordinate.
  /// @param z_ Z coordinate.
  Position(float x_, float y_, float z_) : Vector3(x_, y_, z_) {}
};

/// Vector3d for Euler angles.
struct EulerAngles {
  EulerAngles() {}
  /// Construct a Euler vector from roll, pitch and yaw values.
  ///
  /// @param roll_ roll coordinate.
  /// @param pitch_ pitch coordinate.
  /// @param yaw_ yaw coordinate.
  EulerAngles(float roll_, float pitch_, float yaw_)
      : roll(roll_), pitch(pitch_), yaw(yaw_) {}

  /// pitch angle.
  float roll = 0.0f;
  /// roll angle.
  float pitch = 0.0f;
  /// yaw angle.
  float yaw = 0.0f;
};

/// Quaternion for rotation.
struct Rotation {
  friend class PrimitivesTest;

  Rotation() {}
  /// Construct a rotation as a quaternion from XYZW values.
  ///
  /// @param x_ X component.
  /// @param y_ Y component.
  /// @param z_ Z component.
  /// @param w_ W component.
  Rotation(float x_, float y_, float z_, float w_)
      : x(x_), y(y_), z(z_), w(w_) {}

  /// Copy constructor.
  Rotation(const Rotation& other) = default;

  /// Move constructor.
  Rotation(Rotation&&) = default;

  /// Copy assignment operator.
  Rotation& operator=(const Rotation& other) = default;

  /// Create a rotation from a direction vector.
  ///
  /// @param direction Vector with the desired direction to convert. This vector
  ///         must be normalized.
  ///
  /// @return Rotation equivalent to the direction provided.
  static Rotation FromDirectionVector(const Vector3& direction);

  /// Create a rotation from a direction vector
  ///
  /// @param x Component of direction vector.
  /// @param y Component of direction vector.
  /// @param z Component of direction vector.
  ///
  /// @return Rotation equivalent to the direction provided.
  static Rotation FromDirectionVector(float x_, float y_, float z_);

  /// Create a rotation from euler angles.
  /// The conversion follows Body 2-1-3 sequence convention (rotate Pitch, then
  /// Roll and last Yaw). The type of rotation is extrinsic.
  ///
  /// @param angles Euler angles to convert in radians.
  ///
  /// @return Rotation equivalent to the angles provided.
  static Rotation FromEulerAngles(const EulerAngles& angles);

  /// Create a rotation from Euler angles.
  /// The conversion follows Body 2-1-3 sequence convention (rotate Pitch, then
  /// Roll and last Yaw). The type of rotation is extrinsic.
  ///
  /// @param roll Roll angle in radians.
  /// @param pitch Pitch angle in radians.
  /// @param yaw Yaw angle in radians.
  ///
  /// @return Rotation equivalent to the angles provided.
  static Rotation FromEulerAngles(float roll, float pitch, float yaw);

  /// Convert Quaternion to Euler angles.
  ///
  /// @param rotation Rotation to convert
  ///
  /// @return EulerAngles equivalent to the rotation provided.
  static EulerAngles ToEulerAngles(const Rotation& rotation);

  /// x component.
  float x = 0.0f;
  /// y component.
  float y = 0.0f;
  /// z component.
  float z = 0.0f;
  /// w component.
  float w = 1.0f;

 private:
  /// Operator that allows to multiply quaternions.
  Rotation operator*(const Rotation& rhs);
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_PRIMITIVES_H_
