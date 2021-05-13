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

#ifndef FALKEN_SDK_TF_WRAPPER_LITE_MODEL_H_
#define FALKEN_SDK_TF_WRAPPER_LITE_MODEL_H_

#ifdef FALKEN_ENABLE_TFLITE
#include <stdint.h>

#include <map>
#include <string>

#include "src/core/model_signature.h"
#include "src/core/status_macros.h"
#include "src/core/statusor.h"
#include "src/core/tensor.h"
#include "absl/status/status.h"
#include "tensorflow/lite/core/api/error_reporter.h"
#include "tensorflow/lite/interpreter.h"
#include "tensorflow/lite/model.h"
#include "tensorflow/lite/optional_debug_tools.h"

namespace falken {
namespace tf_wrapper {

// Stores errors in a string.
struct StringErrorReporter : public tflite::ErrorReporter {
  std::string error;
  int Report(const char* format, va_list args) override;
};

// Wrapper over TFLite models.
class LiteModel {
 public:
  LiteModel() = default;

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
  LiteModel(const LiteModel&) = delete;
  LiteModel& operator=(const LiteModel&) = delete;

  // Clear the loaded model.
  void Clear();

  // Clear the loaded model if the provided status indicates an error.
  absl::Status ClearIfError(absl::Status status);

  // TF-lite error reporting helper.
  StringErrorReporter error_reporter_;

  // TFLite model and interpreter.
  std::unique_ptr<tflite::FlatBufferModel> model_;
  std::unique_ptr<tflite::Interpreter> interpreter_;
  // Maps that matches each input / output tensor index with their index "i" to
  // access the tensor with interpreter_->tensors(i). These mappings should
  // _not_ be used to access interpreter_->inputs values.
  std::vector<int> input_indices_;
  std::vector<int> output_indices_;

  // Signature of the loaded model.
  ModelSignature model_signature_;
};

}  // namespace tf_wrapper
}  // namespace falken
#endif  // FALKEN_ENABLE_TFLITE

#endif  // RESEARCH_KERNEL_FALKEN_SDK_TF_WRAPPER_LITE_MODEL_H_
