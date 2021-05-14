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

#include <cmath>
#include <vector>

#include "src/core/statusor.h"
#include "src/core/tensor.h"
#include "src/tf_wrapper/example_model.h"
#include "src/tf_wrapper/lite_model.h"
#include "src/tf_wrapper/model.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "absl/flags/parse.h"

namespace falken {

using falken::tensor::DataType::DT_FLOAT;
using falken::tensor::DataType::DT_INT32;
using falken::tensor::NamedTensor;
using falken::tensor::Tensor;

// Calculate the average value of each element in the provided vector
// of tensors the returned tensor is the same shape with float values.
template <typename T>
Tensor CalculateAverageValues(const std::vector<Tensor>& tensors) {
  Tensor output(DT_FLOAT, tensors[0].shape());
  auto output_flat = output.flat<float>();
  std::vector<double> sum(output_flat.size(), 0.0);
  // Sum input values across each element.
  for (auto& tensor : tensors) {
    auto input_flat = tensor.flat<T>();
    ABSL_HARDENING_ASSERT(input_flat.size() == sum.size());
    for (int i = 0; i < input_flat.size(); ++i) {
      sum[i] += static_cast<double>(input_flat(i));
    }
  }
  // Average inputs across each element.
  for (int i = 0; i < output_flat.size(); ++i) {
    output_flat(i) =
        static_cast<float>(sum[i] / static_cast<double>(tensors.size()));
  }
  return output;
}

// Same as CalculateAverageValues<T> but interprets input data based upon
// the dtype() of the first tensor.
Tensor CalculateAverageValues(const std::vector<Tensor>& tensors) {
  ABSL_HARDENING_ASSERT(tensors.size());
  const auto& first = tensors[0];
  switch (first.dtype()) {
    case DT_FLOAT:
      return CalculateAverageValues<float>(tensors);
    case DT_INT32:
      return CalculateAverageValues<int>(tensors);
    default:
      ABSL_HARDENING_ASSERT(false);
      return Tensor();
  }
}

// Verify that Model and LiteModel produce equivalent outputs when given the
// same inputs.
TEST(LiteModel, TestModelAndLiteModelAreEquivalent) {
  std::srand(0);
  std::string model_path = example_model::GetExampleModelPath();
  auto input_named_tensors = example_model::CreateNamedInputs();
  auto output_named_tensors = example_model::CreateNamedOutputs();
  auto lite_output_named_tensors = example_model::CreateNamedOutputs();

  falken::tf_wrapper::Model model;
  EXPECT_TRUE(model.Load(model_path).ok());
  EXPECT_TRUE(model.Prepare(input_named_tensors, output_named_tensors).ok());

  falken::tf_wrapper::LiteModel lite_model;
  EXPECT_TRUE(lite_model.Load(model_path).ok());
  EXPECT_TRUE(
      lite_model.Prepare(input_named_tensors, lite_output_named_tensors).ok());

  std::vector<std::vector<Tensor>> outputs(output_named_tensors.size());
  std::vector<std::vector<Tensor>> lite_outputs(
      lite_output_named_tensors.size());

  const int kIterations = 500;
  for (int i = 0; i < kIterations; ++i) {
    example_model::RandomizeInputs(input_named_tensors);

    EXPECT_TRUE(model.Run(input_named_tensors, output_named_tensors).ok());
    EXPECT_TRUE(
        lite_model.Run(input_named_tensors, lite_output_named_tensors).ok());

    for (int j = 0; j < output_named_tensors.size(); ++j) {
      outputs[j].push_back(output_named_tensors[j].second);
      lite_outputs[j].push_back(lite_output_named_tensors[j].second);
    }
  }

  std::vector<std::vector<Tensor>> average_outputs(outputs.size());
  std::vector<std::vector<Tensor>> lite_average_outputs(lite_outputs.size());
  for (int i = 0; i < outputs.size(); ++i) {
    Tensor average_output = CalculateAverageValues(outputs[i]);
    Tensor lite_average_output = CalculateAverageValues(lite_outputs[i]);
    // Compare averages per tensor element for each output.
    auto average_output_flat = average_output.flat<float>();
    auto lite_average_output_flat = lite_average_output.flat<float>();
    for (int j = 0; j < average_output_flat.size(); ++j) {
      double delta =
          std::fabs(average_output_flat(j) - lite_average_output_flat(j));
      EXPECT_LT(delta, 0.15)
          << "Different averages for output " << i << " tensor element " << j
          << " :" << std::endl
          << "      tf: " << average_output_flat(j) << std::endl
          << " tf-lite: " << lite_average_output_flat(j);
    }
  }
}

}  // namespace falken

// Define main so ParseCommandLine can be called and command line arguments can
// be retrieved.
int main(int argc, char** argv) {
  testing::InitGoogleTest(&argc, argv);
  absl::ParseCommandLine(argc, argv);
  return RUN_ALL_TESTS();
}
