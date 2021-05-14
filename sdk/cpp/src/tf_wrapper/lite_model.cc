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

#ifdef FALKEN_ENABLE_TFLITE
#include "src/tf_wrapper/lite_model.h"  // NOLINT

#include <assert.h>

#include <cctype>
#include <cstdio>
#include <string>

#include "src/core/model_signature.h"
#include "src/core/status_macros.h"
#include "src/core/statusor.h"
#include "src/core/tensor.h"
#include "absl/status/status.h"
#include "absl/strings/match.h"
#include "absl/strings/str_cat.h"
#include "flatbuffers/util.h"
#include "tensorflow/lite/kernels/custom_ops_register.h"
#include "tensorflow/lite/kernels/register.h"

namespace falken {
namespace tf_wrapper {

namespace {

// Provides a falken::tensor::Tensor interface for TfLiteTensor.
class TfLiteTensorInterface {
 public:
  explicit TfLiteTensorInterface(const TfLiteTensor& tensor)
      : tensor_(tensor), tensor_data_size_(0) {
    const auto& dims = *tensor_.dims;
    if (dims.size > 0) {
      tensor_data_size_ = 1;
      for (int dim = 0; dim < dims.size; dim++) {
        tensor_data_size_ *= dims.data[dim];
      }
    }
  }

  template <typename T>
  const tensor::TensorMap<T> flat() const {
    return tensor::TensorMap<T>(reinterpret_cast<const T*>(tensor_.data.raw),
                                tensor_data_size_);
  }

  template <typename T>
  falken::tensor::TensorMap<T> flat() {
    return tensor::TensorMap<T>(reinterpret_cast<T*>(tensor_.data.raw),
                                tensor_data_size_);
  }

  const falken::tensor::TensorShape& shape() const {
    InitializeSpec();
    return spec_.shape();
  }

  falken::tensor::DataType dtype() const {
    InitializeSpec();
    return spec_.dtype();
  }

  const falken::tensor::TensorSpec& spec() const {
    InitializeSpec();
    return spec_;
  }

 private:
  // Lazy initialization of the TensorSpec.
  void InitializeSpec() const {
    if (spec_.dtype() == falken::tensor::DT_INVALID) {
      falken::tensor::DataType dtype;
      switch (tensor_.type) {
        case kTfLiteFloat32:
          dtype = falken::tensor::DT_FLOAT;
          break;
        case kTfLiteInt32:
          dtype = falken::tensor::DT_INT32;
          break;
        default:
          dtype = falken::tensor::DT_INVALID;
          break;
      }
      falken::tensor::TensorShape tensor_shape;
      const auto& dims = *tensor_.dims;
      tensor_shape.reserve(dims.size);
      for (int dim = 0; dim < dims.size; dim++) {
        tensor_shape.push_back(dims.data[dim]);
      }
      falken::tensor::TensorSpec new_spec(dtype, std::move(tensor_shape));
      spec_ = std::move(new_spec);
    }
  }

 private:
  const TfLiteTensor& tensor_;
  mutable falken::tensor::TensorSpec spec_;
  int tensor_data_size_;
};

// Try to get the main subgraph from a tflite::Model.
const tflite::SubGraph* GetMainSubGraph(const tflite::Model& model) {
  auto* sub_graphs = model.subgraphs();
  // TFLite models always contain the main graph at index 0.
  return sub_graphs ? (*sub_graphs)[0] : nullptr;
}

// Convert a FlatBuffers tflite::Tensor to a falken::tensor::TensorSpec.
common::StatusOr<std::pair<std::string, falken::tensor::TensorSpec>>
FlatBuffersTfLiteTensorToSpec(const tflite::Tensor& tensor) {
  auto* fb_name = tensor.name();
  if (!fb_name) {
    return absl::InternalError("Unnamed tensor found in model");
  }
  std::string name(fb_name->c_str());

  falken::tensor::TensorShape shape;
  // shape_signature is only exported when the tensor doesn't have a static
  // shape.
  auto* tensor_shape = tensor.shape();
  auto* tensor_shape_signature = tensor.shape_signature();
  if (tensor_shape_signature) {
    shape.reserve(tensor_shape_signature->size());
    for (int32_t dimension : *tensor_shape_signature) {
      shape.push_back(dimension);
    }
  } else if (tensor_shape) {
    shape.reserve(tensor_shape->size());
    for (int32_t dimension : *tensor_shape) shape.push_back(dimension);
  } else {
    return absl::InternalError("Tensor " + name + " has no shape");
  }

  falken::tensor::DataType dtype;
  switch (tensor.type()) {
    case tflite::TensorType_FLOAT32:
      dtype = falken::tensor::DT_FLOAT;
      break;
    case tflite::TensorType_INT32:
      dtype = falken::tensor::DT_INT32;
      break;
    default:
      return absl::InternalError("Unexpected tensor type for tensor: " + name +
                                 " type: " + std::to_string(tensor.type()));
  }
  return std::pair<std::string, falken::tensor::TensorSpec>(
      std::move(name), falken::tensor::TensorSpec(dtype, std::move(shape)));
}

// Convert a set of TFLite Tensor FlatBuffers to NamedTensorSpec instances.
absl::Status TfLiteTensorsToNamedTensorSpecs(
    const flatbuffers::Vector<flatbuffers::Offset<tflite::Tensor>>& tensors,
    const flatbuffers::Vector<int32_t>& tensor_indices,
    std::vector<ModelPort>& model_ports) {
  model_ports.clear();
  model_ports.reserve(tensor_indices.size());
  for (int32_t tensor_index : tensor_indices) {
    auto status = FlatBuffersTfLiteTensorToSpec(*tensors[tensor_index]);
    if (!status.ok()) {
      model_ports.clear();
      return status.status();
    }
    model_ports.push_back(ModelPort(
        status->first, tensor::NamedTensorSpec(std::to_string(tensor_index),
                                               std::move(status->second))));
  }
  return absl::OkStatus();
}

// Convert a TFLite Model FlatBuffer to a ModelSignature and retrieve
// input/output names to indices.
absl::Status TfLiteModelToModelSignature(const tflite::Model* model,
                                         ModelSignature& model_signature) {
  model_signature.Clear();
  if (!model) {
    return absl::InternalError("Model buffer not found.");
  }
  const tflite::SubGraph* sub_graph = GetMainSubGraph(*model);
  if (!sub_graph) {
    return absl::InternalError("Main SubGraph not found in TFLite model.");
  }
  const auto* tensors = sub_graph->tensors();
  const auto* inputs = sub_graph->inputs();
  const auto* outputs = sub_graph->outputs();
  if (!(tensors && inputs && outputs)) {
    return absl::InternalError("Malformed TFLite model.");
  }

  auto status = TfLiteTensorsToNamedTensorSpecs(
      *tensors, *inputs, model_signature.model_ports_to_inputs);
  if (status.ok()) {
    status = TfLiteTensorsToNamedTensorSpecs(
        *tensors, *outputs, model_signature.model_ports_to_outputs);
  }
  if (status.ok()) {
    model_signature.Sort();
  } else {
    model_signature.Clear();
  }
  return status;
}

// Type check requested tensors against the provided list of tensors in the
// model signature and populate a map of indices from the offset of a tensor
// in requested_tensors to the index of the input / output in the graph.
absl::Status TypeCheckAndCreateIndexMap(
    const char* direction_description,
    const std::vector<ModelPort>& tensor_signatures,
    const std::vector<tensor::NamedTensor>& requested_tensors,
    std::vector<int>& index_map) {
  index_map.reserve(requested_tensors.size());
  return ModelSignature::TypeCheckTensors(
      direction_description, tensor_signatures, requested_tensors,
      [&index_map](const ModelPort& tensor_signature,
                   const tensor::NamedTensor& requested_tensor) {
        auto tensor_index = std::stoi(tensor_signature.tensor_spec.first);
        if (tensor_index < 0) {
          return absl::FailedPreconditionError(absl::StrCat(
              "Failed to map tensor ", tensor_signature.name,
              " to a valid index (parsed: ", tensor_signature.tensor_spec.first,
              ")"));
        }
        index_map.push_back(tensor_index);
        return absl::OkStatus();
      });
}

}  // namespace

int StringErrorReporter::Report(const char* format, va_list args) {
  va_list calculate_string_size_list;
  va_copy(calculate_string_size_list, args);
  int length = vsnprintf(nullptr, 0, format, calculate_string_size_list);
  va_end(calculate_string_size_list);

  std::string formatted_string(length, '\0');
  int formatted_length = vsnprintf(
      &formatted_string[0],
      // vsnprintf subtracts 1 from length to leave room for a terminating null
      length + 1,
      format,
      args);
  ABSL_ASSERT(formatted_length == length);
  if (!error.empty()) {
    error += "\n";
  }
  error += formatted_string;
  return formatted_length;
}

void LiteModel::Clear() {
  model_.reset(nullptr);
  interpreter_.reset(nullptr);
  input_indices_.clear();
  output_indices_.clear();
  model_signature_.Clear();
}

absl::Status LiteModel::ClearIfError(absl::Status status) {
  if (!status.ok()) {
    Clear();
  }
  return status;
}

absl::Status LiteModel::Load(const std::string& model_path) {
  Clear();
  const std::string tflite_path = flatbuffers::ConCatPathFileName(
      model_path, "tflite/model.tflite");
  model_ = tflite::FlatBufferModel::BuildFromFile(
      tflite_path.c_str(), &error_reporter_);
  if (model_ == nullptr) {
    Clear();
    return absl::Status(
        absl::StatusCode::kInternal,
        absl::StrCat("Could not load TFLite model from file: ", model_path,
                    " - ", error_reporter_.error));
  }

  FALKEN_RETURN_IF_ERROR(ClearIfError(
      TfLiteModelToModelSignature(model_->GetModel(), model_signature_)));

  // Build the interpreter.
  tflite::ops::builtin::BuiltinOpResolver resolver;
  resolver.AddCustom("RandomStandardNormal",
                     tflite::ops::custom::Register_RANDOM_STANDARD_NORMAL());
  resolver.AddCustom("Multinomial",
                     tflite::ops::custom::Register_MULTINOMIAL());
  resolver.AddCustom("Atan2",
                     tflite::ops::custom::Register_ATAN2());
  resolver.AddCustom("Sign",
                     tflite::ops::custom::Register_SIGN());
  tflite::InterpreterBuilder builder(*model_, resolver);
  builder(&interpreter_);
  if (interpreter_ == nullptr) {
    Clear();
    return absl::Status(absl::StatusCode::kInternal,
                        absl::StrCat("Could not build TFLite interpreter. ",
                                     error_reporter_.error));
  }

  // Register custom ops
  auto allocate_status = interpreter_->AllocateTensors();
  if (allocate_status != kTfLiteOk) {
    Clear();
    return absl::Status(
        absl::StatusCode::kInternal,
        absl::StrCat("TFLite allocation error or custom op unavailable: ",
                     error_reporter_.error));
  }
  return absl::OkStatus();
}

absl::Status LiteModel::Prepare(
    const std::vector<tensor::NamedTensor>& input_named_tensors,
    const std::vector<tensor::NamedTensor>& output_named_tensors) {
  if (input_named_tensors.size() !=
      model_signature_.model_ports_to_inputs.size()) {
    Clear();
    return absl::FailedPreconditionError(
        absl::StrCat("Number of requested inputs ", input_named_tensors.size(),
                     " does not match the number of required inputs ",
                     model_signature_.model_ports_to_inputs.size()));
  }
  FALKEN_RETURN_IF_ERROR(ClearIfError(TypeCheckAndCreateIndexMap(
      "Input", model_signature_.model_ports_to_inputs, input_named_tensors,
      input_indices_)));
  FALKEN_RETURN_IF_ERROR(ClearIfError(TypeCheckAndCreateIndexMap(
      "Output", model_signature_.model_ports_to_outputs, output_named_tensors,
      output_indices_)));
  return absl::OkStatus();
}

absl::Status LiteModel::Run(
    const std::vector<tensor::NamedTensor>& input_named_tensors,
    std::vector<tensor::NamedTensor>& output_named_tensors) {
  if (model_ == nullptr) {
    return absl::FailedPreconditionError("No TFLite model loaded, can't run.");
  }
  ABSL_ASSERT(input_named_tensors.size() == input_indices_.size());
  for (int i = 0; i < input_named_tensors.size(); ++i) {
    TfLiteTensorInterface tflite_tensor(
        *interpreter_->tensor(input_indices_[i]));
    FALKEN_RETURN_IF_ERROR(falken::tensor::Tensor::Copy(
        input_named_tensors[i].second.dtype(), input_named_tensors[i].second,
        tflite_tensor));
  }
  auto invoke_status = interpreter_->Invoke();
  if (invoke_status != kTfLiteOk) {
    return absl::InternalError(
        absl::StrCat("TFLite invocation error: ", invoke_status));
  }
  ABSL_ASSERT(output_named_tensors.size() == output_indices_.size());
  for (int i = 0; i < output_named_tensors.size(); ++i) {
    TfLiteTensorInterface tflite_tensor(
        *interpreter_->tensor(output_indices_[i]));
    FALKEN_RETURN_IF_ERROR(falken::tensor::Tensor::Copy(
        output_named_tensors[i].second.dtype(), tflite_tensor,
        output_named_tensors[i].second));
  }
  return absl::OkStatus();
}

}  // namespace tf_wrapper
}  // namespace falken
#endif  // FALKEN_ENABLE_TFLITE
