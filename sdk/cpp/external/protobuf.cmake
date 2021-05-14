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

if(TARGET libprotobuf OR protobuf_POPULATED)
  return()
endif()

include(OverridableFetchContent)

OverridableFetchContent_Declare(
  protobuf
  GIT_REPOSITORY https://github.com/protocolbuffers/protobuf
  # Fixes Android build error due to missing `__android_log_write` symbol.
  # See https://github.com/protocolbuffers/protobuf/issues/2719 and
  # https://github.com/protocolbuffers/protobuf/pull/7288.
  GIT_TAG v3.14.0
  GIT_SHALLOW TRUE
  GIT_SUBMODULES "src" # https://gitlab.kitware.com/cmake/cmake/-/issues/20579
  GIT_PROGRESS TRUE
  SOURCE_DIR "${CMAKE_BINARY_DIR}/protobuf"
)
OverridableFetchContent_GetProperties(protobuf)
if(NOT protobuf_POPULATED)
  OverridableFetchContent_Populate(protobuf)
endif()

set(protobuf_BUILD_TESTS OFF CACHE BOOL "Disable protobuf tests")
set(protobuf_BUILD_CONFORMANCE OFF CACHE BOOL "Disable conformance tests")
set(protobuf_BUILD_EXAMPLES OFF CACHE BOOL "Disable examples")
set(protobuf_BUILD_PROTOC_BINARIES ON CACHE BOOL
  "Build libprotoc and protoc compiler"
)
set(protobuf_WITH_ZLIB ON CACHE BOOL "Build with zlib support")

add_subdirectory(
  "${protobuf_SOURCE_DIR}/cmake"
  "${protobuf_BINARY_DIR}"
  EXCLUDE_FROM_ALL
)

include(BuildHostBinary)
BuildHostBinary_Declare(
  VAR_NAME PROTOC_HOST
  TARGET_NAME protoc
  BASENAME protoc
  CMAKE_PROJECT "${protobuf_SOURCE_DIR}/cmake"
  CMAKE_ARGS
    -Dprotobuf_BUILD_TESTS=${protobuf_BUILD_TESTS}
    -Dprotobuf_BUILD_CONFORMANCE=${protobuf_BUILD_CONFORMANCE}
    -Dprotobuf_BUILD_EXAMPLES=${protobuf_BUILD_EXAMPLES}
    -Dprotobuf_BUILD_PROTOC_BINARIES=ON
    -Dprotobuf_WITH_ZLIB=ON
)
