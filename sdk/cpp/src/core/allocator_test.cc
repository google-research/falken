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

#include "falken/allocator.h"

#if _MSC_VER
#include <malloc.h>
#endif  // _MSC_VER
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#include <algorithm>
#include <array>
#include <memory>

#include "gtest/gtest.h"

namespace falken {

class AllocatorTest : public testing::Test {
 public:
  void SetUp() override {
    original_callbacks_ =
        std::make_unique<AllocatorCallbacks>(GetAllocatorCallbacks());
    allocated_bytes_ = AllocatorCallbacks::allocated_bytes();
  }

  void TearDown() override {
    AllocatorCallbacks::Set(*original_callbacks_);
    EXPECT_EQ(allocated_bytes_, AllocatorCallbacks::allocated_bytes());
  }

  // Construct allocator callbacks that use this object.
  AllocatorCallbacks CustomAllocatorCallbacks() {
    return AllocatorCallbacks(Allocate, Free, this);
  }

  // Get the number of bytes allocated since the start of the test.
  size_t allocated_bytes() {
    return AllocatorCallbacks::allocated_bytes() - allocated_bytes_;
  }

  // Get the current allocator function.
  static AllocatorCallbacks::AllocateFunc GetAllocatorCallbacksAllocateFunc(
      const AllocatorCallbacks& callbacks) {
    return callbacks.allocate_;
  }

  // Get the current free function.
  static AllocatorCallbacks::FreeFunc GetAllocatorCallbacksFreeFunc(
      const AllocatorCallbacks& callbacks) {
    return callbacks.free_;
  }

  // Get the context.
  static void* GetAllocatorCallbacksContext(
      const AllocatorCallbacks& callbacks) {
    return callbacks.context_;
  }

  // Get the current set allocator callbacks.
  static AllocatorCallbacks& GetAllocatorCallbacks() {
    return AllocatorCallbacks::Get();
  }

  // Custom allocation method that tracks allocated memory.
  static void* Allocate(size_t size, void* context) {
    auto& this_ = *reinterpret_cast<AllocatorTest*>(context);
    void* ptr = malloc(size);
    this_.MarkAsAllocated(reinterpret_cast<intptr_t>(ptr), size);
    return ptr;
  }

  // Custom free method that tracks allocated memory.
  static void Free(void* ptr, void* context) {
    if (ptr) {
      auto& this_ = *reinterpret_cast<AllocatorTest*>(context);
      this_.MarkAsDeallocated(reinterpret_cast<intptr_t>(ptr));
      free(ptr);
    }
  }

  void MarkAsAllocated(intptr_t ptr, size_t size) {
    auto it = std::find_if(
        allocated_control_blocks_.begin(), allocated_control_blocks_.end(),
        [](const AllocationControlBlock& block) { return !block.used; });
    if (it != allocated_control_blocks_.end()) {
      it->used = true;
      it->ptr = ptr;
      it->size = size;
    }
  }

  void MarkAsDeallocated(intptr_t ptr) {
    auto it = std::find_if(allocated_control_blocks_.begin(),
                           allocated_control_blocks_.end(),
                           [ptr](const AllocationControlBlock& block) {
                             return block.used == true && block.ptr == ptr;
                           });
    if (it != allocated_control_blocks_.end()) {
      it->used = false;
    }
  }

  bool IsAllocatedAndSizeMatches(intptr_t ptr, size_t size) {
    auto it = std::find_if(allocated_control_blocks_.begin(),
                           allocated_control_blocks_.end(),
                           [ptr](const AllocationControlBlock& block) {
                             return block.used && block.ptr == ptr;
                           });
    if (it == allocated_control_blocks_.end()) {
      return false;
    }
    return it->size == size;
  }

  struct AllocationControlBlock {
    bool used = false;
    intptr_t ptr;
    size_t size;
  };

  // Memory managed by Allocate() / Free().
  std::array<AllocationControlBlock, 10> allocated_control_blocks_;

  // Allocator callbacks before the test starts.
  std::unique_ptr<AllocatorCallbacks> original_callbacks_;
  // Number of bytes allocated at the start of the test.
  size_t allocated_bytes_;
};

TEST_F(AllocatorTest, DefaultCallbacksAreSet) {
  auto& callbacks = GetAllocatorCallbacks();
  EXPECT_NE(nullptr, GetAllocatorCallbacksAllocateFunc(callbacks));
  EXPECT_NE(nullptr, GetAllocatorCallbacksFreeFunc(callbacks));
  EXPECT_EQ(nullptr, GetAllocatorCallbacksContext(callbacks));
}

TEST_F(AllocatorTest, ConstructCallbacks) {
  AllocatorCallbacks callbacks = CustomAllocatorCallbacks();
  EXPECT_EQ(
      reinterpret_cast<intptr_t>(AllocatorTest::Allocate),
      reinterpret_cast<intptr_t>(GetAllocatorCallbacksAllocateFunc(callbacks)));
  EXPECT_EQ(
      reinterpret_cast<intptr_t>(AllocatorTest::Free),
      reinterpret_cast<intptr_t>(GetAllocatorCallbacksFreeFunc(callbacks)));
  EXPECT_EQ(this, GetAllocatorCallbacksContext(callbacks));
}

TEST_F(AllocatorTest, SetCallbacks) {
  AllocatorCallbacks new_callbacks = CustomAllocatorCallbacks();
  auto default_callbacks = GetAllocatorCallbacks();
  auto previous_callbacks = AllocatorCallbacks::Set(new_callbacks);
  // Make sure the method returns the previous callbacks.
  EXPECT_EQ(GetAllocatorCallbacksAllocateFunc(default_callbacks),
            GetAllocatorCallbacksAllocateFunc(previous_callbacks));
  EXPECT_EQ(GetAllocatorCallbacksFreeFunc(default_callbacks),
            GetAllocatorCallbacksFreeFunc(previous_callbacks));
  EXPECT_EQ(GetAllocatorCallbacksContext(default_callbacks),
            GetAllocatorCallbacksContext(previous_callbacks));
  // Make sure the new callbacks have been set.
  auto& new_set_callbacks = GetAllocatorCallbacks();
  EXPECT_EQ(GetAllocatorCallbacksAllocateFunc(new_set_callbacks),
            GetAllocatorCallbacksAllocateFunc(new_callbacks));
  EXPECT_EQ(GetAllocatorCallbacksFreeFunc(new_set_callbacks),
            GetAllocatorCallbacksFreeFunc(new_callbacks));
  EXPECT_EQ(GetAllocatorCallbacksContext(new_set_callbacks),
            GetAllocatorCallbacksContext(new_callbacks));
}

TEST_F(AllocatorTest, CustomCallbacks) {
  AllocatorCallbacks::Set(CustomAllocatorCallbacks());
  auto& current_callbacks = GetAllocatorCallbacks();
  void* block10 = current_callbacks.Allocate(10);
  memset(block10, 0x10, 10);
  EXPECT_TRUE(
      IsAllocatedAndSizeMatches(reinterpret_cast<intptr_t>(block10), 10));
  void* block32 = current_callbacks.Allocate(32);
  memset(block32, 0x32, 32);
  EXPECT_TRUE(
      IsAllocatedAndSizeMatches(reinterpret_cast<intptr_t>(block10), 10));
  EXPECT_TRUE(
      IsAllocatedAndSizeMatches(reinterpret_cast<intptr_t>(block32), 32));
  current_callbacks.Free(block10);
  EXPECT_FALSE(
      IsAllocatedAndSizeMatches(reinterpret_cast<intptr_t>(block10), 10));
  EXPECT_TRUE(
      IsAllocatedAndSizeMatches(reinterpret_cast<intptr_t>(block32), 32));
  current_callbacks.Free(block32);
  EXPECT_FALSE(
      IsAllocatedAndSizeMatches(reinterpret_cast<intptr_t>(block10), 10));
  EXPECT_FALSE(
      IsAllocatedAndSizeMatches(reinterpret_cast<intptr_t>(block32), 32));
}

TEST_F(AllocatorTest, GlobalAllocateAligned) {
  const size_t kAllocSize = 10;
  for (int log2align = 0; log2align < 10 /* up to 1kb */; ++log2align) {
    size_t alignment = 1 << log2align;
    void* ptr = AllocatorCallbacks::GlobalAllocate(kAllocSize, alignment);
    memset(ptr, 0xde, kAllocSize);
    EXPECT_EQ(allocated_bytes(), kAllocSize);
    intptr_t ptr_int = reinterpret_cast<intptr_t>(ptr);
    // Make sure the allocated block is aligned to the requested alignment.
    EXPECT_EQ(ptr_int & (alignment - 1), 0);
    AllocatorCallbacks::GlobalFree(ptr);
    EXPECT_EQ(allocated_bytes(), 0);
  }
}

TEST_F(AllocatorTest, AllocatorAllocFree) {
  const size_t kNumberOfInts = 5;
  const size_t kAllocationSize = kNumberOfInts * sizeof(int);
  Allocator<int> int_allocator;
  int* ints = int_allocator.allocate(kNumberOfInts);
  memset(ints, 0x32, kAllocationSize);
  EXPECT_EQ(allocated_bytes(), kAllocationSize);
  int_allocator.deallocate(ints, kNumberOfInts);
}

TEST_F(AllocatorTest, VectorWithAllocator) {
  EXPECT_EQ(allocated_bytes(), 0);
  {
    std::vector<int, Allocator<int>> ints;
    ints.push_back(0);
    ints.push_back(0);
    ints.push_back(4);
    ints.push_back(2);
    EXPECT_NE(allocated_bytes(), 0);
  }
  EXPECT_EQ(allocated_bytes(), 0);
}

TEST_F(AllocatorTest, AllocatorTraits) {
  EXPECT_EQ(sizeof(Allocator<int>::size_type), sizeof(size_t));
  EXPECT_EQ(sizeof(Allocator<int>::pointer), sizeof(int*));
  EXPECT_EQ(sizeof(Allocator<int>::const_pointer), sizeof(int*));
}

TEST_F(AllocatorTest, AllocatorRebindAndCopyConstruct) {
  struct FooBar {
    int external;
    int secret;
  };
  Allocator<FooBar> foo_bar_allocator;
  FooBar* foo_bar = foo_bar_allocator.allocate(1);
  EXPECT_EQ(allocated_bytes(), sizeof(*foo_bar));
  foo_bar->external = 24;
  foo_bar->secret = 42;
  foo_bar_allocator.deallocate(foo_bar, 1);
  EXPECT_EQ(allocated_bytes(), 0);

  decltype(foo_bar_allocator)::rebind<int>::other int_allocator;
  int* a_int = int_allocator.allocate(1);
  *a_int = 5;
  EXPECT_EQ(allocated_bytes(), sizeof(*a_int));
  int_allocator.deallocate(a_int, 1);
  EXPECT_EQ(allocated_bytes(), 0);

  Allocator<float> float_allocator(int_allocator);
  float* a_float = float_allocator.allocate(1);
  *a_float = 3.14f;
  EXPECT_EQ(allocated_bytes(), sizeof(*a_float));
  float_allocator.deallocate(a_float, 1);
  EXPECT_EQ(allocated_bytes(), 0);
}

}  // namespace falken
