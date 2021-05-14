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

#include "falken/attribute.h"

#include "falken/attribute_base.h"
#include "falken/joystick_attribute.h"
#include "falken/log.h"
#include "falken/primitives.h"
#include "src/core/string_logger.h"
#include "src/core/test_utils.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "absl/strings/str_format.h"

namespace falken {

// Access private / protected state of AttributeBase and AttributeContainer.
class AttributeTest {
 public:
  static bool GetModified(const falken::AttributeContainer& container) {
    return container.modified();
  }

  static void AttributeContainerResetAttributesDirtyFlags(
      falken::AttributeContainer& container) {
    container.reset_attributes_dirty_flags();
  }

  static bool AttributeContainerAllAttributesAreSet(
      const falken::AttributeContainer& container) {
    return container.all_attributes_are_set();
  }

  static bool AttributeContainerHasUnmodifiedAttributes(
      const falken::AttributeContainer& container,
      std::vector<std::string>& unset_attribute_names) {
    return container.HasUnmodifiedAttributes(unset_attribute_names);
  }

  static bool AttributeBaseModified(const falken::AttributeBase& attribute) {
    return attribute.modified();
  }

  static void AttributeBaseResetModified(falken::AttributeBase& attribute) {
    attribute.reset_modified();
  }

  static bool AttributeBaseIsNotModified(
      falken::AttributeBase& attribute,
      std::vector<std::string>& unmodified_attribute_names) {
    return attribute.IsNotModified(unmodified_attribute_names);
  }

  static void AttributeBaseCopyValue(falken::AttributeBase& attribute,
                                     falken::AttributeBase& other) {
    attribute.CopyValue(other);
  }

  static void AttributeBaseMoveValue(falken::AttributeBase& attribute,
                                     falken::AttributeBase&& other) {
    attribute.MoveValue(std::move(other));
  }
};

}  // namespace falken

namespace {

using falken::AttributeTest;
using ::testing::ElementsAreArray;
using ::testing::StrEq;

TEST(AttributeContainerTest, TestGetAttributeByName) {
  falken::AttributeContainer attribute_container;
  falken::AttributeBase attribute1(attribute_container, "float_attribute", 0.0f,
                                   100.0f);
  falken::AttributeBase attribute2(attribute_container, "categorical_attribute",
                                   {"zero", "one", "two"});
  auto attribute3 = attribute_container.attribute("float_attribute");
  EXPECT_THAT(attribute3->name(), StrEq("float_attribute"));
}

TEST(AttributeContainerTest, TestMoveAttribute) {
  // Create objects.
  falken::AttributeContainer attribute_container;
  falken::AttributeBase bool_attribute(attribute_container, "bool_attribute",
                                       falken::AttributeBase::kTypeBool);
  falken::AttributeBase float_attribute(attribute_container, "float_attribute",
                                        falken::AttributeBase::kTypeFloat);

  // Set logger.
  auto logger = falken::SystemLogger::Get();
  logger->set_abort_on_fatal_error(false);
  falken::testing::StringLogger sink;
  EXPECT_TRUE(logger->AddLogger(sink));

  // Test and assert
  AttributeTest::AttributeBaseMoveValue(bool_attribute,
                                        std::move(float_attribute));
  EXPECT_EQ(sink.last_log_level(), falken::kLogLevelFatal);
  EXPECT_EQ(sink.last_message(),
            absl::StrFormat("Failed moving attributes: The type of the "
                            "'float_attribute' attribute is 'Bool', while the "
                            "type of the destination attribute "
                            "'bool_attribute' is 'Number'."));
}

TEST(AttributeContainerTest, TestCopyAttribute) {
  // Create objects.
  falken::AttributeContainer attribute_container;
  falken::AttributeBase bool_attribute(attribute_container, "bool_attribute",
                                       falken::AttributeBase::kTypeBool);
  falken::AttributeBase float_attribute(attribute_container, "float_attribute",
                                        falken::AttributeBase::kTypeFloat);

  // Set logger.
  auto logger = falken::SystemLogger::Get();
  logger->set_abort_on_fatal_error(false);
  falken::testing::StringLogger sink;
  EXPECT_TRUE(logger->AddLogger(sink));

  // Test and assert
  AttributeTest::AttributeBaseCopyValue(bool_attribute, float_attribute);
  EXPECT_EQ(sink.last_log_level(), falken::kLogLevelFatal);
  EXPECT_EQ(sink.last_message(),
            absl::StrFormat("Failed copying attributes: The type of the "
                            "'float_attribute' attribute is 'Bool', while the "
                            "type of the destination attribute "
                            "'bool_attribute' is 'Number'."));
}

TEST(AttributeContainerTest, TestGetAttributes) {
  falken::AttributeContainer attribute_container;
  const char* names[] = {"attribute1", "attribute2", "attribute3"};
  falken::AttributeBase attribute1(attribute_container, names[0], 0.0f, 100.0f);
  falken::AttributeBase attribute2(attribute_container, names[1], 0.0f, 100.0f);
  falken::AttributeBase attribute3(attribute_container, names[2],
                                   {"zero", "one", "two"});
  int index = 0;
  for (const auto* attribute : attribute_container.attributes()) {
    EXPECT_THAT(attribute->name(), StrEq(names[index])) << "index: " << index;
    index++;
  }
}

TEST(AttributeContainerTest, TestRemoveAttribute) {
  falken::AttributeContainer attribute_container;
  falken::AttributeBase attribute1(attribute_container, "attribute1", 0.0f,
                                   100.0f);
  {
    falken::AttributeBase attribute2(attribute_container, "attribute2",
                                     {"zero", "one", "two"});
    auto attributes = attribute_container.attributes();
    EXPECT_EQ(attributes[0], &attribute1);
    EXPECT_EQ(attributes[1], &attribute2);
    EXPECT_EQ(attributes.size(), 2);
  }
  auto attributes = attribute_container.attributes();
  EXPECT_EQ(attributes[0], &attribute1);
  EXPECT_EQ(attributes.size(), 1);
}

// Test that no exception/access violation occurs when destroying the
// container before the attribute.
TEST(AttributeContainerTest, TestDestroyContainerBeforeAttributes) {
  falken::AttributeContainer* attribute_container =
      new falken::AttributeContainer();
  {
    falken::AttributeBase attribute1(*attribute_container, "attribute1", 0.0f,
                                     100.0f);
    delete attribute_container;
  }
}

TEST(AttributeContainerTest, TestModificationFlags) {
  // Tests that AttributeContainer all_attributes_are_set() is only
  // true if all the attributes within have been modified.
  // Tests that calling reset_attributes_dirty_flag() marks all
  // attributes as unmodified.
  falken::AttributeContainer attribute_container;
  falken::BoolAttribute attribute0(attribute_container, "attribute1");
  falken::BoolAttribute attribute1(attribute_container, "attribute2");
  falken::BoolAttribute attribute2(attribute_container, "attribute3");
  {
    EXPECT_FALSE(AttributeTest::AttributeContainerAllAttributesAreSet(
        attribute_container));
    std::vector<std::string> unmodified_attributes;
    EXPECT_TRUE(AttributeTest::AttributeContainerHasUnmodifiedAttributes(
        attribute_container, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>(
                  {attribute0.name(), attribute1.name(), attribute2.name()}),
              unmodified_attributes);
  }
  attribute0 = false;
  attribute1 = false;
  {
    EXPECT_FALSE(AttributeTest::AttributeContainerAllAttributesAreSet(
        attribute_container));
    std::vector<std::string> unmodified_attributes;
    EXPECT_TRUE(AttributeTest::AttributeContainerHasUnmodifiedAttributes(
        attribute_container, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>({attribute2.name()}),
              unmodified_attributes);
  }
  attribute2 = false;
  {
    EXPECT_TRUE(AttributeTest::AttributeContainerAllAttributesAreSet(
        attribute_container));
    std::vector<std::string> unmodified_attributes;
    EXPECT_FALSE(AttributeTest::AttributeContainerHasUnmodifiedAttributes(
        attribute_container, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>(), unmodified_attributes);
  }
  AttributeTest::AttributeBaseResetModified(attribute1);
  {
    EXPECT_FALSE(AttributeTest::AttributeContainerAllAttributesAreSet(
        attribute_container));
    std::vector<std::string> unmodified_attributes;
    EXPECT_TRUE(AttributeTest::AttributeContainerHasUnmodifiedAttributes(
        attribute_container, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>({attribute1.name()}),
              unmodified_attributes);
  }
  attribute1 = false;
  {
    EXPECT_TRUE(AttributeTest::AttributeContainerAllAttributesAreSet(
        attribute_container));
    std::vector<std::string> unmodified_attributes;
    EXPECT_FALSE(AttributeTest::AttributeContainerHasUnmodifiedAttributes(
        attribute_container, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>(), unmodified_attributes);
  }
  AttributeTest::AttributeContainerResetAttributesDirtyFlags(
      attribute_container);
  {
    EXPECT_FALSE(AttributeTest::AttributeContainerAllAttributesAreSet(
        attribute_container));
    std::vector<std::string> unmodified_attributes;
    EXPECT_TRUE(AttributeTest::AttributeContainerHasUnmodifiedAttributes(
        attribute_container, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>(
                  {attribute0.name(), attribute1.name(), attribute2.name()}),
              unmodified_attributes);
  }
  EXPECT_FALSE(AttributeTest::AttributeBaseModified(attribute0));
  EXPECT_FALSE(AttributeTest::AttributeBaseModified(attribute1));
  EXPECT_FALSE(AttributeTest::AttributeBaseModified(attribute2));
}

TEST(NumberAttributeTest, TestConstruct) {
  falken::AttributeContainer attribute_container;
  falken::NumberAttribute<float> attribute(attribute_container,
                                           "float_attribute", 5.0f, 100.0f);
  EXPECT_THAT(attribute.name(), StrEq("float_attribute"));
  EXPECT_EQ(attribute.type(), falken::AttributeBase::kTypeFloat);
  EXPECT_EQ(attribute.number_minimum(), 5.0f);
  EXPECT_EQ(attribute.number_maximum(), 100.0f);
  EXPECT_EQ(attribute.value(), 5.0f);
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
  EXPECT_FALSE(AttributeTest::AttributeBaseModified(attribute));
}

TEST(NumberAttributeTest, TestSetValue) {
  falken::AttributeContainer attribute_container;
  falken::NumberAttribute<float> attribute(attribute_container,
                                           "float_attribute", 5.0f, 100.0f);
  EXPECT_THAT(attribute.name(), StrEq("float_attribute"));
  EXPECT_EQ(attribute.type(), falken::AttributeBase::kTypeFloat);
  EXPECT_EQ(attribute.number_minimum(), 5.0f);
  EXPECT_EQ(attribute.number_maximum(), 100.0f);
  EXPECT_EQ(attribute.value(), 5.0f);
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
  {
    EXPECT_FALSE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_TRUE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>({attribute.name()}),
              unmodified_attributes);
  }
  attribute.set_value(10.0f);
  {
    EXPECT_TRUE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_FALSE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>({}), unmodified_attributes);
  }
  AttributeTest::AttributeBaseResetModified(attribute);
  {
    EXPECT_FALSE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_TRUE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>({attribute.name()}),
              unmodified_attributes);
  }
}

TEST(NumberAttributeTest, TestCopyConstruct) {
  falken::AttributeContainer attribute_container;
  falken::NumberAttribute<float> attribute(attribute_container,
                                           "float_attribute", 5.0f, 100.0f);
  falken::AttributeContainer attribute_container2;
  falken::NumberAttribute<float> attribute2(attribute_container2, attribute);
  EXPECT_THAT(attribute2.name(), StrEq("float_attribute"));
  EXPECT_EQ(attribute2.type(), falken::AttributeBase::kTypeFloat);
  EXPECT_EQ(attribute2.number_minimum(), 5.0f);
  EXPECT_EQ(attribute2.number_maximum(), 100.0f);
  EXPECT_EQ(attribute2.value(), 5.0f);
  EXPECT_EQ(attribute_container.attribute("float_attribute"), &attribute);
  EXPECT_EQ(attribute_container2.attribute("float_attribute"), &attribute2);
  attribute.set_value(10.0f);
  EXPECT_EQ(attribute.value(), 10.0f);
  EXPECT_TRUE(AttributeTest::GetModified(attribute_container));
  EXPECT_EQ(attribute2.value(), 5.0f);
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container2));
}

TEST(NumberAttributeTest, TestMoveConstruct) {
  falken::AttributeContainer attribute_container;
  falken::NumberAttribute<float> attribute(attribute_container,
                                           "float_attribute", 5.0f, 100.0f);
  falken::NumberAttribute<float> attribute2(std::move(attribute));
  EXPECT_THAT(attribute2.name(), StrEq("float_attribute"));
  EXPECT_EQ(attribute2.type(), falken::AttributeBase::kTypeFloat);
  EXPECT_EQ(attribute2.number_minimum(), 5.0f);
  EXPECT_EQ(attribute2.number_maximum(), 100.0f);
  EXPECT_EQ(attribute2.value(), 5.0f);
  EXPECT_EQ(attribute_container.attribute("float_attribute"), &attribute2);
}

TEST(NumberAttributeTest, TestMoveContainerConstruct) {
  falken::AttributeContainer attribute_container;
  falken::NumberAttribute<float> attribute(attribute_container,
                                           "float_attribute", 5.0f, 100.0f);
  falken::AttributeContainer attribute_container2;
  falken::NumberAttribute<float> attribute2(attribute_container2,
                                            std::move(attribute));
  EXPECT_THAT(attribute2.name(), StrEq("float_attribute"));
  EXPECT_EQ(attribute2.type(), falken::AttributeBase::kTypeFloat);
  EXPECT_EQ(attribute2.number_minimum(), 5.0f);
  EXPECT_EQ(attribute2.number_maximum(), 100.0f);
  EXPECT_EQ(attribute2.value(), 5.0f);
  EXPECT_EQ(attribute_container.attribute("float_attribute"), nullptr);
  EXPECT_EQ(attribute_container2.attribute("float_attribute"), &attribute2);
}

TEST(NumberAttributeTest, TestConversionFromAttributeBase) {
  falken::AttributeContainer attribute_container;
  falken::NumberAttribute<float> attribute(attribute_container,
                                           "float_attribute", 5.0f, 100.0f);
  falken::CategoricalAttribute attribute2(
      attribute_container, "categorical_attribute", {"zero", "one", "two"});

  falken::NumberAttribute<float>& number_attribute =
      attribute_container.attribute("float_attribute")->AsNumber<float>();
  number_attribute = 20.0f;
  EXPECT_EQ(attribute.value(), 20.0f);

  const falken::NumberAttribute<float>& const_number_attribute =
      attribute_container.attribute("float_attribute")->AsNumber<float>();
  EXPECT_EQ(const_number_attribute, 20.0f);

  EXPECT_DEATH(
      attribute_container.attribute("categorical_attribute")->AsNumber<float>(),
      "Cannot cast base attribute to concrete attribute: Type mismatch. "
      "Attribute 'categorical_attribute' is not a 'Number'. Its type is "
      "'Categorical'.");
}

TEST(CategoricalAttributeTest, TestConstruct) {
  falken::AttributeContainer attribute_container;
  falken::CategoricalAttribute attribute(
      attribute_container, "categorical_attribute", {"zero", "one", "two"});
  EXPECT_THAT(attribute.name(), StrEq("categorical_attribute"));
  EXPECT_EQ(attribute.type(), falken::AttributeBase::kTypeCategorical);
  EXPECT_THAT(attribute.category_values(),
              ElementsAreArray({"zero", "one", "two"}));
  EXPECT_EQ(attribute.value(), 0);
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
}

TEST(CategoricalAttributeTest, TestSetValue) {
  falken::AttributeContainer attribute_container;
  falken::CategoricalAttribute attribute(
      attribute_container, "categorical_attribute", {"zero", "one", "two"});
  EXPECT_THAT(attribute.name(), StrEq("categorical_attribute"));
  EXPECT_EQ(attribute.type(), falken::AttributeBase::kTypeCategorical);
  EXPECT_THAT(attribute.category_values(),
              ElementsAreArray({"zero", "one", "two"}));
  EXPECT_EQ(attribute.value(), 0);
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
  {
    EXPECT_FALSE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_TRUE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>({attribute.name()}),
              unmodified_attributes);
  }
  attribute = 1;
  {
    EXPECT_TRUE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_FALSE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>({}), unmodified_attributes);
  }
  AttributeTest::AttributeBaseResetModified(attribute);
  {
    EXPECT_FALSE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_TRUE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>({attribute.name()}),
              unmodified_attributes);
  }
}

TEST(CategoricalAttributeTest, TestCopyConstruct) {
  falken::AttributeContainer attribute_container;
  falken::CategoricalAttribute attribute(
      attribute_container, "categorical_attribute", {"zero", "one", "two"});
  falken::AttributeContainer attribute_container2;
  falken::CategoricalAttribute attribute2(attribute_container2, attribute);
  EXPECT_THAT(attribute2.name(), StrEq("categorical_attribute"));
  EXPECT_EQ(attribute2.type(), falken::AttributeBase::kTypeCategorical);
  EXPECT_THAT(attribute2.category_values(),
              ElementsAreArray({"zero", "one", "two"}));
  EXPECT_EQ(attribute2.value(), 0);
  EXPECT_EQ(attribute_container.attribute("categorical_attribute"), &attribute);
  EXPECT_EQ(attribute_container2.attribute("categorical_attribute"),
            &attribute2);
  attribute = 2;
  attribute2 = 1;
  EXPECT_EQ(attribute.value(), 2);
  EXPECT_EQ(attribute2.value(), 1);
}

TEST(CategoricalAttributeTest, TestMoveConstruct) {
  falken::AttributeContainer attribute_container;
  falken::CategoricalAttribute attribute(
      attribute_container, "categorical_attribute", {"zero", "one", "two"});
  falken::CategoricalAttribute attribute2(std::move(attribute));
  EXPECT_THAT(attribute2.name(), StrEq("categorical_attribute"));
  EXPECT_EQ(attribute2.type(), falken::AttributeBase::kTypeCategorical);
  EXPECT_THAT(attribute2.category_values(),
              ElementsAreArray({"zero", "one", "two"}));
  EXPECT_EQ(attribute2.value(), 0);
  EXPECT_EQ(attribute_container.attribute("categorical_attribute"),
            &attribute2);
}

TEST(CategoricalAttributeTest, TestMoveContainerConstruct) {
  falken::AttributeContainer attribute_container;
  falken::CategoricalAttribute attribute(
      attribute_container, "categorical_attribute", {"zero", "one", "two"});
  falken::AttributeContainer attribute_container2;
  falken::CategoricalAttribute attribute2(attribute_container2,
                                          std::move(attribute));
  EXPECT_THAT(attribute2.name(), StrEq("categorical_attribute"));
  EXPECT_EQ(attribute2.type(), falken::AttributeBase::kTypeCategorical);
  EXPECT_THAT(attribute2.category_values(),
              ElementsAreArray({"zero", "one", "two"}));
  EXPECT_EQ(attribute2.value(), 0);
  EXPECT_EQ(attribute_container.attribute("categorical_attribute"), nullptr);
  EXPECT_EQ(attribute_container2.attribute("categorical_attribute"),
            &attribute2);
}

TEST(CategoricalAttributeTest, TestConversionFromAttributeBase) {
  falken::AttributeContainer attribute_container;
  falken::CategoricalAttribute attribute(
      attribute_container, "categorical_attribute", {"zero", "one", "two"});
  falken::NumberAttribute<float> attribute2(attribute_container,
                                            "float_attribute", 5.0f, 100.0f);
  falken::CategoricalAttribute& categorical_attribute =
      attribute_container.attribute("categorical_attribute")->AsCategorical();
  categorical_attribute = 1;
  EXPECT_EQ(attribute.value(), 1);

  const falken::CategoricalAttribute& const_categorical_attribute =
      attribute_container.attribute("categorical_attribute")->AsCategorical();
  EXPECT_EQ(const_categorical_attribute, 1);

  EXPECT_DEATH(
      attribute_container.attribute("float_attribute")->AsCategorical(),
      "Cannot cast base attribute to concrete attribute: Type mismatch. "
      "Attribute 'float_attribute' is not a 'Categorical'. Its type is "
      "'Number'.");
}

TEST(BoolAttributeTest, TestConstruct) {
  falken::AttributeContainer attribute_container;
  falken::BoolAttribute attribute(attribute_container, "bool_attribute");
  EXPECT_THAT(attribute.name(), StrEq("bool_attribute"));
  EXPECT_EQ(attribute.type(), falken::AttributeBase::kTypeBool);
  EXPECT_FALSE(attribute.value());
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
}

TEST(BoolAttributeTest, TestSetValue) {
  falken::AttributeContainer attribute_container;
  falken::BoolAttribute attribute(attribute_container, "bool_attribute");
  EXPECT_THAT(attribute.name(), StrEq("bool_attribute"));
  EXPECT_EQ(attribute.type(), falken::AttributeBase::kTypeBool);
  EXPECT_FALSE(attribute.value());
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
  {
    EXPECT_FALSE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_TRUE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>({attribute.name()}),
              unmodified_attributes);
  }
  attribute = true;
  {
    EXPECT_TRUE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_FALSE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>(), unmodified_attributes);
  }
  AttributeTest::AttributeBaseResetModified(attribute);
  {
    EXPECT_FALSE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_TRUE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>({attribute.name()}),
              unmodified_attributes);
  }
}

TEST(BoolAttributeTest, TestCopyConstruct) {
  falken::AttributeContainer attribute_container;
  falken::BoolAttribute attribute(attribute_container, "bool_attribute");
  falken::AttributeContainer attribute_container2;
  falken::BoolAttribute attribute2(attribute_container2, "bool_attribute");
  EXPECT_THAT(attribute.name(), StrEq("bool_attribute"));
  EXPECT_EQ(attribute.type(), falken::AttributeBase::kTypeBool);
  EXPECT_FALSE(attribute.value());
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
  attribute = true;
  EXPECT_TRUE(attribute.value());
  EXPECT_FALSE(attribute2.value());
}

TEST(BoolAttributeTest, TestMoveConstruct) {
  falken::AttributeContainer attribute_container;
  falken::BoolAttribute attribute(attribute_container, "bool_attribute");
  attribute = true;
  falken::BoolAttribute attribute2(std::move(attribute));
  EXPECT_THAT(attribute2.name(), StrEq("bool_attribute"));
  EXPECT_EQ(attribute2.type(), falken::AttributeBase::kTypeBool);
  EXPECT_TRUE(attribute2.value());
  EXPECT_EQ(attribute_container.attribute("bool_attribute"), &attribute2);
}

TEST(BoolAttributeTest, TestMoveContainerConstruct) {
  falken::AttributeContainer attribute_container;
  falken::BoolAttribute attribute(attribute_container, "bool_attribute");
  attribute = true;
  falken::AttributeContainer attribute_container2;
  falken::BoolAttribute attribute2(attribute_container2, std::move(attribute));
  EXPECT_THAT(attribute2.name(), StrEq("bool_attribute"));
  EXPECT_EQ(attribute2.type(), falken::AttributeBase::kTypeBool);
  EXPECT_TRUE(attribute2.value());
  EXPECT_EQ(attribute_container.attribute("bool_attribute"), nullptr);
  EXPECT_EQ(attribute_container2.attribute("bool_attribute"), &attribute2);
}

TEST(BoolAttributeTest, TestConversionFromAttributeBase) {
  falken::AttributeContainer attribute_container;
  falken::BoolAttribute attribute(attribute_container, "bool_attribute");
  falken::NumberAttribute<float> attribute2(attribute_container,
                                            "float_attribute", 5.0f, 100.0f);
  falken::BoolAttribute& bool_attribute =
      attribute_container.attribute("bool_attribute")->AsBool();
  bool_attribute = true;
  EXPECT_EQ(attribute.value(), 1);

  const falken::BoolAttribute& const_bool_attribute =
      attribute_container.attribute("bool_attribute")->AsBool();
  EXPECT_EQ(const_bool_attribute, true);

  EXPECT_DEATH(
      attribute_container.attribute("float_attribute")->AsBool(),
      "Cannot cast base attribute to concrete attribute: Type mismatch. "
      "Attribute 'float_attribute' is not a 'Bool'. Its type is "
      "'Number'.");
}

TEST(FeelerAttributeTest, TestConstruct) {
  falken::AttributeContainer attribute_container;
  falken::FeelersAttribute feelers(attribute_container, "feeler_attribute", 3,
                                   1.0f, 0.5f, 0.5f);
  EXPECT_THAT(feelers.name(), StrEq("feeler_attribute"));
  EXPECT_EQ(feelers.type(), falken::AttributeBase::kTypeFeelers);
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
}

TEST(FeelerAttributeTest, TestSetDistances) {
  falken::AttributeContainer attribute_container;
  falken::FeelersAttribute attribute(attribute_container, "feeler_attribute", 3,
                                     1.0f, 0.5f, 0.5f, {"zero", "one", "two"});
  EXPECT_THAT(attribute.name(), StrEq("feeler_attribute"));
  EXPECT_EQ(attribute.type(), falken::AttributeBase::kTypeFeelers);
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
  {
    EXPECT_FALSE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_TRUE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(
        std::vector<std::string>({std::string(attribute.name()) + "/distance_0",
                                  std::string(attribute.name()) + "/distance_1",
                                  std::string(attribute.name()) + "/distance_2",
                                  std::string(attribute.name()) + "/id_0",
                                  std::string(attribute.name()) + "/id_1",
                                  std::string(attribute.name()) + "/id_2"}),
        unmodified_attributes);
  }
  attribute.distances()[0] = 1.0f;
  attribute.distances()[1] = 1.0f;
  attribute.ids()[0].set_value(2);
  attribute.ids()[1].set_value(2);
  {
    EXPECT_FALSE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_TRUE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(
        std::vector<std::string>({std::string(attribute.name()) + "/distance_2",
                                  std::string(attribute.name()) + "/id_2"}),
        unmodified_attributes);
  }
  attribute.distances()[2] = 1.0f;
  {
    EXPECT_FALSE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_TRUE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(
        std::vector<std::string>({std::string(attribute.name()) + "/id_2"}),
        unmodified_attributes);
  }
  attribute.ids()[2].set_value(2);
  {
    EXPECT_TRUE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_FALSE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>(), unmodified_attributes);
  }
  AttributeTest::AttributeBaseResetModified(attribute);
  {
    EXPECT_FALSE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_TRUE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(
        std::vector<std::string>({std::string(attribute.name()) + "/distance_0",
                                  std::string(attribute.name()) + "/distance_1",
                                  std::string(attribute.name()) + "/distance_2",
                                  std::string(attribute.name()) + "/id_0",
                                  std::string(attribute.name()) + "/id_1",
                                  std::string(attribute.name()) + "/id_2"}),
        unmodified_attributes);
  }
}

TEST(FeelerAttributeTest, TestMoveConstruct) {
  falken::AttributeContainer attribute_container;
  falken::FeelersAttribute feelers(attribute_container, "feeler_attribute", 3,
                                   1.0f, 0.5f, 0.5f, {"zero", "one", "two"});
  feelers.distances()[0] = 1.0f;
  feelers.ids()[1] = 2;
  falken::FeelersAttribute feelers2(std::move(feelers));
  EXPECT_THAT(feelers2.name(), StrEq("feeler_attribute"));
  EXPECT_EQ(feelers2.type(), falken::AttributeBase::kTypeFeelers);
  EXPECT_EQ(feelers2.distances()[0].value(), 1.0f);
  EXPECT_EQ(feelers2.ids()[1].value(), 2);
  EXPECT_EQ(feelers2.distances().size(), 3);
  EXPECT_EQ(feelers2.length(), 1.0f);
  EXPECT_EQ(feelers2.radius(), 0.5f);
  EXPECT_EQ(feelers2.fov_angle(), 0.5f);
  EXPECT_EQ(attribute_container.attribute("feeler_attribute"), &feelers2);
}

TEST(FeelerAttributeTest, TestMoveContainerConstruct) {
  falken::AttributeContainer attribute_container;
  falken::AttributeContainer attribute_container_copy;
  falken::FeelersAttribute feelers(attribute_container, "feeler_attribute", 3,
                                   1.0f, 0.5f, 0.5f, {"zero", "one", "two"});
  feelers.distances()[0] = 0.5f;
  falken::FeelersAttribute feelers2(attribute_container_copy,
                                    std::move(feelers));
  EXPECT_THAT(feelers2.name(), StrEq("feeler_attribute"));
  EXPECT_EQ(feelers2.type(), falken::AttributeBase::kTypeFeelers);
  EXPECT_EQ(feelers2.distances()[0].value(), 0.5f);
  EXPECT_EQ(feelers2.distances().size(), 3);
  EXPECT_EQ(feelers2.length(), 1.0f);
  EXPECT_EQ(feelers2.radius(), 0.5f);
  EXPECT_EQ(feelers2.fov_angle(), 0.5f);
  EXPECT_EQ(attribute_container.attribute("feeler_attribute"), nullptr);
  EXPECT_EQ(attribute_container_copy.attribute("feeler_attribute"), &feelers2);
}

TEST(FeelerAttributeTest, TestCopyConstruct) {
  falken::AttributeContainer attribute_container;
  falken::AttributeContainer attribute_container_copy;
  falken::FeelersAttribute feelers(attribute_container, "feeler_attribute", 3,
                                   1.0f, 0.5f, 0.5f, {"zero", "one", "two"});
  falken::FeelersAttribute feelers2(attribute_container_copy, feelers);
  EXPECT_THAT(feelers2.name(), StrEq(feelers.name()));
  EXPECT_EQ(feelers2.type(), feelers.type());
  EXPECT_EQ(feelers2.distances().size(), 3);
  EXPECT_EQ(feelers2.length(), 1.0f);
  EXPECT_EQ(feelers2.radius(), 0.5f);
  EXPECT_EQ(feelers2.fov_angle(), 0.5f);
  EXPECT_EQ(feelers2.distances()[0].value(), feelers.distances()[0].value());
  EXPECT_EQ(attribute_container.attribute("feeler_attribute"), &feelers);
  EXPECT_EQ(attribute_container_copy.attribute("feeler_attribute"), &feelers2);
}

TEST(FeelerAttributeTest, TestDistanceFeelers) {
  falken::AttributeContainer attribute_container;
  falken::FeelersAttribute feelers(attribute_container, "feeler_attribute", 3,
                                   1.0f, 0.5f, 0.5f);
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
  std::shared_ptr<falken::SystemLogger> logger = falken::SystemLogger::Get();
  logger->set_abort_on_fatal_error(false);
  falken::testing::StringLogger sink;
  EXPECT_TRUE(logger->AddLogger(sink));
  EXPECT_FALSE(feelers.distances()[1].set_value(1.5f));
  EXPECT_EQ(sink.last_log_level(), falken::kLogLevelFatal);
  EXPECT_EQ(sink.last_message(),
            absl::StrFormat("Unable to set value of attribute '%s' to %.1f "
                            "as it is out of the specified range %d to %d.",
                            "distance_1", 1.5f, 0, 1));
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
  EXPECT_TRUE(feelers.distances()[0].set_value(1.0f));
  EXPECT_TRUE(AttributeTest::GetModified(attribute_container));
  EXPECT_TRUE(feelers.distances()[2].set_value(1.0f));
}

TEST(FeelerAttributeTest, TestIdsFeelers) {
  falken::AttributeContainer attribute_container;
  falken::FeelersAttribute feelers(attribute_container, "feeler_attribute", 3,
                                   1.0f, 0.5f, 0.5f, {"zero", "one", "two"});
  EXPECT_EQ(feelers.distances().size(), 3);
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
  std::shared_ptr<falken::SystemLogger> logger = falken::SystemLogger::Get();
  logger->set_abort_on_fatal_error(false);
  falken::testing::StringLogger sink;
  EXPECT_TRUE(logger->AddLogger(sink));
  EXPECT_FALSE(feelers.ids()[2].set_value(4));
  EXPECT_EQ(sink.last_log_level(), falken::kLogLevelFatal);
  EXPECT_EQ(sink.last_message(),
            absl::StrFormat("Unable to set value of attribute '%s' to %d "
                            "as it is out of the specified range %d to %d.",
                            "id_2", 4, 0, 2));
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
  EXPECT_TRUE(feelers.ids()[0].set_value(0));
  EXPECT_TRUE(AttributeTest::GetModified(attribute_container));
  EXPECT_TRUE(feelers.ids()[1].set_value(2));
  EXPECT_THAT(feelers.ids()[0].category_values(),
              ElementsAreArray({"zero", "one", "two"}));
  EXPECT_THAT(feelers.ids()[1].category_values(),
              ElementsAreArray({"zero", "one", "two"}));
  EXPECT_THAT(feelers.ids()[2].category_values(),
              ElementsAreArray({"zero", "one", "two"}));
}

TEST(FeelerAttributeTest, TestBothFeelers) {
  falken::AttributeContainer attribute_container;
  falken::FeelersAttribute feelers(attribute_container, "feeler_attribute", 3,
                                   1.0f, 0.5f, 0.5f, {"zero", "one", "two"});
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
  std::shared_ptr<falken::SystemLogger> logger = falken::SystemLogger::Get();
  logger->set_abort_on_fatal_error(false);
  falken::testing::StringLogger sink;
  EXPECT_TRUE(logger->AddLogger(sink));
  EXPECT_TRUE(feelers.distances()[0].set_value(0.7f));
  EXPECT_FALSE(feelers.distances()[1].set_value(1.5f));
  EXPECT_EQ(sink.last_log_level(), falken::kLogLevelFatal);
  EXPECT_EQ(sink.last_message(),
            absl::StrFormat("Unable to set value of attribute '%s' to %.1f "
                            "as it is out of the specified range %d to %d.",
                            "distance_1", 1.5f, 0, 1));
  EXPECT_TRUE(feelers.distances()[2].set_value(0.1f));
  EXPECT_TRUE(feelers.ids()[0].set_value(0));
  EXPECT_TRUE(feelers.ids()[1].set_value(2));
  EXPECT_FALSE(feelers.ids()[2].set_value(4));
  EXPECT_EQ(sink.last_log_level(), falken::kLogLevelFatal);
  EXPECT_EQ(sink.last_message(),
            absl::StrFormat("Unable to set value of attribute '%s' to %d "
                            "as it is out of the specified range %d to %d.",
                            "id_2", 4, 0, 2));
  EXPECT_TRUE(AttributeTest::GetModified(attribute_container));
}

TEST(FeelerAttributeTest, TestConversionFromAttributeBase) {
  falken::AttributeContainer attribute_container;
  falken::FeelersAttribute attribute(attribute_container, "feelers_attribute",
                                     3, 1.0f, 0.5f, 0.5f);
  falken::NumberAttribute<float> attribute2(attribute_container,
                                            "float_attribute", 5.0f, 100.0f);
  falken::FeelersAttribute& feelers_attribute =
      attribute_container.attribute("feelers_attribute")->AsFeelers();
  feelers_attribute.distances()[0] = 1.0f;
  EXPECT_EQ(feelers_attribute.distances()[0], 1.0f);

  const falken::FeelersAttribute& const_feelers_attribute =
      attribute_container.attribute("feelers_attribute")->AsFeelers();
  EXPECT_EQ(const_feelers_attribute.distances()[0], 1.0f);

  EXPECT_DEATH(
      attribute_container.attribute("float_attribute")->AsFeelers(),
      "Cannot cast base attribute to concrete attribute: Type mismatch. "
      "Attribute 'float_attribute' is not a 'Feelers'. Its type is "
      "'Number'.");
}

TEST(FeelerAttributeTest, TestInvalidNumberOfFeelers) {
  ASSERT_DEATH(
      []() {
        falken::AttributeContainer attribute_container;
        falken::FeelersAttribute feelers(
            attribute_container, "feeler_attribute", 10, 1.0f, 0.5f, 0.5f);
      }(),
      "Can't construct feeler attribute with '10' feelers. Please use any of "
      "the allowed values: 1, 2, 3, 4, 14, 15, 32, 33, 68, 69, 140, 141.");
}

TEST(PositionAttributeTest, TestConstruct) {
  falken::AttributeContainer attribute_container;
  falken::PositionAttribute attribute(attribute_container,
                                      "position_attribute");
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
  falken::Position position({1.0f, 2.0f, 3.0f});
  attribute = position;
  EXPECT_TRUE(AttributeTest::GetModified(attribute_container));
  EXPECT_THAT(attribute.name(), StrEq("position_attribute"));
  EXPECT_EQ(attribute.type(), falken::AttributeBase::kTypePosition);
  EXPECT_EQ(attribute.value(), position);
}

TEST(PositionAttributeTest, TesSetValue) {
  falken::AttributeContainer attribute_container;
  falken::PositionAttribute attribute(attribute_container,
                                      "position_attribute");
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
  falken::Position position({1.0f, 2.0f, 3.0f});
  {
    EXPECT_FALSE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_TRUE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>({std::string(attribute.name())}),
              unmodified_attributes);
  }
  attribute = position;
  {
    EXPECT_TRUE(AttributeTest::GetModified(attribute_container));
    EXPECT_THAT(attribute.name(), StrEq("position_attribute"));
    EXPECT_EQ(attribute.type(), falken::AttributeBase::kTypePosition);
    EXPECT_EQ(attribute.value(), position);
    EXPECT_TRUE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_FALSE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>(), unmodified_attributes);
  }
  AttributeTest::AttributeBaseResetModified(attribute);
  {
    EXPECT_FALSE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_TRUE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>({std::string(attribute.name())}),
              unmodified_attributes);
  }
}

TEST(PositionAttributeTest, TestMoveConstruct) {
  falken::AttributeContainer attribute_container;
  falken::AttributeContainer attribute_container2;
  falken::PositionAttribute attribute(attribute_container,
                                      "position_attribute");
  falken::Position position({1.0f, 2.0f, 3.0f});
  attribute = position;
  falken::PositionAttribute attribute2(attribute_container2,
                                       std::move(attribute));
  EXPECT_THAT(attribute2.name(), StrEq("position_attribute"));
  EXPECT_EQ(attribute2.type(), falken::AttributeBase::kTypePosition);
  EXPECT_EQ(attribute2.value(), position);
  EXPECT_EQ(attribute_container.attribute("position_attribute"), nullptr);
  EXPECT_EQ(attribute_container2.attribute("position_attribute"), &attribute2);
}

TEST(PositionAttributeTest, TestCopyConstruct) {
  falken::AttributeContainer attribute_container;
  falken::AttributeContainer attribute_container2;
  falken::PositionAttribute attribute(attribute_container,
                                      "position_attribute");
  falken::Position position({1.0f, 2.0f, 3.0f});
  attribute = position;
  falken::PositionAttribute attribute2(attribute_container2, attribute);
  EXPECT_THAT(attribute2.name(), StrEq("position_attribute"));
  EXPECT_EQ(attribute2.type(), falken::AttributeBase::kTypePosition);
  EXPECT_EQ(attribute2.value(), position);
  EXPECT_EQ(attribute_container.attribute("position_attribute"), &attribute);
  EXPECT_EQ(attribute_container2.attribute("position_attribute"), &attribute2);
}

TEST(PositionAttributeTest, TestConversionFromAttributeBase) {
  falken::AttributeContainer attribute_container;
  falken::PositionAttribute attribute(attribute_container,
                                      "position_attribute");
  falken::NumberAttribute<float> attribute2(attribute_container,
                                            "float_attribute", 5.0f, 100.0f);
  falken::PositionAttribute& position_attribute =
      attribute_container.attribute("position_attribute")->AsPosition();
  falken::Position position({1.0f, 2.0f, 3.0f});
  position_attribute = position;
  EXPECT_EQ(position_attribute.value(), position);

  const falken::PositionAttribute& const_position_attribute =
      attribute_container.attribute("position_attribute")->AsPosition();
  EXPECT_EQ(const_position_attribute.value(), position);

  EXPECT_DEATH(
      attribute_container.attribute("float_attribute")->AsPosition(),
      "Cannot cast base attribute to concrete attribute: Type mismatch. "
      "Attribute 'float_attribute' is not a 'Position'. Its type is "
      "'Number'.");
}

TEST(RotationAttributeTest, TestConstruct) {
  falken::AttributeContainer attribute_container;
  falken::RotationAttribute attribute(attribute_container,
                                      "rotation_attribute");
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
  falken::Rotation rotation({1.0f, 1.0f, 1.0f, 0.0f});
  attribute = rotation;
  EXPECT_TRUE(AttributeTest::GetModified(attribute_container));
  EXPECT_THAT(attribute.name(), StrEq("rotation_attribute"));
  EXPECT_EQ(attribute.type(), falken::AttributeBase::kTypeRotation);
  EXPECT_EQ(attribute.value(), rotation);
}

TEST(RotationAttributeTest, TestSetValue) {
  falken::AttributeContainer attribute_container;
  falken::RotationAttribute attribute(attribute_container,
                                      "rotation_attribute");
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
  falken::Rotation rotation({1.0f, 1.0f, 1.0f, 0.0f});
  {
    EXPECT_FALSE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_TRUE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>({std::string(attribute.name())}),
              unmodified_attributes);
  }
  attribute = rotation;
  {
    EXPECT_TRUE(AttributeTest::GetModified(attribute_container));
    EXPECT_THAT(attribute.name(), StrEq("rotation_attribute"));
    EXPECT_EQ(attribute.type(), falken::AttributeBase::kTypeRotation);
    EXPECT_EQ(attribute.value(), rotation);
    EXPECT_TRUE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_FALSE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>(), unmodified_attributes);
  }
  AttributeTest::AttributeBaseResetModified(attribute);
  {
    EXPECT_FALSE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_TRUE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>({std::string(attribute.name())}),
              unmodified_attributes);
  }
}

TEST(RotationAttributeTest, TestMoveConstruct) {
  falken::AttributeContainer attribute_container;
  falken::AttributeContainer attribute_container2;
  falken::RotationAttribute attribute(attribute_container,
                                      "rotation_attribute");
  falken::Rotation rotation({1.0f, 1.0f, 1.0f, 0.0f});
  attribute = rotation;
  falken::RotationAttribute attribute2(attribute_container2,
                                       std::move(attribute));
  EXPECT_THAT(attribute2.name(), StrEq("rotation_attribute"));
  EXPECT_EQ(attribute2.type(), falken::AttributeBase::kTypeRotation);
  EXPECT_EQ(attribute2.value(), rotation);
  EXPECT_EQ(attribute_container.attribute("rotation_attribute"), nullptr);
  EXPECT_EQ(attribute_container2.attribute("rotation_attribute"), &attribute2);
}

TEST(RotationAttributeTest, TestCopyConstruct) {
  falken::AttributeContainer attribute_container;
  falken::AttributeContainer attribute_container2;
  falken::RotationAttribute attribute(attribute_container,
                                      "rotation_attribute");
  falken::Rotation rotation({1.0f, 1.0f, 1.0f, 0.0f});
  attribute = rotation;
  falken::RotationAttribute attribute2(attribute_container2, attribute);
  EXPECT_THAT(attribute2.name(), StrEq("rotation_attribute"));
  EXPECT_EQ(attribute2.type(), falken::AttributeBase::kTypeRotation);
  EXPECT_EQ(attribute2.value(), rotation);
  EXPECT_EQ(attribute_container.attribute("rotation_attribute"), &attribute);
  EXPECT_EQ(attribute_container2.attribute("rotation_attribute"), &attribute2);
}

TEST(RotationAttributeTest, TestConversionFromAttributeBase) {
  falken::AttributeContainer attribute_container;
  falken::RotationAttribute attribute(attribute_container,
                                      "rotation_attribute");
  falken::NumberAttribute<float> attribute2(attribute_container,
                                            "float_attribute", 5.0f, 100.0f);
  falken::RotationAttribute& rotation_attribute =
      attribute_container.attribute("rotation_attribute")->AsRotation();
  falken::Rotation rotation({1.0f, 1.0f, 1.0f, 0.0f});
  rotation_attribute = rotation;
  EXPECT_EQ(rotation_attribute.value(), rotation);

  const falken::RotationAttribute& const_rotation_attribute =
      attribute_container.attribute("rotation_attribute")->AsRotation();
  EXPECT_EQ(const_rotation_attribute.value(), rotation);

  EXPECT_DEATH(
      attribute_container.attribute("float_attribute")->AsRotation(),
      "Cannot cast base attribute to concrete attribute: Type mismatch. "
      "Attribute 'float_attribute' is not a 'Rotation'. Its type is "
      "'Number'.");
}

TEST(NumberAttributeTest, TestSetOkValueFloatAttribute) {
  falken::AttributeContainer attribute_container;
  falken::NumberAttribute<float> attribute(attribute_container,
                                           "float_attribute", 0.0f, 100.0f);
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
  EXPECT_TRUE(attribute.set_value(0.0f));
  EXPECT_TRUE(attribute.set_value(50.0f));
  EXPECT_TRUE(attribute.set_value(100.0f));
  EXPECT_TRUE(AttributeTest::GetModified(attribute_container));
}

TEST(CategoricalAttributeTest, TestSetOkValue) {
  falken::AttributeContainer attribute_container;
  falken::CategoricalAttribute attribute(
      attribute_container, "categorical_attribute", {"zero", "one", "two"});
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
  EXPECT_TRUE(attribute.set_value(0));
  EXPECT_TRUE(attribute.set_value(1));
  EXPECT_TRUE(attribute.set_value(2));
  EXPECT_TRUE(AttributeTest::GetModified(attribute_container));
}

TEST(BoolAttributeTest, TestSetOkValue) {
  falken::AttributeContainer attribute_container;
  falken::BoolAttribute attribute(attribute_container, "bool_attribute");
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
  EXPECT_TRUE(attribute.set_value(true));
  EXPECT_TRUE(attribute.set_value(false));
  EXPECT_TRUE(AttributeTest::GetModified(attribute_container));
}

TEST(NumberAttributeTest, TestSetWrongValueFloatAttribute) {
  falken::AttributeContainer attribute_container;
  falken::NumberAttribute<float> attribute(attribute_container,
                                           "float_attribute", 0.0f, 100.0f);
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
  std::shared_ptr<falken::SystemLogger> logger = falken::SystemLogger::Get();
  logger->set_abort_on_fatal_error(false);
  falken::testing::StringLogger sink;
  EXPECT_TRUE(logger->AddLogger(sink));
  EXPECT_FALSE(attribute.set_value(-50.0f));
  EXPECT_EQ(sink.last_log_level(), falken::kLogLevelFatal);
  EXPECT_EQ(sink.last_message(),
            absl::StrFormat("Unable to set value of attribute '%s' to %d "
                            "as it is out of the specified range %d to %d.",
                            attribute.name(), -50, 0, 100));
  EXPECT_FALSE(attribute.set_value(-1.0f));

  EXPECT_EQ(sink.last_log_level(), falken::kLogLevelFatal);
  EXPECT_EQ(sink.last_message(),
            absl::StrFormat("Unable to set value of attribute '%s' to %d "
                            "as it is out of the specified range %d to %d.",
                            attribute.name(), -1, 0, 100));
  EXPECT_FALSE(attribute.set_value(101.0f));
  EXPECT_EQ(sink.last_log_level(), falken::kLogLevelFatal);
  EXPECT_EQ(sink.last_message(),
            absl::StrFormat("Unable to set value of attribute '%s' to %d "
                            "as it is out of the specified range %d to %d.",
                            attribute.name(), 101, 0, 100));
  EXPECT_FALSE(attribute.set_value(150.0f));
  EXPECT_EQ(sink.last_log_level(), falken::kLogLevelFatal);
  EXPECT_EQ(sink.last_message(),
            absl::StrFormat("Unable to set value of attribute '%s' to %d "
                            "as it is out of the specified range %d to %d.",
                            attribute.name(), 150, 0, 100));
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
}

TEST(CategoricalAttributeTest, TestSetWrongValue) {
  falken::AttributeContainer attribute_container;
  falken::CategoricalAttribute attribute(
      attribute_container, "categorical_attribute", {"zero", "one", "two"});
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
  std::shared_ptr<falken::SystemLogger> logger = falken::SystemLogger::Get();
  logger->set_abort_on_fatal_error(false);
  falken::testing::StringLogger sink;
  EXPECT_TRUE(logger->AddLogger(sink));
  EXPECT_FALSE(attribute.set_value(-5));
  EXPECT_EQ(sink.last_log_level(), falken::kLogLevelFatal);
  EXPECT_EQ(sink.last_message(),
            absl::StrFormat("Unable to set value of attribute '%s' to %d "
                            "as it is out of the specified range %d to %d.",
                            attribute.name(), -5, 0, 2));
  EXPECT_FALSE(attribute.set_value(-1));
  EXPECT_EQ(sink.last_log_level(), falken::kLogLevelFatal);
  EXPECT_EQ(sink.last_message(),
            absl::StrFormat("Unable to set value of attribute '%s' to %d "
                            "as it is out of the specified range %d to %d.",
                            attribute.name(), -1, 0, 2));
  EXPECT_FALSE(attribute.set_value(3));
  EXPECT_EQ(sink.last_log_level(), falken::kLogLevelFatal);
  EXPECT_EQ(sink.last_message(),
            absl::StrFormat("Unable to set value of attribute '%s' to %d "
                            "as it is out of the specified range %d to %d.",
                            attribute.name(), 3, 0, 2));
  EXPECT_FALSE(attribute.set_value(5));
  EXPECT_EQ(sink.last_log_level(), falken::kLogLevelFatal);
  EXPECT_EQ(sink.last_message(),
            absl::StrFormat("Unable to set value of attribute '%s' to %d "
                            "as it is out of the specified range %d to %d.",
                            attribute.name(), 5, 0, 2));
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
}

TEST(UnconstrainedAttributeTest, TestSetGetFloatNumber) {
  falken::AttributeContainer attribute_container;
  falken::UnconstrainedAttribute<float, falken::AttributeBase::kTypeFloat>
      attribute(attribute_container, "test");
  attribute.set_value(42.0f);
  EXPECT_EQ(attribute.value(), 42.0f);
}

TEST(UnconstrainedAttributeTest, TestSetGetIntNumber) {
  falken::AttributeContainer attribute_container;
  falken::UnconstrainedAttribute<int, falken::AttributeBase::kTypeFloat>
      attribute(attribute_container, "test");
  attribute.set_value(42);
  EXPECT_EQ(attribute.value(), 42);
}

TEST(UnconstrainedAttributeTest, TestSetGetBool) {
  falken::AttributeContainer attribute_container;
  falken::UnconstrainedAttribute<bool, falken::AttributeBase::kTypeBool>
      attribute(attribute_container, "test");
  attribute.set_value(true);
  EXPECT_EQ(attribute.value(), true);
  attribute.set_value(false);
  EXPECT_EQ(attribute.value(), false);
}

TEST(UnconstrainedAttributeTest, TestSetGetPosition) {
  falken::AttributeContainer attribute_container;
  falken::UnconstrainedAttribute<falken::Position,
                                 falken::AttributeBase::kTypePosition>
      attribute(attribute_container, "test");
  const falken::Position kValue(1.0f, 2.0f, 3.0f);
  attribute.set_value(kValue);
  EXPECT_EQ(attribute.value(), kValue);
}


TEST(UnconstrainedAttributeTest, TestSetGetRotation) {
  falken::AttributeContainer attribute_container;
  falken::UnconstrainedAttribute<falken::Rotation,
                                 falken::AttributeBase::kTypeRotation>
      attribute(attribute_container, "test");
  const falken::Rotation kValue(0.0f, 0.0f, 0.0f, 1.0f);
  attribute.set_value(kValue);
  EXPECT_EQ(attribute.value(), kValue);
}

TEST(JoystickAttributeTest, TestGetSetAxes) {
  falken::AttributeContainer attribute_container;
  falken::JoystickAttribute joystick(
      attribute_container, "joystick_attribute",
      falken::kAxesModeDeltaPitchYaw,
      falken::kControlledEntityPlayer,
      falken::kControlFrameCamera);
  std::shared_ptr<falken::SystemLogger> logger = falken::SystemLogger::Get();
  logger->set_abort_on_fatal_error(false);
  falken::testing::StringLogger sink;
  EXPECT_TRUE(logger->AddLogger(sink));

  EXPECT_TRUE(joystick.set_x_axis(0.5f));
  EXPECT_TRUE(joystick.set_y_axis(0.25f));

  EXPECT_FALSE(joystick.set_x_axis(1.5f));
  EXPECT_EQ(sink.last_log_level(), falken::kLogLevelFatal);
  EXPECT_FALSE(joystick.set_y_axis(-1.25f));
  EXPECT_EQ(sink.last_log_level(), falken::kLogLevelFatal);

  EXPECT_EQ(joystick.x_axis(), 0.5f);
  EXPECT_EQ(joystick.y_axis(), 0.25f);
}

TEST(JoystickAttributeTest, TestConstruct) {
  falken::AttributeContainer attribute_container;
  falken::JoystickAttribute joystick(
      attribute_container, "joystick_attribute",
      falken::kAxesModeDeltaPitchYaw,
      falken::kControlledEntityPlayer,
      falken::kControlFrameCamera);

  EXPECT_THAT(joystick.name(), StrEq("joystick_attribute"));
  EXPECT_EQ(joystick.type(), falken::AttributeBase::kTypeJoystick);
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
}

TEST(JoystickAttributeTest, TestSetValues) {
  falken::AttributeContainer attribute_container;
  falken::JoystickAttribute attribute(
      attribute_container, "joystick_attribute", falken::kAxesModeDeltaPitchYaw,
      falken::kControlledEntityPlayer, falken::kControlFrameCamera);
  EXPECT_THAT(attribute.name(), StrEq("joystick_attribute"));
  EXPECT_EQ(attribute.type(), falken::AttributeBase::kTypeJoystick);
  EXPECT_FALSE(AttributeTest::GetModified(attribute_container));
  {
    EXPECT_FALSE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_TRUE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(
        std::vector<std::string>({std::string(attribute.name()) + "/x_axis",
                                  std::string(attribute.name()) + "/y_axis"}),
        unmodified_attributes);
  }
  attribute.set_x_axis(1.0f);
  {
    EXPECT_FALSE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_TRUE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(
        std::vector<std::string>({std::string(attribute.name()) + "/y_axis"}),
        unmodified_attributes);
  }
  attribute.set_y_axis(1.0f);
  {
    EXPECT_TRUE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_FALSE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>(), unmodified_attributes);
  }
  AttributeTest::AttributeBaseResetModified(attribute);
  {
    EXPECT_FALSE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_TRUE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(
        std::vector<std::string>({std::string(attribute.name()) + "/x_axis",
                                  std::string(attribute.name()) + "/y_axis"}),
        unmodified_attributes);
  }
  attribute.set_y_axis(1.0f);
  {
    EXPECT_FALSE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_TRUE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(
        std::vector<std::string>({std::string(attribute.name()) + "/x_axis"}),
        unmodified_attributes);
  }
  attribute.set_x_axis(1.0f);
  {
    EXPECT_TRUE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_FALSE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(std::vector<std::string>(), unmodified_attributes);
  }
  AttributeTest::AttributeBaseResetModified(attribute);
  {
    EXPECT_FALSE(AttributeTest::AttributeBaseModified(attribute));
    std::vector<std::string> unmodified_attributes;
    EXPECT_TRUE(AttributeTest::AttributeBaseIsNotModified(
        attribute, unmodified_attributes));
    EXPECT_EQ(
        std::vector<std::string>({std::string(attribute.name()) + "/x_axis",
                                  std::string(attribute.name()) + "/y_axis"}),
        unmodified_attributes);
  }
}

TEST(JoystickAttributeTest, TestMoveConstruct) {
  falken::AttributeContainer attribute_container;
  falken::JoystickAttribute joystick(
      attribute_container, "joystick_attribute",
      falken::kAxesModeDeltaPitchYaw,
      falken::kControlledEntityPlayer,
      falken::kControlFrameCamera);

  EXPECT_TRUE(joystick.set_x_axis(0.5f));
  EXPECT_TRUE(joystick.set_y_axis(0.25f));

  falken::JoystickAttribute joystick2(std::move(joystick));
  EXPECT_THAT(joystick2.name(), StrEq("joystick_attribute"));
  EXPECT_EQ(joystick2.type(), falken::AttributeBase::kTypeJoystick);
  EXPECT_EQ(joystick2.joystick_control_frame(), falken::kControlFrameCamera);
  EXPECT_EQ(joystick2.joystick_controlled_entity(),
            falken::kControlledEntityPlayer);
  EXPECT_EQ(joystick2.x_axis(), 0.5f);
  EXPECT_EQ(joystick2.y_axis(), 0.25f);
}

TEST(JoystickAttributeTest, TestMoveContainerConstruct) {
  falken::AttributeContainer attribute_container;
  falken::AttributeContainer attribute_container_copy;
  falken::JoystickAttribute joystick(
      attribute_container, "joystick_attribute",
      falken::kAxesModeDeltaPitchYaw,
      falken::kControlledEntityPlayer,
      falken::kControlFrameCamera);

  EXPECT_TRUE(joystick.set_x_axis(0.5f));
  EXPECT_TRUE(joystick.set_y_axis(0.25f));

  falken::JoystickAttribute joystick2(attribute_container_copy,
                                      std::move(joystick));
  EXPECT_THAT(joystick2.name(), StrEq("joystick_attribute"));
  EXPECT_EQ(joystick2.type(), falken::AttributeBase::kTypeJoystick);

  EXPECT_EQ(attribute_container.attribute("joystick_attribute"), nullptr);
  EXPECT_EQ(attribute_container_copy.attribute("joystick_attribute"),
            &joystick2);

  EXPECT_EQ(joystick2.joystick_control_frame(), falken::kControlFrameCamera);
  EXPECT_EQ(joystick2.joystick_controlled_entity(),
            falken::kControlledEntityPlayer);
  EXPECT_EQ(joystick2.x_axis(), 0.5f);
  EXPECT_EQ(joystick2.y_axis(), 0.25f);
}

TEST(JoystickAttributeTest, TestCopyConstruct) {
  falken::AttributeContainer attribute_container;
  falken::AttributeContainer attribute_container_copy;

  falken::JoystickAttribute joystick(
      attribute_container, "joystick_attribute",
      falken::kAxesModeDeltaPitchYaw,
      falken::kControlledEntityPlayer,
      falken::kControlFrameCamera);

  EXPECT_TRUE(joystick.set_x_axis(0.5f));
  EXPECT_TRUE(joystick.set_y_axis(0.25f));

  falken::JoystickAttribute joystick2(attribute_container_copy, joystick);
  EXPECT_THAT(joystick2.name(), StrEq("joystick_attribute"));
  EXPECT_EQ(joystick2.type(), falken::AttributeBase::kTypeJoystick);
  EXPECT_EQ(joystick2.joystick_control_frame(), falken::kControlFrameCamera);
  EXPECT_EQ(joystick2.joystick_controlled_entity(),
            falken::kControlledEntityPlayer);
  EXPECT_EQ(joystick2.x_axis(), 0.5f);
  EXPECT_EQ(joystick2.y_axis(), 0.25f);

  EXPECT_EQ(attribute_container.attribute("joystick_attribute"), &joystick);
  EXPECT_EQ(attribute_container_copy.attribute("joystick_attribute"),
            &joystick2);
}

}  // namespace
