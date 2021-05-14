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

#if _MSC_VER
#define _USE_MATH_DEFINES
#endif  // _MSC_VER
#include <cmath>

#include "gmock/gmock.h"
#include "gtest/gtest.h"

namespace falken {
class PrimitivesTest : public ::testing::Test {
 public:
  static Rotation multiply_quaternions(Rotation q1, Rotation q2) {
    return q1 * q2;
  }
  // Tolerance for comparison.
  const float kErrorTolerance = 0.001f;
};
}  // namespace falken

namespace {
using falken::PrimitivesTest;
using falken::Rotation;

// Test conversion from direction vector to quaternion.
TEST_F(PrimitivesTest, TestQuaternionFromDirectionVector) {
  // Normalized vector
  falken::Position angles(0.64f, 0.768f, 0.0f);

  // Convert to quaternion and check.
  auto rotation = Rotation::FromDirectionVector(angles);
  EXPECT_NEAR(rotation.x, -0.299f, kErrorTolerance);
  EXPECT_NEAR(rotation.y, -0.299f, kErrorTolerance);
  EXPECT_NEAR(rotation.z, 0.64f, kErrorTolerance);
  EXPECT_NEAR(rotation.w, 0.64f, kErrorTolerance);
}

// Test Euler angles conversion to quaternion.
TEST_F(PrimitivesTest, TestQuaternionFromEuler) {
  falken::EulerAngles angles(0.6f, 2.3f, 1.5f);

  // Convert to quaternion and check.
  auto rotation = Rotation::FromEulerAngles(angles);
  EXPECT_NEAR(rotation.x, 0.682f, kErrorTolerance);
  EXPECT_NEAR(rotation.y, 0.555f, kErrorTolerance);
  EXPECT_NEAR(rotation.z, 0.068f, kErrorTolerance);
  EXPECT_NEAR(rotation.w, 0.469f, kErrorTolerance);

  // Convert back to euler and check.
  auto converted_angles = Rotation::ToEulerAngles(rotation);
  EXPECT_NEAR(angles.yaw, converted_angles.yaw, kErrorTolerance);
  EXPECT_NEAR(angles.pitch, converted_angles.pitch, kErrorTolerance);
  EXPECT_NEAR(angles.roll, converted_angles.roll, kErrorTolerance);

  falken::EulerAngles angle_1(M_PI_2, 0.0f, 0.0f);
  falken::EulerAngles angle_2(-M_PI_2, 0.0f, 0.0f);
  falken::EulerAngles angle_3(0.0f, M_PI_2, 0.0f);
  falken::EulerAngles angle_4(0.0f, -M_PI_2, 0.0f);
  falken::EulerAngles angle_5(0.0f, 0.0f, M_PI_2);
  falken::EulerAngles angle_6(0.0f, 0.0f, -M_PI_2);

  rotation = Rotation::FromEulerAngles(angle_1);
  EXPECT_NEAR(rotation.x, 0.707f, kErrorTolerance);
  EXPECT_NEAR(rotation.y, 0.0f, kErrorTolerance);
  EXPECT_NEAR(rotation.z, 0.0f, kErrorTolerance);
  EXPECT_NEAR(rotation.w, 0.707f, kErrorTolerance);
  converted_angles = Rotation::ToEulerAngles(rotation);
  EXPECT_NEAR(angle_1.yaw, converted_angles.yaw, kErrorTolerance);
  EXPECT_NEAR(angle_1.pitch, converted_angles.pitch, kErrorTolerance);
  EXPECT_NEAR(angle_1.roll, converted_angles.roll, kErrorTolerance);

  rotation = Rotation::FromEulerAngles(angle_2);
  EXPECT_NEAR(rotation.x, -0.707f, kErrorTolerance);
  EXPECT_NEAR(rotation.y, 0.0f, kErrorTolerance);
  EXPECT_NEAR(rotation.z, 0.0f, kErrorTolerance);
  EXPECT_NEAR(rotation.w, 0.707f, kErrorTolerance);
  converted_angles = Rotation::ToEulerAngles(rotation);
  EXPECT_NEAR(angle_2.yaw, converted_angles.yaw, kErrorTolerance);
  EXPECT_NEAR(angle_2.pitch, converted_angles.pitch, kErrorTolerance);
  EXPECT_NEAR(angle_2.roll, converted_angles.roll, kErrorTolerance);

  rotation = Rotation::FromEulerAngles(angle_3);
  EXPECT_NEAR(rotation.x, 0.0f, kErrorTolerance);
  EXPECT_NEAR(rotation.y, 0.707f, kErrorTolerance);
  EXPECT_NEAR(rotation.z, 0.0f, kErrorTolerance);
  EXPECT_NEAR(rotation.w, 0.707f, kErrorTolerance);
  converted_angles = Rotation::ToEulerAngles(rotation);
  EXPECT_NEAR(angle_3.yaw, converted_angles.yaw, kErrorTolerance);
  EXPECT_NEAR(angle_3.pitch, converted_angles.pitch, kErrorTolerance);
  EXPECT_NEAR(angle_3.roll, converted_angles.roll, kErrorTolerance);

  rotation = Rotation::FromEulerAngles(angle_4);
  EXPECT_NEAR(rotation.x, 0.0f, kErrorTolerance);
  EXPECT_NEAR(rotation.y, -0.707f, kErrorTolerance);
  EXPECT_NEAR(rotation.z, 0.0f, kErrorTolerance);
  EXPECT_NEAR(rotation.w, 0.707f, kErrorTolerance);
  converted_angles = Rotation::ToEulerAngles(rotation);
  EXPECT_NEAR(angle_4.yaw, converted_angles.yaw, kErrorTolerance);
  EXPECT_NEAR(angle_4.pitch, converted_angles.pitch, kErrorTolerance);
  EXPECT_NEAR(angle_4.roll, converted_angles.roll, kErrorTolerance);

  rotation = Rotation::FromEulerAngles(angle_5);
  EXPECT_NEAR(rotation.x, 0.0f, kErrorTolerance);
  EXPECT_NEAR(rotation.y, 0.0f, kErrorTolerance);
  EXPECT_NEAR(rotation.z, 0.707f, kErrorTolerance);
  EXPECT_NEAR(rotation.w, 0.707f, kErrorTolerance);
  converted_angles = Rotation::ToEulerAngles(rotation);
  EXPECT_NEAR(angle_5.yaw, converted_angles.yaw, kErrorTolerance);
  EXPECT_NEAR(angle_5.pitch, converted_angles.pitch, kErrorTolerance);
  EXPECT_NEAR(angle_5.roll, converted_angles.roll, kErrorTolerance);

  rotation = Rotation::FromEulerAngles(angle_6);
  EXPECT_NEAR(rotation.x, 0.0f, kErrorTolerance);
  EXPECT_NEAR(rotation.y, 0.0f, kErrorTolerance);
  EXPECT_NEAR(rotation.z, -0.707f, kErrorTolerance);
  EXPECT_NEAR(rotation.w, 0.707f, kErrorTolerance);
  converted_angles = Rotation::ToEulerAngles(rotation);
  EXPECT_NEAR(angle_6.yaw, converted_angles.yaw, kErrorTolerance);
  EXPECT_NEAR(angle_6.pitch, converted_angles.pitch, kErrorTolerance);
  EXPECT_NEAR(angle_6.roll, converted_angles.roll, kErrorTolerance);
}

// Test quaternion multiplication operator.
TEST_F(PrimitivesTest, TestQuaternionMultiplication) {
  // Convert to quaternion and check.
  Rotation quat_1(0.0f, 1.0f, 0.0f, 1.0f);
  Rotation quat_2(0.5f, 0.5f, 0.75f, 1.0f);

  auto result = multiply_quaternions(quat_1, quat_2);
  EXPECT_NEAR(result.x, 1.25f, kErrorTolerance);
  EXPECT_NEAR(result.y, 1.5f, kErrorTolerance);
  EXPECT_NEAR(result.z, 0.25f, kErrorTolerance);
  EXPECT_NEAR(result.w, 0.5f, kErrorTolerance);
}

}  // namespace
