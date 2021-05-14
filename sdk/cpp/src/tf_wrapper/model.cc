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

#ifdef FALKEN_ENABLE_TF

#include "src/tf_wrapper/model.h"

#include <string>

#include "src/core/status_macros.h"
#include "src/core/tensor.h"
#include "absl/status/status.h"
#include "absl/strings/str_cat.h"
#include "tensorflow/cc/saved_model/tag_constants.h"
#include "tensorflow/core/framework/tensor.h"
#include "tensorflow/core/framework/tensor_shape.h"
#include "tensorflow/core/framework/tensor_shape.pb.h"  // NOLINT
#include "tensorflow/core/framework/types.pb.h"  // NOLINT

namespace falken {
namespace tf_wrapper {

namespace {

absl::Status TensorflowStatusToAbseil(tensorflow::Status status) {
  const int tensorflow_int_status = static_cast<int>(status.code());
  return absl::Status(static_cast<absl::StatusCode>(tensorflow_int_status),
                      status.error_message());
}

// Build an empty TF tensor from a Falken tensor spec.
tensorflow::Tensor ConstructTfTensorFromTensorSpec(
    const tensor::TensorSpec& tensor_spec) {
  tensorflow::TensorShape shape;
  for (const int dim : tensor_spec.shape()) shape.AddDim(dim);
  return tensorflow::Tensor(
      static_cast<tensorflow::DataType>(tensor_spec.dtype()), shape);
}

// Convert the map of tensor info objects into a vector of tensor signatures.
absl::Status TensorInfoMapToNamedTensorSpecs(
    const tensorflow::protobuf::Map<std::string, tensorflow::TensorInfo>&
        tensor_info_map,
    std::vector<ModelPort>& model_ports) {
  model_ports.reserve(tensor_info_map.size());
  for (const auto& name_tensor_info : tensor_info_map) {
    const std::string& tensor_spec_name = name_tensor_info.first;
    const auto& tensor_info = name_tensor_info.second;
    falken::tensor::DataType dtype;
    switch (tensor_info.dtype()) {
      case tensorflow::DataType::DT_FLOAT:
        dtype = falken::tensor::DT_FLOAT;
        break;
      case tensorflow::DataType::DT_INT32:
        dtype = falken::tensor::DT_INT32;
        break;
      default:
        model_ports.clear();
        return absl::InternalError(
            "Unexpected dtype in tensorflow tensor: " +
            tensor_spec_name + " " + tensor_info.name() + " dtype: " +
            std::to_string(tensor_info.dtype()));
    }

    tensor::TensorShape shape;
    tensorflow::PartialTensorShape shape_from_proto(tensor_info.tensor_shape());
    shape.reserve(shape_from_proto.dim_sizes().size());
    for (auto dimension_size : shape_from_proto.dim_sizes()) {
      shape.push_back(dimension_size);
    }
    model_ports.push_back(
        ModelPort(tensor_spec_name,
                  tensor::NamedTensorSpec(tensor_info.name(),
                                          tensor::TensorSpec(dtype, shape))));
  }
  return absl::OkStatus();
}

// Parse the tensorflow model signature definition into a Falken model
// signature.
absl::Status SignatureDefToModelSignature(
    const tensorflow::SignatureDef& signature_def,
    ModelSignature& model_signature) {
  model_signature.Clear();
  auto status = TensorInfoMapToNamedTensorSpecs(
      signature_def.inputs(), model_signature.model_ports_to_inputs);
  if (status.ok()) {
    status = TensorInfoMapToNamedTensorSpecs(
        signature_def.outputs(), model_signature.model_ports_to_outputs);
  }
  if (status.ok()) {
    model_signature.Sort();
  } else {
    model_signature.Clear();
  }
  return status;
}

// Type check requested tensors against the model signature and construct
// an array of tensors to feed data into and fetch data from the graph.
absl::Status TypeCheckAndPrepareTensors(
    const char* direction_description,
    const std::vector<ModelPort>& tensor_signatures,
    const std::vector<tensor::NamedTensor>& requested_tensors,
    std::vector<std::pair<std::string, tensorflow::Tensor>>& prepared_tensors) {
  return ModelSignature::TypeCheckTensors(
      direction_description, tensor_signatures, requested_tensors,
      [&prepared_tensors](const ModelPort& tensor_signature,
                          const tensor::NamedTensor& requested_tensor) {
        prepared_tensors.push_back(std::pair<std::string, tensorflow::Tensor>(
            tensor_signature.tensor_spec.first,
            ConstructTfTensorFromTensorSpec(requested_tensor.second.spec())));
        return absl::OkStatus();
      });
}

}  // namespace

absl::Status Model::Clear() {
  model_signature_.Clear();
  input_tf_tensors_.clear();
  requested_outputs_.clear();
  if (model_bundle_.session) {
    tensorflow::Status status = tensorflow::Reset(tensorflow::SessionOptions(),
                                                  std::vector<std::string>());
    if (!status.ok()) {
      return TensorflowStatusToAbseil(status);
    }
  }
  return absl::OkStatus();
}

absl::Status Model::Load(const std::string& model_path) {
  FALKEN_RETURN_IF_ERROR(Clear());
  tensorflow::Status model_status = tensorflow::LoadSavedModel(
      tensorflow::SessionOptions(), tensorflow::RunOptions(), model_path,
      {tensorflow::kSavedModelTagServe}, &model_bundle_);
  if (!model_status.ok()) {
    auto ignore = Clear();
    return TensorflowStatusToAbseil(model_status);
  }

  const auto& signature_def_map = model_bundle_.meta_graph_def.signature_def();
  const auto& signature = signature_def_map.find("action");
  if (signature == signature_def_map.end()) {
    auto ignore = Clear();
    return absl::NotFoundError(
          "No signature def found for model " + model_path);
  }
  auto status = SignatureDefToModelSignature(signature->second,
                                             model_signature_);
  if (!status.ok()) {
    auto ignore = Clear();
    return status;
  }
  return absl::OkStatus();
}

absl::Status Model::Prepare(
    const std::vector<tensor::NamedTensor>& input_named_tensors,
    const std::vector<tensor::NamedTensor>& output_named_tensors) {
  if (input_named_tensors.size() !=
      model_signature_.model_ports_to_inputs.size()) {
    auto ignore = Clear();
    return absl::FailedPreconditionError(
        absl::StrCat("Number of requested inputs ", input_named_tensors.size(),
                     " does not match the number of required inputs ",
                     model_signature_.model_ports_to_inputs.size()));
  }
  FALKEN_RETURN_IF_ERROR(TypeCheckAndPrepareTensors(
      "Input", model_signature_.model_ports_to_inputs, input_named_tensors,
      input_tf_tensors_));
  std::vector<std::pair<std::string, tensorflow::Tensor>> output_tf_tensors;
  FALKEN_RETURN_IF_ERROR(TypeCheckAndPrepareTensors(
      "Output", model_signature_.model_ports_to_outputs, output_named_tensors,
      output_tf_tensors));
  for (const auto& output_tf_tensor : output_tf_tensors) {
    requested_outputs_.push_back(std::move(output_tf_tensor.first));
  }
  return absl::OkStatus();
}

absl::Status Model::Run(
    const std::vector<tensor::NamedTensor>& input_named_tensors,
    std::vector<tensor::NamedTensor>& output_named_tensors) {
  ABSL_ASSERT(input_named_tensors.size() == input_tf_tensors_.size());
  for (int i = 0; i < input_named_tensors.size(); ++i) {
    FALKEN_RETURN_IF_ERROR(tensor::Tensor::Copy(
        input_named_tensors[i].second.dtype(), input_named_tensors[i].second,
        input_tf_tensors_[i].second));
  }

  std::vector<tensorflow::Tensor> output_tf_tensors;
  ABSL_ASSERT(output_named_tensors.size() == requested_outputs_.size());
  FALKEN_RETURN_IF_ERROR(TensorflowStatusToAbseil(model_bundle_.session->Run(
      input_tf_tensors_, requested_outputs_, std::vector<std::string>(),
      &output_tf_tensors)));
  ABSL_ASSERT(output_named_tensors.size() == output_tf_tensors.size());
  for (size_t i = 0; i < output_tf_tensors.size(); ++i) {
    FALKEN_RETURN_IF_ERROR(tensor::Tensor::Copy(
        output_named_tensors[i].second.dtype(), output_tf_tensors[i],
        output_named_tensors[i].second));
  }
  return absl::OkStatus();
}

}  // namespace tf_wrapper
}  // namespace falken

#endif  // FALKEN_ENABLE_TF
