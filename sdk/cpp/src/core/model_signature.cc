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

namespace falken {

absl::Status ModelSignature::TypeCheckTensors(
    const char* direction_description,
    const std::vector<ModelPort>& model_ports,
    const std::vector<tensor::NamedTensor>& requested_tensors,
    std::function<absl::Status(const ModelPort& tensor_signature,
                               const tensor::NamedTensor& requested_tensor)>
        visit) {
  for (const auto& requested_tensor : requested_tensors) {
    const auto* tensor_signature =
        ModelSignature::FindPortByName(requested_tensor.first, model_ports);
    if (!tensor_signature) {
      return absl::FailedPreconditionError(
          absl::StrCat(direction_description, " ", requested_tensor.first,
                       " not found on model."));
    }
    auto compare_status = tensor::TensorSpec::Compare(
        requested_tensor.second.spec(), tensor_signature->tensor_spec.second);
    if (!compare_status.ok()) {
      return absl::FailedPreconditionError(
          absl::StrCat(direction_description, " ", requested_tensor.first,
                       " does not match the expected tensor format: ",
                       compare_status.message()));
    }
    auto visit_status = visit(*tensor_signature, requested_tensor);
    if (!visit_status.ok()) {
      return absl::FailedPreconditionError(absl::StrCat(
          direction_description, " ", requested_tensor.first,
          " failed to map to tensor ", tensor_signature->tensor_spec.first,
          " (", visit_status.message(), ")"));
    }
  }
  return absl::OkStatus();
}

}  // namespace falken
