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

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_ALLOCATOR_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_ALLOCATOR_H_

#include <stddef.h>

#include <memory>

#include "falken/config.h"

namespace falken {

/// @brief Callback methods that can be used to override Falken's allocator.
class FALKEN_EXPORT AllocatorCallbacks {
  friend class AllocatorTest;

 public:
  /// Allocate memory.
  ///
  /// @param size Size in bytes to allocate.
  /// @param context User defined context.
  ///
  /// @return Pointer to allocated memory.
  typedef void* (*AllocateFunc)(size_t size, void* context);

  /// Free memory.
  ///
  /// @param ptr Memory to deallocate.
  /// @param context user defined context.
  typedef void (*FreeFunc)(void* ptr, void* context);

  /// Construct a set of callbacks
  ///
  /// @param allocate Allocate function.
  /// @param free Free function.
  /// @param context User defined context that should be passed to allocate
  /// and free.
  AllocatorCallbacks(AllocateFunc allocate, FreeFunc free, void* context);

  /// Copy allocation callbacks on construction.
  ///
  /// @param callbacks callbacks to copy.
  AllocatorCallbacks(const AllocatorCallbacks& callbacks) = default;

  /// Allocate memory with the allocation function.
  ///
  /// @note The application developer should only use this if they intend to
  /// chain allocators.
  ///
  /// @param size Size in bytes to allocate.
  ///
  /// @return Pointer to allocated memory.
  void* Allocate(size_t size);

  /// Free memory with the free function.
  ///
  /// @note The application developer should only use this if they intend to
  /// chain allocators.
  ///
  /// @param ptr Memory to deallocate.
  void Free(void* ptr);

  /// @brief Set global allocator callbacks.
  ///
  /// @note The returned allocation callbacks can be used by the application
  /// developer if they wish to chain allocators.
  ///
  /// @param callbacks Allocation callbacks to use from this point on.
  ///
  /// @return Previous allocation callbacks.
  static AllocatorCallbacks Set(const AllocatorCallbacks& callbacks);

  /// Allocate memory with the global allocator.
  ///
  /// @warning The application developer should not need to call this method.
  ///
  /// @param size Size in bytes to allocate.
  /// @param alignment Allocation aligment in bytes. If this parameter is not
  ///     set, the memory will be allocated at the default alignment for the
  ///     platform.
  ///
  /// @return Pointer to allocated memory.
  static void* GlobalAllocate(size_t size, size_t alignment = 0);

  /// Free memory with the global deallocator.
  ///
  /// @warning The application developer should not need to call this method.
  ///
  /// @param ptr Memory to deallocate.
  static void GlobalFree(void* ptr);

  /// Get the total memory allocated by the global allocator.
  ///
  /// @return Total number of bytes allocated by the global allocator.
  static size_t allocated_bytes();

 private:
  /// Get the global callbacks.
  ///
  /// @note This should only be called when the global lock is held.
  ///
  /// @return Global allocator callbacks.
  static AllocatorCallbacks& Get();

  /// Allocate memory.
  AllocateFunc allocate_;
  /// Free memory.
  FreeFunc free_;
  /// User defined context passed to allocate and free methods.
  void* context_;

  // Running total of all memory allocated by the global allocator.
  static size_t allocated_bytes_;
};

/// Allocator which uses callbacks configured by
/// falken::SetAllocatorCallbacks().
///
/// @tparam T Type of the object this should allocate.
template <typename T>
class Allocator : public std::allocator<T> {
 public:
  /// Size type.
  typedef size_t size_type;
  /// Pointer of type T.
  typedef T* pointer;
  /// Const pointer of type T.
  typedef const T* const_pointer;

  /// Construct.
  Allocator() throw() : std::allocator<T>() {}

  /// @brief Copy on construction.
  ///
  /// @param a Allocator to copy.
  Allocator(const Allocator& a) throw() : std::allocator<T>(a) {}  // NOLINT

  /// @brief Constructs and copies an Allocator.
  ///
  /// @param allocator Allocator to copy.
  ///
  /// @tparam U type of the object allocated by the allocator to copy.
  template <class U>
  Allocator(const Allocator<U>& allocator) throw()  // NOLINT
      : std::allocator<T>(allocator) {}
  /// @brief Destructs an Allocator.
  ~Allocator() throw() {}

  /// @brief Obtains an allocator of a different type.
  ///
  /// @tparam NewType Type of the new allocator.
  template <typename NewType>
  struct rebind {
    /// @brief Allocator of type _Tp1.
    typedef Allocator<NewType> other;
  };

  /// @brief Allocate memory for object T.
  ///
  /// @param n Number of instances to allocate.
  /// @return Pointer to the newly allocated memory.
  pointer allocate(size_type n) {
    return reinterpret_cast<pointer>(
        AllocatorCallbacks::GlobalAllocate(n * sizeof(T)));
  }

  /// Deallocate memory referenced by pointer p.
  ///
  /// @param p Pointer to memory to deallocate.
  void deallocate(pointer p, size_type) { AllocatorCallbacks::GlobalFree(p); }
};

#define FALKEN_DEFINE_NEW_DELETE                                         \
  static void* operator new(std::size_t count) {                         \
    return falken::AllocatorCallbacks::GlobalAllocate(count);            \
  }                                                                      \
  static void* operator new[](std::size_t count) {                       \
    return falken::AllocatorCallbacks::GlobalAllocate(count);            \
  }                                                                      \
  static void* operator new(std::size_t count,                           \
                            const std::nothrow_t& /*tag*/) noexcept {    \
    return falken::AllocatorCallbacks::GlobalAllocate(count);            \
  }                                                                      \
  static void* operator new[](std::size_t count,                         \
                              const std::nothrow_t& /*tag*/) noexcept {  \
    return falken::AllocatorCallbacks::GlobalAllocate(count);            \
  }                                                                      \
  static void operator delete(void* ptr) noexcept {                      \
    falken::AllocatorCallbacks::GlobalFree(ptr);                         \
  }                                                                      \
  static void operator delete[](void* ptr) throw() {                     \
    falken::AllocatorCallbacks::GlobalFree(ptr);                         \
  }                                                                      \
  static void operator delete(void* ptr,                                 \
                              const std::nothrow_t& /*tag*/) {   \
    falken::AllocatorCallbacks::GlobalFree(ptr);                         \
  }                                                                      \
  static void operator delete[](void* ptr,                               \
                                const std::nothrow_t& /*tag*/) { \
    falken::AllocatorCallbacks::GlobalFree(ptr);                         \
  }                                                                      \
  static void operator delete(void* const ptr, size_t const) noexcept {  \
    falken::AllocatorCallbacks::GlobalFree(ptr);                         \
  }                                                                      \
  static void operator delete[](void* ptr, size_t /*sz*/) noexcept {     \
    falken::AllocatorCallbacks::GlobalFree(ptr);                         \
  }                                                                      \
  static void operator delete(void* ptr, int64_t /*formal*/) {           \
    falken::AllocatorCallbacks::GlobalFree(ptr);                         \
  }                                                                      \
  static void operator delete[](void* ptr, int64_t /*formal*/) {         \
    falken::AllocatorCallbacks::GlobalFree(ptr);                         \
  }

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_ALLOCATOR_H_
