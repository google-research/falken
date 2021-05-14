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

#include "src/tf_wrapper/example_model.h"

#include <fstream>
#include <random>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

#include <google/protobuf/text_format.h>
#include "src/core/log.h"
#include "absl/flags/flag.h"
#include "absl/strings/str_replace.h"

ABSL_FLAG(std::string, example_model_path, "",
          "The path of the example model used for testing.");

namespace falken {
namespace example_model {

using falken::tensor::DataType;
using falken::tensor::NamedTensor;
using falken::tensor::Tensor;

namespace {

// Read an example model text proto.
std::string ReadExampleModelTextProto(const std::string& proto_file) {
  std::string filename = GetExampleModelPath() + proto_file;
  std::ifstream file(filename.c_str());
  if (!file.is_open()) {
    LogFatal("Failed to read %s.", filename.c_str());
    return std::string();
  }
  std::stringstream buffer;
  buffer << file.rdbuf();
  file.close();
  return buffer.str();
}

// Format a string like Python's str.format().
std::string Format(
    const std::string& to_format,
    const std::vector<std::pair<std::string, std::string>>& replacements) {
  std::vector<std::pair<std::string, std::string>> expanded_replacements;
  expanded_replacements.reserve(replacements.size());
  for (auto& it : replacements) {
    expanded_replacements.push_back({"{" + it.first + "}", it.second});
  }
  // Unescape "{{" as "{" and "}}" as "}".
  // Python format strings are formatted with replaced tokens in the form
  // "{token}" so { and } are escaped with {{ and }} respectively.
  expanded_replacements.push_back({"{{", "{"});
  expanded_replacements.push_back({"}}", "}"});
  return absl::StrReplaceAll(to_format, expanded_replacements);
}

}  // namespace

proto::ObservationSpec ObservationSpec() {
  proto::ObservationSpec observation_spec;
  google::protobuf::TextFormat::ParseFromString(
      ReadExampleModelTextProto("observation_spec.pbtxt"), &observation_spec);
  return observation_spec;
}

proto::ActionSpec ActionSpec() {
  proto::ActionSpec action_spec;
  google::protobuf::TextFormat::ParseFromString(
      ReadExampleModelTextProto("action_spec.pbtxt"), &action_spec);
  return action_spec;
}

proto::ObservationData ObservationData() {
  proto::ObservationData observation_data;
  google::protobuf::TextFormat::ParseFromString(
      Format(ReadExampleModelTextProto("observation_data.pbtxt_template"),
             {{"position0", "0"},
              {"position1", "1"},
              {"position2", "2"},
              {"health", "50.0"}}),
      &observation_data);
  return observation_data;
}

proto::ActionData ActionData() {
  proto::ActionData action_data;
  google::protobuf::TextFormat::ParseFromString(
      Format(ReadExampleModelTextProto("action_data.pbtxt_template"),
             {{"switch_weapon", "0"}, {"throttle", "0.2"}}),
      &action_data);
  return action_data;
}

std::string GetExampleModelPath() {
  return absl::GetFlag(FLAGS_example_model_path);
}

std::vector<NamedTensor> CreateNamedInputs() {
  // Should match the spec in example_model/observation_spec.pbtxt
  std::vector<NamedTensor> inputs{
      NamedTensor{"0/discount", Tensor(DataType::DT_FLOAT, {1})},
      NamedTensor{"0/observation/camera/position",
                  Tensor(DataType::DT_FLOAT, {1, 3})},
      NamedTensor{"0/observation/camera/rotation",
                  Tensor(DataType::DT_FLOAT, {1, 4})},
      NamedTensor{"0/observation/global_entities/0/position",
                  Tensor(DataType::DT_FLOAT, {1, 3})},
      NamedTensor{"0/observation/global_entities/0/rotation",
                  Tensor(DataType::DT_FLOAT, {1, 4})},
      NamedTensor{"0/observation/global_entities/1/position",
                  Tensor(DataType::DT_FLOAT, {1, 3})},
      NamedTensor{"0/observation/global_entities/1/rotation",
                  Tensor(DataType::DT_FLOAT, {1, 4})},
      NamedTensor{"0/observation/global_entities/2/position",
                  Tensor(DataType::DT_FLOAT, {1, 3})},
      NamedTensor{"0/observation/global_entities/2/rotation",
                  Tensor(DataType::DT_FLOAT, {1, 4})},
      NamedTensor{"0/observation/global_entities/2/drink",
                  Tensor(DataType::DT_INT32, {1, 1})},
      NamedTensor{"0/observation/global_entities/2/evilness",
                  Tensor(DataType::DT_FLOAT, {1, 1})},
      NamedTensor{"0/observation/player/position",
                  Tensor(DataType::DT_FLOAT, {1, 3})},
      NamedTensor{"0/observation/player/rotation",
                  Tensor(DataType::DT_FLOAT, {1, 4})},
      NamedTensor{"0/observation/player/health",
                  Tensor(DataType::DT_FLOAT, {1, 1})},
      NamedTensor{"0/observation/player/feeler",
                  Tensor(DataType::DT_FLOAT, {1, 3, 2})},
      NamedTensor{"0/reward", Tensor(DataType::DT_FLOAT, {1})},
      NamedTensor{"0/step_type", Tensor(DataType::DT_INT32, {1})},
  };
  RandomizeInputs(inputs);
  return inputs;
}

std::vector<NamedTensor> CreateNamedOutputs() {
  // Should match the spec in example_model/action_spec.pbtxt
  return {
      NamedTensor{"action/switch_weapon", Tensor(DataType::DT_INT32, {1})},
      NamedTensor{"action/throttle", Tensor(DataType::DT_FLOAT, {1})},
      NamedTensor{"action/joy_pitch_yaw", Tensor(DataType::DT_FLOAT, {2})},
      NamedTensor{"action/joy_xz", Tensor(DataType::DT_FLOAT, {2})},
      NamedTensor{"action/joy_xz_world", Tensor(DataType::DT_FLOAT, {2})},
  };
}

template <typename ElementType, typename RandomNumberGeneratorType>
void RandomizeTensor(tensor::TensorMap<ElementType>& tensor_map,
                     RandomNumberGeneratorType&& random_distribution) {
  static std::random_device random;  // NOLINT
  int size = tensor_map.size();
  for (int i = 0; i < size; ++i) tensor_map(i) = random_distribution(random);
}

template <typename T>
void RandomizeTensor(tensor::TensorMap<T>&& tensor_map, T minimum_value,
                     T maximum_value) {
  RandomizeTensor(tensor_map, std::uniform_real_distribution<float>(
                                  minimum_value, maximum_value));
}

template <>
void RandomizeTensor(tensor::TensorMap<int>&& tensor_map, int minimum_value,
                     int maximum_value) {
  RandomizeTensor(tensor_map, std::uniform_int_distribution<int>(
                                  minimum_value, maximum_value));
}

// Populate inputs for the test model with random data.
void RandomizeInputs(std::vector<falken::tensor::NamedTensor>& inputs) {
  int i = 0;
  // 0/discount
  RandomizeTensor(inputs[i++].second.flat<float>(), 0.0f, 1.0f);
  // 0/observation/camera/position
  RandomizeTensor(inputs[i++].second.flat<float>(), -1.0f, 1.0f);
  // 0/observation/rotation/position
  RandomizeTensor(inputs[i++].second.flat<float>(), -1.0f, 1.0f);
  // 0/observation/global_entities/0/position
  RandomizeTensor(inputs[i++].second.flat<float>(), -10.0f, 10.0f);
  // 0/observation/global_entities/0/rotation
  RandomizeTensor(inputs[i++].second.flat<float>(), -1.0f, 1.0f);
  // 0/observation/global_entities/1/position
  RandomizeTensor(inputs[i++].second.flat<float>(), -10.0f, 10.0f);
  // 0/observation/global_entities/1/rotation
  RandomizeTensor(inputs[i++].second.flat<float>(), -1.0f, 1.0f);
  // 0/observation/global_entities/2/position
  RandomizeTensor(inputs[i++].second.flat<float>(), -10.0f, 10.0f);
  // 0/observation/global_entities/2/rotation
  RandomizeTensor(inputs[i++].second.flat<float>(), -1.0f, 1.0f);
  // 0/observation/global_entities/2/drink
  RandomizeTensor(inputs[i++].second.flat<int>(), 0, 2);
  // 0/observation/global_entities/2/evilness
  RandomizeTensor(inputs[i++].second.flat<float>(), 0.0f, 100.0f);
  // 0/observation/player/position
  RandomizeTensor(inputs[i++].second.flat<float>(), -10.0f, 10.0f);
  // 0/observation/player/rotation
  RandomizeTensor(inputs[i++].second.flat<float>(), -1.0f, 1.0f);
  // 0/observation/player/health
  RandomizeTensor(inputs[i++].second.flat<float>(), 0.0f, 100.0f);
  // 0/observation/player/feeler
  // NOTE: This isn't correct as feeler distances for the example can be between
  // 0..100 and experimental data should really be one-hot encoded.
  RandomizeTensor(inputs[i++].second.flat<float>(), 0.0f, 100.0f);
  // 0/reward
  RandomizeTensor(inputs[i++].second.flat<float>(), 0.0f, 1.0f);
  // 0/step_type
  RandomizeTensor(inputs[i++].second.flat<int>(), 0, 10);
}

}  // namespace example_model
}  // namespace falken
