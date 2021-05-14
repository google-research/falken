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

if(TARGET c-ares OR c-ares_POPULATED)
  return()
endif()

include(OverridableFetchContent)

# Include the version number and convert to a git tag.
include(c-ares-configVersion)
string(REPLACE "." "_" C_ARES_GIT_TAG "${PACKAGE_VERSION}")

OverridableFetchContent_Declare(
  c-ares
  GIT_REPOSITORY https://github.com/c-ares/c-ares
  # Based on https://github.com/grpc/grpc/blob/v1.30.0/bazel/grpc_deps.bzl
  GIT_TAG "cares-${C_ARES_GIT_TAG}" # e982924acee7f7313b4baa4ee5ec000c5e373c30
  GIT_SHALLOW TRUE
  GIT_PROGRESS TRUE
  PREFIX "${CMAKE_BINARY_DIR}"
  SOURCE_DIR "${CMAKE_BINARY_DIR}/c-ares"
)
OverridableFetchContent_GetProperties(c-ares)
if(NOT c-ares_POPULATED)
  OverridableFetchContent_Populate(c-ares)
endif()

set(CARES_STATIC ON CACHE BOOL "Enable static library build")
set(CARES_SHARED OFF CACHE BOOL "Disable shared library build")
set(CARES_INSTALL OFF CACHE BOOL "Disable installation")
set(CARES_STATIC_PIC OFF CACHE BOOL "Disable position independent code")
set(CARES_BUILD_TESTS OFF CACHE BOOL "Disable tests")
set(CARES_BUILD_TOOLS OFF CACHE BOOL "Disable tools")
add_subdirectory("${c-ares_SOURCE_DIR}" "${c-ares_BINARY_DIR}"
  EXCLUDE_FROM_ALL
)
