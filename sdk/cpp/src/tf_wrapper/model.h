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

#ifndef FALKEN_SDK_TF_WRAPPER_MODEL_H_
#define FALKEN_SDK_TF_WRAPPER_MODEL_H_

#ifdef FALKEN_ENABLE_TF


#include <string>

#include "src/core/model_signature.h"
#include "src/core/tensor.h"
#include "absl/status/status.h"
#include "tensorflow/cc/saved_model/loader.h"
#include "tensorflow/core/protobuf/meta_graph.pb.h"  // NOLINT

namespace falken {
namespace tf_wrapper {

// Wrapper over Tensorflow.
class Model {
 public:
  Model() = default;

  // Clear any previously loaded model and saved tensors and
  // load a model from a given path.
  ::absl::Status Load(const std::string& model_path);

  // Allocate memory for a model based upon a set of requested inputs and
  // outputs. This must be called at least once after Load() and if any
  // provided inputs or outputs change.
  absl::Status Prepare(
      const std::vector<tensor::NamedTensor>& input_named_tensors,
      const std::vector<tensor::NamedTensor>& output_named_tensors);

  // Run the loaded model with the given inputs and outputs.
  // input_named_tensors and output_named_tensors must be in the same order
  // as the call to Prepare().
  absl::Status Run(const std::vector<tensor::NamedTensor>& input_named_tensors,
                   std::vector<tensor::NamedTensor>& output_named_tensors);

  // Get the signature of the loaded model
  const ModelSignature& model_signature() const { return model_signature_; }

 private:
  Model(const Model&) = delete;
  Model& operator=(const Model&) = delete;

  // Clear the loaded model.
  absl::Status Clear();

  // Tensorflow model.
  tensorflow::SavedModelBundle model_bundle_;
  // Signature of the loaded model.
  ModelSignature model_signature_;

  // Input tensors that are updated on each call to run.
  std::vector<std::pair<std::string, tensorflow::Tensor>> input_tf_tensors_;
  // Output tensors that should be calculated.
  std::vector<std::string> requested_outputs_;
};

}  // namespace tf_wrapper
}  // namespace falken

#endif  // FALKEN_ENABLE_TF

#endif  // RESEARCH_KERNEL_FALKEN_SDK_TF_WRAPPER_MODEL_H_
