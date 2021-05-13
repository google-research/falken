//  Copyright 2021 Google LLC
//
//  Licensed under the Apache License, Version 2.0 (the "License");
//  you may not use this file except in compliance with the License.
//  You may obtain a copy of the License at
//
//       http://www.apache.org/licenses/LICENSE-2.0
//
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.

#ifndef FALKEN_SDK_TF_WRAPPER_EXAMPLE_MODEL_H_
#define FALKEN_SDK_TF_WRAPPER_EXAMPLE_MODEL_H_

#include "src/core/protos.h"
#include "src/core/tensor.h"
#include "absl/strings/string_view.h"

namespace falken {
namespace example_model {

// Load ObservationSpec corresponding to graph.
proto::ObservationSpec ObservationSpec();

proto::ObservationData ObservationData();

// Load ActionSpec corresponding to graph.
proto::ActionSpec ActionSpec();

proto::ActionData ActionData();

// Get the path to the example model.
std::string GetExampleModelPath();

// Create a set of inputs for the test model.
std::vector<falken::tensor::NamedTensor> CreateNamedInputs();

// Create a set of outputs for the test model.
std::vector<falken::tensor::NamedTensor> CreateNamedOutputs();

// Populate inputs for the test model with random data.
void RandomizeInputs(std::vector<falken::tensor::NamedTensor>& inputs);

}  // namespace example_model
}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_TF_WRAPPER_EXAMPLE_MODEL_H_
