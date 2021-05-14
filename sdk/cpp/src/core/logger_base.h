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

#ifndef FALKEN_SDK_CORE_LOGGER_BASE_H_
#define FALKEN_SDK_CORE_LOGGER_BASE_H_

#include <stdarg.h>

#include <string>

namespace falken {

// Format a string with sprintf().
std::string FormatString(const char* format, ...);
std::string FormatStringv(const char* format, va_list args);

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_LOGGER_BASE_H_
