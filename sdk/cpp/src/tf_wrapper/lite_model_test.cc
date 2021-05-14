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

#include "src/tf_wrapper/lite_model.h"

#include "src/tf_wrapper/example_model.h"
#include "src/tf_wrapper/model.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "absl/flags/parse.h"
#include "absl/strings/str_cat.h"
#include "tensorflow/lite/c/common.h"

namespace falken {
namespace tf_wrapper {
namespace {

using ::falken::tensor::DataType;
using ::falken::tensor::NamedTensor;
using ::falken::tensor::Tensor;
using ::falken::tensor::TensorShape;

class LiteModelTest : public testing::Test {
 protected:
  falken::tf_wrapper::LiteModel& LoadLiteModel() {
    EXPECT_TRUE(model_.Load(example_model::GetExampleModelPath()).ok());
    return model_;
  }

  LiteModel model_;
};

TEST_F(LiteModelTest, TestModel) {
  LiteModel& model = LoadLiteModel();

  auto input_named_tensors = example_model::CreateNamedInputs();
  auto output_named_tensors = example_model::CreateNamedOutputs();
  ASSERT_TRUE(model.Prepare(input_named_tensors, output_named_tensors).ok());
  EXPECT_TRUE(model.Run(input_named_tensors, output_named_tensors).ok());

  for (NamedTensor& tensor : output_named_tensors) {
    if (tensor.second.dtype() == DataType::DT_FLOAT) {
      auto tensor_map = tensor.second.flat<float>();
      for (int i = 0; i < tensor_map.size(); ++i) {
        EXPECT_THAT(tensor_map(i), testing::Not(testing::FloatEq(0.0)));
      }
    }
  }
}

TEST_F(LiteModelTest, TestBenchmark) {
  LiteModel& model = LoadLiteModel();
  auto input_named_tensors = example_model::CreateNamedInputs();
  auto output_named_tensors = example_model::CreateNamedOutputs();
  ASSERT_TRUE(model.Prepare(input_named_tensors, output_named_tensors).ok());
  for (int i = 0; i < 10000; ++i) {
    example_model::RandomizeInputs(input_named_tensors);
    EXPECT_TRUE(model.Run(input_named_tensors, output_named_tensors).ok());
  }
}

TEST_F(LiteModelTest, TestModelNotFound) {
  const std::string bad_path = "/tmp/BAD_PATH";
  EXPECT_FALSE(model_.Load(bad_path).ok());
}

TEST_F(LiteModelTest, TestWrongInputCount) {
  LiteModel& model = LoadLiteModel();

  std::vector<NamedTensor> input_named_tensors = {
    example_model::CreateNamedInputs()[0],
  };
  auto output_named_tensors = example_model::CreateNamedOutputs();
  EXPECT_FALSE(model.Prepare(input_named_tensors, output_named_tensors).ok());
  EXPECT_FALSE(model.Run(input_named_tensors, output_named_tensors).ok());
}

TEST_F(LiteModelTest, TestBadlyNamedTensor) {
  LiteModel& model = LoadLiteModel();

  std::vector<NamedTensor> input_named_tensors =
      example_model::CreateNamedInputs();
  input_named_tensors[5].first = "INCORRECT_NAME";
  auto output_named_tensors = example_model::CreateNamedOutputs();
  EXPECT_FALSE(model.Prepare(input_named_tensors, output_named_tensors).ok());
  EXPECT_FALSE(model.Run(input_named_tensors, output_named_tensors).ok());
}

TEST_F(LiteModelTest, TestErrorReporter) {
  StringErrorReporter error_reporter;
  int result1 = error_reporter.ReportError(nullptr, "%s %d", "test", 1000);
  int result2 = error_reporter.ReportError(nullptr, "%.2f %s", 1.0, "test");
  EXPECT_EQ(result1, 9);
  EXPECT_EQ(result2, 9);
  EXPECT_EQ(error_reporter.error, "test 1000\n1.00 test");
}

}  // namespace
}  // namespace tf_wrapper
}  // namespace falken

// Define main so ParseCommandLine can be called and command line arguments can
// be retrieved.
int main(int argc, char** argv) {
  testing::InitGoogleTest(&argc, argv);
  absl::ParseCommandLine(argc, argv);
  return RUN_ALL_TESTS();
}
