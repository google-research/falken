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

#include <assert.h>
#if _MSC_VER
#include <malloc.h>
#endif  // _MSC_VER
#include <stdlib.h>

#include <cstdint>
#include <cstdlib>
#include <iostream>

#include "absl/base/const_init.h"
#include "absl/synchronization/mutex.h"

// FALKEN_ALLOCATOR_DISABLED disables the allocator
// (see GlobalAllocate/GlobalFree) which is used all objects that
// are passed from the Falken SDK to the application for deallocation.
// This should really only be disabled to debug whether the custom allocator
// is causing an issue.

// FALKEN_GLOBAL_NEW_DELETE_ENABLED enables global new/delete overrides for
// all allocations inside the Falken SDK.
#if !defined(FALKEN_GLOBAL_NEW_DELETE_ENABLED)
// Global allocators can not be used in dynamic libraries on macOS and Linux
// variants as STL classes will call a mix of library and application defined
// new / delete methods.
#if !defined(_MSC_VER)
#define FALKEN_GLOBAL_NEW_DELETE_ENABLED 0
#elif defined(FALKEN_ALLOCATOR_DISABLED)
#define FALKEN_GLOBAL_NEW_DELETE_ENABLED 0
#else
#define FALKEN_GLOBAL_NEW_DELETE_ENABLED 1
#endif  // !defined(_MSC_VER)
#endif  // !defined(FALKEN_GLOBAL_NEW_DELETE_ENABLED)

// Most platforms define the minimum memory allocation alignment as the size
// of the largest integral type supported by the architecture. For 64-bit
// platforms this is int64_t.
#define FALKEN_DEFAULT_ALIGNMENT (sizeof(int64_t))

namespace {

// Used to align allocated blocks and free memory with the correct deallocator.
struct AllocateData {
  // Original address of the allocation.
  char* allocated_address;
  // Total size of data associated with this block of memory including this
  // data structure and any padding required for alignment.
  size_t allocated_size;
  // Size of memory that is usable in this block.
  size_t requested_size;
  // Allocator for this block.
  falken::AllocatorCallbacks allocator;
};

// Guards use of global allocator callbacks returned by
// AllocatorCallbacks::Get().
static absl::Mutex global_falken_allocator_lock(absl::kConstInit);

// Round size up to the nearest alignment bytes.
static size_t RoundUpToAlignment(size_t size, size_t alignment) {
  if (!alignment) return size;
  return ((size + alignment - 1) / alignment) * alignment;
}

}  // namespace

namespace falken {

// Total number of memory allocated by AllocatorCallbacks::Alloc().
size_t AllocatorCallbacks::allocated_bytes_ = 0;

AllocatorCallbacks::AllocatorCallbacks(AllocateFunc allocate, FreeFunc free,
                                       void* context)
    : allocate_(allocate), free_(free), context_(context) {
  assert(allocate);
  assert(free);
}

void* AllocatorCallbacks::Allocate(size_t size) {
  return allocate_(size, context_);
}

void AllocatorCallbacks::Free(void* ptr) { free_(ptr, context_); }

AllocatorCallbacks AllocatorCallbacks::Set(
    const AllocatorCallbacks& callbacks) {
  absl::MutexLock lock(&global_falken_allocator_lock);
  auto& current = Get();
  AllocatorCallbacks previous(current);
  current = callbacks;
  return previous;
}

AllocatorCallbacks& AllocatorCallbacks::Get() {
  static AllocatorCallbacks current_callbacks(
      [](size_t size, void* /*context*/) { return malloc(size); },
      [](void* ptr, void* /*context*/) { free(ptr); }, nullptr);
  return current_callbacks;
}

size_t AllocatorCallbacks::allocated_bytes() { return allocated_bytes_; }

void* AllocatorCallbacks::GlobalAllocate(size_t size, size_t alignment) {
  alignment = alignment ? alignment : FALKEN_DEFAULT_ALIGNMENT;
#if !defined(FALKEN_ALLOCATOR_DISABLED)
  absl::MutexLock lock(&global_falken_allocator_lock);
  // Calculate the memory to allocate including the tracking data structure
  // and accounting for alignment.
  size_t total_size =
      RoundUpToAlignment(size + sizeof(AllocateData) + alignment, alignment);

  // Allocate memory.
  auto& callbacks = Get();
  char* buffer = reinterpret_cast<char*>(callbacks.Allocate(total_size));
  // Align the returned pointer.
  char* aligned_buffer = reinterpret_cast<char*>(RoundUpToAlignment(
      reinterpret_cast<size_t>(buffer) + sizeof(AllocateData), alignment));
  // Calculate address of the tracking data structure.
  auto* allocate_data = reinterpret_cast<AllocateData*>(
      reinterpret_cast<uint8_t*>(aligned_buffer) - sizeof(AllocateData));
  // Make sure we have enough space between the allocated address and the
  // tracking data structure.
  assert(static_cast<size_t>(aligned_buffer - buffer) >= sizeof(allocate_data));
  // Track the block.
  allocate_data->allocated_address = buffer;
  allocate_data->allocated_size = total_size;
  allocate_data->requested_size = size;
  allocate_data->allocator = callbacks;
  // Keep a running total of allocated memory.
  allocated_bytes_ += size;
  return aligned_buffer;
#else
#if _MSC_VER
  return _aligned_malloc(size, alignment);
#elif defined(__APPLE__)
  void *ptr = nullptr;
  posix_memalign(&ptr, alignment, size);
  return ptr;
#else
  return aligned_alloc(alignment, size);
#endif  // _MSC_VER
#endif  // !defined(FALKEN_ALLOCATOR_DISABLED)
}

void AllocatorCallbacks::GlobalFree(void* ptr) {
#if !defined(FALKEN_ALLOCATOR_DISABLED)
  if (ptr) {
    // Calculate address of the tracking data structure.
    auto* allocate_data = reinterpret_cast<AllocateData*>(
        reinterpret_cast<uint8_t*>(ptr) - sizeof(AllocateData));
    allocated_bytes_ -= allocate_data->requested_size;
    // Deallocate the originally allocated address.
    allocate_data->allocator.Free(allocate_data->allocated_address);
  }
#else
#if _MSC_VER
  return _aligned_free(ptr);
#else
  return free(ptr);
#endif  // _MSC_VER
#endif  // !defined(FALKEN_ALLOCATOR_DISABLED)
}

}  // namespace falken

#if FALKEN_GLOBAL_NEW_DELETE_ENABLED
void* operator new(std::size_t count) {
  return falken::AllocatorCallbacks::GlobalAllocate(count);
}

void* operator new[](std::size_t count) {
  return falken::AllocatorCallbacks::GlobalAllocate(count);
}

void* operator new(std::size_t count, const std::nothrow_t& /*tag*/) noexcept {
  return falken::AllocatorCallbacks::GlobalAllocate(count);
}

void* operator new[](std::size_t count,
                     const std::nothrow_t& /*tag*/) noexcept {
  return falken::AllocatorCallbacks::GlobalAllocate(count);
}

void operator delete(void* ptr) noexcept {
  falken::AllocatorCallbacks::GlobalFree(ptr);
}

void operator delete[](void* ptr) throw() {
  falken::AllocatorCallbacks::GlobalFree(ptr);
}

void operator delete(void* ptr, const std::nothrow_t& /*tag*/) {
  falken::AllocatorCallbacks::GlobalFree(ptr);
}

void operator delete[](void* ptr, const std::nothrow_t& /*tag*/) {
  falken::AllocatorCallbacks::GlobalFree(ptr);
}

void operator delete(void* const ptr, size_t const) noexcept {
  falken::AllocatorCallbacks::GlobalFree(ptr);
}

void operator delete[](void* ptr, size_t /*sz*/) noexcept {
  falken::AllocatorCallbacks::GlobalFree(ptr);
}

void operator delete(void* ptr, int64_t /*formal*/) {
  falken::AllocatorCallbacks::GlobalFree(ptr);
}

void operator delete[](void* ptr, int64_t /*formal*/) {
  falken::AllocatorCallbacks::GlobalFree(ptr);
}
#endif  // FALKEN_GLOBAL_NEW_DELETE_ENABLED
