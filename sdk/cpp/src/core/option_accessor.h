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

#ifndef FALKEN_SDK_CORE_OPTION_ACCESSOR_H_
#define FALKEN_SDK_CORE_OPTION_ACCESSOR_H_

#include <functional>
#include <string>
#include <vector>

#include "flatbuffers/flexbuffers.h"
#include "flatbuffers/idl.h"

namespace falken {
namespace core {

// Build a string from a flexbuffers reference to a string or string list.
std::string FlexbuffersStringListToString(const flexbuffers::Reference& value);

// Configuration option value accessor.
template <typename T>
class OptionAccessor {
  // Allow some OptionAccessorTest test cases to access private members of this
  // class.
  friend class OptionAccessorTest_SetOne_Test;
  friend class OptionAccessorTest_SetOneFail_Test;
  friend class OptionAccessorTest_GetOne_Test;

 public:
  // Set a configuration option on T from a reference to the option value.
  typedef std::function<bool(
      T* storage_object, const OptionAccessor<T>& accessor,
      const std::string& path, const flexbuffers::Reference& builder)>
      SetFunc;
  // Get a configuration from T and store in the provided flexbuffer.
  typedef std::function<void(
      const T& storage_object, const OptionAccessor<T>& accessor,
      const std::string& path, flexbuffers::Builder* builder)>
      GetFunc;

  // Accessor that can set or get attributes of T.
  OptionAccessor(const char* name, SetFunc set, GetFunc get)
      : name_(name), set_(set), get_(get) {}

  // Accessor that is a group for other accessors.
  OptionAccessor(const char* name,
                 const std::vector<OptionAccessor<T>>& children)
      : name_(name), set_(nullptr), get_(nullptr), children_(children) {}

  OptionAccessor(const char* name, SetFunc set, GetFunc get,
                 const std::vector<OptionAccessor<T>>& children)
      : name_(name), set_(set), get_(get), children_(children) {}

  // Get the name of this option.
  const std::string& name() const { return name_; }

  // Set values on storage_object from the provided options.
  static bool SetOptions(T* storage_object,
                         const std::vector<OptionAccessor<T>>& option_accessors,
                         const flexbuffers::Map& map_reference) {
    bool successful = true;
    for (const auto& accessor : option_accessors) {
      auto value = map_reference[accessor.name_.c_str()];
      if (!value.IsNull() && !accessor.Set(storage_object, value)) {
        successful = false;
      }
    }
    return successful;
  }

  // Get options as a flexbuffer from the provided storage object.
  // The returned builder is not finished.
  static void GetOptions(flexbuffers::Builder* builder, const T& storage_object,
                         const std::vector<OptionAccessor<T>>& option_accessors,
                         const std::string* map_item_name = nullptr,
                         const std::string* parent_path = nullptr) {
    if (map_item_name && parent_path) {
      builder->Map(map_item_name->c_str(), [&storage_object, option_accessors,
                                            builder, parent_path]() {
        GetOptions(storage_object, option_accessors, builder, parent_path);
      });
    } else {
      builder->Map([&storage_object, option_accessors, builder]() {
        GetOptions(storage_object, option_accessors, builder);
      });
    }
  }

  // Set values on storage_object from the options in the specified JSON.
  static bool SetOptionsFromJson(
      T* storage_object, const std::vector<OptionAccessor<T>>& option_accessors,
      const char* json_config) {
    flexbuffers::Builder builder;
    {
      flatbuffers::Parser parser;
      if (!parser.ParseFlexBuffer(json_config, nullptr, &builder)) {
        return false;
      }
    }
    return SetOptions(storage_object, option_accessors,
                      flexbuffers::GetRoot(builder.GetBuffer()).AsMap());
  }

  // Get options from storage_object as JSON.
  static std::string GetOptionsAsJson(
      const T& storage_object,
      const std::vector<OptionAccessor<T>>& option_accessors) {
    flexbuffers::Builder builder;
    GetOptions(&builder, storage_object, option_accessors);
    builder.Finish();
    return flexbuffers::GetRoot(builder.GetBuffer()).ToString();
  }

 private:
  // Call the set method.
  bool Set(T* storage_object, const flexbuffers::Reference& value,
           const std::string* parent_path = nullptr) const {
    std::string path = CreatePath(parent_path);
    return set_ ? set_(storage_object, *this, path, value)
                : SetChildren(storage_object, path, value);
  }

  // Call the get method.
  void Get(const T& storage_object, flexbuffers::Builder* builder,
           const std::string* parent_path = nullptr) const {
    std::string path = CreatePath(parent_path);
    return get_ ? get_(storage_object, *this, path, builder)
                : GetChildren(storage_object, path, builder);
  }

  // Sets the values of children of this option.
  bool SetChildren(T* storage_object, const std::string& path,
                   const flexbuffers::Reference& value) const {
    bool successful = true;
    if (value.IsMap()) {
      auto value_map = value.AsMap();
      for (const auto& accessor : children_) {
        const auto child_value = value_map[accessor.name_];
        if (!child_value.IsNull() &&
            !accessor.Set(storage_object, child_value, &path)) {
          successful = false;
        }
      }
    }
    return successful;
  }

  // Gets the values of children of this option.
  void GetChildren(const T& storage_object, const std::string& path,
                   flexbuffers::Builder* builder) const {
    builder->Map(name_.c_str(), [this, &storage_object, &path, builder]() {
      GetOptions(storage_object, children_, builder, &path);
    });
  }

  // Generate the a path to this option in the form "parent_path.name", if
  // parent is nullptr the name of this option accessor is returned.
  std::string CreatePath(const std::string* parent_path) const {
    return parent_path ? *parent_path + "." + name_ : name_;
  }

  // Get the specified options given a builder that references a Map.
  static void GetOptions(const T& storage_object,
                         const std::vector<OptionAccessor<T>>& option_accessors,
                         flexbuffers::Builder* builder,
                         const std::string* parent_path = nullptr) {
    for (const auto& accessor : option_accessors) {
      accessor.Get(storage_object, builder, parent_path);
    }
  }

 private:
  // Name of the option.
  std::string name_;
  // Accessors.
  SetFunc set_;
  GetFunc get_;
  // If this option is a group, this provides an array of accessors for the
  // group.
  std::vector<OptionAccessor<T>> children_;
};

}  // namespace core
}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_OPTION_ACCESSOR_H_
