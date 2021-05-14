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

#ifndef FALKEN_SDK_CORE_VECTOR_SEARCH_H_
#define FALKEN_SDK_CORE_VECTOR_SEARCH_H_

#include <string.h>

#include <algorithm>
#include <cstdint>
#include <functional>
#include <vector>

namespace falken {

// Find an item in a sorted vector.
//
// Compare is the function int(const KeyType& key, const ItemType& item)
// that returns less than 0 if key is less than item, 0 if the they're
// equal and greater than 1 if key is greater than item.
// ItemType is the type of element in the vector, Allocator is the
// allocator used by the vector type and KeyType is the type of the key to
// search for.
//
// For example:
// struct Item {
//   std::string id;
//
//   static int CompareId(int id, const Item& item) {
//     return id - item.id;
//   }
// };
//
// std::vector<Item> sorted_items({{4}, {20}, {42}});
// auto it = SearchSortedVectorByKey<int, Item, Item::CompareName>(items, 20);
template <typename KeyType, typename ItemType,
          int (*Compare)(const KeyType&, const ItemType&),
          typename Allocator = std::allocator<ItemType>>
typename std::vector<ItemType, Allocator>::const_iterator
SearchSortedVectorByKey(const std::vector<ItemType, Allocator>& items,
                        const KeyType& key) {
  void* found = static_cast<ItemType*>(
      std::bsearch(&key, items.data(), items.size(), sizeof(ItemType),
                   [](const void* key, const void* item) {
                     return Compare(*static_cast<const KeyType*>(key),
                                    *static_cast<const ItemType*>(item));
                   }));
  if (!found) return items.end();
  // While vector<T>::iterator can be implemented as T* this does avoids the
  // assumption by calculating the offset by index.
  return items.begin() + ((reinterpret_cast<intptr_t>(found) -
                           reinterpret_cast<intptr_t>(items.data())) /
                          sizeof(ItemType));
}

// Used to compare items using the result of GetName() with a const char* key.
template <typename ItemType, const char* GetName(const ItemType&)>
struct ConstCharKey {
  const char* name;

  static int CompareName(const ConstCharKey& key, const ItemType& item) {
    return strcmp(key.name, GetName(item));
  }
};

// Find an item by name in a sorted vector where GetName is a function that
// returns a const char* name of the specified item.
template <typename ItemType, const char* GetName(const ItemType&),
          typename Allocator = std::allocator<ItemType>>
typename std::vector<ItemType, Allocator>::const_iterator
SearchSortedVectorByName(const std::vector<ItemType, Allocator>& items,
                         const char* name) {
  // Wrap the key in a struct so that it's possible to use an inline comparison
  // function.
  ConstCharKey<ItemType, GetName> key = {name};
  return SearchSortedVectorByKey<
      ConstCharKey<ItemType, GetName>, ItemType,
      ConstCharKey<ItemType, GetName>::CompareName, Allocator>(items, key);
}

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_VECTOR_SEARCH_H_
