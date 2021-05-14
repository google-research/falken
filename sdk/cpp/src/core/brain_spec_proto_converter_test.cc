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

#include "src/core/brain_spec_proto_converter.h"

#include <memory>

#include <google/protobuf/text_format.h>
#include "src/core/protos.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "absl/strings/str_format.h"

namespace {

using ::testing::ElementsAreArray;

const char kActionSpec[] = R"pb(
  actions {
    name: "NumberAction"
    number { minimum: -1.0 maximum: 1.0 }
  }
  actions {
    name: "CategoryAction"
    category { enum_values: "Off" enum_values: "On" }
  }
)pb";

const char kObservationSpec[] = R"pb(
  player {
    position {}
    entity_fields {
      name: "NumberAction"
      number { minimum: -1.0 maximum: 1.0 }
    }
    entity_fields {
      name: "CategoryAction"
      category { enum_values: "Off" enum_values: "On" }
    }
  }
)pb";

const char kBrainSpec[] = R"pb(
  observation_spec {
    player {
      position {}
      rotation {}
      entity_fields {
        name: "health"
        number { minimum: %f maximum: %f }
      }
      entity_fields {
        name: "feelers"
        feeler {
          count: 2
          distance { maximum: 1 }
          yaw_angles: -60
          yaw_angles: 60
          experimental_data { maximum: 1 }
          experimental_data { maximum: 1 }
          experimental_data { maximum: 1 }
          thickness: 0.2
        }
      }
    }
    global_entities {
      position {}
      rotation {}
      entity_fields {
        name: "spells"
        category { enum_values: "%s" enum_values: "%s" }
      }
      entity_fields {
        name: "happiness"
        number { minimum: %f maximum: %f }
      }
    }
    global_entities {
      position {}
      rotation {}
      entity_fields {
        name: "evilness"
        number { minimum: 1.0 maximum: 5.0 }
      }
      entity_fields {
        name: "magic"
        number { minimum: 5.0 maximum: 50.0 }
      }
    }
  }
  action_spec {
    actions {
      name: "speed"
      number { minimum: %f maximum: %f }
    }
  }
)pb";

struct TestObservations : public falken::ObservationsBase {
 public:
  TestObservations() : FALKEN_NUMBER(health, 1.0f, 3.0f) {}

  falken::NumberAttribute<float> health;
};

struct TestActions : public falken::ActionsBase {
 public:
  TestActions() : falken::ActionsBase(), FALKEN_NUMBER(speed, 5.0f, 10.0f) {}

  falken::NumberAttribute<float> speed;
};

struct TestEnemyEntityBase : public falken::EntityBase {
 public:
  TestEnemyEntityBase(falken::EntityContainer& container, const char* name)
      : falken::EntityBase(container, name),
        FALKEN_NUMBER(evilness, 1.0f, 5.0f),
        FALKEN_NUMBER(magic, 5.0f, 50.0f) {}

  falken::NumberAttribute<float> evilness;
  falken::NumberAttribute<float> magic;
};

struct TestAllyEntityBase : public falken::EntityBase {
 public:
  TestAllyEntityBase(falken::EntityContainer& container, const char* name)
      : falken::EntityBase(container, name),
        FALKEN_NUMBER(happiness, 2.0f, 3.0f),
        FALKEN_CATEGORICAL(spells, {"dark", "ice"}) {}

  falken::NumberAttribute<float> happiness;
  falken::CategoricalAttribute spells;
};

struct TestExtendedObservationsBase : public falken::ObservationsBase {
 public:
  TestExtendedObservationsBase()
      : ObservationsBase(),
        FALKEN_NUMBER(health, 1.0f, 3.0f),
        FALKEN_FEELERS(feelers, 2, 1, 120, 0.2f, {"foo", "bar", "baz"}),
        FALKEN_ENTITY(enemy_entity_base),
        FALKEN_ENTITY(ally_entity_base) {}

  falken::NumberAttribute<float> health;
  falken::FeelersAttribute feelers;
  TestEnemyEntityBase enemy_entity_base;
  TestAllyEntityBase ally_entity_base;
};

using TestTemplateBrainSpec =
    falken::BrainSpec<TestExtendedObservationsBase, TestActions>;

TEST(BrainSpecProtoConverter, TestFromBrainSpec) {
  falken::proto::BrainSpec brain_spec;
  google::protobuf::TextFormat::ParseFromString(kActionSpec,
                                      brain_spec.mutable_action_spec());
  google::protobuf::TextFormat::ParseFromString(kObservationSpec,
                                      brain_spec.mutable_observation_spec());
  std::unique_ptr<falken::BrainSpecBase> brain_spec_base =
      falken::BrainSpecProtoConverter::FromBrainSpec(brain_spec);
  ASSERT_TRUE(brain_spec_base);
  const falken::EntityBase* player_entity =
      brain_spec_base->observations_base().entity("player");
  // Position and rotation are added automatically, that's why they are four.
  EXPECT_EQ(player_entity->attributes().size(), 4);
  falken::AttributeBase* number_action_attribute =
      player_entity->attribute("NumberAction");
  falken::AttributeBase* category_action_attribute =
      player_entity->attribute("CategoryAction");
  EXPECT_TRUE(number_action_attribute);
  EXPECT_EQ(number_action_attribute->number_maximum(), 1.0f);
  EXPECT_EQ(number_action_attribute->number_minimum(), -1.0f);
  EXPECT_TRUE(category_action_attribute);
  EXPECT_THAT(category_action_attribute->category_values(),
              ElementsAreArray({"Off", "On"}));

  const falken::ActionsBase& actions_base = brain_spec_base->actions_base();
  EXPECT_EQ(actions_base.attributes().size(), 2);
  EXPECT_TRUE(actions_base.attribute("NumberAction"));
  EXPECT_EQ(actions_base.attribute("NumberAction")->number_maximum(), 1.0f);
  EXPECT_EQ(actions_base.attribute("NumberAction")->number_minimum(), -1.0f);
  EXPECT_TRUE(actions_base.attribute("CategoryAction"));
  EXPECT_THAT(actions_base.attribute("CategoryAction")->category_values(),
              ElementsAreArray({"Off", "On"}));
}

TEST(BrainSpecProtoConverter, TestTemplateFromBrainSpec) {
  constexpr float player_health_min = 1.0f;
  constexpr float player_health_max = 3.0f;
  constexpr const char* const global_entity_dark_spell = "dark";
  constexpr const char* const global_entity_ice_spell = "ice";
  constexpr float global_entity_happiness_min = 2.0f;
  constexpr float global_entity_happiness_max = 3.0f;
  constexpr float action_speed_min = 5.0f;
  constexpr float action_speed_max = 10.0f;
  const std::string brain_spec_formatted =
      absl::StrFormat(kBrainSpec, player_health_min, player_health_max,
                      global_entity_dark_spell, global_entity_ice_spell,
                      global_entity_happiness_min, global_entity_happiness_max,
                      action_speed_min, action_speed_max);
  falken::proto::BrainSpec brain_spec;
  google::protobuf::TextFormat::ParseFromString(brain_spec_formatted, &brain_spec);
  EXPECT_TRUE(falken::BrainSpecProtoConverter::VerifyBrainSpecIntegrity<
              TestTemplateBrainSpec>(brain_spec));
}

TEST(BrainSpecProtoConverter, TestTemplateFromWrongBrainSpec) {
  using TestBrainSpec = falken::BrainSpec<TestObservations, TestActions>;
  constexpr float player_health_min = 1.0f;
  constexpr float player_health_max = 3.0f;
  constexpr const char* const global_entity_dark_spell = "dark";
  constexpr const char* const global_entity_ice_spell = "ice";
  constexpr float global_entity_happiness_min = 2.0f;
  constexpr float global_entity_happiness_max = 3.0f;
  constexpr float action_speed_min = 5.0f;
  constexpr float action_speed_max = 10.0f;
  const std::string brain_spec_formatted =
      absl::StrFormat(kBrainSpec, player_health_min, player_health_max,
                      global_entity_dark_spell, global_entity_ice_spell,
                      global_entity_happiness_min, global_entity_happiness_max,
                      action_speed_min, action_speed_max);
  falken::proto::BrainSpec brain_spec;
  google::protobuf::TextFormat::ParseFromString(brain_spec_formatted, &brain_spec);
  EXPECT_FALSE(
      falken::BrainSpecProtoConverter::VerifyBrainSpecIntegrity<TestBrainSpec>(
          brain_spec));
}

TEST(BrainSpecProtoConverter, TestTemplateWrongRangeInPlayerFromBrainSpec) {
  constexpr float player_health_min = 2.0f;
  constexpr float player_health_max = 3.0f;
  constexpr const char* const global_entity_dark_spell = "dark";
  constexpr const char* const global_entity_ice_spell = "ice";
  constexpr float global_entity_happiness_min = 2.0f;
  constexpr float global_entity_happiness_max = 3.0f;
  constexpr float action_speed_min = 5.0f;
  constexpr float action_speed_max = 10.0f;
  const std::string brain_spec_formatted =
      absl::StrFormat(kBrainSpec, player_health_min, player_health_max,
                      global_entity_dark_spell, global_entity_ice_spell,
                      global_entity_happiness_min, global_entity_happiness_max,
                      action_speed_min, action_speed_max);
  falken::proto::BrainSpec brain_spec;
  google::protobuf::TextFormat::ParseFromString(kBrainSpec, &brain_spec);
  EXPECT_FALSE(falken::BrainSpecProtoConverter::VerifyBrainSpecIntegrity<
               TestTemplateBrainSpec>(brain_spec));
}

TEST(BrainSpecProtoConverter, TestTemplateWrongCategoryGlobalEntity) {
  constexpr float player_health_min = 1.0f;
  constexpr float player_health_max = 3.0f;
  constexpr const char* const global_entity_dark_spell = "dark";
  constexpr const char* const global_entity_fire_spell = "fire";
  constexpr float global_entity_happiness_min = 2.0f;
  constexpr float global_entity_happiness_max = 3.0f;
  constexpr float action_speed_min = 5.0f;
  constexpr float action_speed_max = 10.0f;
  const std::string brain_spec_formatted =
      absl::StrFormat(kBrainSpec, player_health_min, player_health_max,
                      global_entity_dark_spell, global_entity_fire_spell,
                      global_entity_happiness_min, global_entity_happiness_max,
                      action_speed_min, action_speed_max);
  falken::proto::BrainSpec brain_spec;
  google::protobuf::TextFormat::ParseFromString(kBrainSpec, &brain_spec);
  EXPECT_FALSE(falken::BrainSpecProtoConverter::VerifyBrainSpecIntegrity<
               TestTemplateBrainSpec>(brain_spec));
}

TEST(BrainSpecProtoConverter, TestTemplateWrongRangeAction) {
  constexpr float player_health_min = 1.0f;
  constexpr float player_health_max = 3.0f;
  constexpr const char* const global_entity_dark_spell = "dark";
  constexpr const char* const global_entity_ice_spell = "ice";
  constexpr float global_entity_happiness_min = 2.0f;
  constexpr float global_entity_happiness_max = 3.0f;
  constexpr float action_speed_min = 8.0f;
  constexpr float action_speed_max = 10.0f;
  const std::string brain_spec_formatted =
      absl::StrFormat(kBrainSpec, player_health_min, player_health_max,
                      global_entity_dark_spell, global_entity_ice_spell,
                      global_entity_happiness_min, global_entity_happiness_max,
                      action_speed_min, action_speed_max);
  falken::proto::BrainSpec brain_spec;
  google::protobuf::TextFormat::ParseFromString(kBrainSpec, &brain_spec);
  EXPECT_FALSE(falken::BrainSpecProtoConverter::VerifyBrainSpecIntegrity<
               TestTemplateBrainSpec>(brain_spec));
}

}  // namespace
