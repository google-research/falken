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

#include "src/core/temp_file.h"

#include <stdio.h>
// Required for chdir().
#ifdef _MSC_VER
#include <direct.h>
#include <stdlib.h>
#else
#include <unistd.h>
#endif  // _MSC_VER

#include "src/core/stdout_logger.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "flatbuffers/util.h"

using testing::Not;
using testing::EndsWith;
using testing::HasSubstr;

namespace falken {
namespace core {

class TempFileTest : public testing::Test {
 protected:
  void SetUp() override {
    // Use a portable method to get the temporary directory.
    char* tmpdir = getenv("TEST_TMPDIR");
    if (tmpdir) {
      // Change the working directory to the temporary directory to simplify
      // test cases.
      chdir(tmpdir);

#if _MSC_VER
      // Windows tests on Forge can't write to the system temporary directory
      // so override the system temporary directory. TMP is checked first by
      // GetTempPath() to get the temporary path for the process.
      char* cwd = getcwd(nullptr, 1024);
      ASSERT_NE(nullptr, cwd);
      std::string settmp = std::string("TMP=") + cwd;
      EXPECT_EQ(putenv(settmp.c_str()), 0);
      free(cwd);
#endif  //  _MSC_VER
    }
  }

  // Create a test file.
  void CreateFile(const std::string& filename) {
    std::string contents("hello");
    std::string directory = flatbuffers::StripFileName(filename);
    EXPECT_TRUE(TempFile::CreateDir(directory));
    EXPECT_TRUE(flatbuffers::SaveFile(filename.c_str(), filename.c_str(),
                                      filename.size(), false));
  }

  // Determine whether two paths end with the same components.
  // i.e ensure that a/b/c/d.txt ends with c/d.txt.
  void PathsEndWithSameComponents(const std::string& enclosing_path,
                                  const std::string& enclosed_path) {
    auto enclosing = flatbuffers::PosixPath(enclosing_path.c_str());
    auto enclosed = flatbuffers::PosixPath(enclosed_path.c_str());
    EXPECT_EQ(enclosed.substr(enclosed.size() - enclosing.size()), enclosing);
  }

  StandardOutputErrorLogger logger_;
};

TEST_F(TempFileTest, DeleteDirectory) {
  for (auto& it : { "foo/bar/test.txt", "foo/test.txt", "foo/bar.txt" }) {
    CreateFile(it);
  }
  TempFile::Delete(logger_, "foo");
  EXPECT_FALSE(flatbuffers::DirExists("foo"));
}

TEST_F(TempFileTest, CreateAndCleanUpFile) {
  std::string temp_filename;
  {
    std::string directory("foo/bar");
    TempFile temp(logger_, directory);
    EXPECT_FALSE(temp.exists());
    EXPECT_TRUE(temp.path().empty());

    EXPECT_TRUE(temp.Create());
    EXPECT_FALSE(temp.exists());

    temp_filename = temp.path();
    EXPECT_THAT(temp_filename, EndsWith(directory));
    EXPECT_THAT(temp_filename, Not(HasSubstr("XXXXXX")));
    CreateFile(temp_filename);
    EXPECT_TRUE(temp.exists());
  }
  EXPECT_FALSE(flatbuffers::FileExists(temp_filename.c_str()));
}

TEST_F(TempFileTest, CreateAndLeaveFile) {
  std::string temp_directory;
  std::string temp_filename;
  {
    std::string directory("foo/bar");
    TempFile temp(logger_, directory, false, false /* delete_on_destruction */);
    EXPECT_FALSE(temp.exists());
    EXPECT_TRUE(temp.path().empty());

    EXPECT_TRUE(temp.Create());
    EXPECT_FALSE(temp.exists());

    temp_filename = temp.path();
    EXPECT_THAT(temp_filename, EndsWith(directory));
    EXPECT_THAT(temp_filename, Not(HasSubstr("XXXXXX")));
    CreateFile(temp_filename);
    EXPECT_TRUE(temp.exists());

    temp_directory = temp.GetTemporaryDirectory();
    EXPECT_FALSE(temp_directory.empty());
  }
  EXPECT_TRUE(flatbuffers::FileExists(temp_filename.c_str()));
  TempFile::Delete(logger_, temp_directory);
}

TEST_F(TempFileTest, CreateAndCleanUpDirectory) {
  std::string temp_filename;
  {
    std::string directory("foo/bar");
    TempFile temp(logger_, directory, true /* create directory */);
    EXPECT_FALSE(temp.exists());
    EXPECT_TRUE(temp.path().empty());
    EXPECT_TRUE(temp.Create());
    EXPECT_TRUE(temp.exists());
    temp_filename = temp.path();
    EXPECT_THAT(temp_filename, EndsWith(directory));
    EXPECT_THAT(temp_filename, Not(HasSubstr("XXXXXX")));
    EXPECT_TRUE(flatbuffers::DirExists(temp_filename.c_str()));
  }
  EXPECT_FALSE(flatbuffers::DirExists(temp_filename.c_str()));
}

TEST_F(TempFileTest, CreateAndLeaveDirectory) {
  std::string temp_directory;
  std::string temp_filename;
  {
    std::string directory("foo/bar");
    TempFile temp(logger_, directory, true /* create directory */,
                  false /* delete_on_destruction */);
    EXPECT_FALSE(temp.exists());
    EXPECT_TRUE(temp.path().empty());
    EXPECT_TRUE(temp.Create());
    EXPECT_TRUE(temp.exists());
    temp_filename = temp.path();
    EXPECT_THAT(temp_filename, EndsWith(directory));
    EXPECT_THAT(temp_filename, Not(HasSubstr("XXXXXX")));
    EXPECT_TRUE(flatbuffers::DirExists(temp_filename.c_str()));
    temp_directory = temp.GetTemporaryDirectory();
    EXPECT_FALSE(temp_directory.empty());
  }
  EXPECT_TRUE(flatbuffers::DirExists(temp_filename.c_str()));
  TempFile::Delete(logger_, temp_directory);
}

}  // namespace core
}  // namespace falken
