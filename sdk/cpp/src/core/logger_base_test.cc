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

#include "src/core/logger_base.h"

#include <stdarg.h>

#include "falken/log.h"
#include "src/core/string_logger.h"
#include "gtest/gtest.h"

namespace falken {

using falken::testing::StringLogger;

TEST(LoggerBaseTest, FormatString) {
  EXPECT_EQ(FormatString("hello %s the answer is %d", "world", 42),
            "hello world the answer is 42");
}

TEST(LoggerBaseTest, LogMessage) {
  StringLogger logger;
  logger.Log(kLogLevelDebug, "a debug message");
  EXPECT_EQ(logger.last_log_level(), kLogLevelDebug);
  EXPECT_STREQ(logger.last_message(), "a debug message");
  logger.Log(kLogLevelInfo, "an informational message");
  EXPECT_EQ(logger.last_log_level(), kLogLevelInfo);
  EXPECT_STREQ(logger.last_message(), "an informational message");
}

TEST(LoggerBaseTest, LogFormatted) {
  StringLogger logger;
  logger.set_log_level(kLogLevelDebug);
  logger.LogDebug("a %s message %d", "debug", 42);
  EXPECT_EQ(logger.last_log_level(), kLogLevelDebug);
  EXPECT_STREQ(logger.last_message(), "a debug message 42");

  logger.LogVerbose("verbose %s", "person");
  EXPECT_EQ(logger.last_log_level(), kLogLevelVerbose);
  EXPECT_STREQ(logger.last_message(), "verbose person");

  logger.LogInfo("%s things", "useful");
  EXPECT_EQ(logger.last_log_level(), kLogLevelInfo);
  EXPECT_STREQ(logger.last_message(), "useful things");

  logger.LogWarning("warning %s %s", "milly", "bobinson");
  EXPECT_EQ(logger.last_log_level(), kLogLevelWarning);
  EXPECT_STREQ(logger.last_message(), "warning milly bobinson");

  logger.LogError("something failed: %s", "bad stuff happened");
  EXPECT_EQ(logger.last_log_level(), kLogLevelError);
  EXPECT_STREQ(logger.last_message(), "something failed: bad stuff happened");

  logger.LogFatal("%s called with invalid args %d, %d", "foo", 12, 32);
  EXPECT_EQ(logger.last_log_level(), kLogLevelFatal);
  EXPECT_STREQ(logger.last_message(), "foo called with invalid args 12, 32");
}

TEST(LoggerBaseTest, FilterLogs) {
  StringLogger logger;
  EXPECT_EQ(logger.log_level(), kLogLevelInfo);
  logger.LogDebug("a message that should be filtered");
  EXPECT_EQ(logger.last_log_level(), kLogLevelFatal);
  EXPECT_STREQ(logger.last_message(), "");

  logger.set_log_level(kLogLevelDebug);
  logger.LogDebug("should see this message");
  EXPECT_EQ(logger.last_log_level(), kLogLevelDebug);
  EXPECT_STREQ(logger.last_message(), "should see this message");
}

}  // namespace falken
