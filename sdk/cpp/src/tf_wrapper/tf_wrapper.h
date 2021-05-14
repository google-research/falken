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

// This API wraps on some key Tensorflow operations.
#ifndef FALKEN_SDK_TF_WRAPPER_TF_WRAPPER_H_
#define FALKEN_SDK_TF_WRAPPER_TF_WRAPPER_H_

#include <stdint.h>

#include <string>
#include <vector>

#include "src/core/model_signature.h"
#include "src/core/tensor.h"
#include "absl/status/status.h"

namespace falken {
namespace tf_wrapper {

// Values of this type are the same than those of the
// tensorflow::DataType enum, so a direct cast is allowed.
typedef uint32_t DataType;

struct TFWrapperInternal;

class TFWrapper {
 public:
  TFWrapper();
  ~TFWrapper();

  // Load a TensorFlow model and return the signature that describes the inputs
  // and outputs.
  absl::Status LoadModel(const std::string& path,
                         ModelSignature& model_signature);

  // Allocate memory for a model based upon a set of requested inputs and
  // outputs. This must be called at least once after LoadModel() and if any
  // provided inputs or outputs change.
  absl::Status PrepareModel(
      const std::vector<tensor::NamedTensor>& input_named_tensors,
      const std::vector<tensor::NamedTensor>& output_named_tensors);

  // Run the loaded model with the given inputs and outputs.
  // input_named_tensors and output_named_tensors must be in the same order
  // as the call to PrepareModel().
  absl::Status RunModel(
      const std::vector<tensor::NamedTensor>& input_named_tensors,
      std::vector<tensor::NamedTensor>& output_named_tensors);

 private:
  TFWrapperInternal* internal_;
};

}  // namespace tf_wrapper
}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_TF_WRAPPER_TF_WRAPPER_H_
