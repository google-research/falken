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

#include "src/core/log.h"

#include "falken/log.h"
#include "src/core/string_logger.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"

namespace falken {
namespace core {

TEST(LogTest, TestLog) {
  testing::StringLogger logger;
  auto system_logger = SystemLogger::Get();
  system_logger->AddLogger(logger);
  system_logger->set_abort_on_fatal_error(false);

  LogDebug("hello %s", "barb");
  EXPECT_EQ(logger.last_log_level(), kLogLevelDebug);
  EXPECT_STREQ(logger.last_message(), "hello barb");

  LogVerbose("hello %s %d", "bob", 123);
  EXPECT_EQ(logger.last_log_level(), kLogLevelVerbose);
  EXPECT_STREQ(logger.last_message(), "hello bob 123");

  LogInfo("the %s train is arriving at %d:%d", "waterloo", 7, 23);
  EXPECT_EQ(logger.last_log_level(), kLogLevelInfo);
  EXPECT_STREQ(logger.last_message(), "the waterloo train is arriving at 7:23");

  LogWarning("%s the gap", "mind");
  EXPECT_EQ(logger.last_log_level(), kLogLevelWarning);
  EXPECT_STREQ(logger.last_message(), "mind the gap");

  LogError("move %s from the %s", "away", "doors");
  EXPECT_EQ(logger.last_log_level(), kLogLevelError);
  EXPECT_STREQ(logger.last_message(), "move away from the doors");

  LogFatal("the %d:%d to %s is delayed due to %s", 5, 45, "bank",
           "an incident");
  EXPECT_EQ(logger.last_log_level(), kLogLevelFatal);
  EXPECT_STREQ(logger.last_message(),
               "the 5:45 to bank is delayed due to an incident");
}

}  // namespace core
}  // namespace falken
