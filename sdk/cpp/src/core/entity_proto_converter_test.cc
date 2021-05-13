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

#include "src/core/entity_proto_converter.h"

#include <google/protobuf/text_format.h>
#include <google/protobuf/util/message_differencer.h>
#include "falken/log.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"

namespace {

using MessageDifferencer = google::protobuf::util::MessageDifferencer;

struct TestEntity : public falken::EntityBase {
 public:
  explicit TestEntity(falken::EntityContainer& entity_container,
                      const char* name)
      : falken::EntityBase(entity_container, name),
        FALKEN_FEELERS(feelers, 2, 1.0f, 120.0f, 0.2f, {"door", "wall", "car"}),
        FALKEN_FEELERS(feelers1, 1, 2.0f, 0.0f, 0.2f, {"cat", "dog"}),
        FALKEN_FEELERS(feelers2, 3, 4.0f, 180.0f, 0.5f,
                       {"table", "glass", "dish"}),
        FALKEN_NUMBER(health, 10.0f, 50.0f),
        FALKEN_BOOL(sprint),
        FALKEN_CATEGORICAL(weapons, {"shotgun", "pistol", "whip"}) {}

  falken::FeelersAttribute feelers;
  falken::FeelersAttribute feelers1;
  falken::FeelersAttribute feelers2;
  falken::NumberAttribute<float> health;
  falken::BoolAttribute sprint;
  falken::CategoricalAttribute weapons;
};

struct TestEntityWithExtraPositionAndRotation : public TestEntity {
 public:
  explicit TestEntityWithExtraPositionAndRotation(
      falken::EntityContainer& entity_container)
      : TestEntity(entity_container, "EntityExtraPositionRotation"),
        FALKEN_UNCONSTRAINED(other_position),
        FALKEN_UNCONSTRAINED(other_rotation) {}

  falken::PositionAttribute other_position;
  falken::RotationAttribute other_rotation;
};

TEST(EntityProtoConverterTest, TestToEntityType) {
  falken::EntityContainer plain_container;
  TestEntity test_entity(plain_container, "TestEntity");
  falken::proto::EntityType entity_type =
      falken::EntityProtoConverter::ToEntityType(test_entity);

  falken::proto::EntityType expected_entity_type;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        position: {}
        rotation: {}
        entity_fields:
        [ {
          name: "feelers"
          feeler: {
            count: 2
            distance: { maximum: 1 }
            yaw_angles: -60
            yaw_angles: 60
            experimental_data: { maximum: 1 }
            experimental_data: { maximum: 1 }
            experimental_data: { maximum: 1 }
            thickness: 0.2
          }
        }
          , {
            name: "feelers1"
            feeler: {
              count: 1
              distance: { maximum: 2 }
              yaw_angles: 0
              experimental_data: { maximum: 1 }
              experimental_data: { maximum: 1 }
              thickness: 0.2
            }
          }
          , {
            name: "feelers2"
            feeler: {
              count: 3
              distance: { maximum: 4 }
              yaw_angles: -90
              yaw_angles: 0
              yaw_angles: 90
              experimental_data: { maximum: 1 }
              experimental_data: { maximum: 1 }
              experimental_data: { maximum: 1 }
              thickness: 0.5
            }
          }
          , {
            name: "health"
            number: { minimum: 10 maximum: 50 }
          }
          , {
            name: "sprint"
            category: { enum_values: "false" enum_values: "true" }
          }
          , {
            name: "weapons"
            category: {
              enum_values: "shotgun"
              enum_values: "pistol"
              enum_values: "whip"
            }
          }]
      )",
      &expected_entity_type);
  MessageDifferencer diff;
  std::string output;
  diff.ReportDifferencesToString(&output);
  EXPECT_TRUE(diff.Compare(entity_type, expected_entity_type))
      << "Difference is: " << output;
}

TEST(EntityProtoConverterTest, TestToEntity) {
  falken::EntityContainer plain_container;
  TestEntity test_entity(plain_container, "TestEntity");
  test_entity.sprint.set_value(true);
  test_entity.weapons.set_category(2);
  test_entity.health.set_value(25.5f);
  test_entity.feelers.feelers_distances()[0].set_value(0.5);
  test_entity.feelers.feelers_distances()[1].set_value(0.7);
  test_entity.feelers1.feelers_distances()[0].set_value(0.8);
  test_entity.feelers2.feelers_distances()[0].set_value(0.1);
  test_entity.feelers2.feelers_distances()[1].set_value(0.2);
  test_entity.feelers2.feelers_distances()[2].set_value(0.3);
  test_entity.feelers.feelers_ids()[0].set_value(2);
  test_entity.feelers.feelers_ids()[1].set_value(1);
  test_entity.feelers1.feelers_ids()[0].set_value(1);
  test_entity.feelers2.feelers_ids()[0].set_value(2);
  test_entity.feelers2.feelers_ids()[1].set_value(1);
  test_entity.feelers2.feelers_ids()[2].set_value(0);
  test_entity.position.set_value(falken::Position({1.0f, 2.0f, 3.0f}));
  test_entity.rotation.set_value(falken::Rotation({0.0f, 0.0f, 0.0f, 1.0f}));
  falken::proto::Entity entity =
      falken::EntityProtoConverter::ToEntity(test_entity);

  falken::proto::Entity expected_entity;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        position: { x: 1 y: 2 z: 3 }
        rotation: { x: 0 y: 0 z: 0 w: 1 }
        entity_fields:
        [ {
          feeler: {
            measurements: {
              distance: { value: 0.5 }
              experimental_data: {}
              experimental_data: {}
              experimental_data: { value: 1 }
            },
            measurements: {
              distance: { value: 0.7 }
              experimental_data: {}
              experimental_data: { value: 1 }
              experimental_data: {}
            }
          }
        }
          , {
            feeler: {
              measurements: {
                distance: { value: 0.8 }
                experimental_data: {}
                experimental_data: { value: 1 }
              }
            }
          }
          , {
            feeler: {
              measurements: {
                distance: { value: 0.1 }
                experimental_data: {}
                experimental_data: {}
                experimental_data: { value: 1 }
              },
              measurements: {
                distance: { value: 0.2 }
                experimental_data: {}
                experimental_data: { value: 1 }
                experimental_data: {}
              },
              measurements: {
                distance: { value: 0.3 }
                experimental_data: { value: 1 }
                experimental_data: {}
                experimental_data: {}
              }
            }
          }
          , { number: { value: 25.5 } }
          , { category: { value: 1 } }
          , { category: { value: 2 } }]
      )",
      &expected_entity);
  MessageDifferencer diff;
  std::string output;
  diff.ReportDifferencesToString(&output);
  EXPECT_TRUE(diff.Compare(entity, expected_entity))
      << "Difference is: " << output;
}

// Verifies that no other position and rotation attribute is added to the
// EntityType.
TEST(EntityProtoConverterTest, TestExtraPositionAndRotationAttributes) {
  falken::EntityContainer plain_container;
  TestEntityWithExtraPositionAndRotation test_entity(plain_container);
  test_entity.sprint.set_value(true);
  test_entity.weapons.set_category(2);
  test_entity.health.set_value(25.5f);
  test_entity.feelers.feelers_distances()[0].set_value(0.5);
  test_entity.feelers.feelers_distances()[1].set_value(0.7);
  test_entity.feelers1.feelers_distances()[0].set_value(0.8);
  test_entity.feelers2.feelers_distances()[0].set_value(0.1);
  test_entity.feelers2.feelers_distances()[1].set_value(0.2);
  test_entity.feelers2.feelers_distances()[2].set_value(0.3);
  test_entity.feelers.feelers_ids()[0].set_value(2);
  test_entity.feelers.feelers_ids()[1].set_value(1);
  test_entity.feelers1.feelers_ids()[0].set_value(1);
  test_entity.feelers2.feelers_ids()[0].set_value(2);
  test_entity.feelers2.feelers_ids()[1].set_value(1);
  test_entity.feelers2.feelers_ids()[2].set_value(0);
  test_entity.position.set_value(falken::Position({1.0f, 2.0f, 3.0f}));
  test_entity.rotation.set_value(falken::Rotation({0.0f, 0.0f, 0.0f, 1.0f}));
  falken::proto::Entity entity =
      falken::EntityProtoConverter::ToEntity(test_entity);

  falken::proto::Entity expected_entity;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        position: { x: 1 y: 2 z: 3 }
        rotation: { x: 0 y: 0 z: 0 w: 1 }
        entity_fields:
        [ {
          feeler: {
            measurements: {
              distance: { value: 0.5 }
              experimental_data: {}
              experimental_data: {}
              experimental_data: { value: 1 }
            },
            measurements: {
              distance: { value: 0.7 }
              experimental_data: {}
              experimental_data: { value: 1 }
              experimental_data: {}
            }
          }
        }
          , {
            feeler: {
              measurements: {
                distance: { value: 0.8 }
                experimental_data: {}
                experimental_data: { value: 1 }

              }
            }
          }
          , {
            feeler: {
              measurements: {
                distance: { value: 0.1 }
                experimental_data: {}
                experimental_data: {}
                experimental_data: { value: 1 }
              },
              measurements: {
                distance: { value: 0.2 }
                experimental_data: {}
                experimental_data: { value: 1 }
                experimental_data: {}
              },
              measurements: {
                distance: { value: 0.3 }
                experimental_data: { value: 1 }
                experimental_data: {}
                experimental_data: {}
              }
            }
          }
          , { number: { value: 25.5 } }
          , { category: { value: 1 } }
          , { category: { value: 2 } }]
      )",
      &expected_entity);
  MessageDifferencer diff;
  std::string output;
  diff.ReportDifferencesToString(&output);
  EXPECT_TRUE(diff.Compare(entity, expected_entity))
      << "Difference is: " << output;
}

TEST(EntityProtoConverterTest, TestFromEntityOk) {
  falken::EntityContainer plain_container;
  TestEntity test_entity(plain_container, "TestEntity");
  falken::proto::Entity entity;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        position: { x: 1 y: 2 z: 3 }
        rotation: { x: 0 y: 0 z: 0 w: 1 }
        entity_fields:
        [ {
          feeler: {
            measurements: {
              distance: { value: 0.5 }
              experimental_data: {}
              experimental_data: {}
              experimental_data: { value: 1 }
            },
            measurements: {
              distance: { value: 0.7 }
              experimental_data: {}
              experimental_data: { value: 1 }
              experimental_data: {}
            }
          }
        }
          , {
            feeler: {
              measurements: {
                distance: { value: 0.8 }
                experimental_data: {}
                experimental_data: { value: 1 }

              }
            }
          }
          , {
            feeler: {
              measurements: {
                distance: { value: 0.1 }
                experimental_data: {}
                experimental_data: {}
                experimental_data: { value: 1 }
              },
              measurements: {
                distance: { value: 0.2 }
                experimental_data: {}
                experimental_data: { value: 1 }
                experimental_data: {}
              },
              measurements: {
                distance: { value: 0.3 }
                experimental_data: { value: 1 }
                experimental_data: {}
                experimental_data: {}
              }
            }
          }
          , { number: { value: 25.5 } }
          , { category: { value: 1 } }
          , { category: { value: 2 } }]
      )",
      &entity);
  EXPECT_TRUE(falken::EntityProtoConverter::FromEntity(entity, test_entity));
  EXPECT_EQ(static_cast<float>(test_entity.health), 25.5f);
  EXPECT_EQ(static_cast<int>(test_entity.weapons), 2);
  EXPECT_TRUE(test_entity.sprint);
  EXPECT_EQ(test_entity.feelers.feelers_distances()[0].value(), 0.5f);
  EXPECT_EQ(test_entity.feelers.feelers_distances()[1].value(), 0.7f);
  EXPECT_EQ(test_entity.feelers.feelers_ids()[0].value(), 2);
  EXPECT_EQ(test_entity.feelers.feelers_ids()[1].value(), 1);
  EXPECT_EQ(test_entity.feelers1.feelers_distances()[0].value(), 0.8f);
  EXPECT_EQ(test_entity.feelers1.feelers_ids()[0].value(), 1);
  EXPECT_EQ(test_entity.feelers2.feelers_distances()[0].value(), 0.1f);
  EXPECT_EQ(test_entity.feelers2.feelers_distances()[1].value(), 0.2f);
  EXPECT_EQ(test_entity.feelers2.feelers_distances()[2].value(), 0.3f);
  EXPECT_EQ(test_entity.feelers2.feelers_ids()[0].value(), 2);
  EXPECT_EQ(test_entity.feelers2.feelers_ids()[1].value(), 1);
  EXPECT_EQ(test_entity.feelers2.feelers_ids()[2].value(), 0);
  EXPECT_EQ(test_entity.position.value().x, 1.0f);
  EXPECT_EQ(test_entity.position.value().y, 2.0f);
  EXPECT_EQ(test_entity.position.value().z, 3.0f);
  EXPECT_EQ(test_entity.rotation.value().x, 0.0f);
  EXPECT_EQ(test_entity.rotation.value().y, 0.0f);
  EXPECT_EQ(test_entity.rotation.value().z, 0.0f);
  EXPECT_EQ(test_entity.rotation.value().w, 1.0f);
}

TEST(EntityProtoConverterTest, TestFromEntityNumberOutOfRange) {
  falken::EntityContainer plain_container;
  TestEntity test_entity(plain_container, "TestEntity");
  falken::proto::Entity entity;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        position: { x: 1 y: 2 z: 3 }
        rotation: { x: 0 y: 0 z: 0 w: 1 }
        entity_fields:
        [ {
          feeler: {
            measurements: {
              distance: { value: 0.5 }
              experimental_data: {}
              experimental_data: {}
              experimental_data: { value: 1 }
            },
            measurements: {
              distance: { value: 0.7 }
              experimental_data: {}
              experimental_data: { value: 1 }
              experimental_data: {}
            }
          }
        }
          , {
            feeler: {
              measurements: {
                distance: { value: 0.8 }
                experimental_data: {}
                experimental_data: { value: 1 }

              }
            }
          }
          , {
            feeler: {
              measurements: {
                distance: { value: 0.1 }
                experimental_data: {}
                experimental_data: {}
                experimental_data: { value: 1 }
              },
              measurements: {
                distance: { value: 0.2 }
                experimental_data: {}
                experimental_data: { value: 1 }
                experimental_data: {}
              },
              measurements: {
                distance: { value: 0.3 }
                experimental_data: { value: 1 }
                experimental_data: {}
                experimental_data: {}
              }
            }
          }
          , { number: { value: 75.5 } }
          , { category: { value: 1 } }
          , { category: { value: 2 } }]
      )",
      &entity);
  std::shared_ptr<falken::SystemLogger> logger =
      falken::SystemLogger::Get();
  logger->set_abort_on_fatal_error(false);
  EXPECT_FALSE(falken::EntityProtoConverter::FromEntity(entity, test_entity));
}

TEST(EntityProtoConverterTest, TestFromEntityFeelerNumberOutOfRange) {
  falken::EntityContainer plain_container;
  TestEntity test_entity(plain_container, "TestEntity");
  falken::proto::Entity entity;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        position: { x: 1 y: 2 z: 3 }
        rotation: { x: 0 y: 0 z: 0 w: 1 }
        entity_fields:
        [ {
          feeler: {
            measurements: {
              distance: { value: 5.0 }
              experimental_data: {}
              experimental_data: {}
              experimental_data: { value: 1 }
            },
            measurements: {
              distance: { value: 0.7 }
              experimental_data: {}
              experimental_data: { value: 1 }
              experimental_data: {}
            }
          }
        }
          , {
            feeler: {
              measurements: {
                distance: { value: 0.8 }
                experimental_data: {}
                experimental_data: { value: 1 }

              }
            }
          }
          , {
            feeler: {
              measurements: {
                distance: { value: 0.1 }
                experimental_data: {}
                experimental_data: {}
                experimental_data: { value: 1 }
              },
              measurements: {
                distance: { value: 0.2 }
                experimental_data: {}
                experimental_data: { value: 1 }
                experimental_data: {}
              },
              measurements: {
                distance: { value: 0.3 }
                experimental_data: { value: 1 }
                experimental_data: {}
                experimental_data: {}
              }
            }
          }
          , { number: { value: 25.5 } }
          , { category: { value: 1 } }
          , { category: { value: 2 } }]
      )",
      &entity);
  std::shared_ptr<falken::SystemLogger> logger =
      falken::SystemLogger::Get();
  logger->set_abort_on_fatal_error(false);
  EXPECT_FALSE(falken::EntityProtoConverter::FromEntity(entity, test_entity));
}

TEST(EntityProtoConverterTest, TestFromEntityFeelerCategoryOutOfRange) {
  falken::EntityContainer plain_container;
  TestEntity test_entity(plain_container, "TestEntity");
  falken::proto::Entity entity;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        position: { x: 1 y: 2 z: 3 }
        rotation: { x: 0 y: 0 z: 0 w: 1 }
        entity_fields:
        [ {
          feeler: {
            measurements: {
              distance: { value: 0.5 }
              experimental_data: {}
              experimental_data: {}
              experimental_data: { value: 5 }
            },
            measurements: {
              distance: { value: 0.7 }
              experimental_data: {}
              experimental_data: { value: 1 }
              experimental_data: {}
            }
          }
        }
          , {
            feeler: {
              measurements: {
                distance: { value: 0.8 }
                experimental_data: {}
                experimental_data: { value: 1 }

              }
            }
          }
          , {
            feeler: {
              measurements: {
                distance: { value: 0.1 }
                experimental_data: {}
                experimental_data: {}
                experimental_data: { value: 1 }
              },
              measurements: {
                distance: { value: 0.2 }
                experimental_data: {}
                experimental_data: { value: 1 }
                experimental_data: {}
              },
              measurements: {
                distance: { value: 0.3 }
                experimental_data: { value: 1 }
                experimental_data: {}
                experimental_data: {}
              }
            }
          }
          , { number: { value: 25.5 } }
          , { category: { value: 2 } }
          , { category: { value: 1 } }]
      )",
      &entity);
  std::shared_ptr<falken::SystemLogger> logger =
      falken::SystemLogger::Get();
  logger->set_abort_on_fatal_error(false);
  EXPECT_FALSE(falken::EntityProtoConverter::FromEntity(entity, test_entity));
}

TEST(EntityProtoConverterTest, TestFromEntityCategoryOutOfRange) {
  falken::EntityContainer plain_container;
  TestEntity test_entity(plain_container, "TestEntity");
  falken::proto::Entity entity;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        position: { x: 1 y: 2 z: 3 }
        rotation: { x: 0 y: 0 z: 0 w: 1 }
        entity_fields:
        [ {
          feeler: {
            measurements: {
              distance: { value: 0.5 }
              experimental_data: {}
              experimental_data: {}
              experimental_data: { value: 1 }
            },
            measurements: {
              distance: { value: 0.7 }
              experimental_data: {}
              experimental_data: { value: 1 }
              experimental_data: {}
            }
          }
        }
          , {
            feeler: {
              measurements: {
                distance: { value: 0.8 }
                experimental_data: {}
                experimental_data: { value: 1 }

              }
            }
          }
          , {
            feeler: {
              measurements: {
                distance: { value: 0.1 }
                experimental_data: {}
                experimental_data: {}
                experimental_data: { value: 1 }
              },
              measurements: {
                distance: { value: 0.2 }
                experimental_data: {}
                experimental_data: { value: 1 }
                experimental_data: {}
              },
              measurements: {
                distance: { value: 0.3 }
                experimental_data: { value: 1 }
                experimental_data: {}
                experimental_data: {}
              }
            }
          }
          , { number: { value: 25.5 } }
          , { category: { value: 3 } }
          , { category: { value: 2 } }]
      )",
      &entity);
  std::shared_ptr<falken::SystemLogger> logger =
      falken::SystemLogger::Get();
  logger->set_abort_on_fatal_error(false);
  EXPECT_FALSE(falken::EntityProtoConverter::FromEntity(entity, test_entity));
}

TEST(EntityProtoConverterTest, TestFromEntityWrongAttributesOrder) {
  falken::EntityContainer plain_container;
  TestEntity test_entity(plain_container, "TestEntity");
  falken::proto::Entity entity;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        position: { x: 1 y: 2 z: 3 }
        rotation: { x: 0 y: 0 z: 0 w: 1 }
        entity_fields:
        [ {
          feeler: {
            measurements: {
              distance: { value: 0.5 }
              experimental_data: {}
              experimental_data: {}
              experimental_data: { value: 1 }
            },
            measurements: {
              distance: { value: 0.7 }
              experimental_data: {}
              experimental_data: { value: 1 }
              experimental_data: {}
            }
          }
        }
          , {
            feeler: {
              measurements: {
                distance: { value: 0.8 }
                experimental_data: {}
                experimental_data: { value: 1 }

              }
            }
          }
          , {
            feeler: {
              measurements: {
                distance: { value: 0.1 }
                experimental_data: {}
                experimental_data: {}
                experimental_data: { value: 1 }
              },
              measurements: {
                distance: { value: 0.2 }
                experimental_data: {}
                experimental_data: { value: 1 }
                experimental_data: {}
              },
              measurements: {
                distance: { value: 0.3 }
                experimental_data: { value: 1 }
                experimental_data: {}
                experimental_data: {}
              }
            }
          }
          , { category: { value: 1 } }
          , { number: { value: 25.5 } }
          , { category: { value: 2 } }]
      )",
      &entity);
  EXPECT_FALSE(falken::EntityProtoConverter::FromEntity(entity, test_entity));
}

TEST(EntityProtoConverterTest, TestFromEntityMoreAttributesThanExpected) {
  falken::EntityContainer plain_container;
  TestEntity test_entity(plain_container, "TestEntity");
  falken::proto::Entity entity;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        position: { x: 1 y: 2 z: 3 }
        rotation: { x: 0 y: 0 z: 0 w: 1 }
        entity_fields:
        [ {
          feeler: {
            measurements: {
              distance: { value: 0.5 }
              experimental_data: {}
              experimental_data: {}
              experimental_data: { value: 1 }
            },
            measurements: {
              distance: { value: 0.7 }
              experimental_data: {}
              experimental_data: { value: 1 }
              experimental_data: {}
            }
          }
        }
          , {
            feeler: {
              measurements: {
                distance: { value: 0.8 }
                experimental_data: {}
                experimental_data: { value: 1 }

              }
            }
          }
          , {
            feeler: {
              measurements: {
                distance: { value: 0.1 }
                experimental_data: {}
                experimental_data: {}
                experimental_data: { value: 1 }
              },
              measurements: {
                distance: { value: 0.2 }
                experimental_data: {}
                experimental_data: { value: 1 }
                experimental_data: {}
              },
              measurements: {
                distance: { value: 0.3 }
                experimental_data: { value: 1 }
                experimental_data: {}
                experimental_data: {}
              }
            }
          }
          , { number: { value: 25.5 } }
          , { number: { value: 24.5 } }
          , { category: { value: 1 } }]
      )",
      &entity);
  EXPECT_FALSE(falken::EntityProtoConverter::FromEntity(entity, test_entity));
}

TEST(EntityProtoConverterTest, TestFromEntityLessAttributesThanExpected) {
  falken::EntityContainer plain_container;
  TestEntity test_entity(plain_container, "TestEntity");
  falken::proto::Entity entity;
  google::protobuf::TextFormat::ParseFromString(
      R"(
        position: { x: 1 y: 2 z: 3 }
        rotation: { x: 0 y: 0 z: 0 w: 1 }
        entity_fields:
        [ { number: { value: 25.5 } }]
      )",
      &entity);
  EXPECT_FALSE(falken::EntityProtoConverter::FromEntity(entity, test_entity));
}

}  // namespace
