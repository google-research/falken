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

#include <map>

#include "falken/log.h"
#include "absl/synchronization/mutex.h"

namespace {

// Logger that wraps a callback and some context.
class CallbackLogger : public falken::LoggerBase {
 public:
  CallbackLogger(falken::LogCallback callback, void* context)
      : callback_(callback), context_(context) {}

  void Log(falken::LogLevel log_level, const char* message) override {
    callback_(log_level, message, context_);
  }

 private:
  falken::LogCallback callback_;
  void* context_;
};

}  // namespace

namespace falken {

class LoggerNotifierInternal {
 private:
  struct LoggerReference {
    LoggerReference(LoggerBase* logger_, bool deallocate_)
        : logger(logger_), deallocate(deallocate_) {}

    LoggerReference() = default;
    LoggerReference(const LoggerReference&) = default;
    LoggerReference& operator=(const LoggerReference& other) = default;

    LoggerBase* logger;
    // true if the logger is owned by this object.
    bool deallocate;
  };

 public:
  explicit LoggerNotifierInternal(LoggerNotifier& notifier)
      : notifier_(&notifier), next_handle_(0) {}
  // Remove all references to this notifier.
  ~LoggerNotifierInternal();

  // Get the next handle to assign a logger.
  LoggerNotifier::Handle CreateHandle();

  // Add a logger to this notifier.
  LoggerNotifier::Handle AddLogger(LoggerBase& logger,
                                   bool deallocate_on_remove);

  // Add a log callback to this notifier.
  LoggerNotifier::Handle AddLogCallback(LogCallback callback, void* context);

  // Remove a logger from this notifier.
  void RemoveLogger(LoggerBase& logger);
  void RemoveLogger(unsigned int handle);

  // Notify registered loggers.
  bool Notify(LogLevel log_level, const char* message) const;

  // Attach to a new notifier.
  void ReplaceNotifier(LoggerNotifier& notifier);

 private:
  // This should only be called if mutex_ is already held.
  void RemoveLoggerUnsafe(LoggerBase& logger);

 private:
  mutable absl::Mutex mutex_;  // Guards all operations in this object.
  std::map<LoggerNotifier::Handle, LoggerReference> logger_by_handle_;
  LoggerNotifier* notifier_;
  LoggerNotifier::Handle next_handle_;
};

LoggerNotifierInternal::~LoggerNotifierInternal() {
  absl::MutexLock lock(&mutex_);
  while (!logger_by_handle_.empty()) {
    RemoveLoggerUnsafe(*logger_by_handle_.begin()->second.logger);
  }
}

LoggerNotifier::Handle LoggerNotifierInternal::CreateHandle() {
  do {
    next_handle_++;
  } while (next_handle_ == 0);
  return next_handle_;
}

unsigned int LoggerNotifierInternal::AddLogger(LoggerBase& logger,
                                               bool deallocate_on_remove) {
  absl::MutexLock lock(&mutex_);
  // Logger has already been added to a notifier.
  if (logger.notifier_) return 0;
  int handle = CreateHandle();
  logger.notifier_ = notifier_;
  logger.notifier_handle_ = handle;
  logger_by_handle_[handle] = LoggerReference(&logger, deallocate_on_remove);
  return handle;
}

void LoggerNotifierInternal::RemoveLoggerUnsafe(LoggerBase& logger) {
  // If the logger isn't in this notifier ignore.
  if (logger.notifier_ != notifier_) return;
  // Remove the logger from the map.
  auto it = logger_by_handle_.find(logger.notifier_handle_);
  if (it == logger_by_handle_.end()) return;
  logger.notifier_ = nullptr;
  logger.notifier_handle_ = 0;
  // Optionally delete the logger.
  if (it->second.deallocate) delete it->second.logger;
  logger_by_handle_.erase(it);
}

void LoggerNotifierInternal::RemoveLogger(LoggerBase& logger) {
  absl::MutexLock lock(&mutex_);
  RemoveLoggerUnsafe(logger);
}

void LoggerNotifierInternal::RemoveLogger(LoggerNotifier::Handle handle) {
  absl::MutexLock lock(&mutex_);
  auto it = logger_by_handle_.find(handle);
  if (it == logger_by_handle_.end()) return;
  RemoveLoggerUnsafe(*it->second.logger);
}

LoggerNotifier::Handle LoggerNotifierInternal::AddLogCallback(
    LogCallback callback, void* context) {
  auto* logger = new CallbackLogger(callback, context);
  return AddLogger(*logger, true);
}

bool LoggerNotifierInternal::Notify(LogLevel log_level,
                                    const char* message) const {
  absl::MutexLock lock(&mutex_);
  for (const auto& it : logger_by_handle_) {
    it.second.logger->Log(log_level, message);
  }
  return !logger_by_handle_.empty();
}

void LoggerNotifierInternal::ReplaceNotifier(LoggerNotifier& notifier) {
  // The source notifier lock isn't acquired to avoid a potential deadlock
  // also if the source is being moved from, it should be in a state where
  // nothing is calling it.
  absl::MutexLock target_lock(&mutex_);

  auto& source_notifier = *notifier_;
  auto& target_notifier = notifier;

  // Move this LoggerNotifierInternal to the target_notifier.
  delete target_notifier.internal_;
  target_notifier.internal_ = this;
  notifier_ = &target_notifier;
  for (auto& it : logger_by_handle_) {
    it.second.logger->notifier_ = &target_notifier;
  }

  // Reset the original notifier attached to this object.
  source_notifier.internal_ = new LoggerNotifierInternal(source_notifier);
}

LoggerNotifier::LoggerNotifier() {
  internal_ = new LoggerNotifierInternal(*this);
}

LoggerNotifier::~LoggerNotifier() { delete internal_; }

bool LoggerNotifier::AddLogger(LoggerBase& logger) {
  return internal_->AddLogger(logger, false) != 0;
}

void LoggerNotifier::RemoveLogger(LoggerBase& logger) {
  internal_->RemoveLogger(logger);
}

LoggerNotifier::Handle LoggerNotifier::AddLogCallback(LogCallback log_callback,
                                                      void* context) {
  return internal_->AddLogCallback(log_callback, context);
}

void LoggerNotifier::RemoveLogCallback(LoggerNotifier::Handle handle) {
  internal_->RemoveLogger(handle);
}

bool LoggerNotifier::Notify(LogLevel log_level, const char* message) const {
  return internal_->Notify(log_level, message);
}

LoggerNotifier& LoggerNotifier::operator=(LoggerNotifier&& other) {
  other.internal_->ReplaceNotifier(*this);
  return *this;
}

}  // namespace falken
