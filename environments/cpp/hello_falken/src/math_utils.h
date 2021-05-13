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

#ifndef HELLO_FALKEN_MATH_H_
#define HELLO_FALKEN_MATH_H_

// Required for Windows to use M_PI.
#define _USE_MATH_DEFINES
#include <math.h>
#include <stdlib.h>

#include <array>

#include "falken/observations.h"

namespace hello_falken {

inline float DegreesToRadians(float degrees) {
  return degrees * (M_PI / 180.f);
}

// Convert a normalized axis and angle to a quaternion.
inline falken::Rotation AxisAngle(falken::Position axis, float degrees) {
  float radians = DegreesToRadians(degrees);
  float s = sin(radians / 2);
  return {s * axis.x, s * axis.y, s * axis.z, cos(radians / 2)};
}

inline float RandomInRange(float min, float max) {
  float random = static_cast<float>(rand()) / static_cast<float>(RAND_MAX);
  float diff = max - min;
  float r = random * diff;
  return min + r;
}

inline float Clamp(float value, float min, float max) {
  return fmin(fmax(value, min), max);
}

class Vec2 {
 public:
  float x;
  float y;

  Vec2() : x(0.f), y(0.f) {}
  Vec2(float x, float y) : x(x), y(y) {}
  Vec2(float angle) : x(cosf(angle)), y(sinf(angle)) {}

  inline Vec2 operator*(float f) const { return Vec2(x * f, y * f); }

  inline Vec2& operator*=(float f) {
    x *= f;
    y *= f;
    return *this;
  }

  inline Vec2 operator-(const Vec2& v) const { return Vec2(x - v.x, y - v.y); }

  inline Vec2 operator-() const { return Vec2(-x, -y); }

  inline Vec2& operator-=(const Vec2& v) {
    x -= v.x;
    y -= v.y;
    return *this;
  }

  inline Vec2& operator+=(const Vec2& v) {
    x += v.x;
    y += v.y;
    return *this;
  }

  inline float MagnitudeSquared() const { return x * x + y * y; }

  inline float Magnitude() const { return sqrt(MagnitudeSquared()); }

  inline float Dot(const Vec2& v) const { return x * v.x + y * v.y; }

  inline void Randomize(float x_range, float y_range) {
    x = RandomInRange(-x_range, x_range);
    y = RandomInRange(-y_range, y_range);
  }
};

// Convert a 2D position as a 3D position on the XZ plane.
inline falken::Position AsXZPosition(const Vec2& pos2d) {
  return falken::Position({pos2d.x, 0, pos2d.y});
}

// Convert a HelloFalken 2D angle to a quaternion specifying a 3D rotation.
inline falken::Rotation HFAngleToQuaternion(float angle) {
  // Falken uses 3D coordinates. We therefore interpret game 2D locations as
  // 3D positions on the XZ plane. We translate a HelloFalken angle into a
  // quaternion that specifies a rotation around the Y-axis. We need to
  // modify the angle in two ways before constructing the quaternion:
  // 1) We need to offset the angle by 90 degrees. This is because Falken
  //    assumes that an object at neutral orientation points towards the
  //    Z-axis, but an object at neutral orientation in HelloFalken points
  //    towards the X-axis.
  // 2) Falken uses a left-handed coordinate system, so rotations around the
  //    Y-axis are clockwise (when looking at the XZ plane from above). Since
  //    angles in HelloFalken are counter-clockwise, we need to negate the
  //    angle.
  float lh_angle_around_y = -angle - 90;
  return AxisAngle({0.0, 1.0, 0.0}, lh_angle_around_y);
}

class Mat4 {
 public:
  std::array<float, 4> data_[4];

  /// @brief Construct a 4x4 matrix of uninitialized values.
  inline Mat4() {}

  /// @brief Create a 4x4 matrix from sixteen floats.
  ///
  /// @param s00 Value of the first row and column.
  /// @param s10 Value of the second row, first column.
  /// @param s20 Value of the third row, first column.
  /// @param s30 Value of the fourth row, first column.
  /// @param s01 Value of the first row, second column.
  /// @param s11 Value of the second row and column.
  /// @param s21 Value of the third row, second column.
  /// @param s31 Value of the fourth row, second column.
  /// @param s02 Value of the first row, third column.
  /// @param s12 Value of the second row, third column.
  /// @param s22 Value of the third row and column.
  /// @param s32 Value of the fourth row, third column.
  /// @param s03 Value of the first row, fourth column.
  /// @param s13 Value of the second row, fourth column.
  /// @param s23 Value of the third row, fourth column.
  /// @param s33 Value of the fourth row and column.
  inline Mat4(float s00, float s10, float s20, float s30, float s01, float s11,
              float s21, float s31, float s02, float s12, float s22, float s32,
              float s03, float s13, float s23, float s33) {
    data_[0] = std::array<float, 4>({s00, s10, s20, s30});
    data_[1] = std::array<float, 4>({s01, s11, s21, s31});
    data_[2] = std::array<float, 4>({s02, s12, s22, s32});
    data_[3] = std::array<float, 4>({s03, s13, s23, s33});
  }

  /// @brief Multiplies two 4x4 matrices.
  ///
  /// @param m The 4x4 matrix.
  /// @return Matrix containing the result.
  Mat4 operator*(const Mat4& m) {
    Mat4 result;
    for (int i = 0; i < 4; ++i) {
      for (int j = 0; j < 4; ++j) {
        result.data_[i][j] = 0.0f;
        for (int k = 0; k < 4; ++k) {
          result.data_[i][j] += this->data_[k][j] * m.data_[i][k];
        }
      }
    }
    return result;
  }

  /// @brief Returns the 4x4 matrix content as a column-first array.
  ///
  /// @return Array containing the result.
  std::array<float, 16> ToArray() {
    std::array<float, 16> result;
    for (int i = 0; i < 4; ++i) {
      for (int j = 0; j < 4; ++j) {
        result[i * 4 + j] = this->data_[i][j];
      }
    }
    return result;
  }

  /// @brief Create a 4x4 translation matrix from a 3-dimensional vector.
  ///
  /// @param v The vector of size 3.
  /// @return Matrix containing the result.
  static inline Mat4 FromTranslationVector(const std::vector<float>& v) {
    return Mat4(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, v[0], v[1], v[2], 1);
  }

  /// @brief Create a 4x4 scale matrix from a 3-dimensional vector.
  ///
  /// @param v The vector of size 3.
  /// @return Matrix containing the result.
  static inline Mat4 FromScaleVector(const std::vector<float>& v) {
    return Mat4(v[0], 0, 0, 0, 0, v[1], 0, 0, 0, 0, v[2], 0, 0, 0, 0, 1);
  }

  /// @brief Create a 4x4 rotation matrix from an angle (in radians) around
  /// the Z axis.
  ///
  /// @param angle Angle (in radians).
  /// @return Matrix containing the result.
  static inline Mat4 FromRotationZ(float angle) {
    return FromRotationZ(Vec2(cosf(angle), sinf(angle)));
  }

  /// @brief Create a 4x4 rotation Matrix from a 2D normalized directional
  /// vector around the Z axis.
  ///
  /// @param v 2D normalized directional vector.
  /// @return Matrix containing the result.
  static inline Mat4 FromRotationZ(const Vec2& v) {
    return Mat4(v.x, v.y, 0, 0, -v.y, v.x, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1);
  }

  /// @brief Create a 4x4 orthographic matrix.
  ///
  /// @param left Left extent.
  /// @param right Right extent.
  /// @param bottom Bottom extent.
  /// @param top Top extent.
  /// @param znear Near plane location.
  /// @param zfar Far plane location.
  /// @param handedness 1.0f for RH, -1.0f for LH
  /// @return Matrix containing the result.
  static inline Mat4 Ortho(float left, float right, float bottom, float top,
                           float znear, float zfar, float handedness = 1) {
    return Mat4(2.0f / (right - left), 0, 0, 0, 0, 2.0f / (top - bottom), 0, 0,
                0, 0, -handedness * 2.0f / (zfar - znear), 0,
                -(right + left) / (right - left),
                -(top + bottom) / (top - bottom),
                -(zfar + znear) / (zfar - znear), 1.0f);
  }
};

}  // namespace hello_falken

#endif /* HELLO_FALKEN_MATH_H_ */
