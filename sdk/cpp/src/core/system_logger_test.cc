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

#include <stdio.h>
#include <stdlib.h>

#include <memory>
#include <regex>  // NOLINT(build/c++11)
#include <string>

#include "falken/log.h"
#include "src/core/string_logger.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "flatbuffers/util.h"

namespace falken {

using testing::StringLogger;

class SystemLoggerTest : public ::testing::Test {
 protected:
  void SetUp() override {
    // Get the temporary directory.
    std::string tmpdir = ::testing::TempDir();
    ASSERT_NE("", tmpdir);
    // Log to the temporary directory.
    log_filename_ = flatbuffers::ConCatPathFileName(tmpdir, "test.log");

    logger_ = SystemLogger::Get();
    if (default_log_filename_.empty()) {
      default_log_filename_ =
          logger_->file_logger().filename().c_str();  // NOLINT
    }
  }

  void TearDown() override {
    // Delete the temporary log files.
    unlink(log_filename_.c_str());
    // Reset the system logger state.
    logger_->file_logger().set_filename("");
    logger_->set_log_level(kLogLevelInfo);
    std::remove(log_filename_.c_str());
  }

  // Read a log file.
  std::string ReadLog() {
    std::string out;
    flatbuffers::LoadFile(log_filename_.c_str(), false, &out);
    return out;
  }

  std::shared_ptr<SystemLogger> logger_;
  std::string log_filename_;
  static std::string default_log_filename_;
};

std::string SystemLoggerTest::default_log_filename_;  // NOLINT

TEST_F(SystemLoggerTest, CreatesTemporaryLogFile) {
  EXPECT_TRUE(flatbuffers::FileExists(default_log_filename_.c_str())) <<
      "Log filename: " << default_log_filename_;
}

TEST_F(SystemLoggerTest, LogToFile) {
  logger_->file_logger().set_filename(log_filename_.c_str());
  logger_->LogInfo("hello");
  EXPECT_EQ(ReadLog(), "[Falken] INFO: hello\n");
}

#if defined(FALKEN_ABSL_LOGGING)
TEST_F(SystemLoggerTest, LogToFileFromAbsl) {
  logger_->file_logger().set_filename(log_filename_.c_str());
  LOG(INFO) << "hello from absl";
  std::regex regex(".*hello from absl\n");
  EXPECT_TRUE(std::regex_match(ReadLog(), regex));
}
#endif  // defined(FALKEN_ABSL_LOGGING)

TEST_F(SystemLoggerTest, AbortOnFatalDisabled) {
  logger_->file_logger().set_filename(log_filename_.c_str());
  logger_->set_abort_on_fatal_error(false);
  logger_->LogFatal("do not blow up");
  EXPECT_EQ(ReadLog(), "[Falken] FATAL: do not blow up\n");
}

TEST_F(SystemLoggerTest, AbortOnFatal) {
  EXPECT_DEATH_IF_SUPPORTED(logger_->LogFatal("termination"), ".*");
}

TEST_F(SystemLoggerTest, NotifyLastLog) {
  StringLogger sink;
  EXPECT_TRUE(logger_->AddLogger(sink));
  logger_->LogDebug("hello");
  EXPECT_EQ(sink.last_log_level(), kLogLevelDebug);
  EXPECT_STREQ(sink.last_message(), "hello");
}

TEST_F(SystemLoggerTest, NotifyMultipleLogs) {
  StringLogger sink;
  EXPECT_TRUE(logger_->AddLogger(sink));
  logger_->LogDebug("I'm a debug log");
  logger_->LogWarning("I'm a warning log");
  logger_->LogError("I'm an error log");

  std::vector<std::pair<LogLevel, std::string>> expected_logs{
      {kLogLevelFatal, ""},
      {kLogLevelDebug, "I'm a debug log"},
      {kLogLevelWarning, "I'm a warning log"},
      {kLogLevelError, "I'm an error log"}};

  EXPECT_EQ(sink.logs().size(), 4);
  for (int i = 0; i < 4; ++i) {
    EXPECT_EQ(sink.logs().at(i), expected_logs.at(i));
  }

  EXPECT_EQ(sink.last_log_level(), kLogLevelError);
  EXPECT_STREQ(sink.last_message(), "I'm an error log");
}

TEST_F(SystemLoggerTest, CheckFindLog) {
  StringLogger sink;
  EXPECT_TRUE(logger_->AddLogger(sink));
  logger_->LogDebug("I'm a debug log");
  logger_->LogWarning("I'm a warning log");
  logger_->LogError("I'm an error log");

  ASSERT_NE(sink.FindLog(kLogLevelWarning, "I'm a warning log"), nullptr);
  EXPECT_EQ(sink.FindLog(kLogLevelWarning, "I'm a warning log")->first,
            kLogLevelWarning);
  EXPECT_EQ(sink.FindLog(kLogLevelWarning, "I'm a warning log")->second,
            "I'm a warning log");
  ASSERT_NE(sink.FindLog(kLogLevelWarning, "I'm a.*log"), nullptr);
  EXPECT_EQ(sink.FindLog(kLogLevelWarning, "I'm a.*log")->first,
            kLogLevelWarning);
  EXPECT_EQ(sink.FindLog(kLogLevelWarning, "I'm a.*log")->second,
            "I'm a warning log");

  // Level and message mismatch.
  EXPECT_EQ(sink.FindLog(kLogLevelDebug, "I'm a warning log"), nullptr);
  // Non-existent level.
  EXPECT_EQ(sink.FindLog(kLogLevelInfo, "I'm a debug log"), nullptr);
  // Non-existent log.
  EXPECT_EQ(sink.FindLog(kLogLevelDebug, "I'm a non-existent log"), nullptr);
}

TEST_F(SystemLoggerTest, PersistNotifier) {
  StringLogger sink;
  EXPECT_TRUE(logger_->AddLogger(sink));
  logger_ = nullptr;
  logger_ = SystemLogger::Get();
  logger_->LogDebug("hello");
  EXPECT_EQ(sink.last_log_level(), kLogLevelDebug);
  EXPECT_STREQ(sink.last_message(), "hello");
}

TEST_F(SystemLoggerTest, PersistLogLevel) {
  logger_->set_log_level(kLogLevelWarning);
  logger_ = nullptr;
  logger_ = SystemLogger::Get();
  EXPECT_EQ(logger_->log_level(), kLogLevelWarning);
}

TEST_F(SystemLoggerTest, PersistFilename) {
  logger_->file_logger().set_filename("falken");
  logger_ = nullptr;
  logger_ = SystemLogger::Get();
  EXPECT_EQ(logger_->file_logger().filename(), "falken");
}

TEST_F(SystemLoggerTest, VersionInformation) {
  StringLogger sink;

  EXPECT_TRUE(logger_->AddLogger(sink));
  logger_->set_log_level(kLogLevelVerbose);
  logger_ = nullptr;
  logger_ = SystemLogger::Get();
  EXPECT_EQ(sink.last_log_level(), kLogLevelVerbose);
  std::string log_version = sink.last_message();
#if !defined(NDEBUG)
  std::regex regex(
      "Falken SDK: Version ([0-9]+)\\.([0-9]+)\\.([0-9]+) \\(CL: "
      "[a-zA-Z0-9_]+, Commit: [0-9a-f]{2,40}, (Debug|Release|Nightly)\\)");
  EXPECT_TRUE(std::regex_match(log_version, regex));
#else
  EXPECT_EQ(log_version, "Falken SDK: Version 1.2.3 (CL: 5, Commit: 12)");
#endif
}

}  // namespace falken
