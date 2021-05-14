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

#include "src/core/status_macros.h"

#include "src/core/statusor.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"

namespace {

using ::testing::Eq;
using ::testing::Return;

using falken::common::StatusOr;

struct ReturnStatus {
  virtual ~ReturnStatus() {}
  virtual absl::Status test() = 0;
};

struct MockReturnStatus : public ReturnStatus {
  MOCK_METHOD(absl::Status, test, (), (override));
};

absl::Status ReturnStatusOk() { return absl::OkStatus(); }

absl::Status ReturnStatusError(std::string msg) {
  return absl::Status(absl::StatusCode::kUnknown, msg);
}

struct ReturnStatusOr {
  virtual ~ReturnStatusOr() {}
  virtual StatusOr<int> test() = 0;
};

struct MockReturnStatusOr : public ReturnStatusOr {
  MOCK_METHOD(StatusOr<int>, test, (), (override));
};

StatusOr<int> ReturnStatusOrValue(int value) { return value; }

StatusOr<int> ReturnStatusOrError(std::string msg) {
  return absl::Status(absl::StatusCode::kUnknown, msg);
}

TEST(FalkenReturnIfErrorTest, TestWorksWithOkAndErrorStatus) {
  auto func = []() -> absl::Status {
    FALKEN_RETURN_IF_ERROR(ReturnStatusOk());
    FALKEN_RETURN_IF_ERROR(ReturnStatusOk());
    FALKEN_RETURN_IF_ERROR(ReturnStatusError("Houston, we have a problem"));
    return ReturnStatusError("Error");
  };

  EXPECT_THAT(func().message(), Eq("Houston, we have a problem"));
}

TEST(FalkenReturnIfErrorTest, TestExpressionIsExecutedOnlyOnce) {
  MockReturnStatus mock_return_status;
  EXPECT_CALL(mock_return_status, test())
      .Times(1)
      .WillOnce(Return(ReturnStatusError("Expected error")));
  auto func = [&mock_return_status]() -> absl::Status {
    FALKEN_RETURN_IF_ERROR(mock_return_status.test());
    return ReturnStatusOk();
  };
  EXPECT_THAT(func().message(), Eq("Expected error"));
}

TEST(FalkenAssignOrReturnTest, TestWorksWithOkAndErrorStatus) {
  auto func = []() -> absl::Status {
    FALKEN_ASSIGN_OR_RETURN(int number1, ReturnStatusOrValue(1));
    EXPECT_EQ(1, number1);
    FALKEN_ASSIGN_OR_RETURN(const int number2, ReturnStatusOrValue(2));
    EXPECT_EQ(2, number2);
    FALKEN_ASSIGN_OR_RETURN(const int& number3, ReturnStatusOrValue(3));
    EXPECT_EQ(3, number3);
    FALKEN_ASSIGN_OR_RETURN(int number4,
                            ReturnStatusOrError("Houston, we have a problem"));
    number4 = 0;  // Avoids unused error
    return ReturnStatusError("Error");
  };

  EXPECT_THAT(func().message(), Eq("Houston, we have a problem"));
}

TEST(FalkenAssignOrReturnTest, TestExpressionIsExecutedOnlyOnce) {
  MockReturnStatusOr mock_return_status_or;
  EXPECT_CALL(mock_return_status_or, test())
      .Times(1)
      .WillOnce(Return(ReturnStatusError("Expected error")));
  auto func = [&mock_return_status_or]() -> absl::Status {
    FALKEN_ASSIGN_OR_RETURN(int number, mock_return_status_or.test());
    number = 0;  // Avoids unused error
    return ReturnStatusOk();
  };
  EXPECT_THAT(func().message(), Eq("Expected error"));
}

TEST(FalkenAppendLineNumExpandTest, TestWorks) {
  int FALKEN_APPEND_LINE_NUM_EXPAND(variable_, 1) = 1;
  EXPECT_EQ(1, variable_1);
  int FALKEN_APPEND_LINE_NUM_EXPAND(variable_, 2) = 2;
  EXPECT_EQ(2, variable_2);
  int FALKEN_APPEND_LINE_NUM_EXPAND(variable_, 3) = 3;
  EXPECT_EQ(3, variable_3);
}

}  // namespace
