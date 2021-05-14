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

#include "src/core/temp_file.h"

#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>

#ifdef _MSC_VER
#include <direct.h>
#include <windows.h>
#else
#include <dirent.h>
#endif  // _MSC_VER

#include <utility>
#include <vector>

#ifdef __APPLE__
#import <Foundation/Foundation.h>
#endif  // __APPLE__

#include "falken/log.h"
#include "src/core/stdout_logger.h"
#include "absl/synchronization/mutex.h"
#include "flatbuffers/util.h"

namespace {

static std::string global_default_system_temporary_directory;       // NOLINT
static std::string global_user_defined_system_temporary_directory;  // NOLINT
// Guards global_default_system_temporary_directory and
// global_user_defined_system_temporary_directory.
static absl::Mutex global_system_temporary_directory_lock(absl::kConstInit);

// List files in a directory returning a list of absolute paths to files.
static std::vector<std::string> ListDirectory(falken::LoggerBase& logger,
                                              const std::string& directory) {
  std::vector<std::string> contents;
#if _MSC_VER
  WIN32_FIND_DATAA find_data;
  auto find_handle = FindFirstFileA(
      flatbuffers::ConCatPathFileName(directory, "*").c_str(),
      &find_data);
  if (INVALID_HANDLE_VALUE != find_handle) {
    do {
      std::string filename(find_data.cFileName);
      if (filename == "." || filename == "..") continue;
      contents.push_back(flatbuffers::ConCatPathFileName(directory, filename));
    } while (FindNextFile(find_handle, &find_data) != 0);
    FindClose(find_handle);
  } else {
    logger.LogError("Failed to enumerate directory %s (0x%08x)",
                    directory.c_str(), static_cast<int>(GetLastError()));
  }
#else
  auto* dir = opendir(directory.c_str());
  if (dir) {
    while (auto* entry = readdir(dir)) {
      std::string filename(entry->d_name);
      if (filename == "." || filename == "..") continue;
      contents.push_back(flatbuffers::ConCatPathFileName(directory, filename));
    }
    closedir(dir);
  } else {
    auto error = errno;
    logger.LogError("Failed to enumerate directory %s (%s %d)",
                    directory.c_str(), strerror(error), error);
  }
#endif  // _MSC_VER
  return contents;
}

}  // namespace

namespace falken {
namespace core {

TempFile::~TempFile() {
  if (delete_on_destruction_) Delete();
}

bool TempFile::CreateDir(const std::string& directory) {
  flatbuffers::EnsureDirExists(directory);
  return flatbuffers::DirExists(directory.c_str());
}

bool TempFile::Create() {
  if (!exists()) {
    const std::string& temporary_directory = GetTemporaryDirectory();
    if (temporary_directory.empty()) return false;

    std::string path = flatbuffers::ConCatPathFileName(temporary_directory,
                                                       filename_);
    if (create_directory_ && !CreateDir(path))  return false;
    path_ = flatbuffers::PosixPath(flatbuffers::AbsolutePath(path).c_str());
  }
  return true;
}

bool TempFile::exists() const {
  const std::string& path_to_check = path();
  if (path_to_check.empty()) return false;
  if (create_directory_) {
    if (!flatbuffers::DirExists(path_to_check.c_str())) return false;
  } else {
    if (!flatbuffers::FileExists(path_to_check.c_str())) return false;
  }
  return true;
}

void TempFile::Delete() {
  if (exists()) {
    Delete(logger_, path_);
    path_.clear();
  }
}

void TempFile::Delete(LoggerBase& logger, const std::string& filename) {
  if (flatbuffers::DirExists(filename.c_str())) {
    for (auto& it : ListDirectory(logger, filename)) {
      Delete(logger, it);
    }
    if (rmdir(filename.c_str()) != 0) {
      auto error = errno;
      logger.LogError("Failed to delete temporary directory %s (%s %d)",
                      filename.c_str(), strerror(error), error);
    }
  } else if (flatbuffers::FileExists(filename.c_str())) {
    if (unlink(filename.c_str()) != 0) {
      auto error = errno;
      logger.LogError("Failed to delete temporary file %s (%s %d)",
                      filename.c_str(), strerror(error), error);
    }
    return;
  }
}

bool TempFile::SetSystemTemporaryDirectory(LoggerBase& logger,
                                           const std::string& directory) {
  absl::MutexLock lock(&global_system_temporary_directory_lock);
  if (!global_default_system_temporary_directory.empty()) {
    logger.LogError(
        "Temporary directory has already been created in the default location "
        "for this system. Please set the desired temporary directory before "
        "connecting to the service.");
  }

  if (directory.empty()) {
    // Provides a way to unset the temporary directory.
    logger.LogDebug("Provided temporary directory is empty.");
    global_user_defined_system_temporary_directory = std::string();
  } else if (flatbuffers::DirExists(directory.c_str())) {
    global_user_defined_system_temporary_directory = directory;
  } else {
    logger.LogError("Provided temporary directory %s does not exist",
                    directory.c_str());
    return false;
  }
  return true;
}

std::string TempFile::GetSystemTemporaryDirectory() {
  absl::MutexLock lock(&global_system_temporary_directory_lock);
  if (!global_user_defined_system_temporary_directory.empty()) {
    return global_user_defined_system_temporary_directory;
  }

  return global_default_system_temporary_directory;
}

std::string TempFile::SetupSystemTemporaryDirectory(LoggerBase& logger) {
  absl::MutexLock lock(&global_system_temporary_directory_lock);
  if (!global_user_defined_system_temporary_directory.empty()) {
    return global_user_defined_system_temporary_directory;
  }

  // Check if FALKEN_TMPDIR environment variable is set with a valid directory.
  const char* falken_temporary_dir = getenv("FALKEN_TMPDIR");
  if (falken_temporary_dir) {
    if (flatbuffers::DirExists(falken_temporary_dir)) {
      global_user_defined_system_temporary_directory =
          std::string(falken_temporary_dir);
      return global_user_defined_system_temporary_directory;
    } else {
      logger.LogError(
          "Temporary directory %s provided via FALKEN_TMPDIR environment "
          "variable does not exist",
          falken_temporary_dir);
    }
  }

  if (!global_default_system_temporary_directory.empty()) {
    return global_default_system_temporary_directory;
  }

  std::vector<char> filename_buffer;
#ifdef _MSC_VER
  std::vector<char> path_buffer(MAX_PATH);
  auto len = GetTempPathA(MAX_PATH, &path_buffer[0]);
  DWORD error = 0;
  if (len != 0 && len <= MAX_PATH) {
    filename_buffer.resize(MAX_PATH, '\0');
    if (GetTempFileNameA(&path_buffer[0], "falken", 0, &filename_buffer[0]) !=
        0) {
      // Delete the temporary file and create a directory of the same name.
      std::string temporary_dir(&filename_buffer[0]);
      Delete(logger, temporary_dir);
      if (!CreateDir(temporary_dir)) {
        error = ENOENT;
        logger.LogError("Failed to create directory %s", temporary_dir.c_str());
      }
    } else {
      error = GetLastError();
      logger.LogError("Unable to get temporary filename in %s (error=0x%08x)",
                      &path_buffer[0], static_cast<int>(error));
    }
  } else {
    error = GetLastError();
    logger.LogError("Failed to get temporary directory (error=0x%08x)",
                    static_cast<int>(error));
  }
  if (error) {
    return global_default_system_temporary_directory;
  }
#else
  const char* temporary_dir = nullptr;
#if defined(__APPLE__)
  NSString* temporary_dir_string = NSTemporaryDirectory();
  // Trim the trailing / if it's present.
  if ([temporary_dir_string hasSuffix:@"/"]) {
    temporary_dir_string =
        [temporary_dir_string substringToIndex:temporary_dir_string.length - 1];
  }
  temporary_dir = temporary_dir_string.UTF8String;
#else
  temporary_dir = getenv("TMPDIR");
#if defined(P_tmpdir)  // Provided by glibc.
  if (!temporary_dir) temporary_dir = P_tmpdir;
#endif                 // defined(P_tmpdir)
#endif
  if (!temporary_dir) {
    temporary_dir = "/tmp";
    logger.LogDebug(
        "Using %s as the root temporary directory as "
        "NSTemporaryDirectory (macOS), TMPDIR & P_tmpdir (Linux) "
        "returned no value.",
        temporary_dir);
  }

  static const char template_dir[] = "falken.XXXXXX";
  filename_buffer.assign(temporary_dir, temporary_dir + strlen(temporary_dir));
  filename_buffer.push_back('/');
  filename_buffer.insert(filename_buffer.end(), template_dir,
                         &template_dir[sizeof(template_dir)]);

  if (!CreateDir(temporary_dir) || mkdtemp(&filename_buffer[0]) == nullptr) {
    auto error = errno;
    logger.LogError("Failed to create temporary directory %s (error=%s, %d)",
                    &filename_buffer[0], strerror(error), error);
    return global_default_system_temporary_directory;
  }
#endif  // _MSC_VER
  global_default_system_temporary_directory.assign(&filename_buffer[0]);
  global_default_system_temporary_directory =
      flatbuffers::PosixPath(global_default_system_temporary_directory.c_str());

  // Delete the temporary directory when the application gracefully exits.
  // If the application fires an unhandled signal the temporary directory
  // isn't cleaned up.
  atexit([]() {
    absl::MutexLock lock(&global_system_temporary_directory_lock);
    if (!global_default_system_temporary_directory.empty()) {
      StandardOutputErrorLogger logger;
      TempFile::Delete(logger, global_default_system_temporary_directory);
      global_default_system_temporary_directory.clear();
    }
  });

  return global_default_system_temporary_directory;
}

const std::string& TempFile::GetTemporaryDirectory() {
  if (temporary_directory_.empty()) {
    temporary_directory_ = SetupSystemTemporaryDirectory(logger_);
  }
  return temporary_directory_;
}

}  // namespace core
}  // namespace falken
