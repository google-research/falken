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

#include "src/core/child_resource_map.h"

#include "gmock/gmock.h"
#include "gtest/gtest.h"

namespace falken {

TEST(ChildResourceMapTest, AddLookupDestroy) {
  const char* kId = "id";
  const char* kExtra = "extra";
  ChildResourceMap<int> map;
  std::shared_ptr<int> strongref(new int(42));
  std::weak_ptr<int> weakref;
  map.AddChild(strongref, weakref, kId, kExtra);
  ASSERT_FALSE(map.LookupChild(kId));
  ASSERT_TRUE(map.LookupChild(kId, kExtra));
  strongref.reset();
  ASSERT_FALSE(map.LookupChild(kId, kExtra));
}

TEST(ChildResourceMapTest, CollectGarbage) {
  const char* kId = "id";
  ChildResourceMap<int> map;
  std::shared_ptr<int> strongref(new int(42));
  std::weak_ptr<int> weakref;
  map.AddChild(strongref, weakref, kId);
  ASSERT_EQ(map.GetChildren().size(), 1);
  strongref.reset();
  ASSERT_EQ(map.GetChildren().size(), 0);
}

}  // namespace falken
