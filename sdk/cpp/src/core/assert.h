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

#ifndef FALKEN_SDK_CORE_ASSERT_H_
#define FALKEN_SDK_CORE_ASSERT_H_

#include "src/core/log.h"
#include "src/core/macros.h"

// Only include file and line number in debug build assert messages.
// This expands to a string in the form "filename(linenumber): ".
#if defined(NDEBUG)
#define FALKEN_ASSERT_MESSAGE_PREFIX
#else
#define FALKEN_ASSERT_MESSAGE_PREFIX \
  __FILE__ "(" FALKEN_EXPAND_STRINGIFY(__LINE__) "): "
#endif  // defined(NDEBUG)

// Asset that is included in all builds.
#define FALKEN_ASSERT(condition)                                            \
  do {                                                                      \
    if (!(condition)) {                                                     \
      falken::LogFatal("%s", FALKEN_ASSERT_MESSAGE_PREFIX                   \
                             FALKEN_EXPAND_STRINGIFY(condition));           \
    }                                                                       \
  } while (false)

// Asset that fails by displaying __VA_ARGS__ in the assert message if
// condition is not true.
// e.g
// FALKEN_ASSERT_MESSAGE(succeeded, "Failed to do %s because of %s",
//                       operation, failure_message);
#define FALKEN_ASSERT_MESSAGE(condition, ...)                               \
  do {                                                                      \
    if (!(condition)) {                                                     \
      falken::LogError("%s", FALKEN_ASSERT_MESSAGE_PREFIX                   \
                             FALKEN_EXPAND_STRINGIFY(condition));           \
      falken::LogFatal(__VA_ARGS__);                                        \
    }                                                                       \
  } while (false)

// Assert that is compiled out in non-debug builds.
#if defined(NDEBUG)
#define FALKEN_DEV_ASSERT(condition) \
  { (void)(condition); }
#else
#define FALKEN_DEV_ASSERT(condition) FALKEN_ASSERT(condition)
#endif  // defined(NDEBUG)

// Assert that displays a custom message if the condition fails.
#if defined(NDEBUG)
#define FALKEN_DEV_ASSERT_MESSAGE(condition, ...) \
  { (void)(condition); }
#else
#define FALKEN_DEV_ASSERT_MESSAGE(condition, ...) \
  FALKEN_ASSERT_MESSAGE(condition, __VA_ARGS__)
#endif  // defined(NDEBUG)

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_ASSERT_H_
