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

#include "src/core/absl_log_sink.h"

#include "src/core/string_logger.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"

namespace falken {

using falken::testing::StringLogger;
using ::testing::MatchesRegex;

class AbslLogSinkTest : public ::testing::Test {
 protected:
  AbslLogSinkTest() : sink_(logger_) {
    sink_.log_time_ = 1600715120000; /* Mon 21 Sep 2020 12:05:20 PM PDT */
  }

  StringLogger logger_;
  AbslLogSink sink_;
};

TEST_F(AbslLogSinkTest, LogMessage) {
}

}  // namespace falken
