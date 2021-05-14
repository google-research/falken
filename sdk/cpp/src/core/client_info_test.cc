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

#include "src/core/client_info.h"

#include <regex>  // NOLINT(build/c++11)

#include "gmock/gmock.h"
#include "gtest/gtest.h"

namespace falken {

TEST(ClientInfoTest, GetVersionInformation) {
#if !defined(NDEBUG)
  std::regex regex(
      "Version ([0-9]+)\\.([0-9]+)\\.([0-9]+) \\(CL: [a-zA-Z0-9_]+, Commit: "
      "[0-9a-f]{1,40}, (Debug|Release|Nightly)\\)");
  EXPECT_TRUE(std::regex_match(GetVersionInformation(), regex));
#else
  EXPECT_EQ(GetVersionInformation(), "Version 1.2.3 (CL: 5, Commit: 12)");
#endif
}

TEST(ClientInfoTest, GetUserAgent) {
  static const char kExpectedUserAgent[] =
      "falken-cpp/([0-9]+)\\.([0-9]+)\\.([0-9]+) "
      "falken-cpp-commit/[0-9a-f]{1,40} "
      "falken-cpp-cl/[a-zA-Z0-9_]+ "
#if defined(NDEBUG)
      "falken-cpp-build/release "
#else
      "falken-cpp-build/debug "
#endif  // defined(NDEBUG)
      "falken-cpp-runtime/[^ ]+ "
      "falken-os/[^ ]+ "
      "falken-cpu/[^ ]+";

  std::regex regex(kExpectedUserAgent);
  EXPECT_TRUE(std::regex_match(GetUserAgent(), regex));
}

}  // namespace falken
