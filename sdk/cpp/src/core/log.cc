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

#include "src/core/log.h"

#include <stdarg.h>

#include "falken/log.h"

namespace falken {

const char* kContactFalkenTeamBug =
    "If the error persists, please contact Falken team to report this as a bug";

const char* kContactFalkenTeam =
    "If the error persists, please contact Falken for further assistance.";

namespace {

void Logv(LogLevel log_level, const char* format, va_list args) {
  SystemLogger::Get()->Logv(log_level, format, args);
}

}  // namespace

void LogDebug(const char* format, ...) {
  va_list args;
  va_start(args, format);
  Logv(kLogLevelDebug, format, args);
  va_end(args);
}

void LogVerbose(const char* format, ...) {
  va_list args;
  va_start(args, format);
  Logv(kLogLevelVerbose, format, args);
  va_end(args);
}

void LogInfo(const char* format, ...) {
  va_list args;
  va_start(args, format);
  Logv(kLogLevelInfo, format, args);
  va_end(args);
}

void LogWarning(const char* format, ...) {
  va_list args;
  va_start(args, format);
  Logv(kLogLevelWarning, format, args);
  va_end(args);
}

void LogError(const char* format, ...) {
  va_list args;
  va_start(args, format);
  Logv(kLogLevelError, format, args);
  va_end(args);
}

void LogFatal(const char* format, ...) {
  va_list args;
  va_start(args, format);
  Logv(kLogLevelFatal, format, args);
  va_end(args);
}

}  // namespace falken
