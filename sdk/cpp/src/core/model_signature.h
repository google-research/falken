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

#ifndef FALKEN_SDK_CORE_MODEL_SIGNATURE_H_
#define FALKEN_SDK_CORE_MODEL_SIGNATURE_H_

#include <algorithm>
#include <functional>
#include <string>
#include <utility>
#include <vector>

#include "src/core/tensor.h"
#include "src/core/vector_search.h"
#include "absl/status/status.h"
#include "absl/strings/str_cat.h"

namespace falken {

// Tuple of TensorSpec name and the associated Tensor along with it's parameters
// in a graph.
struct ModelPort {
  ModelPort(const std::string& name_,
            const tensor::NamedTensorSpec& tensor_spec_)
      : name(name_), tensor_spec(tensor_spec_) {}

  // Name of the tensor spec used to create the tensor (i.e the original
  // signature of the graph's input or output).
  std::string name;
  // Description of the instanced tensor's input or output in the graph.
  // This is a TensorSpec vs. Tensor as it has no associated value.
  tensor::NamedTensorSpec tensor_spec;

  // Compare with the name member of this struct.
  static int NameComparator(const std::string& name,
                            const ModelPort& named_tensor) {
    return name.compare(named_tensor.name);
  }
};

// Information about a loaded model.
struct ModelSignature {
  // Maps the original tensor spec names used to construct the model to
  // input tensors in the graph.
  std::vector<ModelPort> model_ports_to_inputs;
  // Maps the original tensor spec names used to construct the model to
  // output tensors in the graph.
  std::vector<ModelPort> model_ports_to_outputs;

  // Clear the contents of this object.
  void Clear() {
    model_ports_to_inputs.clear();
    model_ports_to_outputs.clear();
  }

  // Sort inputs and outputs by tensor spec name.
  void Sort() {
    SortPortsByName(model_ports_to_inputs);
    SortPortsByName(model_ports_to_outputs);
  }

  // Find a tensor spec by name in the list of inputs.
  const ModelPort* FindInputPort(const std::string& tensor_spec_name) const {
    return FindPortByName(tensor_spec_name, model_ports_to_inputs);
  }

  // Find a tensor spec by name in the list of outputs.
  const ModelPort* FindOutputPort(const std::string& tensor_spec_name) const {
    return FindPortByName(tensor_spec_name, model_ports_to_outputs);
  }

  // Sort a list of tensors by tensor spec name.
  static void SortPortsByName(std::vector<ModelPort>& named_tensors) {
    std::sort(named_tensors.begin(), named_tensors.end(),
              [](const ModelPort& lhs, const ModelPort& rhs) {
                return lhs.name < rhs.name;
              });
  }

  // Find a tensor spec by name - the vector must be sorted first.
  static const ModelPort* FindPortByName(
      const std::string& tensor_spec_name,
      const std::vector<ModelPort>& named_tensors) {
    auto it = SearchSortedVectorByKey<std::string, ModelPort,
                                      ModelPort::NameComparator>(
        named_tensors, tensor_spec_name);
    return it != named_tensors.end() ? &(*it) : nullptr;
  }

  // Type check requested tensors against the model signature and call visit
  // for each requested tensor that matches the graph specification.
  //
  // For example:
  // std::vector<std::pair<std::string, std::string>> visited;
  // auto status = ModelSignature::TypeCheckTensors(
  //   "Input", signature.model_ports_to_inputs, requested_tensors,
  //   [&visited](const ModelPort& tensor_signature,
  //              const tensor::NamedTensor& requested_tensor) -> absl::Status {
  //     visited.push_back(
  //       {requested_tensor.first, tensor_signature.tensor_spec.first});
  //     return absl::OkStatus();
  //   }));
  static absl::Status TypeCheckTensors(
      const char* direction_description,
      const std::vector<ModelPort>& model_ports,
      const std::vector<tensor::NamedTensor>& requested_tensors,
      std::function<absl::Status(const ModelPort& tensor_signature,
                                 const tensor::NamedTensor& requested_tensor)>
          visit);
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_MODEL_SIGNATURE_H_
