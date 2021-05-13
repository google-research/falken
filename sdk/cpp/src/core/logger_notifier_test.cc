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

#include <utility>

#include "falken/log.h"
#include "src/core/string_logger.h"
#include "gtest/gtest.h"

namespace falken {

using testing::StringLogger;

// Expose the Notify() method for testing.
class TestLoggerNotifier : public LoggerNotifier {
 public:
  bool Notify(LogLevel log_level, const char* message) const {
    return LoggerNotifier::Notify(log_level, message);
  }
};

void FALKEN_MONO_STDCALL TestCallback(LogLevel log_level, const char* message,
                                      void* context) {
  reinterpret_cast<StringLogger*>(context)->Log(log_level, message);
}

TEST(LoggerNotifier, NotifyEmpty) {
  TestLoggerNotifier notifier;
  notifier.Notify(kLogLevelVerbose, "shouting into the void");
}

TEST(LoggerNotifier, NotifyLogger) {
  TestLoggerNotifier notifier;
  {
    StringLogger logger;
    EXPECT_TRUE(notifier.AddLogger(logger));
    EXPECT_TRUE(notifier.Notify(kLogLevelInfo, "hello"));
    EXPECT_EQ(logger.last_log_level(), kLogLevelInfo);
    EXPECT_STREQ(logger.last_message(), "hello");
    // logger should be removed from notifier here.
  }
  EXPECT_FALSE(notifier.Notify(kLogLevelInfo, "goodbye"));
}

TEST(LoggerNotifier, NotifyMultipleLoggers) {
  TestLoggerNotifier notifier;
  StringLogger logger1;
  StringLogger logger2;
  StringLogger logger3;
  EXPECT_TRUE(notifier.AddLogger(logger1));
  EXPECT_TRUE(notifier.AddLogger(logger2));
  EXPECT_TRUE(notifier.Notify(kLogLevelDebug, "hello"));
  EXPECT_EQ(logger1.last_log_level(), kLogLevelDebug);
  EXPECT_STREQ(logger1.last_message(), "hello");
  EXPECT_EQ(logger2.last_log_level(), kLogLevelDebug);
  EXPECT_STREQ(logger2.last_message(), "hello");
  EXPECT_EQ(logger3.last_log_level(), kLogLevelFatal);
  EXPECT_STREQ(logger3.last_message(), "");

  notifier.RemoveLogger(logger1);
  EXPECT_TRUE(notifier.Notify(kLogLevelWarning, "hello 2"));
  EXPECT_EQ(logger1.last_log_level(), kLogLevelDebug);
  EXPECT_STREQ(logger1.last_message(), "hello");
  EXPECT_EQ(logger2.last_log_level(), kLogLevelWarning);
  EXPECT_STREQ(logger2.last_message(), "hello 2");
}

TEST(LoggerNotifier, DestroyNotifierBeforeLogger) {
  StringLogger logger;
  {
    TestLoggerNotifier notifier;
    notifier.AddLogger(logger);
    // notifier should remove logger here.
  }
}

TEST(LoggerNotifier, AddLoggerMultipleTimes) {
  StringLogger logger;
  TestLoggerNotifier notifier1;
  TestLoggerNotifier notifier2;
  EXPECT_TRUE(notifier1.AddLogger(logger));
  EXPECT_FALSE(notifier2.AddLogger(logger));
  EXPECT_TRUE(notifier1.Notify(kLogLevelWarning, "pixies in the pipes"));
  EXPECT_FALSE(notifier2.Notify(kLogLevelError, "pixies have attacked"));
  EXPECT_EQ(logger.last_log_level(), kLogLevelWarning);
  EXPECT_STREQ(logger.last_message(), "pixies in the pipes");
}

TEST(LoggerNotifier, AddCallback) {
  TestLoggerNotifier notifier;
  StringLogger logger;
  EXPECT_NE(notifier.AddLogCallback(TestCallback, &logger), 0);
  EXPECT_TRUE(notifier.Notify(kLogLevelInfo, "hello callback"));
  EXPECT_EQ(logger.last_log_level(), kLogLevelInfo);
  EXPECT_STREQ(logger.last_message(), "hello callback");
}

TEST(LoggerNotifier, NotifyMultipleCallbacks) {
  TestLoggerNotifier notifier;
  StringLogger logger1;
  StringLogger logger2;
  StringLogger logger3;
  auto handle1 = notifier.AddLogCallback(TestCallback, &logger1);
  EXPECT_NE(handle1, 0);
  auto handle2 = notifier.AddLogCallback(TestCallback, &logger2);
  EXPECT_NE(handle2, 0);
  EXPECT_TRUE(notifier.Notify(kLogLevelInfo, "hello callbacks"));
  EXPECT_EQ(logger1.last_log_level(), kLogLevelInfo);
  EXPECT_STREQ(logger1.last_message(), "hello callbacks");
  EXPECT_EQ(logger2.last_log_level(), kLogLevelInfo);
  EXPECT_STREQ(logger2.last_message(), "hello callbacks");
  EXPECT_EQ(logger3.last_log_level(), kLogLevelFatal);
  EXPECT_STREQ(logger3.last_message(), "");

  notifier.RemoveLogCallback(handle1);
  EXPECT_TRUE(notifier.Notify(kLogLevelWarning, "hello callbacks 2"));
  EXPECT_EQ(logger1.last_log_level(), kLogLevelInfo);
  EXPECT_STREQ(logger1.last_message(), "hello callbacks");
  EXPECT_EQ(logger2.last_log_level(), kLogLevelWarning);
  EXPECT_STREQ(logger2.last_message(), "hello callbacks 2");
}

TEST(LoggerNotifier, Move) {
  TestLoggerNotifier notifier1;
  TestLoggerNotifier notifier2;
  StringLogger logger;

  notifier1.AddLogger(logger);
  EXPECT_FALSE(notifier2.Notify(kLogLevelInfo, "hello2"));
  EXPECT_EQ(logger.last_log_level(), kLogLevelFatal);
  EXPECT_STREQ(logger.last_message(), "");

  EXPECT_TRUE(notifier1.Notify(kLogLevelInfo, "hello1"));
  EXPECT_EQ(logger.last_log_level(), kLogLevelInfo);
  EXPECT_STREQ(logger.last_message(), "hello1");

  notifier2 = std::move(notifier1);
  EXPECT_TRUE(notifier2.Notify(kLogLevelInfo, "moved?"));
  EXPECT_EQ(logger.last_log_level(), kLogLevelInfo);
  EXPECT_STREQ(logger.last_message(), "moved?");
}

}  // namespace falken
