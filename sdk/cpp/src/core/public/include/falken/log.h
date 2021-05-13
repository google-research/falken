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

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_LOG_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_LOG_H_

#include <stdarg.h>

#include <memory>

#include "falken/types.h"

namespace falken {

/// Mono's calling convention for C# delegate entry points.
/// Any methods that can call back into a C# entry point should use this calling
/// convention.
#if !defined(FALKEN_MONO_STDCALL)
#if defined(_WIN32) || defined(__WIN32__)
#define FALKEN_MONO_STDCALL __stdcall
#else
#define FALKEN_MONO_STDCALL
#endif  // defined(_WIN32) || defined(__WIN32__)
#endif  // !defined(FALKEN_MONO_STDCALL)

/// Log level of messages.
///
/// The log level is used to indicate the importance of a message from
/// least important (kLogLevelDebug) to critical (kLogLevelFatal).
enum LogLevel {
  /// Debug message.
  kLogLevelDebug = -2,
  /// Verbose message.
  kLogLevelVerbose = -1,
  /// Informational message.
  kLogLevelInfo = 0,  // Same value as absl::LogSeverity::kInfo
  /// Warning message.
  kLogLevelWarning = 1,  // Same value as absl::LogSeverity::kWarning
  /// Error message.
  kLogLevelError = 2,  // Same value as absl::LogSeverity::kError
  /// Fatal message.
  kLogLevelFatal = 3  // Same value as absl::LogSeverity::kFatal
};

/// Called with log message notifications.
///
/// @param log_level Log level of the message.
/// @param message Log message.
/// @param context Optional user specified context for the log callback.
typedef void(FALKEN_MONO_STDCALL* LogCallback)(LogLevel log_level,
                                               const char* message,
                                               void* context);

class LoggerBase;
class LoggerNotifierInternal;

/// Forwards log messages to other logger instances.
class FALKEN_EXPORT LoggerNotifier {
  friend class LoggerNotifierInternal;

 public:
  // Handle to a registered callback.
  typedef unsigned int Handle;

  /// Construct a logger notifier.
  LoggerNotifier();

  /// Destruct a logger notifier.
  ~LoggerNotifier();

#if !defined(SWIG)
  /// Register a logger to handle log messages.
  ///
  /// @param logger Logger that has Logger::Log() called for all messages sent
  ///   to the system logger.
  ///
  /// @return true if successful, false otherwise.
  bool AddLogger(LoggerBase& logger);

  /// Unregister a logger.
  ///
  /// @param logger Logger to unregister for messages.
  void RemoveLogger(LoggerBase& logger);
#endif  // !defined(SWIG)

  /// Register a callback for log messages.
  ///
  /// @param log_callback Called when a message is logged. This can be called
  ///   from any thread.
  /// @param context Developer defined data to pass to log_callback.
  ///
  /// @return Handle that can optionally be used to unregister this callback.
  ///   Returns a value greater than 0 if successful, 0 otherwise.
  Handle AddLogCallback(LogCallback log_callback, void* context);

  /// Unregister a callback for log messages.
  ///
  /// @param handle Handle returned by AddLogCallback() which unregisters the
  ///   associated callback. After the handle has been unregistered it is
  ///   invalid.
  void RemoveLogCallback(LoggerNotifier::Handle handle);

  /// Move all logger references from another notifier.
  ///
  /// @param other Notifier to move from.
  LoggerNotifier& operator=(LoggerNotifier&& other);

 protected:
  /// Notify loggers of a new log message.
  ///
  /// @param log_level Verbosity of the message.
  /// @param message Message to log.
  bool Notify(LogLevel log_level, const char* message) const;

 private:
  LoggerNotifierInternal* internal_;
};

/// Common functionality for all loggers.
class FALKEN_EXPORT LoggerBase {
  friend class LoggerNotifierInternal;

 public:
  /// Construct a logger.
  LoggerBase();

  /// Destruct a logger.
  ///
  /// This will also attempt to unregister itself from the system logger.
  virtual ~LoggerBase();

  /// Set the current log verbosity.
  ///
  /// @param log_level All messages at and above the provided log level will be
  ///   reported to log callbacks. The default log level is kLogLevelInfo so
  ///   messages logged at kLogLevelInfo through to kLogLevelFatal will be
  ///   logged.
  void set_log_level(LogLevel log_level);

  /// Get the current log verbosity.
  ///
  /// @return Log verbosity.
  LogLevel log_level() const;

  /// Log a message.
  ///
  /// @param log_level Verbosity of the message.
  /// @param message Message to log.
  virtual void Log(LogLevel log_level, const char* message) = 0;

#if !defined(SWIG)
  /// Log a message.
  ///
  /// @param log_level Verbosity of the message.
  /// @param format printf() compatible format specification.
  /// @param args Arguments for the format specification.
  virtual void Logv(LogLevel log_level, const char* format, va_list args);
#endif  // !defined(SWIG)

  /// Log a debug message.
  ///
  /// @param format printf() compatible format specification.
  /// @param ... Arguments for the format specification.
  void LogDebug(const char* format, ...);

  /// Log a verbose message.
  ///
  /// @param format printf() compatible format specification.
  /// @param ... Arguments for the format specification.
  void LogVerbose(const char* format, ...);

  /// Log an informational message.
  ///
  /// @param format printf() compatible format specification.
  /// @param ... Arguments for the format specification.
  void LogInfo(const char* format, ...);

  /// Log a warning message.
  ///
  /// @param format printf() compatible format specification.
  /// @param ... Arguments for the format specification.
  void LogWarning(const char* format, ...);

  /// Log an error message.
  ///
  /// @param format printf() compatible format specification.
  /// @param ... Arguments for the format specification.
  void LogError(const char* format, ...);

  /// Log a fatal message.
  ///
  /// @param format printf() compatible format specification.
  /// @param ... Arguments for the format specification.
  void LogFatal(const char* format, ...);

 protected:
  /// Determines whether a message at the specified log level should be logged.
  ///
  /// For example:
  /// @code{.cpp}
  /// if (ShouldLog(log_level)) printf("%s\n", message);
  /// @endcode
  ///
  /// @param log_level Log level to test.
  ///
  /// @return True if the message should be logged, false otherwise.
  bool ShouldLog(LogLevel log_level) const;

 private:
  LogLevel log_level_;
  // Object that is notifying this logger.
  LoggerNotifier* notifier_;
  unsigned int notifier_handle_;
};

class FileLoggerInternal;

/// Logger that logs to a file.
class FALKEN_EXPORT FileLogger : public LoggerBase {
 public:
  /// Construct a file logger.
  FileLogger();

  /// Destruct a file logger.
  ~FileLogger() override;

  /// Set the filename to log to.
  ///
  /// @param filename Path to the file to log to. If an existing log file is
  ///   open it is closed and this method will attempt to open the specified
  ///   file instead. When given an empty filename or nullptr this will close
  ///   the associated file.
  ///
  /// @return true if the file is opened successfully, false otherwise.
  virtual bool set_filename(const char* filename);

  /// Get the current log filename.
  ///
  /// @return Log filename.
  String filename() const;

  /// Log a message
  ///
  /// @param log_level Verbosity of the message.
  /// @param message Message to log.
  void Log(LogLevel log_level, const char* message) override;

 protected:
  FileLoggerInternal* internal_;
};

class SystemLoggerInternal;

/// System logger that is the final destination for all log messages.
///
/// This object can be used to:
/// <ul>
///   <li>Register for notifications of all log messages from Falken.</li>
///   <li>Filter logs sent to default log sinks using set_log_level().</li>
///   <li>Log to a file by configuring the FileLogger returned by
///   file_logger().</li>
/// </ul>
///
class FALKEN_EXPORT SystemLogger
#if !defined(SWIG)
    : public LoggerBase, public LoggerNotifier
#endif  // !defined(SWIG)
{
  friend class SystemLoggerInternal;

 public:
  /// Destruct the system logger.
  ~SystemLogger() override;

  /// Get the system-wide file logger.
  ///
  /// @return File logger.
  FileLogger& file_logger();

  /// Log a message
  ///
  /// @param log_level Verbosity of the message.
  /// @param message Message to log.
  void Log(LogLevel log_level, const char* message) override;

#if !defined(SWIG)
  /// Log a message.
  ///
  /// @param log_level Verbosity of the message.
  /// @param format printf() compatible format specification.
  /// @param args Arguments for the format specification.
  void Logv(LogLevel log_level, const char* format, va_list args) override;
#endif  // !defined(SWIG)

  /// Whether to abort on fatal errors or continue.
  ///
  /// @warning Use of this method to disable aborting on fatal errors is not
  /// recommended. If you continue to use Falken after a fatal error the
  /// behavior can be undefined.
  ///
  /// @param enable Enables aborting the application on fatal errors. This is
  ///   the default behavior.
  void set_abort_on_fatal_error(bool enable);

  /// Gets whether to abort on fatal errors.
  ///
  /// @return Whether to abort on fatal errors.
  bool abort_on_fatal_error() const;

  /// Get or create the system logger singleton.
  ///
  /// @return System logger that is deleted when all references are removed.
  /// Falken will hold a reference to this instance in all objects that
  /// log messages. If the application wants to register additional loggers or
  /// callbacks
  static std::shared_ptr<SystemLogger> Get();

 protected:
  // Construct the logger. See Get().
  SystemLogger();

 private:
  /// Notify loggers of a new log message.
  ///
  /// @param log_level Verbosity of the message.
  /// @param message Message to log.
  bool Notify(LogLevel log_level, const char* message) const;

 private:
  SystemLoggerInternal* internal_;
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_LOG_H_
