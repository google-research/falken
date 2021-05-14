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

#ifndef FALKEN_SDK_CORE_STATUS_MACROS_H_
#define FALKEN_SDK_CORE_STATUS_MACROS_H_

#include <memory>

#include "src/core/statusor.h"
#include "absl/status/status.h"

namespace falken {
namespace common {

// Concatenates `x` and `y` tokens.
#define FALKEN_APPEND_LINE_NUM_CAT(x, y) x##y

// Required to force the expansion of `__LINE__` into the line number.
#define FALKEN_APPEND_LINE_NUM_EXPAND(x, y) FALKEN_APPEND_LINE_NUM_CAT(x, y)

// Appends current line number to `x`.
#define FALKEN_APPEND_LINE_NUM(x) FALKEN_APPEND_LINE_NUM_EXPAND(x, __LINE__)

// Evaluates an expression that returns an `absl::Status`. If the returned
// status is ok it does nothing, otherwise returns from the current function
// with the error status.
#define FALKEN_RETURN_IF_ERROR(expr) \
  {                                  \
    auto internal_status = (expr);   \
    if (!internal_status.ok()) {     \
      return internal_status;        \
    }                                \
  }

// Internal macro that receives the status_or variable name, which allows this
// macro to be called multiple times within the same function.
#define FALKEN_ASSIGN_OR_RETURN_INNER(status_or, lhs, expr) \
  auto status_or = (expr);                                  \
  if (!status_or.ok()) {                                    \
    return status_or.status();                              \
  }                                                         \
  lhs = std::move(status_or.ValueOrDie());

// Evaluates an expression that returns an `falken::common::StatusOr<T>`. If the
// returned status is ok it moves its value to lhs, otherwise returns from the
// current function with the error status.
#define FALKEN_ASSIGN_OR_RETURN(lhs, expr) \
  FALKEN_ASSIGN_OR_RETURN_INNER(FALKEN_APPEND_LINE_NUM(status_or_), lhs, expr)

}  // namespace common
}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_STATUS_MACROS_H_
