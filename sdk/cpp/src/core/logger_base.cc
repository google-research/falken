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

#include "src/core/logger_base.h"

#include <assert.h>
#include <stdarg.h>
#include <stdio.h>

#include <string>

#include "falken/log.h"

namespace falken {

std::string FormatString(const char* format, ...) {
  va_list args;
  va_start(args, format);
  std::string out = FormatStringv(format, args);
  va_end(args);
  return out;
}

std::string FormatStringv(const char* format, va_list args) {
  va_list calculate_string_size_list;
  va_copy(calculate_string_size_list, args);
  int length = vsnprintf(nullptr, 0, format, calculate_string_size_list);
  va_end(calculate_string_size_list);

  std::string formatted_string(length, '\0');
  int formatted_length = vsnprintf(
      &formatted_string[0],
      // vsnprintf subtracts 1 from size to leave room for a null character.
      formatted_string.size() + 1, format, args);
  (void)formatted_length;
  assert(formatted_length == length);
  return formatted_string;
}

LoggerBase::LoggerBase()
    : log_level_(kLogLevelInfo), notifier_(nullptr), notifier_handle_(0) {}

LoggerBase::~LoggerBase() {
  if (notifier_) notifier_->RemoveLogger(*this);
}

void LoggerBase::set_log_level(LogLevel log_level) { log_level_ = log_level; }

LogLevel LoggerBase::log_level() const { return log_level_; }

void LoggerBase::LogDebug(const char* format, ...) {
  va_list args;
  va_start(args, format);
  Logv(kLogLevelDebug, format, args);
  va_end(args);
}

void LoggerBase::LogVerbose(const char* format, ...) {
  va_list args;
  va_start(args, format);
  Logv(kLogLevelVerbose, format, args);
  va_end(args);
}

void LoggerBase::LogInfo(const char* format, ...) {
  va_list args;
  va_start(args, format);
  Logv(kLogLevelInfo, format, args);
  va_end(args);
}

void LoggerBase::LogWarning(const char* format, ...) {
  va_list args;
  va_start(args, format);
  Logv(kLogLevelWarning, format, args);
  va_end(args);
}

void LoggerBase::LogError(const char* format, ...) {
  va_list args;
  va_start(args, format);
  Logv(kLogLevelError, format, args);
  va_end(args);
}

void LoggerBase::LogFatal(const char* format, ...) {
  va_list args;
  va_start(args, format);
  Logv(kLogLevelFatal, format, args);
  va_end(args);
}

void LoggerBase::Logv(LogLevel log_level, const char* format, va_list args) {
  if (ShouldLog(log_level)) Log(log_level, FormatStringv(format, args).c_str());
}

bool LoggerBase::ShouldLog(LogLevel log_level) const {
  return log_level >= log_level_;
}

}  // namespace falken
