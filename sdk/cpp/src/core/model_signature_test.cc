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

#include "src/core/model_signature.h"

#include <string>
#include <vector>

#include "gmock/gmock.h"
#include "gtest/gtest.h"

using testing::ElementsAreArray;

namespace falken {
namespace tensor {

class ModelSignatureTest : public testing::Test {
 public:
  void SetUp() override {
    auto& inputs = signature_.model_ports_to_inputs;
    inputs.push_back(
        ModelPort("z/1", NamedTensorSpec("z_1", TensorSpec(DT_FLOAT, {1, 3}))));
    inputs.push_back(
        ModelPort("a/4", NamedTensorSpec("a_4", TensorSpec(DT_INT32, {2, 5}))));
    inputs.push_back(ModelPort(
        "fe/el", NamedTensorSpec("touch", TensorSpec(DT_FLOAT, {1, 32, 4}))));
    auto& outputs = signature_.model_ports_to_outputs;
    outputs.push_back(
        ModelPort("f/b", NamedTensorSpec("f_b", TensorSpec(DT_FLOAT, {1, 1}))));
    outputs.push_back(
        ModelPort("b/c", NamedTensorSpec("b_c", TensorSpec(DT_INT32, {4, 2}))));
  }

  // Get the names of the specified list of model signature infos.
  static std::vector<std::string> IoNames(const std::vector<ModelPort>& io) {
    std::vector<std::string> names;
    names.reserve(io.size());
    for (auto& tensor : io) {
      names.push_back(tensor.name);
    }
    return names;
  }

  ModelSignature signature_;
};

TEST_F(ModelSignatureTest, Clear) {
  EXPECT_NE(signature_.model_ports_to_inputs.size(), 0);
  EXPECT_NE(signature_.model_ports_to_outputs.size(), 0);
  signature_.Clear();
  EXPECT_EQ(signature_.model_ports_to_inputs.size(), 0);
  EXPECT_EQ(signature_.model_ports_to_outputs.size(), 0);
}

TEST_F(ModelSignatureTest, Sort) {
  ModelSignature copy = signature_;
  ModelSignature::SortPortsByName(copy.model_ports_to_inputs);
  EXPECT_THAT(IoNames(copy.model_ports_to_inputs),
              ElementsAreArray({"a/4", "fe/el", "z/1"}));
  EXPECT_THAT(IoNames(copy.model_ports_to_outputs),
              ElementsAreArray({"f/b", "b/c"}));
  copy = signature_;
  copy.Sort();
  EXPECT_THAT(IoNames(copy.model_ports_to_inputs),
              ElementsAreArray({"a/4", "fe/el", "z/1"}));
  EXPECT_THAT(IoNames(copy.model_ports_to_outputs),
              ElementsAreArray({"b/c", "f/b"}));
}

TEST_F(ModelSignatureTest, FindByName) {
  signature_.Sort();
  EXPECT_EQ(
      ModelSignature::FindPortByName("z/1", signature_.model_ports_to_inputs)
          ->name,
      "z/1");
  EXPECT_EQ(ModelSignature::FindPortByName("foo/bar",
                                           signature_.model_ports_to_inputs),
            nullptr);
  EXPECT_EQ(signature_.FindInputPort("fe/el")->name, "fe/el");
  EXPECT_EQ(signature_.FindInputPort("el/fe"), nullptr);
  EXPECT_EQ(signature_.FindOutputPort("f/b")->name, "f/b");
  EXPECT_EQ(signature_.FindOutputPort("z/z"), nullptr);
}

TEST_F(ModelSignatureTest, TypeCheckTensors) {
  signature_.Sort();
  {
    std::vector<std::pair<std::string, std::string>> visited;
    EXPECT_TRUE(
        ModelSignature::TypeCheckTensors(
            "Input", signature_.model_ports_to_inputs,
            {NamedTensor("fe/el", Tensor(DT_FLOAT, {1, 32, 4})),
             NamedTensor("z/1", Tensor(DT_FLOAT, {1, 3}))},
            [&visited](
                const ModelPort& tensor_signature,
                const tensor::NamedTensor& requested_tensor) -> absl::Status {
              visited.push_back(
                  {requested_tensor.first, tensor_signature.tensor_spec.first});
              return absl::OkStatus();
            })
            .ok());
    std::vector<std::pair<std::string, std::string>> expected = {
        {"fe/el", "touch"}, {"z/1", "z_1"}};
    EXPECT_EQ(visited, expected);
  }

  // Visitor found a problem.
  EXPECT_FALSE(
      ModelSignature::TypeCheckTensors(
          "Input", signature_.model_ports_to_inputs,
          {
              NamedTensor("fe/el", Tensor(DT_INT32, {1, 32, 4})),
          },
          [](const ModelPort&, const tensor::NamedTensor&) -> absl::Status {
            return absl::InternalError("An error occurred");
          })
          .ok());

  // Mismatched data type.
  EXPECT_FALSE(
      ModelSignature::TypeCheckTensors(
          "Input", signature_.model_ports_to_inputs,
          {
              NamedTensor("fe/el", Tensor(DT_INT32, {1, 32, 4})),
          },
          [](const ModelPort&, const tensor::NamedTensor&) -> absl::Status {
            return absl::OkStatus();
          })
          .ok());
  // Mismatched shape.
  EXPECT_FALSE(
      ModelSignature::TypeCheckTensors(
          "Input", signature_.model_ports_to_inputs,
          {
              NamedTensor("fe/el", Tensor(DT_FLOAT, {1, 31, 4})),
          },
          [](const ModelPort&, const tensor::NamedTensor&) -> absl::Status {
            return absl::OkStatus();
          })
          .ok());
}

}  // namespace tensor
}  // namespace falken
