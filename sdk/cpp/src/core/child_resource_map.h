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

#ifndef FALKEN_SDK_CORE_CHILD_RESOURCE_MAP_H_
#define FALKEN_SDK_CORE_CHILD_RESOURCE_MAP_H_

#include <map>
#include <memory>
#include <string>
#include <vector>

#include "src/core/assert.h"

namespace falken {

// Utility class which manages weak_ptr's to children created by Falken's
// resource classes like Service, Brain, and Session.
template <typename T>
class ChildResourceMap {
 public:
  // Adds an instance of a child resource to the map and sets up the child's
  // own weak_this pointer.
  void AddChild(const std::shared_ptr<T>& child,
                std::weak_ptr<T>& child_weak_this, const char* id,
                const char* extra = nullptr) {
    GarbageCollectAndGetChildren();
    std::string key = ToKey(id, extra);
    FALKEN_ASSERT(created_.find(key) == created_.end());
    created_[key] = std::weak_ptr<T>(child);
    child_weak_this = child;
  }

  // Retrieves a child resource from the map, if it exists.
  std::shared_ptr<T> LookupChild(const char* id,
                                 const char* extra = nullptr) const {
    auto created = created_.find(ToKey(id, extra));
    if (created != created_.end()) {
      return created->second.lock();
    }
    return std::shared_ptr<T>();
  }

  // Returns a linear list of children contained in the map. Will not include
  // any children which have been deallocated.
  std::vector<std::shared_ptr<T>> GetChildren() {
    std::vector<std::shared_ptr<T>> children;
    GarbageCollectAndGetChildren(&children);
    return children;
  }

 private:
  std::string ToKey(const char* id, const char* extra) const {
    std::string key(id);
    if (extra) {
      key += std::string("/") + extra;
    }
    return key;
  }

  void GarbageCollectAndGetChildren(
      std::vector<std::shared_ptr<T>>* children = nullptr) {
    auto item = created_.begin();
    while (item != created_.end()) {
      auto child = item->second.lock();
      if (child) {
        if (children) children->push_back(std::move(child));
        ++item;
      } else {
        item = created_.erase(item);
      }
    }
  }

  std::map<std::string, std::weak_ptr<T>> created_;
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_CHILD_RESOURCE_MAP_H_
