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

#include "src/core/unpack_model.h"

#include <fstream>
#include <string>

#include "src/core/status_macros.h"
#include "absl/status/status.h"
#include "flatbuffers/util.h"

namespace falken {
namespace core {

namespace {

static absl::Status RecursivelyCreateDir(const std::string& dir) {
  flatbuffers::EnsureDirExists(dir);
  if (!flatbuffers::DirExists(dir.c_str())) {
    return absl::InternalError("Failed to create directory " + dir);
  }
  return absl::Status();
}

}  // namespace

absl::Status UnpackModel(const proto::SerializedModel& model,
                         const std::string& output_dir,
                         const std::string& model_subdir) {
  if (output_dir.empty()) {
    return absl::InvalidArgumentError("Output directory must be provided.");
  }
  if (model_subdir.empty()) {
    return absl::InvalidArgumentError("Model subdirectory must be provided.");
  }

  std::string model_dir =
      flatbuffers::ConCatPathFileName(output_dir, model_subdir);
  if (flatbuffers::FileExists(model_dir.c_str())) {
    return absl::InvalidArgumentError("Directory \"" + model_dir +
                                      "\" already exists. Models " +
                                      "must be unpacked to a new directory.");
  }
  FALKEN_RETURN_IF_ERROR(RecursivelyCreateDir(model_dir));

  for (const auto& it : model.packed_files_payload().files()) {
    const std::string& relative_file_path = it.first;
    const std::string& contents = it.second;

    std::string file_path =
        flatbuffers::ConCatPathFileName(model_dir, relative_file_path);
    std::string subdir_path = flatbuffers::StripFileName(file_path);
    FALKEN_RETURN_IF_ERROR(RecursivelyCreateDir(subdir_path));

    std::ofstream file(file_path, std::ofstream::out | std::ofstream::binary);
    file << contents;
    if (!file.good()) {
      return absl::InternalError("could not write to file \"" + file_path +
                                 "\"");
    }
    file.close();
    if (!file) {
      return absl::InternalError("could not write to file \"" + file_path +
                                 "\"");
    }
  }

  return absl::Status();
}

}  // namespace core
}  // namespace falken
