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

#ifndef FALKEN_SDK_CORE_STATUSOR_H_
#define FALKEN_SDK_CORE_STATUSOR_H_

#include <cstdlib>

#include "src/core/log.h"
#include "absl/status/status.h"
#include "absl/strings/str_cat.h"

namespace falken {
namespace common {

// A StatusOr holds a Status (in the case of an error), or a value T.
template <typename T>
class StatusOr {
 public:
  // If no arguments are provided, status is unknown.
  StatusOr() : status_(absl::StatusCode::kUnknown, "") {}

  // Builds from a specified status. Crashes if status is ok.
  StatusOr(const absl::Status& status);  // NOLINT

  // Builds from a specified value.
  StatusOr(const T& value) : value_(value) {}        // NOLINT
  StatusOr(T&& value) : value_(std::move(value)) {}  // NOLINT

  // Copy constructor.
  StatusOr(const StatusOr& other)
      : status_(other.status_), value_(other.value_) {}

  // Move constructor.
  StatusOr(StatusOr&& other)
      : status_(std::move(other.status_)), value_(std::move(other.value_)) {}

  // Returns status.
  absl::Status status() const { return status_; }

  // Returns status().ok().
  bool ok() const { return status_.ok(); }

  // Crashes if status is not ok.
  void CheckOk() const;

  // Returns value or crashes if status is not ok.
  const T& ValueOrDie() const&;
  T& ValueOrDie() &;
  const T&& ValueOrDie() const&&;
  T&& ValueOrDie() &&;

  // Returns a reference to the current value.
  const T& operator*() const&;
  T& operator*() &;
  const T&& operator*() const&&;
  T&& operator*() &&;

  // Returns a pointer to the current value.
  const T* operator->() const;
  T* operator->();

  // Convert error message and error code to a string representation.
  std::string ToString() const;

 private:
  absl::Status status_;
  T value_;
};

template <typename T>
StatusOr<T>::StatusOr(const absl::Status& status) : status_(status) {
  if (status.ok()) {
    falken::LogError("absl::OkStatus() is not a valid argument to StatusOr");
    std::abort();
  }
}

template <typename T>
void StatusOr<T>::CheckOk() const {
  if (!ok()) {
    falken::LogFatal(
        "Attempting to fetch value of non-OK StatusOr with error: %s",
        std::string(status_.message()).c_str());
  }
}

template <typename T>
const T& StatusOr<T>::ValueOrDie() const& {
  this->CheckOk();
  return this->value_;
}

template <typename T>
T& StatusOr<T>::ValueOrDie() & {
  this->CheckOk();
  return this->value_;
}

template <typename T>
const T&& StatusOr<T>::ValueOrDie() const&& {
  this->CheckOk();
  return std::move(this->value_);
}

template <typename T>
T&& StatusOr<T>::ValueOrDie() && {
  this->CheckOk();
  return std::move(this->value_);
}

template <typename T>
const T& StatusOr<T>::operator*() const& {
  this->CheckOk();
  return this->value_;
}

template <typename T>
T& StatusOr<T>::operator*() & {
  this->CheckOk();
  return this->value_;
}

template <typename T>
const T&& StatusOr<T>::operator*() const&& {
  this->CheckOk();
  return std::move(this->value_);
}

template <typename T>
T&& StatusOr<T>::operator*() && {
  this->CheckOk();
  return std::move(this->value_);
}

template <typename T>
const T* StatusOr<T>::operator->() const {
  this->CheckOk();
  return &this->value_;
}

template <typename T>
T* StatusOr<T>::operator->() {
  this->CheckOk();
  return &this->value_;
}

template <typename T>
std::string StatusOr<T>::ToString() const {
  return "Error message: " + std::string(status_.message()) + ". Error code: " +
      std::to_string(static_cast<int>(status_.code()));
}

}  // namespace common
}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_STATUSOR_H_
