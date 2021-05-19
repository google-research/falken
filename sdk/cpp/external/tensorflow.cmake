# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

if(TARGET tflite OR tensorflow_POPULATED)
  return()
endif()

include(OverridableFetchContent)

# Fetch the sources and add as part of this project instead to disable
# the install target.
OverridableFetchContent_Declare(
  tensorflow
  GIT_REPOSITORY https://github.com/tensorflow/tensorflow.git
  # Update DL dependency in tflite cmake files
  GIT_TAG cf8e67c4f33b587189f018b019b1c2517ba5e56d
  # It's not currently possible to shallow clone with a GIT TAG
  # as cmake attempts to git checkout the commit hash after the clone
  # which doesn't work as it's a shallow clone hence a different commit hash.
  # https://gitlab.kitware.com/cmake/cmake/-/issues/20579
  # GIT_SHALLOW TRUE
  GIT_SUBMODULES "tensorflow"
  GIT_PROGRESS TRUE
  SOURCE_DIR "${CMAKE_BINARY_DIR}/tensorflow"
)
option(TFLITE_ENABLE_XNNPACK "Enable XNNPACK backend" OFF) # TODO: Add XNNPACK
OverridableFetchContent_GetProperties(tensorflow)
if(NOT tensorflow_POPULATED)
  OverridableFetchContent_Populate(tensorflow)
endif()

add_subdirectory("${tensorflow_SOURCE_DIR}/tensorflow/lite"
 "${tensorflow_BINARY_DIR}" EXCLUDE_FROM_ALL
 )
