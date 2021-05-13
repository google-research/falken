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

#include "src/core/observation_proto_converter.h"

#include <google/protobuf/text_format.h>
#include <google/protobuf/util/message_differencer.h>
#include "gmock/gmock.h"
#include "gtest/gtest.h"

namespace {

using MessageDifferencer = google::protobuf::util::MessageDifferencer;

struct TestObservation : public falken::ObservationsBase {
 public:
  explicit TestObservation()
      : FALKEN_CATEGORICAL(weapons, {"shotgun", "pistol"}),
        FALKEN_NUMBER(health, 5.0f, 30.0f) {}

  falken::CategoricalAttribute weapons;
  falken::NumberAttribute<float> health;
};

struct Camera : public falken::EntityBase {
 public:
  explicit Camera(falken::EntityContainer& container)
      : falken::EntityBase(container, "camera") {}
};

struct SingleNumberAttributeEntity : public falken::EntityBase {
 public:
  explicit SingleNumberAttributeEntity(falken::EntityContainer& container)
      : falken::EntityBase(container, "SingleNumberAttribute"),
        FALKEN_NUMBER(ammo, 1.0f, 100.0f) {}

  falken::NumberAttribute<float> ammo;
};

struct SingleCategoryAttributeEntity : public falken::EntityBase {
 public:
  explicit SingleCategoryAttributeEntity(falken::EntityContainer& container)
      : falken::EntityBase(container, "SingleCategoryAttribute"),
        FALKEN_CATEGORICAL(spells, {"fire", "ice", "lightning"}) {}

  falken::CategoricalAttribute spells;
};

TEST(ObservationProtoConverterTest, TestToObservationSpec) {
  TestObservation test_observation;
  SingleNumberAttributeEntity single_number_entity(test_observation);
  SingleCategoryAttributeEntity single_categorical_entity(test_observation);
  Camera camera(test_observation);
  falken::proto::ObservationSpec observation_spec =
      falken::ObservationProtoConverter::ToObservationSpec(test_observation);

  falken::proto::ObservationSpec expected_observation_spec;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        camera: {
          position: {}
          rotation: {}
        }
        player: {
          position: {}
          rotation: {}
          entity_fields:
          [ {
            name: "health"
            number { minimum: 5 maximum: 30 }
          }
            , {
              name: "weapons"
              category { enum_values: "shotgun" enum_values: "pistol" }
            }]
        }
        global_entities:
        [ {
          position: {}
          rotation: {}
          entity_fields:
          [ {
            name: "spells"
            category {
              enum_values: "fire"
              enum_values: "ice"
              enum_values: "lightning"
            }
          }]
        }
          , {
            position: {}
            rotation: {}
            entity_fields:
            [ {
              name: "ammo"
              number { minimum: 1 maximum: 100 }
            }]
          }]
      )",
      &expected_observation_spec);
  MessageDifferencer diff;
  std::string output;
  diff.ReportDifferencesToString(&output);
  EXPECT_TRUE(diff.Compare(observation_spec, expected_observation_spec))
      << "Difference is: " << output;
}

TEST(ObservationProtoConverterTest, TestToObservationData) {
  TestObservation test_observation;
  test_observation.weapons.set_category(1);
  test_observation.health.set_value(25.5f);
  test_observation.position.set_value(falken::Position({1.0f, 2.0f, 3.0f}));
  test_observation.rotation.set_value(
      falken::Rotation({0.0f, 0.0f, 0.0f, 1.0f}));

  SingleNumberAttributeEntity single_number_entity(test_observation);
  single_number_entity.ammo.set_value(50.0f);
  single_number_entity.position.set_value(falken::Position({5.0f, 6.0f, 8.0f}));
  single_number_entity.rotation.set_value(
      falken::Rotation({0.3f, 0.5f, 0.2f, 1.0f}));

  SingleCategoryAttributeEntity single_categorical_entity(test_observation);
  single_categorical_entity.spells.set_category(2);
  single_categorical_entity.position.set_value(
      falken::Position({10.0f, 10.0f, 500.5f}));
  single_categorical_entity.rotation.set_value(
      falken::Rotation({0.0f, 0.0f, 0.0f, 1.0f}));
  falken::proto::ObservationData observation_data =
      falken::ObservationProtoConverter::ToObservationData(test_observation);

  falken::proto::ObservationData expected_observation_data;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        player: {
          position: { x: 1 y: 2 z: 3 }
          rotation: { x: 0 y: 0 z: 0 w: 1 }
          entity_fields:
          [ { number: { value: 25.5 } }
            , { category: { value: 1 } }]
        }
        global_entities:
        [ {
          position: { x: 10 y: 10 z: 500.5 }
          rotation: { x: 0 y: 0 z: 0 w: 1 }
          entity_fields:
          [ { category: { value: 2 } }]
        }
          , {
            position: { x: 5 y: 6 z: 8 }
            rotation: { x: 0.3 y: 0.5 z: 0.2 w: 1 }
            entity_fields:
            [ { number: { value: 50 } }]
          }]
      )",
      &expected_observation_data);
  MessageDifferencer diff;
  std::string output;
  diff.ReportDifferencesToString(&output);
  EXPECT_TRUE(diff.Compare(observation_data, expected_observation_data))
      << "Difference is: " << output;
}

TEST(ObservationProtoConverterTest, TestFromObservationDataOk) {
  falken::proto::ObservationData observation_data;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        player: {
          position: { x: 1 y: 2 z: 3 }
          rotation: { x: 0 y: 0 z: 0 w: 1 }
          entity_fields:
          [ { number: { value: 25.5 } }
            , { category: { value: 1 } }]
        }
        global_entities:
        [ {
          position: { x: 10 y: 10 z: 500.5 }
          rotation: { x: 0 y: 0 z: 0 w: 1 }
          entity_fields:
          [ { category: { value: 2 } }]
        }
          , {
            position: { x: 5 y: 6 z: 8 }
            rotation: { x: 0.3 y: 0.5 z: 0.2 w: 1 }
            entity_fields:
            [ { number: { value: 50 } }]
          }]
      )",
      &observation_data);
  TestObservation test_observation;
  SingleNumberAttributeEntity single_number_entity(test_observation);
  SingleCategoryAttributeEntity single_categorical_entity(test_observation);
  EXPECT_TRUE(falken::ObservationProtoConverter::FromObservationData(
      observation_data, test_observation));

  // Check player values.
  EXPECT_EQ(static_cast<float>(test_observation.health), 25.5f);
  EXPECT_EQ(static_cast<int>(test_observation.weapons), 1);
  EXPECT_EQ(test_observation.position.value().x, 1.0f);
  EXPECT_EQ(test_observation.position.value().y, 2.0f);
  EXPECT_EQ(test_observation.position.value().z, 3.0f);
  EXPECT_EQ(test_observation.rotation.value().x, 0.0f);
  EXPECT_EQ(test_observation.rotation.value().y, 0.0f);
  EXPECT_EQ(test_observation.rotation.value().z, 0.0f);
  EXPECT_EQ(test_observation.rotation.value().w, 1.0f);

  // Check global entities values.
  EXPECT_EQ(test_observation.entities().size(), 3);

  auto entity = test_observation.entity("SingleCategoryAttribute");
  EXPECT_EQ(entity->position.value().x, 10.0f);
  EXPECT_EQ(entity->position.value().y, 10.0f);
  EXPECT_EQ(entity->position.value().z, 500.5f);
  EXPECT_EQ(entity->rotation.value().x, 0.0f);
  EXPECT_EQ(entity->rotation.value().y, 0.0f);
  EXPECT_EQ(entity->rotation.value().z, 0.0f);
  EXPECT_EQ(entity->rotation.value().w, 1.0f);
  EXPECT_EQ(entity->attributes().size(), 3);
  EXPECT_EQ(entity->attribute("spells")->category(), 2);

  entity = test_observation.entity("SingleNumberAttribute");
  EXPECT_EQ(entity->position.value().x, 5.0f);
  EXPECT_EQ(entity->position.value().y, 6.0f);
  EXPECT_EQ(entity->position.value().z, 8.0f);
  EXPECT_EQ(entity->rotation.value().x, 0.3f);
  EXPECT_EQ(entity->rotation.value().y, 0.5f);
  EXPECT_EQ(entity->rotation.value().z, 0.2f);
  EXPECT_EQ(entity->rotation.value().w, 1.0f);
  EXPECT_EQ(entity->attributes().size(), 3);
  EXPECT_EQ(entity->attribute("ammo")->number(), 50.0f);
}

TEST(ObservationProtoConverterTest, TestFromObservationDataWrongEntitiesOrder) {
  falken::proto::ObservationData observation_data;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        player: {
          position: { x: 1 y: 2 z: 3 }
          rotation: { x: 0 y: 0 z: 0 w: 1 }
          entity_fields:
          [ { number: { value: 25.5 } }
            , { category: { value: 1 } }]
        }
        global_entities:
        [ {
          position: { x: 5 y: 6 z: 8 }
          rotation: { x: 0.3 y: 0.5 z: 0.2 w: 1 }
          entity_fields:
          [ { number: { value: 50 } }]
        }
          , {
            position: { x: 10 y: 10 z: 500.5 }
            rotation: { x: 0 y: 0 z: 0 w: 1 }
            entity_fields:
            [ { category: { value: 2 } }]
          }]
      )",
      &observation_data);
  TestObservation test_observation;
  SingleNumberAttributeEntity single_number_entity(test_observation);
  SingleCategoryAttributeEntity single_categorical_entity(test_observation);
  EXPECT_FALSE(falken::ObservationProtoConverter::FromObservationData(
      observation_data, test_observation));
}

TEST(ObservationProtoConverterTest,
     TestFromObservationDataMoreEntitiesThanExpected) {
  falken::proto::ObservationData observation_data;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        player: {
          position: { x: 1 y: 2 z: 3 }
          rotation: { x: 0 y: 0 z: 0 w: 1 }
          entity_fields:
          [ { number: { value: 25.5 } }
            , { category: { value: 1 } }]
        }
        global_entities:
        [ {
          position: { x: 10 y: 10 z: 500.5 }
          rotation: { x: 0 y: 0 z: 0 w: 1 }
          entity_fields:
          [ { category: { value: 2 } }]
        }
          , {
            position: { x: 1 y: 2 z: 3 }
            rotation: { x: 0 y: 0 z: 0 w: 1 }
            entity_fields:
            [ { category: { value: 1 } }]
          }
          , {
            position: { x: 5 y: 6 z: 8 }
            rotation: { x: 0.3 y: 0.5 z: 0.2 w: 1 }
            entity_fields:
            [ { number: { value: 50 } }]
          }]
      )",
      &observation_data);
  TestObservation test_observation;
  SingleNumberAttributeEntity single_number_entity(test_observation);
  SingleCategoryAttributeEntity single_categorical_entity(test_observation);
  EXPECT_FALSE(falken::ObservationProtoConverter::FromObservationData(
      observation_data, test_observation));
}

TEST(ObservationProtoConverterTest,
     TestFromObservationDataLessEntitiesThanExpected) {
  falken::proto::ObservationData observation_data;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        player: {
          position: { x: 1 y: 2 z: 3 }
          rotation: { x: 0 y: 0 z: 0 w: 1 }
          entity_fields:
          [ { number: { value: 25.5 } }
            , { category: { value: 1 } }]
        }
        global_entities:
        [ {
          position: { x: 5 y: 6 z: 8 }
          rotation: { x: 0.3 y: 0.5 z: 0.2 w: 1 }
          entity_fields:
          [ { number: { value: 50 } }]
        }]
      )",
      &observation_data);
  TestObservation test_observation;
  SingleNumberAttributeEntity single_number_entity(test_observation);
  SingleCategoryAttributeEntity single_categorical_entity(test_observation);
  EXPECT_FALSE(falken::ObservationProtoConverter::FromObservationData(
      observation_data, test_observation));
}

TEST(ObservationProtoConverterTest,
     TestFromObservationDataPlayerWithWrongNumberOfAttributes) {
  falken::proto::ObservationData observation_data;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        player: {
          position: { x: 1 y: 2 z: 3 }
          rotation: { x: 0 y: 0 z: 0 w: 1 }
          entity_fields:
          [ { number: { value: 25.5 } }]
        }
        global_entities:
        [ {
          position: { x: 10 y: 10 z: 500.5 }
          rotation: { x: 0 y: 0 z: 0 w: 1 }
          entity_fields:
          [ { category: { value: 2 } }]
        }
          , {
            position: { x: 5 y: 6 z: 8 }
            rotation: { x: 0.3 y: 0.5 z: 0.2 w: 1 }
            entity_fields:
            [ { number: { value: 50 } }]
          }]
      )",
      &observation_data);
  TestObservation test_observation;
  SingleNumberAttributeEntity single_number_entity(test_observation);
  SingleCategoryAttributeEntity single_categorical_entity(test_observation);
  EXPECT_FALSE(falken::ObservationProtoConverter::FromObservationData(
      observation_data, test_observation));
}

TEST(ObservationProtoConverterTest,
     TestFromObservationDataGlobalEntityWithWrongNumberOfAttributes) {
  falken::proto::ObservationData observation_data;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        player: {
          position: { x: 1 y: 2 z: 3 }
          rotation: { x: 0 y: 0 z: 0 w: 1 }
          entity_fields:
          [ { number: { value: 25.5 } }
            , { category: { value: 1 } }]
        }
        global_entities:
        [ {
          position: { x: 10 y: 10 z: 500.5 }
          rotation: { x: 0 y: 0 z: 0 w: 1 }
          entity_fields: []
        }
          , {
            position: { x: 5 y: 6 z: 8 }
            rotation: { x: 0.3 y: 0.5 z: 0.2 w: 1 }
            entity_fields:
            [ { number: { value: 50 } }]
          }]
      )",
      &observation_data);
  TestObservation test_observation;
  SingleNumberAttributeEntity single_number_entity(test_observation);
  SingleCategoryAttributeEntity single_categorical_entity(test_observation);
  EXPECT_FALSE(falken::ObservationProtoConverter::FromObservationData(
      observation_data, test_observation));
}

TEST(ObservationProtoConverterTest,
     TestFromObservationDataMissingCamera) {
  falken::proto::ObservationData observation_data_no_cam;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        player: {
          position: { x: 1 y: 2 z: 3 }
          rotation: { x: 0 y: 0 z: 0 w: 1 }
          entity_fields:
          [ { number: { value: 25.5 } }
            , { category: { value: 1 } }]
        }
      )",
      &observation_data_no_cam);

  falken::proto::ObservationData observation_data_with_cam =
      observation_data_no_cam;
  observation_data_with_cam.mutable_camera()->mutable_position();
  observation_data_with_cam.mutable_camera()->mutable_rotation();

  TestObservation test_observation_no_cam;
  TestObservation test_observation_with_cam;
  Camera c(test_observation_with_cam);

  EXPECT_TRUE(falken::ObservationProtoConverter::FromObservationData(
      observation_data_with_cam, test_observation_with_cam));
  EXPECT_TRUE(falken::ObservationProtoConverter::FromObservationData(
      observation_data_no_cam, test_observation_no_cam));
  EXPECT_FALSE(falken::ObservationProtoConverter::FromObservationData(
      observation_data_with_cam, test_observation_no_cam));
  EXPECT_FALSE(falken::ObservationProtoConverter::FromObservationData(
      observation_data_no_cam, test_observation_with_cam));
}

}  // namespace
