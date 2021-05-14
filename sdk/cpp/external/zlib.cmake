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

if(TARGET zlib OR zlib_POPULATED)
  return()
endif()

include(OverridableFetchContent)

OverridableFetchContent_Declare(
  zlib
  GIT_REPOSITORY https://github.com/madler/zlib
  # Based on https://github.com/grpc/grpc/blob/v1.30.0/bazel/grpc_deps.bzl
  GIT_TAG v1.2.11 # cacf7f1d4e3d44d871b605da3b647f07d718623f
  GIT_SHALLOW TRUE
  GIT_PROGRESS TRUE
  SOURCE_DIR "${CMAKE_BINARY_DIR}/zlib"
  LICENSE_FILE "README"
)
OverridableFetchContent_GetProperties(zlib)
if(NOT zlib_POPULATED)
  OverridableFetchContent_Populate(zlib)
endif()

# Disable tests in the project.
if(NOT ZLIB_DISABLED_TESTS)
  set(ZLIB_CMAKELISTS_FILE "${zlib_SOURCE_DIR}/CMakeLists.txt")
  file(READ "${ZLIB_CMAKELISTS_FILE}" ZLIB_CMAKELISTS)
  string(REGEX REPLACE
    "([^#][\t\r\n ]*)(add_test\\([^\\)]+\\))"
    "\\1#\\2"
    ZLIB_CMAKELISTS
    "${ZLIB_CMAKELISTS}"
  )
  file(WRITE "${ZLIB_CMAKELISTS_FILE}" "${ZLIB_CMAKELISTS}")
endif()
set(ZLIB_DISABLED_TESTS ON CACHE BOOL "Disabled zlib tests.")

set(SKIP_INSTALL_ALL OFF CACHE BOOL "Skip install")
set(SKIP_INSTALL_HEADERS OFF CACHE BOOL "Skip install")
set(SKIP_INSTALL_FILES OFF CACHE BOOL "Skip install")

add_subdirectory(
  "${zlib_SOURCE_DIR}"
  "${zlib_BINARY_DIR}"
  EXCLUDE_FROM_ALL
)
