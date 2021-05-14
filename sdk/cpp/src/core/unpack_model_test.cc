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

#include "src/core/unpack_model.h"

#include <cstdio>

#include "src/core/protos.h"
#include "src/core/stdout_logger.h"
#include "src/core/temp_file.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "absl/flags/flag.h"
#include "flatbuffers/util.h"

namespace {

class FalkenStorageTest : public testing::Test {
 protected:
  void SetUp() override {
    tmpdir_ = ::testing::TempDir();
    model_dir_ = flatbuffers::ConCatPathFileName(tmpdir_, "model");
  }

  void TearDown() override {
    falken::StandardOutputErrorLogger logger;
    falken::core::TempFile::Delete(logger, model_dir_);
  }

  std::vector<std::string> filenames_ = {"subdir/subsubdir/file.txt",
                                         "subdir/file2.txt", "file3.txt",
                                         "file4.txt"};

  std::string model_dir_;
  std::string tmpdir_;
};

TEST_F(FalkenStorageTest, TestUnpackModel) {
  falken::proto::SerializedModel model;
  auto files = model.mutable_packed_files_payload()->mutable_files();

  const std::string contents[] = {
    "I am trapped in an alternate universe",
    "and can only communicate through string literals",
    "in unit tests.",
    "send help!",
  };

  for (int i = 0; i < filenames_.size(); ++i) {
    (*files)[filenames_[i]] = contents[i];
  }

  ASSERT_TRUE(falken::core::UnpackModel(model, tmpdir_, "model").ok());

  for (int i = 0; i < 4; ++i) {
    std::string file_content;
    auto path = flatbuffers::ConCatPathFileName(model_dir_, filenames_[i]);
    ASSERT_TRUE(flatbuffers::LoadFile(path.c_str(), false, &file_content));
    EXPECT_EQ(contents[i], file_content);
  }
}

}  // namespace
