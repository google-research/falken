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

#ifndef FALKEN_SDK_CORE_TEMP_FILE_H_
#define FALKEN_SDK_CORE_TEMP_FILE_H_

#include <string>

namespace falken {

class LoggerBase;

namespace core {

// Creates and manages the lifetime of a temporary file / directory.
class TempFile {
 public:
  // Create a temporary file or directory named
  // system_temporary_directory/filename for the lifetime of this object.
  // If directory is true, a directory is created instead of an empty file. If
  // delete_on_destruction is true, the file or directory associated with this
  // object is deleted.
  explicit TempFile(LoggerBase& logger,
                    const std::string& filename,
                    bool create_directory = false,
                    bool delete_on_destruction = true) :
      logger_(logger),
      filename_(filename),
      create_directory_(create_directory),
      delete_on_destruction_(delete_on_destruction) {
  }

  // Delete the file or directory associated with this instance if the object
  // is marked for deletion on destruction.
  ~TempFile();

  // Try to create the temporary file or directory.
  bool Create();

  // Delete the temporary file or directory.
  void Delete();

  // Determine whether the temporary file or directory associated with this
  // object exists.
  bool exists() const;

  // Get the path to the created temporary file or directory, returning an empty
  // string if it couldn't be created.
  const std::string& path() const { return path_; }

  // Set the temporary directory to override the system temporary directory.
  // This must be set before calling Create().
  void SetTemporaryDirectory(const std::string& dir) {
    temporary_directory_ = dir;
  }

  // Get the temporary directory that contains this file / directory tree.
  const std::string& GetTemporaryDirectory();

  // Set / override the system temporary directory for subsequent TempFile
  // instances.
  static bool SetSystemTemporaryDirectory(LoggerBase& logger,
                                          const std::string& directory);

  // Get the system temporary directory.
  static std::string GetSystemTemporaryDirectory();

  // Setup the system temporary directory.
  static std::string SetupSystemTemporaryDirectory(LoggerBase& logger);

  // Create a directory and all intermediate directories.
  static bool CreateDir(const std::string& directory);

  // Delete a file or recursively delete a directory.
  static void Delete(LoggerBase& logger, const std::string& filename);

 private:
  LoggerBase& logger_;
  // File or directory to create under the temporary path.
  std::string filename_;
  // Directory containing the temporary file / directory tree.
  std::string temporary_directory_;
  bool create_directory_;
  bool delete_on_destruction_;
  // Absolute path to the temporary file / directory.
  std::string path_;
};

}  // namespace core
}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_TEMP_FILE_H_
