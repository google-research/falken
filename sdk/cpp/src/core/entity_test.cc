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

#include "falken/entity.h"

#include <utility>

#include "gmock/gmock.h"
#include "gtest/gtest.h"

namespace {

class TestEntity : public falken::EntityBase {
 public:
  explicit TestEntity(falken::EntityContainer& entity_container)
      : falken::EntityBase(entity_container, "TestEntity"),
        FALKEN_CATEGORICAL(weapons_, {"shotgun", "pistol"}),
        FALKEN_NUMBER(health_, 10.0f, 50.0f) {}

  falken::CategoricalAttribute weapons_;
  falken::NumberAttribute<float> health_;
};

TEST(EntityBaseTest, TestEntityBaseRemoval) {
  falken::EntityContainer enemy_container;
  falken::EntityBase* enemy = new falken::EntityBase(enemy_container, "Enemy");
  EXPECT_EQ(enemy_container.entity("Enemy"), enemy);
  delete enemy;
  EXPECT_EQ(enemy_container.entity("Enemy"), nullptr);
}

TEST(EntityBaseTest, TestGetEntityName) {
  falken::EntityContainer enemies_container;
  falken::EntityBase enemy(enemies_container, "Enemy");

  EXPECT_THAT(enemy.name(), testing::StrEq("Enemy"));
}

TEST(EntityContainerTest, TestGetEntityByName) {
  falken::EntityContainer enemies_container;
  falken::EntityBase enemy(enemies_container, "Enemy");
  falken::EntityBase enemy2(enemies_container, "Enemy2");
  auto enemy3 = enemies_container.entity("Enemy");

  EXPECT_THAT(enemy3->name(), testing::StrEq("Enemy"));
}

TEST(EntityContainerTest, TestEntityGetEntities) {
  falken::EntityContainer enemies_container;
  const char* names[] = {"Enemy", "Enemy2", "Enemy3"};
  falken::EntityBase enemy(enemies_container, names[0]);
  falken::EntityBase enemy2(enemies_container, names[1]);
  falken::EntityBase enemy3(enemies_container, names[2]);
  int index = 0;
  for (const auto* elements : enemies_container.entities()) {
    EXPECT_THAT(elements->name(), testing::StrEq(names[index]));
    index++;
  }
}

// Test that no exception/access violation occurs when destroying the
// container before the entity.
TEST(EntityContainerTest, TestDestroyContainerBeforeEntity) {
  falken::EntityContainer* entity_container = new falken::EntityContainer();
  {
    TestEntity test_entity(*entity_container);
    delete entity_container;
  }
}

TEST(EntityContainerTest, TestCategoryAttributeMacro) {
  falken::EntityContainer plain_container;
  TestEntity test_entity(plain_container);
  EXPECT_THAT(test_entity.weapons_.name(), testing::StrEq("weapons_"));
  EXPECT_THAT(test_entity.weapons_.categories(),
              testing::ElementsAreArray({"shotgun", "pistol"}));
}

TEST(EntityContainerTest, TestNumberAttributeMacro) {
  falken::EntityContainer plain_container;
  TestEntity test_entity(plain_container);
  EXPECT_THAT(test_entity.health_.name(), testing::StrEq("health_"));
  EXPECT_THAT(test_entity.health_.value_minimum(), testing::Eq(10.0f));
  EXPECT_THAT(test_entity.health_.value_maximum(), testing::Eq(50.0f));
}

TEST(EntityContainerTest, TestUnconstrainedPositionMacro) {
  falken::EntityContainer plain_container;
  TestEntity test_entity(plain_container);
  EXPECT_THAT(test_entity.position.name(), testing::StrEq("position"));
}

TEST(EntityContainerTest, TestUnconstrainedRotationMacro) {
  falken::EntityContainer plain_container;
  TestEntity test_entity(plain_container);
  EXPECT_THAT(test_entity.rotation.name(), testing::StrEq("rotation"));
}

TEST(EntityContainerTest, MoveEntity) {
  falken::EntityContainer container;
  TestEntity entity1(container);
  EXPECT_THAT(container.entities(), testing::ElementsAre(&entity1));
  TestEntity entity2(std::move(entity1));
  EXPECT_THAT(container.entities(), testing::ElementsAre(&entity2));
}

}  // namespace
