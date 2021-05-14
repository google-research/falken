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

#include "falken/observations.h"

#if _MSC_VER
#define _USE_MATH_DEFINES
#endif  // _MSC_VER
#include <cmath>

#include "falken/attribute.h"
#include "src/core/string_logger.h"
#include "gtest/gtest.h"

namespace {

struct TestObservationWithFeelers : public falken::ObservationsBase {
  TestObservationWithFeelers()
      : FALKEN_FEELERS(feelers, 32, 5.0f, M_PI, 0.0f, true,
                       {"wall", "fruit_stand", "paper_stand", "enemy"}) {}

  falken::FeelersAttribute feelers;
};

struct TestObservationWithJoystick : public falken::ObservationsBase {
  TestObservationWithJoystick()
      : FALKEN_JOYSTICK_DELTA_PITCH_YAW(joystick,
                                        falken::kControlledEntityPlayer) {}
  falken::JoystickAttribute joystick;
};

TEST(ObservationsTest, TestWrongObservationAddedToTheContainer) {
  std::shared_ptr<falken::SystemLogger> logger = falken::SystemLogger::Get();
  logger->set_abort_on_fatal_error(false);
  falken::testing::StringLogger sink;
  EXPECT_TRUE(logger->AddLogger(sink));
  TestObservationWithJoystick observations;
  EXPECT_EQ(sink.last_log_level(), falken::kLogLevelFatal);
  EXPECT_STREQ(sink.last_message(),
               "Can't add attribute joystick to Observations "
               "because it doesn't support type Joystick.");
}

TEST(ObservationsTest, TestWithFeelers) {
  TestObservationWithFeelers observations;
  EXPECT_EQ(observations.feelers.type(), falken::AttributeBase::kTypeFeelers);
}

}  // namespace
