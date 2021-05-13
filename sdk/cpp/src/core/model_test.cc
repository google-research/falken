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

#include <random>

#include "src/core/protos.h"
#include "falken/attribute_base.h"
#include "falken/brain_spec.h"
#include "src/core/status_macros.h"
#include "src/core/statusor.h"
#include "src/tf_wrapper/example_model.h"
#include "src/tf_wrapper/tf_wrapper.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "absl/base/macros.h"
#include "absl/flags/flag.h"
#include "absl/flags/parse.h"

namespace falken {
namespace core {

namespace {

std::random_device global_random;  // NOLINT

float RandomInRange(float minimum_value, float maximum_value) {
  std::uniform_real_distribution<float> distribution(minimum_value,
                                                     maximum_value);
  return distribution(global_random);
}

int RandomInRange(int minimum_value, int maximum_value) {
  std::uniform_int_distribution<int> distribution(minimum_value, maximum_value);
  return distribution(global_random);
}

void RandomizeAttribute(AttributeBase& attribute) {
  switch (attribute.type()) {
    case AttributeBase::kTypeFloat:
      attribute.set_number(RandomInRange(attribute.number_minimum(),
                                         attribute.number_maximum()));
      break;
    case AttributeBase::kTypeCategorical:
      attribute.set_category(
          RandomInRange(0, attribute.category_values().size() - 1));
      break;
    case AttributeBase::kTypeBool:
      attribute.set_boolean(RandomInRange(0, 1));
      break;
    case AttributeBase::kTypePosition:
      attribute.set_position(Position{RandomInRange(-5.0f, 5.0f),
                                      RandomInRange(-5.0f, 5.0f),
                                      RandomInRange(-5.0f, 5.0f)});
      break;
    case AttributeBase::kTypeRotation:
      attribute.set_rotation(
          Rotation{RandomInRange(-1.0f, 1.0f), RandomInRange(-1.0f, 1.0f),
                   RandomInRange(-1.0f, 1.0f), RandomInRange(-1.0f, 1.0f)});
      break;
    case AttributeBase::kTypeFeelers: {
      auto& distances = attribute.feelers_distances();
      for (int i = 0; i < distances.size(); ++i) {
        RandomizeAttribute(distances[i]);
      }
      auto& ids = attribute.feelers_ids();
      for (int i = 0; i < distances.size(); ++i) RandomizeAttribute(ids[i]);
      break;
    }
    default:
      ABSL_ASSERT("Invalid attribute type" == nullptr);
      break;
  }
}

struct Drinker : public EntityBase {
  Drinker(EntityContainer& container, const char* name)
      : EntityBase(container, name),
        FALKEN_NUMBER(evilness, 0.0f, 100.0f),
        FALKEN_CATEGORICAL(drink, {"GIN", "WHISKEY", "VODKA"}) {}

  NumberAttribute<float> evilness;
  CategoricalAttribute drink;
};

struct TestObservations : public ObservationsBase {
  TestObservations()
      : FALKEN_NUMBER(health, 0.0f, 100.0f),
        FALKEN_FEELERS(feeler, 3, 100.0f, 20.0f, 0.0f,
                       std::vector<std::string>{"nothing"}),
        FALKEN_ENTITY(bob),
        FALKEN_ENTITY(jim),
        FALKEN_ENTITY(wolf),
        FALKEN_ENTITY(camera) {}

  NumberAttribute<float> health;
  FeelersAttribute feeler;
  EntityBase bob;
  EntityBase jim;
  Drinker wolf;
  EntityBase camera;
};

struct TestActions : public ActionsBase {
  TestActions()
      : FALKEN_CATEGORICAL(switch_weapon,
                           {"NO_SWITCH", "KNIFE", "PISTOL", "SHOTGUN"}),
        FALKEN_NUMBER(throttle, -1.0f, 1.0f),
        FALKEN_JOYSTICK_DELTA_PITCH_YAW(joy_pitch_yaw,
                                        kControlledEntityPlayer),
        FALKEN_JOYSTICK_DIRECTION_XZ(joy_xz,
                                     kControlledEntityPlayer,
                                     kControlFrameCamera),
        FALKEN_JOYSTICK_DIRECTION_XZ(joy_xz_world,
                                     kControlledEntityPlayer,
                                     kControlFrameWorld) {}

  CategoricalAttribute switch_weapon;
  NumberAttribute<float> throttle;
  JoystickAttribute joy_pitch_yaw;
  JoystickAttribute joy_xz;
  JoystickAttribute joy_xz_world;
};

using TestBrainSpec = BrainSpec<TestObservations, TestActions>;

TEST(Model, LoadInvalidModelTest) {
  auto status = Model::CreateModel(TestBrainSpec(), "invalid_path");
  EXPECT_FALSE(status.ok());
}

TEST(Model, RunModelTest) {
  // This will read saved_model.pb and the variable files.
  TestBrainSpec brain_spec;
  auto model_or =
      Model::CreateModel(brain_spec, example_model::GetExampleModelPath());
  ASSERT_TRUE(model_or.ok());
  std::shared_ptr<Model> model = std::move(model_or.ValueOrDie());

  const int kIterations = 500;
  std::vector<int> switch_weapon;
  std::vector<float> throttle;
  std::vector<std::pair<float, float>> joy_pitch_yaw;
  std::vector<std::pair<float, float>> joy_xz;
  std::vector<std::pair<float, float>> joy_xz_world;
  switch_weapon.reserve(kIterations);
  throttle.reserve(kIterations);
  for (int i = 0; i < kIterations; ++i) {
    TestObservations& observations = brain_spec.observations;
    RandomizeAttribute(observations.health);
    RandomizeAttribute(observations.feeler);
    RandomizeAttribute(observations.bob.position);
    RandomizeAttribute(observations.bob.rotation);
    RandomizeAttribute(observations.jim.position);
    RandomizeAttribute(observations.jim.rotation);
    RandomizeAttribute(observations.wolf.position);
    RandomizeAttribute(observations.wolf.rotation);
    RandomizeAttribute(observations.wolf.evilness);
    RandomizeAttribute(observations.wolf.drink);
    RandomizeAttribute(observations.camera.position);
    RandomizeAttribute(observations.camera.rotation);
    ASSERT_TRUE(model->RunModel(brain_spec).ok());
    TestActions& actions = brain_spec.actions;
    switch_weapon.push_back(static_cast<int>(actions.switch_weapon));
    throttle.push_back(static_cast<float>(actions.throttle));
    joy_pitch_yaw.push_back(
        std::make_pair(actions.joy_pitch_yaw.x_axis(),
                       actions.joy_pitch_yaw.y_axis()));
    joy_xz.push_back(
        std::make_pair(actions.joy_xz.x_axis(),
                       actions.joy_xz.y_axis()));
    joy_xz_world.push_back(
        std::make_pair(actions.joy_xz_world.x_axis(),
                       actions.joy_xz_world.y_axis()));
  }

  // Calculate average actions, each should be non-zero as the model is
  // initialized to random weights.
  float average_switch_weapon = 0.0f;
  float average_throttle = 0.0f;
  std::pair<float, float> average_joy_pitch_yaw{0.0f, 0.0f};
  std::pair<float, float> average_joy_xz{0.0f, 0.0f};
  std::pair<float, float> average_joy_xz_world{0.0f, 0.0f};

  for (int i = 0; i < kIterations; ++i) {
    average_switch_weapon += static_cast<float>(switch_weapon[i]);
    average_throttle += throttle[i];
    std::get<0>(average_joy_pitch_yaw) += std::get<0>(joy_pitch_yaw[i]);
    std::get<1>(average_joy_pitch_yaw) += std::get<1>(joy_pitch_yaw[i]);
    std::get<0>(average_joy_xz) += std::get<0>(joy_xz[i]);
    std::get<1>(average_joy_xz) += std::get<1>(joy_xz[i]);
    std::get<0>(average_joy_xz_world) += std::get<0>(joy_xz_world[i]);
    std::get<1>(average_joy_xz_world) += std::get<1>(joy_xz_world[i]);
  }
  average_switch_weapon /= kIterations;
  average_throttle /= kIterations;
  std::get<0>(average_joy_pitch_yaw) /= kIterations;
  std::get<1>(average_joy_pitch_yaw) /= kIterations;
  std::get<0>(average_joy_xz) /= kIterations;
  std::get<1>(average_joy_xz) /= kIterations;
  std::get<0>(average_joy_xz_world) /= kIterations;
  std::get<1>(average_joy_xz_world) /= kIterations;
  ASSERT_NE(average_switch_weapon, 0.0f);
  ASSERT_NE(average_throttle, 0.0f);
  ASSERT_NE(std::get<0>(average_joy_pitch_yaw), 0.0f);
  ASSERT_NE(std::get<1>(average_joy_pitch_yaw), 0.0f);
  ASSERT_NE(std::get<0>(average_joy_xz), 0.0f);
  ASSERT_NE(std::get<1>(average_joy_xz), 0.0f);
  ASSERT_NE(std::get<0>(average_joy_xz_world), 0.0f);
  ASSERT_NE(std::get<1>(average_joy_xz_world), 0.0f);
}

}  // namespace

}  // namespace core
}  // namespace falken

// Define main so ParseCommandLine can be called and command line arguments can
// be retrieved.
int main(int argc, char** argv) {
  testing::InitGoogleTest(&argc, argv);
  absl::ParseCommandLine(argc, argv);
  return RUN_ALL_TESTS();
}
