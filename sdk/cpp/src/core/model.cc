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

#include "src/core/model.h"

#include <algorithm>
#include <functional>
#include <memory>
#include <string>
#include <utility>

#include "src/core/model_signature.h"
#include "src/core/status_macros.h"
#include "src/core/statusor.h"
#include "src/core/tensor.h"
#include "src/core/assert.h"
#include "src/core/log.h"
#include "falken/attribute_base.h"
#include "falken/brain_spec.h"
#include "falken/entity.h"
#include "src/tf_wrapper/tf_wrapper.h"
#include "absl/memory/memory.h"
#include "absl/status/status.h"
#include "absl/strings/str_cat.h"
#include "absl/strings/str_join.h"

namespace falken {

class AttributeTensorConverter {
 public:
  // Get the tensor specification for an attribute.
  static tensor::TensorSpec ToTensorSpec(const char* attribute_path,
                                         const AttributeBase& attribute) {
    switch (attribute.type()) {
      case AttributeBase::kTypeFloat:
        return tensor::TensorSpec(tensor::DT_FLOAT,
                                  tensor::TensorShape({1, 1}));
      case AttributeBase::kTypeCategorical:
        return tensor::TensorSpec(tensor::DT_INT32,
                                  tensor::TensorShape({1, 1}));
      case AttributeBase::kTypeBool:
        return tensor::TensorSpec(tensor::DT_INT32,
                                  tensor::TensorShape({1, 1}));
      case AttributeBase::kTypePosition:
        return tensor::TensorSpec(tensor::DT_FLOAT,
                                  tensor::TensorShape({1, 3}));
      case AttributeBase::kTypeRotation:
        return tensor::TensorSpec(tensor::DT_FLOAT,
                                  tensor::TensorShape({1, 4}));
      case AttributeBase::kTypeFeelers:
        return tensor::TensorSpec(
            tensor::DT_FLOAT,
            tensor::TensorShape({
                1,
                static_cast<tensor::TensorShapeDimension>(
                    std::max(attribute.feelers_distances().size(),
                             attribute.feelers_ids().size())),
                1 + static_cast<tensor::TensorShapeDimension>(
                    attribute.number_of_feelers_ids()),
            }));
      case AttributeBase::kTypeJoystick:
        return tensor::TensorSpec(
            tensor::DT_FLOAT,
            tensor::TensorShape({1, 2}));
      default:
        LogFatal("Attribute %s has invalid type %d", attribute_path,
                 attribute.type());
        break;
    }
    return tensor::TensorSpec();
  }

  // Populate a tensor from an attribute.
  static void ToTensor(const AttributeBase& attribute, tensor::Tensor& tensor) {
    switch (attribute.type()) {
      case AttributeBase::kTypeFloat:
        tensor.flat<float>()(0) = attribute.number();
        break;
      case AttributeBase::kTypeCategorical:
        tensor.flat<int32_t>()(0) = attribute.category();
        break;
      case AttributeBase::kTypeBool:
        tensor.flat<int32_t>()(0) = attribute.boolean() ? 1 : 0;
        break;
      case AttributeBase::kTypePosition: {
        const auto& position = attribute.position();
        auto elements = tensor.flat<float>();
        elements(0) = position.x;
        elements(1) = position.y;
        elements(2) = position.z;
        break;
      }
      case AttributeBase::kTypeRotation: {
        const auto& rotation = attribute.rotation();
        auto elements = tensor.flat<float>();
        elements(0) = rotation.x;
        elements(1) = rotation.y;
        elements(2) = rotation.z;
        elements(3) = rotation.w;
        break;
      }
      case AttributeBase::kTypeFeelers: {
        const auto& distances = attribute.feelers_distances();
        const auto& ids = attribute.feelers_ids();
        int number_of_feelers = std::max(distances.size(), ids.size());
        int number_of_feelers_ids = attribute.number_of_feelers_ids();
        auto elements = tensor.flat<float>();
        int element_index = 0;
        bool has_distances = !distances.empty();
        bool has_ids = !ids.empty();
        for (int feeler_index = 0; feeler_index < number_of_feelers;
             ++feeler_index) {
          elements(element_index++) =
              has_distances ? distances[feeler_index].value() : 0.0f;
          // One-hot encode the ID.
          if (has_ids) {
            int current_feeler_id = ids[feeler_index].value();
            for (int id = 0; id < number_of_feelers_ids; ++id) {
              elements(element_index++) = id == current_feeler_id ? 1 : 0;
            }
          }
        }
        break;
      }
      case AttributeBase::kTypeJoystick: {
        auto elements = tensor.flat<float>();
        elements(0) = attribute.joystick_x_axis();
        elements(1) = attribute.joystick_y_axis();
        break;
      }
      default:
        LogFatal("Attribute %s has invalid type.", attribute.name(),
                 attribute.type());
        break;
    }
  }

  // Populate an attribute from a tensor.
  static void ToAttribute(const tensor::Tensor& tensor,
                          AttributeBase& attribute) {
    switch (attribute.type()) {
      case AttributeBase::kTypeFloat:
        attribute.set_number(tensor.flat<float>()(0));
        break;
      case AttributeBase::kTypeCategorical:
        attribute.set_category(tensor.flat<int32_t>()(0));
        break;
      case AttributeBase::kTypeBool:
        attribute.set_boolean(tensor.flat<int32_t>()(0) != 0);
        break;
      case AttributeBase::kTypeJoystick:
        attribute.set_joystick_x_axis(tensor.flat<float>()(0));
        attribute.set_joystick_y_axis(tensor.flat<float>()(1));
        break;
      default:
        LogFatal("Action attribute %s has invalid type.", attribute.name(),
                 attribute.type());
        break;
    }
  }
};

namespace core {

namespace {

using absl::Status;
using falken::common::StatusOr;

// Join attribute path components.
std::string JoinAttributePath(const char* parent, const char* child) {
  ABSL_ASSERT(parent);
  return absl::StrJoin({parent, child ? child : ""}, "/");
}

// Called when visiting attributes, return absl::OkStatus() to continue
// iteration.
typedef std::function<absl::Status(const std::string& attribute_path,
                                   AttributeBase& attribute)>
    VisitAttributeWithPathFunction;

// Visit all attributes in an attribute container with the path to the
// attribute.
absl::Status VisitAttributesInContainer(
    AttributeContainer& attribute_container,
    const VisitAttributeWithPathFunction& visit, const char* parent_path) {
  for (auto& attribute : attribute_container.attributes()) {
    FALKEN_RETURN_IF_ERROR(
        visit(JoinAttributePath(parent_path, attribute->name()), *attribute));
  }
  return absl::OkStatus();
}

// Visit all attributes in an entity container with the path to the attribute.
absl::Status VisitAttributesInContainer(
    EntityContainer& entity_container,
    const VisitAttributeWithPathFunction& visit, const char* parent_path) {
  auto& entities = entity_container.entities();
  int global_entity_index = 0;
  for (int i = 0; i < entities.size(); ++i) {
    auto& entity = *entities[i];
    // Unfortunately, entities are identified by index in the brain spec proto
    // and the player is special cased as a top level member of the observation
    // proto.
    const char* entity_name = entity.name();
    std::string global_entity_index_string;
    if (strcmp(entity_name, "player") != 0 &&
        strcmp(entity_name, "camera") != 0) {
      global_entity_index_string = JoinAttributePath(
          "global_entities", std::to_string(global_entity_index).c_str());
      global_entity_index++;
      entity_name = global_entity_index_string.c_str();
    }
    FALKEN_RETURN_IF_ERROR(VisitAttributesInContainer(
        entity, visit, JoinAttributePath(parent_path, entity_name).c_str()));
  }
  return absl::OkStatus();
}

// Called when visiting attributes.
typedef std::function<void(AttributeBase& attribute)> VisitAttributeFunction;

// Visit all attributes in an attribute container.
void VisitAttributesInContainer(AttributeContainer& attribute_container,
                                const VisitAttributeFunction& visit) {
  for (auto& attribute : attribute_container.attributes()) visit(*attribute);
}

// Visit all attributes in an entity container.
void VisitAttributesInContainer(EntityContainer& entity_container,
                                const VisitAttributeFunction& visit) {
  for (auto& entity : entity_container.entities()) {
    VisitAttributesInContainer(*entity, visit);
  }
}

// Create a tensor for the specified attribute (attribute_path / attribute)
// using a spec from the model signature provided by tensor_spec_named and add
// to the tensors vector.
absl::Status CreateNamedTensorForAttribute(
    const std::string& attribute_path, AttributeBase& attribute,
    const std::vector<ModelPort>& model_ports, const std::string& graph_io_name,
    std::vector<tensor::NamedTensor>& tensors) {
  const auto* tensor_spec_in_graph =
      ModelSignature::FindPortByName(attribute_path, model_ports);
  if (!tensor_spec_in_graph) {
    return absl::NotFoundError(absl::StrCat(
        graph_io_name, " attribute ", attribute_path,
        " not found in model."));
  }
  tensor::TensorSpec attribute_tensor_spec =
      AttributeTensorConverter::ToTensorSpec(attribute_path.c_str(), attribute);
  // Make sure the attribute tensor spec matches the requirements of the
  // graph.
  auto spec_compare_status = tensor::TensorSpec::Compare(
      attribute_tensor_spec, tensor_spec_in_graph->tensor_spec.second);
  if (!spec_compare_status.ok()) {
    return absl::FailedPreconditionError(
        absl::StrCat(graph_io_name, " attribute ", attribute_path,
                     " tensor spec does not match model ",
                     spec_compare_status.message()));
  }
  tensors.push_back(tensor::NamedTensor(std::string(tensor_spec_in_graph->name),
                                        tensor::Tensor(attribute_tensor_spec)));
  return absl::OkStatus();
}

// T is the attribute container type, EntityContainer or AttributeContainer.
template <typename T>
absl::Status CreateNamedTensors(
    const T& container, const char* attribute_tensor_spec_name_prefix,
    const std::vector<ModelPort>& model_ports,
    const std::vector<std::string>& unused_tensor_io_names,
    const std::string& graph_io_name,
    std::vector<tensor::NamedTensor>& tensors) {
  tensors.clear();
  tensors.reserve(model_ports.size());

  // Create tensors for attributes.
  FALKEN_RETURN_IF_ERROR(VisitAttributesInContainer(
      // const_cast here is ok as we don't mutate the container.
      const_cast<T&>(container),
      [&tensors, &model_ports, &graph_io_name](
          const std::string& attribute_path, AttributeBase& attribute) {
        return CreateNamedTensorForAttribute(
            attribute_path, attribute, model_ports, graph_io_name, tensors);
      },
      attribute_tensor_spec_name_prefix));

  // Create tensors for unused I/O.
  // We are using frameworks in the service to train models with inputs that
  // we don't currently use, so populate these with empty tensors.
  for (auto& unused_name : unused_tensor_io_names) {
    const auto* tensor_spec_in_graph =
        ModelSignature::FindPortByName(unused_name, model_ports);
    if (!tensor_spec_in_graph) {
      return absl::NotFoundError(graph_io_name + " " + unused_name +
                                 " not found in model.");
    }
    tensors.push_back(tensor::NamedTensor(
        std::string(tensor_spec_in_graph->name),
        tensor::Tensor(tensor_spec_in_graph->tensor_spec.second)));
  }

  // Make sure that all tensors are populated.
  if (model_ports.size() != tensors.size()) {
    std::stringstream message;
    message << "The brain spec does not match the model. ";
    message << graph_io_name << "s from brain spec [";
    for (auto& tensor : tensors) {
      message << tensor.first;
      message << ", ";
    }
    message << "]\nvs. the model [";
    for (auto& tensor_spec : model_ports) {
      message << tensor_spec.name;
      message << ", ";
    }
    message << "]";
    return absl::FailedPreconditionError(message.str());
  }
  return absl::OkStatus();
}

absl::Status CreateTensorsForObservations(
    const ObservationsBase& observations, const ModelSignature& model_signature,
    std::vector<tensor::NamedTensor>& tensors) {
  return CreateNamedTensors(
      static_cast<const EntityContainer&>(observations), "0/observation",
      model_signature.model_ports_to_inputs,
      {"0/reward", "0/step_type", "0/discount"}, "Input", tensors);
}

absl::Status CreateTensorsForActions(
    const ActionsBase& actions, const ModelSignature& model_signature,
    std::vector<tensor::NamedTensor>& tensors) {
  return CreateNamedTensors(actions, "action",
                            model_signature.model_ports_to_outputs,
                            std::vector<std::string>(), "Output", tensors);
}
}  // namespace

Model::Model(tf_wrapper::TFWrapper* tf_wrapper_model,
             std::vector<tensor::NamedTensor>&& input_tensors,
             std::vector<tensor::NamedTensor>&& output_tensors) {
  tf_wrapper_model_ = tf_wrapper_model;
  input_tensors_ = std::move(input_tensors);
  output_tensors_ = std::move(output_tensors);
}

Model::~Model() {
  delete tf_wrapper_model_;
  tf_wrapper_model_ = nullptr;
}

StatusOr<std::shared_ptr<Model>> Model::CreateModel(
    const BrainSpecBase& brain_spec, const std::string& path) {
  ModelSignature model_signature;
  auto tf_wrapper_model = absl::make_unique<tf_wrapper::TFWrapper>();
  FALKEN_RETURN_IF_ERROR(tf_wrapper_model->LoadModel(path, model_signature));

  std::vector<tensor::NamedTensor> input_tensors;
  FALKEN_RETURN_IF_ERROR(CreateTensorsForObservations(
      brain_spec.observations_base(), model_signature, input_tensors));

  std::vector<tensor::NamedTensor> output_tensors;
  FALKEN_RETURN_IF_ERROR(CreateTensorsForActions(
      brain_spec.actions_base(), model_signature, output_tensors));

  FALKEN_RETURN_IF_ERROR(
      tf_wrapper_model->PrepareModel(input_tensors, output_tensors));

  return std::shared_ptr<Model>(new Model(tf_wrapper_model.release(),
                                          std::move(input_tensors),
                                          std::move(output_tensors)));
}

// Runs inference on the model, reading observations from the provided brain
// spec and writing the actions to the same object.
absl::Status Model::RunModel(BrainSpecBase& brain_spec) {
  int attribute_index = 0;
  auto& input_tensors = input_tensors_;
  VisitAttributesInContainer(
      static_cast<EntityContainer&>(brain_spec.observations_base()),
      [&input_tensors, &attribute_index](AttributeBase& attribute) {
        AttributeTensorConverter::ToTensor(
            attribute, input_tensors[attribute_index++].second);
      });

  FALKEN_RETURN_IF_ERROR(
      tf_wrapper_model_->RunModel(input_tensors_, output_tensors_));

  attribute_index = 0;
  auto& output_tensors = output_tensors_;
  VisitAttributesInContainer(
      brain_spec.actions_base(),
      [&output_tensors, &attribute_index](AttributeBase& attribute) {
        AttributeTensorConverter::ToAttribute(
            output_tensors[attribute_index++].second, attribute);
      });
  return absl::OkStatus();
}

}  // namespace core
}  // namespace falken
