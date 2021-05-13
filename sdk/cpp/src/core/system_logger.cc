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

#include <memory>
#include <utility>

#include "src/core/absl_log_sink.h"
#include "src/core/client_info.h"
#include "src/core/logger_base.h"
#include "falken/log.h"
#include "src/core/stdout_logger.h"
#include "src/core/temp_file.h"
#include "absl/synchronization/mutex.h"

// Define FALKEN_LOG_FILENAME at compile time to set the output log file before
// SDK initialization.
#if !defined(FALKEN_LOG_FILENAME)
#define FALKEN_LOG_FILENAME ""
#endif  // !defined(FALKEN_LOG_FILENAME)

namespace falken {

namespace {

// Default configuration for a system logger used to save the state of the
// logger when the global instance is cleaned up so that it can be restored
// when a new instance is created.
struct DefaultLogConfiguration {
  DefaultLogConfiguration() :
      log_level(kLogLevelInfo),
      log_filename(FALKEN_LOG_FILENAME),
      temporary_log_file(temporary_log_file_logger, "falken_log.txt") {
    if (log_filename.empty() && temporary_log_file.Create()) {
      log_filename = temporary_log_file.path();
    }
  }

  LoggerNotifier notifier;
  LogLevel log_level;
  std::string log_filename;
  StandardOutputErrorLogger temporary_log_file_logger;
  core::TempFile temporary_log_file;
};

// Guards default system logger configuration.
absl::Mutex global_default_log_config_lock(absl::kConstInit);
std::unique_ptr<DefaultLogConfiguration> global_default_log_config;  // NOLINT

// Prefix applied to a message at the specified log level.
const char* LogLevelToPrefix(LogLevel log_level) {
  switch (log_level) {
    case kLogLevelDebug:
      return "DEBUG:";
    case kLogLevelVerbose:
      return "VERBOSE:";
    case kLogLevelInfo:
      return "INFO:";
    case kLogLevelWarning:
      return "WARNING:";
    case kLogLevelError:
      return "ERROR:";
    case kLogLevelFatal:
      return "FATAL:";
  }
  assert("Invalid log level" == nullptr);
  return ":";
}

}  // namespace

// Implementation of SystemLogger. This uses an internal LoggerNotifier
// so that it's possible to customize the formatting of messages sent to
// default log sinks.
class SystemLoggerInternal {
 private:
  // Forwards log messages from absl to SystemLoggerInternal.
  class AbslLogger : public LoggerBase {
   public:
    explicit AbslLogger(SystemLoggerInternal& logger_internal)
        : logger_internal_(logger_internal) {}

    void Log(LogLevel log_level, const char* message) override {
      logger_internal_.Notify(log_level, message, false);
    }

   private:
    SystemLoggerInternal& logger_internal_;
  };

  // Exposes the Notify() method so it's possibly to manually notify
  // internal loggers.
  class InternalNotifier : public LoggerNotifier {
   public:
    bool Notify(LogLevel log_level, const char* message) const {
      return LoggerNotifier::Notify(log_level, message);
    }
  };

 public:
  explicit SystemLoggerInternal(SystemLogger& logger);

  FileLogger& file_logger() { return file_logger_; }

  void set_abort_on_fatal_error(bool enable) { abort_on_fatal_ = enable; }
  bool abort_on_fatal_error() const { return abort_on_fatal_; }

  // Send the specified message to all log sinks.  If is_falken_log is true
  // the message is formatted to indicate that it was produced by Falken.
  bool Notify(LogLevel log_level, const char* message, bool is_falken_log);

 private:
  SystemLogger& system_logger_;
  InternalNotifier notifier_;
  FileLogger file_logger_;
  StandardOutputErrorLogger standard_output_error_logger_;
  AbslLogger absl_logger_;
  AbslLogSink absl_log_sink_;
  bool abort_on_fatal_;
};

SystemLoggerInternal::SystemLoggerInternal(SystemLogger& logger)
    : system_logger_(logger),
      absl_logger_(*this),
      absl_log_sink_(absl_logger_),
      abort_on_fatal_(true) {
  file_logger_.set_log_level(kLogLevelDebug);
  notifier_.AddLogger(file_logger_);
  notifier_.AddLogger(standard_output_error_logger_);
}

bool SystemLoggerInternal::Notify(LogLevel log_level, const char* message,
                                  bool is_falken_log) {
  bool notified = false;
  // Notify user log sink.
  notified |= system_logger_.Notify(log_level, message);
  // Update the log level filter for the standard output logger, all other
  // log sinks receive the unfiltered log message.
  standard_output_error_logger_.set_log_level(system_logger_.log_level());
  // Notify internal log sinks.
  notified |= notifier_.Notify(
      log_level,
      is_falken_log
          ? FormatString("[Falken] %s %s", LogLevelToPrefix(log_level), message)
                .c_str()
          : message);
  // If this is a fatal error, optionally stop the application.
  if (log_level == kLogLevelFatal && abort_on_fatal_error()) abort();
  return notified;
}

SystemLogger::SystemLogger() {
  internal_ = new SystemLoggerInternal(*this);
  {
    absl::MutexLock lock(&global_default_log_config_lock);
    auto& config = global_default_log_config;
    if (!config) {
      config = std::make_unique<DefaultLogConfiguration>();
    }
    LoggerNotifier& this_notifier = *this;
    this_notifier = std::move(config->notifier);
    set_log_level(config->log_level);
    file_logger().set_filename(config->log_filename.c_str());
  }
  LogVerbose("Falken SDK: %s", GetVersionInformation().c_str());
}

SystemLogger::~SystemLogger() {
  {
    absl::MutexLock lock(&global_default_log_config_lock);
    auto& config = global_default_log_config;
    config->notifier = std::move(*this);
    config->log_level = log_level();
    config->log_filename = file_logger().filename().c_str();  // NOLINT
  }
  delete internal_;
}

void SystemLogger::Log(LogLevel log_level, const char* message) {
  internal_->Notify(log_level, message, true);
}

void SystemLogger::Logv(LogLevel log_level, const char* format, va_list args) {
  // Send to log sinks without filtering.
  Log(log_level, FormatStringv(format, args).c_str());
}

bool SystemLogger::Notify(LogLevel log_level, const char* message) const {
  return LoggerNotifier::Notify(log_level, message);
}

FileLogger& SystemLogger::file_logger() { return internal_->file_logger(); }

void SystemLogger::set_abort_on_fatal_error(bool enable) {
  internal_->set_abort_on_fatal_error(enable);
}

bool SystemLogger::abort_on_fatal_error() const {
  return internal_->abort_on_fatal_error();
}

std::shared_ptr<SystemLogger> SystemLogger::Get() {
  static std::weak_ptr<falken::SystemLogger> global_system_logger;  // NOLINT
  auto logger = global_system_logger.lock();
  if (!logger) {
    logger = std::shared_ptr<SystemLogger>(new SystemLogger());
    global_system_logger = logger;
  }
  return logger;
}

}  // namespace falken
