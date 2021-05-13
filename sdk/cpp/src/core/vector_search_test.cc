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

#include "src/core/vector_search.h"

#include <string.h>

#include <vector>

#include "gmock/gmock.h"
#include "gtest/gtest.h"

namespace falken {

struct Item {
  const char* id;
  int index;

  static int CompareIndex(const int& index, const Item& item) {  // NOLINT
    return index - item.index;
  }

  static const char* GetName(const Item& item) {
    return item.id;
  }

  template<typename T>
  static const char* PointerGetName(const T& item) {
    return item->id;
  }
};

class VectorSearchTest : public testing::Test {
 public:
  VectorSearchTest() : sorted_items_(
      {{"brilliant", 4}, {"no", 10}, {"very strong", 42}, {"yes", 81}}) {
    for (auto& item : sorted_items_) {
      sorted_items_pointers_.push_back(&item);
    }
  }

  std::vector<Item> sorted_items_;
  std::vector<Item*> sorted_items_pointers_;
};

TEST_F(VectorSearchTest, SearchSortedVectorByKey) {
  auto it = SearchSortedVectorByKey<int, Item, Item::CompareIndex>(
      sorted_items_, 10);
  EXPECT_EQ(&(*it), &sorted_items_[1]);

  it = SearchSortedVectorByKey<int, Item, Item::CompareIndex>(
      sorted_items_, 43);
  EXPECT_EQ(it, sorted_items_.end());
}

TEST_F(VectorSearchTest, SearchSortedVectorByName) {
  auto it = SearchSortedVectorByName<Item, Item::GetName>(sorted_items_,
                                                          "very strong");
  EXPECT_EQ(&(*it), &sorted_items_[2]);

  it = SearchSortedVectorByName<Item, Item::GetName>(sorted_items_,
                                                     "no no yes");
  EXPECT_EQ(it, sorted_items_.end());
}

TEST_F(VectorSearchTest, SearchSortedVectorByNameWithPointers) {
  auto it = SearchSortedVectorByName<Item*, Item::PointerGetName<Item*>>(
      sorted_items_pointers_, "brilliant");
  EXPECT_EQ(*it, sorted_items_pointers_[0]);

  it = SearchSortedVectorByName<Item*, Item::PointerGetName<Item*>>(
      sorted_items_pointers_, "yes no yes");
  EXPECT_EQ(it, sorted_items_pointers_.end());
}

}  // namespace falken
