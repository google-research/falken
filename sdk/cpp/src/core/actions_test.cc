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

#include "falken/actions.h"

#if _MSC_VER
#define _USE_MATH_DEFINES
#endif  // _MSC_VER
#include <cmath>

#include "falken/attribute.h"
#include "src/core/string_logger.h"
#include "gtest/gtest.h"

namespace {

TEST(ActionsTest, TestGetSourceUnmodified) {
  falken::ActionsBase actions;
  EXPECT_EQ(actions.source(), falken::ActionsBase::kSourceInvalid);
}

TEST(ActionsTest, TestGetSourceAfterSet) {
  falken::ActionsBase actions;
  actions.set_source(falken::ActionsBase::kSourceBrainAction);
  EXPECT_EQ(actions.source(), falken::ActionsBase::kSourceBrainAction);
}

struct TestAction : public falken::ActionsBase {
  TestAction() :
      FALKEN_NUMBER(number, 0.0f, 1.0f) {
  }

  falken::NumberAttribute<float> number;
};

struct TestActionWithFeelers : public falken::ActionsBase {
  TestActionWithFeelers()
      : FALKEN_FEELERS(feelers, 32, 5.0f, M_PI, 0.0f, true,
                       {"wall", "fruit_stand", "paper_stand", "enemy"}) {}

  falken::FeelersAttribute feelers;
};

struct TestActionWithJoystick : public falken::ActionsBase {
  TestActionWithJoystick()
      : FALKEN_JOYSTICK_DELTA_PITCH_YAW(joystick,
                                        falken::kControlledEntityPlayer) {}
  falken::JoystickAttribute joystick;
};

TEST(ActionsTest, TestGetSourceAfterAttributeModified) {
  TestAction actions;
  actions.number = 0.5f;
  EXPECT_EQ(actions.source(), falken::ActionsBase::kSourceHumanDemonstration);
}

TEST(ActionsTest, TestWrongActionAddedToTheContainer) {
  std::shared_ptr<falken::SystemLogger> logger = falken::SystemLogger::Get();
  logger->set_abort_on_fatal_error(false);
  falken::testing::StringLogger sink;
  EXPECT_TRUE(logger->AddLogger(sink));
  TestActionWithFeelers actions;
  EXPECT_EQ(sink.last_log_level(), falken::kLogLevelFatal);
  EXPECT_STREQ(sink.last_message(),
               "Can't add attribute feelers to Actions "
               "because it doesn't support type Feelers.");
}

TEST(ActionsTest, TestWithJoystick) {
  TestActionWithJoystick actions;
  actions.set_source(falken::ActionsBase::kSourceNone);
  EXPECT_EQ(actions.source(), falken::ActionsBase::kSourceNone);
}

TEST(ActionsTest, TestGetSourceAfterAttributeModifiedAndSourceSet) {
  TestAction actions;
  actions.number = 0.5f;
  actions.set_source(falken::ActionsBase::kSourceNone);
  EXPECT_EQ(actions.source(), falken::ActionsBase::kSourceNone);
}

TEST(ActionsTest, TestGetSourceAfterModifiedBrainAction) {
  TestAction actions;
  actions.number = 0.5f;
  actions.set_source(falken::ActionsBase::kSourceBrainAction);
  EXPECT_EQ(actions.source(), falken::ActionsBase::kSourceBrainAction);
  actions.number = 0.2f;
  EXPECT_EQ(actions.source(), falken::ActionsBase::kSourceHumanDemonstration);
}

}  // namespace
