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

#ifndef FALKEN_SDK_CORE_STRING_LOGGER_H_
#define FALKEN_SDK_CORE_STRING_LOGGER_H_

#include <string>
#include <utility>
#include <vector>

#include "falken/log.h"
#include "gmock/gmock.h"

namespace falken {
namespace testing {

using ::testing::Matcher;
using ::testing::MatchesRegex;

// Test logger which saves the message and the log level for each log created.
class StringLogger : public LoggerBase {
 public:
  StringLogger() { logs_.emplace_back(std::make_pair(kLogLevelFatal, "")); }

  void Log(LogLevel log_level, const char* message) override {
    logs_.emplace_back(std::make_pair(log_level, message));
  }

  // Get last log level.
  LogLevel last_log_level() const { return logs_.back().first; }

  // Get last log message.
  const char* last_message() const { return logs_.back().second.c_str(); }

  // Get all logs.
  const std::vector<std::pair<LogLevel, std::string>>& logs() const {
    return logs_;
  }

  // Find a certain log. Returns nullptr in case the log does not exist.
  const std::pair<LogLevel, std::string>* FindLog(
      LogLevel log_level, const char* message_regex) const {
    const Matcher<const char*> regex_matcher = MatchesRegex(message_regex);
    for (const auto& log : logs_) {
      if (log_level == log.first && regex_matcher.Matches(log.second.c_str())) {
        return &log;
      }
    }
    return nullptr;
  }

 private:
  std::vector<std::pair<LogLevel, std::string>> logs_;
};

}  // namespace testing
}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_STRING_LOGGER_H_
