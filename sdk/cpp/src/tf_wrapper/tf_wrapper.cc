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

#include "src/tf_wrapper/tf_wrapper.h"

#include <algorithm>
#include <memory>

#include "src/core/status_macros.h"
#ifdef FALKEN_ENABLE_TFLITE
#include "src/tf_wrapper/lite_model.h"
#endif  // FALKEN_ENABLE_TFLITE
#ifdef FALKEN_ENABLE_TF
#include "src/tf_wrapper/model.h"
#endif  // FALKEN_ENABLE_TF

#include "absl/strings/str_cat.h"

#if defined(FALKEN_ENABLE_TFLITE) && defined(FALKEN_ENABLE_TF)
#define FALKEN_COMPARE_TF_AND_TFLITE 1
#else
#define FALKEN_COMPARE_TF_AND_TFLITE 0
#endif  // defined(FALKEN_ENABLE_TFLITE) && defined(FALKEN_ENABLE_TF)

#if FALKEN_COMPARE_TF_AND_TFLITE
namespace {

std::string ModelPortsToString(
    const std::vector<falken::ModelPort>& spec_named_tensors) {
  std::string out;
  for (const auto& tensor : spec_named_tensors) {
    if (!out.empty()) out += ", ";
    out += tensor.name;
  }
  return "[" + out + "]";
}

std::string CompareModelPorts(const std::string& list_name,
                              const std::vector<falken::ModelPort>& lhs,
                              const std::vector<falken::ModelPort>& rhs) {
  std::string error;
  if (lhs.size() != rhs.size()) {
    error += list_name + " sizes mismatch " + std::to_string(lhs.size()) +
             " vs " + std::to_string(rhs.size()) + "\n" +
             ModelPortsToString(lhs) + " !=\n" + ModelPortsToString(rhs) + "\n";
  }
  auto size = std::min(lhs.size(), rhs.size());
  for (int i = 0; i < size; ++i) {
    std::string tensor_index = "tensor[" + std::to_string(i) + "]";
    const std::string& lhs_name = lhs[i].name;
    const std::string& rhs_name = rhs[i].name;
    if (lhs_name != rhs_name) {
      error += list_name + " " + tensor_index + " names mismatch " +
               lhs_name + " vs " + rhs_name + "\n";
    }
    const falken::tensor::TensorSpec& lhs_tensor = lhs[i].tensor_spec.second;
    const falken::tensor::TensorSpec& rhs_tensor = rhs[i].tensor_spec.second;
    if (lhs_tensor.dtype() != rhs_tensor.dtype()) {
      error += list_name + " " + tensor_index + " (" + lhs_name + " vs " +
               rhs_name + ") dtype " + std::to_string(lhs_tensor.dtype()) +
               " vs " + std::to_string(rhs_tensor.dtype()) + "\n";
    }

    if (!falken::tensor::CompareTensorShapes(lhs_tensor.shape(),
                                             rhs_tensor.shape())) {
      error += list_name + " " + tensor_index + " (" + lhs_name + " vs " +
               rhs_name + ") shapes mismatch " +
               falken::tensor::TensorShapeDebugString(lhs_tensor.shape()) +
               " vs " +
               falken::tensor::TensorShapeDebugString(rhs_tensor.shape()) +
               "\n";
    }
  }
  return error;
}

absl::Status CompareModelSignatures(const falken::ModelSignature& lhs,
                                    const falken::ModelSignature& rhs) {
  std::string error;
  error = CompareModelPorts(
      "TF and TFLite model inputs:", lhs.model_ports_to_inputs,
      rhs.model_ports_to_inputs);

  error += CompareModelPorts(
      "TF and TFLite model outputs:", lhs.model_ports_to_outputs,
      rhs.model_ports_to_outputs);
  return error.empty() ? absl::OkStatus() : absl::InternalError(error);
}

}  // namespace
#endif  // FALKEN_COMPARE_TF_AND_TFLITE

#if !defined(NDEBUG)
namespace {

// Compare names and tensor specs of the provided tensors.
absl::Status CompareTensorSpecs(
    const char* io_name,
    const std::vector<falken::tensor::NamedTensor>& expected,
    const std::vector<falken::tensor::NamedTensor>& provided) {
  if (expected.size() != provided.size()) {
    return absl::FailedPreconditionError(
        absl::StrCat(io_name, " provided number of tensors ", provided.size(),
                     " do not match the expected number of tensors ",
                     expected.size()));
  }
  for (int i = 0; i < expected.size(); ++i) {
    if (expected[i].first != provided[i].first) {
      return absl::FailedPreconditionError(
          absl::StrCat(io_name, " provided tensor at index ", i, " (",
                       provided[i].first, ") does not match the expected name ",
                       expected[i].first));
    }
    auto status = falken::tensor::TensorSpec::Compare(
        expected[i].second.spec(), provided[i].second.spec());
    if (!status.ok()) {
      return absl::FailedPreconditionError(
          absl::StrCat(io_name, " provided tensor at index ", i, " (",
                       provided[i].first, ") does not match "
                       "the expected tensor spec: ", status.message()));
    }
  }
  return absl::OkStatus();
}

}  // namespace
#endif   // !defined(NDEBUG)


namespace falken {
namespace tf_wrapper {

struct TFWrapperInternal {
#ifdef FALKEN_ENABLE_TF
  Model model;
#endif  // FALKEN_ENABLE_TF
#ifdef FALKEN_ENABLE_TFLITE
  LiteModel lite_model;
#endif  // FALKEN_ENABLE_TFLITE
#if !defined(NDEBUG)
  std::vector<tensor::NamedTensor> prepared_input_named_tensors;
  std::vector<tensor::NamedTensor> prepared_output_named_tensors;
#endif  // !defined(NDEBUG)
};

TFWrapper::TFWrapper() {
  internal_ = new TFWrapperInternal();  // NOLINT
}

TFWrapper::~TFWrapper() {
  delete internal_;
  internal_ = nullptr;
}

absl::Status TFWrapper::LoadModel(const std::string& path,
                                  ModelSignature& model_signature) {
  auto internal = absl::make_unique<TFWrapperInternal>();
#ifdef FALKEN_ENABLE_TF
  // Load TF model.
  FALKEN_RETURN_IF_ERROR(internal->model.Load(path));
  const ModelSignature& tf_signature = internal->model.model_signature();
#endif  // FALKEN_ENABLE_TF

#ifdef FALKEN_ENABLE_TFLITE
  // Load TFLite model.
  FALKEN_RETURN_IF_ERROR(internal->lite_model.Load(path));
  const ModelSignature& tflite_signature =
      internal->lite_model.model_signature();
#endif  // FALKEN_ENABLE_TFLITE

#if FALKEN_COMPARE_TF_AND_TFLITE
  // Make sure both model signatures match.
  FALKEN_RETURN_IF_ERROR(CompareModelSignatures(tf_signature,
                                                tflite_signature));
  model_signature = tf_signature;

#elif defined(FALKEN_ENABLE_TF)
  model_signature = tf_signature;
#elif defined(FALKEN_ENABLE_TFLITE)
  model_signature = tflite_signature;
#endif

  delete internal_;
  internal_ = internal.release();
  return absl::OkStatus();
}

absl::Status TFWrapper::PrepareModel(
    const std::vector<tensor::NamedTensor>& input_named_tensors,
    const std::vector<tensor::NamedTensor>& output_named_tensors) {
#ifdef FALKEN_ENABLE_TF
  FALKEN_RETURN_IF_ERROR(
      internal_->model.Prepare(input_named_tensors, output_named_tensors));
#endif  // FALKEN_ENABLE_TF

#ifdef FALKEN_ENABLE_TFLITE
  FALKEN_RETURN_IF_ERROR(
      internal_->lite_model.Prepare(input_named_tensors, output_named_tensors));
#endif  // FALKEN_ENABLE_TFLITE

#if !defined(NDEBUG)
  internal_->prepared_input_named_tensors = input_named_tensors;
  internal_->prepared_output_named_tensors = output_named_tensors;
#endif  // !defined(NDEBUG)

  return absl::OkStatus();
}

absl::Status TFWrapper::RunModel(
    const std::vector<tensor::NamedTensor>& input_named_tensors,
    std::vector<tensor::NamedTensor>& output_named_tensors) {
  // Configure output vector based upon enabled TensorFlow runtimes.
#if defined(FALKEN_ENABLE_TF) && defined(FALKEN_ENABLE_TFLITE)
  std::vector<tensor::NamedTensor>& tf_output_tensors = output_named_tensors;
  std::vector<tensor::NamedTensor> tflite_output_named_tensors_storage(
      output_named_tensors);
  std::vector<tensor::NamedTensor>& tflite_output_tensors =
      &tflite_output_named_tensors_storage;
#elif defined(FALKEN_ENABLE_TF)
  std::vector<tensor::NamedTensor>& tf_output_tensors = output_named_tensors;
#elif defined(FALKEN_ENABLE_TFLITE)
  std::vector<tensor::NamedTensor>& tflite_output_tensors =
      output_named_tensors;
#else
#error Inference not possible, Tensorflow and Tensorflow Lite are not enabled.
#endif

#if !defined(NDEBUG)
  FALKEN_RETURN_IF_ERROR(CompareTensorSpecs(
      "Input", internal_->prepared_input_named_tensors, input_named_tensors));
  FALKEN_RETURN_IF_ERROR(CompareTensorSpecs(
      "Output", internal_->prepared_output_named_tensors,
      output_named_tensors));
#endif  // !defined(NDEBUG)

#ifdef FALKEN_ENABLE_TF
  // Run TF model.
  FALKEN_RETURN_IF_ERROR(
      internal_->model.Run(input_named_tensors, tf_output_tensors));
#endif  // FALKEN_ENABLE_TF

#ifdef FALKEN_ENABLE_TFLITE
  FALKEN_RETURN_IF_ERROR(
      internal_->lite_model.Run(input_named_tensors, tflite_output_tensors));
#endif  // FALKEN_ENABLE_TFLITE

#if FALKEN_COMPARE_TF_AND_TFLITE
  // Verify TF and TFLite output tensors are close.
  std::string error =
      CompareModelPorts(tf_output_tensors, tflite_output_tensors);
  if (!error.empty()) return absl::InternalError(error);
#endif  // FALKEN_COMPARE_TF_AND_TFLITE

  return absl::OkStatus();
}

}  // namespace tf_wrapper
}  // namespace falken
