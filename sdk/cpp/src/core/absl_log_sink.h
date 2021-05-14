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

#ifndef FALKEN_SDK_CORE_ABSL_LOG_SINK_H_
#define FALKEN_SDK_CORE_ABSL_LOG_SINK_H_

#include <cstdint>

namespace falken {

class LoggerBase;

// Additional sink for logs originating libraries using absl logging.
class AbslLogSink
{
  friend class AbslLogSinkTest;

 public:
  // Constructing this object adds the instance as a log sink to capture all
  // absl logs. Absl logs are forwarded to the specified logger.
  explicit AbslLogSink(LoggerBase& logger);
  // Remove from the global log source.
  virtual ~AbslLogSink();  // NOLINT

 protected:

 private:
  LoggerBase& logger_;
  // Time in milliseconds since the Unix epoch, exposed to inject the time
  // applied to log messages for testing.
  uint64_t log_time_;
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_ABSL_LOG_SINK_H_
