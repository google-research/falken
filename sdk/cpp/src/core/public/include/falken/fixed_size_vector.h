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

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_FIXED_SIZE_VECTOR_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_FIXED_SIZE_VECTOR_H_

#include <vector>

#include "falken/allocator.h"
#include "falken/config.h"

namespace falken {

/// Vector that can't be resized.
template <typename T>
class FixedSizeVector {
 public:
  /// Vector iterator.
  typedef typename std::vector<T>::iterator iterator;
  /// Vector constant iterator.
  typedef typename std::vector<T>::const_iterator const_iterator;

 public:
  /// Construct fixed size vector.
  ///
  /// @param storage Vector to fix size.
  explicit FixedSizeVector(std::vector<T>* storage) : storage_(storage) {}
  /// Copy assignment operator.
  ///
  /// @param x Vector to copy.
  /// @return Fixed size vector.
  FixedSizeVector& operator=(const std::vector<T>& x) {
    *storage_ = x;
    return *this;
  }

  /// Get iterator that points to the first element of the vector.
  ///
  /// @return Iterator pointing to first element.
  iterator begin() { return storage_->begin(); }
  /// Get constant iterator that points to the first element of the vector.
  ///
  /// @return Constant iterator pointing to first element.
  const_iterator begin() const { return storage_->begin(); }
  /// Get iterator that points to the last element of the vector.
  ///
  /// @return Iterator pointing to last element.
  iterator end() { return storage_->end(); }
  /// Get constant iterator that points to the last element of the vector.
  ///
  /// @return Constant iterator pointing to last element.
  const_iterator end() const { return storage_->end(); }

  /// Get reverse iterator that points to the last element of the vector.
  ///
  /// @return Reverse iterator pointing to last element.
  iterator rbegin() { return storage_->begin(); }
  /// Get constant reverse iterator that points to the last element of the
  /// vector.
  ///
  /// @return Constant reverse iterator pointing to last element.
  const_iterator rbegin() const { return storage_->begin(); }
  /// Get reverse iterator that points to the first element of the vector.
  ///
  /// @return Reverse iterator pointing to first element.
  iterator rend() { return storage_->end(); }
  /// Get constant reverse iterator that points to the first element of the
  /// vector.
  ///
  /// @return Constant reverse iterator pointing to first element.
  const_iterator rend() const { return storage_->end(); }

  /// Get constant iterator that points to the first element of the vector.
  ///
  /// @return Constant iterator pointing to first element.
  const_iterator cbegin() { return storage_->cbegin(); }
  /// Get constant iterator that points to the last element of the vector.
  ///
  /// @return Constant iterator pointing to last element.
  const_iterator cend() const { return storage_->cend(); }
  /// Get constant reverse iterator that points to the last element of the
  /// vector.
  ///
  /// @return Constant reverse iterator pointing to last element.
  const_iterator crbegin() { return storage_->crbegin(); }
  /// Get constant reverse iterator that points to the first element of the
  /// vector.
  ///
  /// @return Constant reverse iterator pointing to first element.
  const_iterator crend() const { return storage_->crend(); }

  /// Get vector size.
  ///
  /// @return Size of the vector.
  size_t size() const { return storage_->size(); }
  /// Get vector maximum size.
  ///
  /// @return Maximum size of the vector.
  size_t max_size() const { return storage_->max_size(); }
  /// Get vector capacity.
  ///
  /// @return Capacity of the vector.
  size_t capacity() const { return storage_->capacity(); }
  /// Check if the vector is empty.
  ///
  /// @return true if the vector is empty, false otherwise.
  bool empty() const { return storage_->empty(); }

  /// Get mutable element by index.
  ///
  /// @param n Index value.
  /// @return Mutable element located in the provided index.
  T& operator[](size_t n) { return (*storage_)[n]; }
  /// Get element by index.
  ///
  /// @param n Index value.
  /// @return Element located in the provided index.
  const T& operator[](size_t n) const { return (*storage_)[n]; }
  /// Get mutable element by index.
  ///
  /// @param n Index value.
  /// @return Mutable element located in the provided index.
  T& at(size_t n) { return storage_->at(n); }
  /// Get element by index.
  ///
  /// @param n Index value.
  /// @return Element located in the provided index.
  const T& at(size_t n) const { return storage_->at(n); }
  /// Get mutable first element.
  ///
  /// @return Mutable first element.
  T& front() { return storage_->front(); }
  /// Get first element.
  ///
  /// @return First element.
  const T& front() const { return storage_->front(); }
  /// Get mutable last element.
  ///
  /// @return Mutable last element.
  T& back() { return storage_->back(); }
  /// Get last element.
  ///
  /// @return Last element.
  const T& back() const { return storage_->back(); }
  /// Get mutable vector data.
  ///
  /// @return Mutable vector data.
  T* data() { return storage_->data(); }
  /// Get vector data.
  ///
  /// @return Vector data.
  const T* data() const { return storage_->data(); }

  FALKEN_DEFINE_NEW_DELETE

 private:
  std::vector<T>* storage_;
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_FIXED_SIZE_VECTOR_H_
