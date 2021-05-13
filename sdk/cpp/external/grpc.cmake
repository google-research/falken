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

if(TARGET grpc OR grpc_POPULATED)
  return()
endif()

include(OverridableFetchContent)

# Fetch the sources and add as part of this project instead to disable
# the install target.
OverridableFetchContent_Declare(
  grpc
  GIT_REPOSITORY https://github.com/grpc/grpc
  GIT_TAG v1.30.0
  GIT_SHALLOW TRUE
  GIT_SUBMODULES "src" # https://gitlab.kitware.com/cmake/cmake/-/issues/20579
  GIT_PROGRESS TRUE
  SOURCE_DIR "${CMAKE_BINARY_DIR}/grpc"
)
OverridableFetchContent_GetProperties(grpc)
if(NOT grpc_POPULATED)
  OverridableFetchContent_Populate(grpc)
endif()

# Point gRPC at the downloaded dependencies.
set(gRPC_ABSL_PROVIDER "package" CACHE STRING "Use absl-config.cmake")
set(gRPC_SSL_PROVIDER "package" CACHE STRING "Use FindOpenSSL.cmake")
set(gRPC_CARES_PROVIDER "package" CACHE STRING "Use c-ares-config.cmake")
set(gRPC_PROTOBUF_PROVIDER "package" CACHE STRING "Use FindProtobuf.cmake")
set(gRPC_ZLIB_PROVIDER "package" CACHE STRING "Use FindZLIB.cmake")
# Set all other options.
set(gRPC_BUILD_TESTS OFF CACHE BOOL "Disable tests")
set(gRPC_INSTALL OFF CACHE BOOL "Disable install")

# Patch grpc with the location
set(GRPC_CMAKE_PROJECT_DIR "${CMAKE_CURRENT_LIST_DIR}/grpc")
set(GRPC_PATCHES_DIR "${GRPC_CMAKE_PROJECT_DIR}/patches")
file(GLOB_RECURSE GRPC_PATCHED_FILES
  LIST_DIRECTORIES NO
  RELATIVE "${GRPC_PATCHES_DIR}"
  "${GRPC_PATCHES_DIR}/*"
)
foreach(PATCHED_FILE ${GRPC_PATCHED_FILES})
  get_filename_component(OUTPUT_DIR "${PATCHED_FILE}" DIRECTORY)
  file(COPY "${GRPC_PATCHES_DIR}/${PATCHED_FILE}"
    DESTINATION "${grpc_SOURCE_DIR}/${OUTPUT_DIR}"
  )
endforeach()

add_subdirectory(
  "${grpc_SOURCE_DIR}"
  "${grpc_BINARY_DIR}"
  EXCLUDE_FROM_ALL
)

include(BuildHostBinary)
BuildHostBinary_Declare(
  VAR_NAME GRPC_CPP_PLUGIN
  TARGET_NAME grpc_cpp_plugin
  BASENAME grpc_cpp_plugin
  CMAKE_PROJECT "${grpc_SOURCE_DIR}"
  CMAKE_ARGS
    -DgRPC_ABSL_PROVIDER=${gRPC_ABSL_PROVIDER}
    -DgRPC_SSL_PROVIDER=${gRPC_SSL_PROVIDER}
    -DgRPC_CARES_PROVIDER=${gRPC_CARES_PROVIDER}
    -DgRPC_PROTOBUF_PROVIDER=${gRPC_PROTOBUF_PROVIDER}
    -DgRPC_ZLIB_PROVIDER=${gRPC_ZLIB_PROVIDER}
    -DgRPC_BUILD_TESTS=${gRPC_BUILD_TESTS}
    -DgRPC_INSTALL=${gRPC_INSTALL}
)
