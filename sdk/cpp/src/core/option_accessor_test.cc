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

#include "src/core/option_accessor.h"

#include <stdio.h>

#include "gtest/gtest.h"
#include "flatbuffers/flexbuffers.h"
#include "flatbuffers/idl.h"

namespace falken {
namespace core {

// Parses JSON into a Flexbuffer and returns a reference to the root.
class FlexBufferParser {
 public:
  bool Parse(const char* json) {
    flatbuffers::Parser parser;
    builder_.Clear();
    return parser.ParseFlexBuffer(json, nullptr, &builder_);
  }

  flexbuffers::Map GetRootMap() {
    return flexbuffers::GetRoot(builder_.GetBuffer()).AsMap();
  }

 private:
  flexbuffers::Builder builder_;
};

class OptionAccessorTest : public testing::Test {
 protected:
  struct NestedTestObject {
    std::string value1;
  };

  // Used to get / set values using options.
  struct TestObject {
    std::string value1;
    int value2;
    std::string group_value1;
    std::string group_value2;
    NestedTestObject nested;
  };

  OptionAccessorTest()
      : value1_accessor_(
            "value1",
            [](TestObject* storage_object,
               const OptionAccessor<TestObject>& accessor,
               const std::string& path, const flexbuffers::Reference& value) {
              if (!value.IsString()) {
                printf("%s must be a string\n", path.c_str());
                return false;
              }
              storage_object->value1 = value.As<std::string>();
              return true;
            },
            [](const TestObject& storage_object,
               const OptionAccessor<TestObject>& accessor,
               const std::string& path, flexbuffers::Builder* builder) {
              builder->String(accessor.name().c_str(), storage_object.value1);
            }),
        value2_accessor_(
            "value2",
            [](TestObject* storage_object,
               const OptionAccessor<TestObject>& accessor,
               const std::string& path, const flexbuffers::Reference& value) {
              if (!value.IsInt()) {
                printf("%s must be an integer\n", path.c_str());
                return false;
              }
              storage_object->value2 = value.AsInt32();
              return true;
            },
            [](const TestObject& storage_object,
               const OptionAccessor<TestObject>& accessor,
               const std::string& path, flexbuffers::Builder* builder) {
              builder->Int(accessor.name().c_str(), storage_object.value2);
            }),
        group_value1_accessor_(
            "value1",
            [](TestObject* storage_object,
               const OptionAccessor<TestObject>& accessor,
               const std::string& path, const flexbuffers::Reference& value) {
              if (!value.IsString()) {
                printf("%s must be a string\n", path.c_str());
                return false;
              }
              storage_object->group_value1 = value.As<std::string>();
              return true;
            },
            [](const TestObject& storage_object,
               const OptionAccessor<TestObject>& accessor,
               const std::string& path, flexbuffers::Builder* builder) {
              builder->String(accessor.name().c_str(),
                              storage_object.group_value1);
            }),
        group_value2_accessor_(
            "value2",
            [](TestObject* storage_object,
               const OptionAccessor<TestObject>& accessor,
               const std::string& path, const flexbuffers::Reference& value) {
              if (!value.IsString()) {
                printf("%s must be a string\n", path.c_str());
                return false;
              }
              storage_object->group_value2 = value.As<std::string>();
              return true;
            },
            [](const TestObject& storage_object,
               const OptionAccessor<TestObject>& accessor,
               const std::string& path, flexbuffers::Builder* builder) {
              builder->String(accessor.name().c_str(),
                              storage_object.group_value2);
            }),
        flat_accessors_({value1_accessor_, value2_accessor_}),
        nested_accessors_({
            OptionAccessor<NestedTestObject>(
                "value1",
                [](NestedTestObject* storage_object,
                   const OptionAccessor<NestedTestObject>& accessor,
                   const std::string& path,
                   const flexbuffers::Reference& value) {
                  if (!value.IsString()) {
                    printf("%s must be a string\n", path.c_str());
                    return false;
                  }
                  storage_object->value1 = value.As<std::string>();
                  return true;
                },
                [](const NestedTestObject& storage_object,
                   const OptionAccessor<NestedTestObject>& accessor,
                   const std::string& path, flexbuffers::Builder* builder) {
                  builder->String(accessor.name().c_str(),
                                  storage_object.value1);
                }),
        }),
        all_accessors_({
            value1_accessor_,
            value2_accessor_,
            OptionAccessor<TestObject>("group",
                                       std::vector<OptionAccessor<TestObject>>({
                                           group_value1_accessor_,
                                           group_value2_accessor_,
                                       })),
            OptionAccessor<TestObject>(
                "nested",
                [this](TestObject* storage_object,
                       const OptionAccessor<TestObject>& accessor,
                       const std::string& path,
                       const flexbuffers::Reference& value) {
                  return OptionAccessor<NestedTestObject>::SetOptions(
                      &storage_object->nested, nested_accessors_,
                      value.AsMap());
                },
                [this](const TestObject& storage_object,
                       const OptionAccessor<TestObject>& accessor,
                       const std::string& path, flexbuffers::Builder* builder) {
                  OptionAccessor<NestedTestObject>::GetOptions(
                      builder, storage_object.nested, nested_accessors_,
                      &accessor.name(), &path);
                }),
        }) {}

 protected:
  OptionAccessor<TestObject> value1_accessor_;
  OptionAccessor<TestObject> value2_accessor_;
  OptionAccessor<TestObject> group_value1_accessor_;
  OptionAccessor<TestObject> group_value2_accessor_;
  std::vector<OptionAccessor<TestObject>> flat_accessors_;
  std::vector<OptionAccessor<NestedTestObject>> nested_accessors_;
  std::vector<OptionAccessor<TestObject>> all_accessors_;
};

TEST_F(OptionAccessorTest, SetOne) {
  TestObject storage;
  FlexBufferParser parser;
  ASSERT_TRUE(parser.Parse("{ \"value1\": \"hello\" }"));
  EXPECT_TRUE(value1_accessor_.Set(&storage, parser.GetRootMap()["value1"]));
  EXPECT_EQ(storage.value1, "hello");
}

TEST_F(OptionAccessorTest, SetOneFail) {
  TestObject storage;
  storage.value1 = "hello";
  FlexBufferParser parser;
  // Set should fail due to the wrong data type.
  ASSERT_TRUE(parser.Parse("{ \"value1\": [ \"goodbye\" ] }"));
  EXPECT_FALSE(value1_accessor_.Set(&storage, parser.GetRootMap()["value1"]));
  EXPECT_EQ(storage.value1, "hello");
}

TEST_F(OptionAccessorTest, GetOne) {
  TestObject storage;
  storage.value1 = "hello";
  flexbuffers::Builder builder;
  builder.Map(
      [this, &storage, &builder] { value1_accessor_.Get(storage, &builder); });
  builder.Finish();
  EXPECT_EQ(flexbuffers::GetRoot(builder.GetBuffer())
                .AsMap()["value1"]
                .As<std::string>(),
            "hello");
}

TEST_F(OptionAccessorTest, SetMultiple) {
  TestObject storage;
  FlexBufferParser parser;
  ASSERT_TRUE(parser.Parse("{ \"value1\": \"hello\", \"value2\": 42 }"));
  EXPECT_TRUE(OptionAccessor<TestObject>::SetOptions(&storage, flat_accessors_,
                                                     parser.GetRootMap()));
  EXPECT_EQ(storage.value1, "hello");
  EXPECT_EQ(storage.value2, 42);
}

TEST_F(OptionAccessorTest, SetMultipleFail) {
  TestObject storage;
  storage.value1 = "hello";
  storage.value2 = 10;
  FlexBufferParser parser;
  ASSERT_TRUE(parser.Parse("{ \"value1\": \"hello\", \"value2\": \"bob\" }"));
  EXPECT_FALSE(OptionAccessor<TestObject>::SetOptions(&storage, flat_accessors_,
                                                      parser.GetRootMap()));
  EXPECT_EQ(storage.value1, "hello");
  EXPECT_EQ(storage.value2, 10);
}

TEST_F(OptionAccessorTest, GetMultiple) {
  TestObject storage;
  storage.value1 = "hello";
  storage.value2 = 42;
  flexbuffers::Builder builder;
  OptionAccessor<TestObject>::GetOptions(&builder, storage, flat_accessors_);
  builder.Finish();
  auto root = flexbuffers::GetRoot(builder.GetBuffer()).AsMap();
  EXPECT_EQ(root["value1"].As<std::string>(), "hello");
  EXPECT_EQ(root["value2"].AsInt32(), 42);
}

TEST_F(OptionAccessorTest, SetNested) {
  TestObject storage;
  FlexBufferParser parser;
  ASSERT_TRUE(
      parser.Parse("{ "
                   "  \"value1\": \"hello\", "
                   "  \"value2\": 42, "
                   "  \"group\": { "
                   "    \"value1\": \"goodbye\", "
                   "    \"value2\": \"gill\" "
                   "  }, "
                   "  \"nested\": { "
                   "    \"value1\": \"ian\" "
                   "  } "
                   "}"));
  EXPECT_TRUE(OptionAccessor<TestObject>::SetOptions(&storage, all_accessors_,
                                                     parser.GetRootMap()));
  EXPECT_EQ(storage.value1, "hello");
  EXPECT_EQ(storage.value2, 42);
  EXPECT_EQ(storage.group_value1, "goodbye");
  EXPECT_EQ(storage.group_value2, "gill");
  EXPECT_EQ(storage.nested.value1, "ian");
}

TEST_F(OptionAccessorTest, SetNestedFail) {
  TestObject storage;
  storage.value1 = "hello";
  storage.value2 = 42;
  storage.group_value1 = "goodbye";
  storage.group_value2 = "nance";
  storage.nested.value1 = "ian";
  FlexBufferParser parser;
  ASSERT_TRUE(
      parser.Parse("{ "
                   "  \"value1\": \"salut\", "
                   "  \"value2\": [ 10 ], "
                   "  \"group\": \"do not set\" "
                   "}"));
  EXPECT_FALSE(OptionAccessor<TestObject>::SetOptions(&storage, all_accessors_,
                                                      parser.GetRootMap()));
  EXPECT_EQ(storage.value1, "salut");
  EXPECT_EQ(storage.value2, 42);
  EXPECT_EQ(storage.group_value1, "goodbye");
  EXPECT_EQ(storage.group_value2, "nance");
  EXPECT_EQ(storage.nested.value1, "ian");
}

TEST_F(OptionAccessorTest, GetNested) {
  TestObject storage;
  storage.value1 = "hello";
  storage.value2 = 42;
  storage.group_value1 = "goodbye";
  storage.group_value2 = "gill";
  storage.nested.value1 = "ian";
  flexbuffers::Builder builder;
  OptionAccessor<TestObject>::GetOptions(&builder, storage, all_accessors_);
  builder.Finish();
  auto root = flexbuffers::GetRoot(builder.GetBuffer()).AsMap();
  EXPECT_EQ(root["value1"].As<std::string>(), "hello");
  EXPECT_EQ(root["value2"].AsInt32(), 42);
  EXPECT_EQ(root["group"].AsMap()["value1"].As<std::string>(), "goodbye");
  EXPECT_EQ(root["group"].AsMap()["value2"].As<std::string>(), "gill");
  EXPECT_EQ(root["nested"].AsMap()["value1"].As<std::string>(), "ian");
}

TEST_F(OptionAccessorTest, SetFromJson) {
  TestObject storage;
  EXPECT_TRUE(OptionAccessor<TestObject>::SetOptionsFromJson(
      &storage, all_accessors_,
      "{ "
      "  \"value1\": \"hello\", "
      "  \"value2\": 42, "
      "  \"group\": { "
      "    \"value1\": \"goodbye\", "
      "    \"value2\": \"gill\" "
      "  }, "
      "  \"nested\": { "
      "    \"value1\": \"ian\" "
      "  } "
      "}"));
  EXPECT_EQ(storage.value1, "hello");
  EXPECT_EQ(storage.value2, 42);
  EXPECT_EQ(storage.group_value1, "goodbye");
  EXPECT_EQ(storage.group_value2, "gill");
  EXPECT_EQ(storage.nested.value1, "ian");
}

TEST_F(OptionAccessorTest, GetAsJson) {
  TestObject storage;
  storage.value1 = "hello";
  storage.value2 = 42;
  storage.group_value1 = "goodbye";
  storage.group_value2 = "gill";
  storage.nested.value1 = "ian";
  EXPECT_EQ(
      OptionAccessor<TestObject>::GetOptionsAsJson(storage, all_accessors_),
      "{ group: { value1: \"goodbye\", value2: \"gill\" }, "
      "nested: { value1: \"ian\" }, value1: \"hello\", value2: 42 }");
}

TEST(FlexbuffersStringListToStringTest, FlexbuffersStringListToString) {
  FlexBufferParser parser;
  ASSERT_TRUE(
      parser.Parse("{ "
                   "  \"item1\": [ "
                   "    \"value\", "
                   "    \"in a\", "
                   "    \"list\" "
                   "  ], "
                   "  \"item2\": \"value in a string\" "
                   "}"));
  EXPECT_EQ(FlexbuffersStringListToString(parser.GetRootMap()["item1"]),
            "value\nin a\nlist\n");
  EXPECT_EQ(FlexbuffersStringListToString(parser.GetRootMap()["item2"]),
            "value in a string");
}

}  // namespace core
}  // namespace falken
