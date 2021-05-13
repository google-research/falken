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

#include <string>

#include "falken/log.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "flatbuffers/util.h"

namespace falken {

class FileLoggerTest : public testing::Test {
 protected:
  void SetUp() override {
    // Get the temporary directory.
    std::string tmpdir = ::testing::TempDir();
    ASSERT_NE("", tmpdir);
    // Log to the temporary directory.
    log_filename1_ =
        flatbuffers::ConCatPathFileName(tmpdir, "subdir/test1.log");
    log_filename2_ = flatbuffers::ConCatPathFileName(tmpdir, "/test2.log");
  }

  void TearDown() override {
    // Delete the temporary log files.
    unlink(log_filename1_.c_str());
    unlink(log_filename2_.c_str());
  }

  // Read a log file.
  std::string ReadLog(const std::string& filename) {
    std::string out;
    flatbuffers::LoadFile(filename.c_str(), false, &out);
    return out;
  }

  std::string log_filename1_;
  std::string log_filename2_;
};

TEST_F(FileLoggerTest, TestNoFile) {
  FileLogger logger;
  EXPECT_STREQ(logger.filename().c_str(), "");
}

TEST_F(FileLoggerTest, OpenFile) {
  FileLogger logger;
  EXPECT_TRUE(logger.set_filename(log_filename1_.c_str()));
  EXPECT_STREQ(logger.filename().c_str(), log_filename1_.c_str());
  EXPECT_TRUE(flatbuffers::FileExists(log_filename1_.c_str()));
}

TEST_F(FileLoggerTest, Log) {
  FileLogger logger;
  EXPECT_TRUE(logger.set_filename(log_filename1_.c_str()));
  EXPECT_STREQ(logger.filename().c_str(), log_filename1_.c_str());
  logger.Log(kLogLevelInfo, "hello");
  logger.Log(kLogLevelInfo, "from a test");
  EXPECT_EQ(ReadLog(log_filename1_), "hello\nfrom a test\n");

  EXPECT_TRUE(logger.set_filename(log_filename2_.c_str()));
  EXPECT_STREQ(logger.filename().c_str(), log_filename2_.c_str());
  logger.Log(kLogLevelInfo, "hi");
  logger.Log(kLogLevelInfo, "log file2");
  EXPECT_EQ(ReadLog(log_filename2_), "hi\nlog file2\n");
}

TEST_F(FileLoggerTest, FilterLog) {
  FileLogger logger;
  EXPECT_TRUE(logger.set_filename(log_filename1_.c_str()));
  EXPECT_STREQ(logger.filename().c_str(), log_filename1_.c_str());
  logger.set_log_level(kLogLevelWarning);
  logger.Log(kLogLevelInfo, "hello");
  EXPECT_EQ(ReadLog(log_filename1_), "");
}

TEST_F(FileLoggerTest, LogToNoFile) {
  FileLogger logger;
  logger.Log(kLogLevelInfo, "hello");
  EXPECT_EQ(ReadLog(log_filename1_), "");
}

}  // namespace falken
