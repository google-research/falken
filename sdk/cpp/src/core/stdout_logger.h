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

#ifndef FALKEN_SDK_CORE_STDOUT_LOGGER_H_
#define FALKEN_SDK_CORE_STDOUT_LOGGER_H_

#include "falken/log.h"

namespace falken {

// Logs to standard output or standard error streams.
class StandardOutputErrorLogger : public LoggerBase {
 public:
  void Log(LogLevel log_level, const char* message) override;
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_STDOUT_LOGGER_H_
