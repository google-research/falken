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

#include <string.h>

#include <fstream>
#include <string>

#include "falken/log.h"
#include "absl/synchronization/mutex.h"
#include "flatbuffers/util.h"

namespace falken {

// Implementation of FileLogger.
class FileLoggerInternal {
 public:
  // Log to the current file.
  void Log(const char* message);

  // Set the current log filename to open / close the log file.
  bool set_filename(const char* filename);

  // Get the path of the currently opened file.
  String filename() const;

 private:
  // Guards operations on this class.
  mutable absl::Mutex mutex_;
  std::ofstream file_;
  std::string filename_;
};

void FileLoggerInternal::Log(const char* message) {
  absl::MutexLock lock(&mutex_);
  if (file_.is_open()) {
    file_ << message << "\n";
    file_.flush();
  }
}

bool FileLoggerInternal::set_filename(const char* filename) {
  absl::MutexLock lock(&mutex_);
  bool filename_changed = !filename || filename != filename_;
  if (filename_changed) {
    if (file_.is_open()) {
      file_.close();
      filename_.clear();
    }
    if (filename && strlen(filename)) {
      filename_ = filename;
      std::string directory = flatbuffers::StripFileName(filename_);
      if (!directory.empty()) flatbuffers::EnsureDirExists(directory);
      file_.open(filename_, std::ofstream::out | std::ofstream::app);
    }
  }
  return file_.is_open();
}

String FileLoggerInternal::filename() const {
  absl::MutexLock lock(&mutex_);
  return filename_.c_str();
}

FileLogger::FileLogger() { internal_ = new FileLoggerInternal(); }
FileLogger::~FileLogger() { delete internal_; }

void FileLogger::Log(LogLevel log_level, const char* message) {
  if (ShouldLog(log_level)) internal_->Log(message);
}

bool FileLogger::set_filename(const char* filename) {
  return internal_->set_filename(filename);
}

String FileLogger::filename() const { return internal_->filename(); }

}  // namespace falken
