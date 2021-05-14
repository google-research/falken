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

if(googleapis_POPULATED)
  return()
endif()

include(OverridableFetchContent)

OverridableFetchContent_Declare(
  googleapis
  GIT_REPOSITORY https://github.com/googleapis/googleapis
  # Referenced by gRPC 1.30.0
  GIT_TAG 80ed4d0bbf65d57cc267dfc63bd2584557f11f9b
  # It's not currently (cmake 3.17) possible to shallow clone with a GIT TAG
  # as cmake attempts to git checkout the commit hash after the clone
  # which doesn't work as it's a shallow clone hence a different commit hash.
  # https://gitlab.kitware.com/cmake/cmake/-/issues/17770
  # GIT_SHALLOW TRUE
  GIT_PROGRESS TRUE
  SOURCE_DIR "${CMAKE_BINARY_DIR}/googleapis"
)
OverridableFetchContent_GetProperties(googleapis)
if(NOT googleapis_POPULATED)
  OverridableFetchContent_Populate(googleapis)
endif()

# Generate library for RPC protos.
find_package(Protobuf REQUIRED)

set(GOOGLEAPIS_RPC_PROTOS
  "${googleapis_SOURCE_DIR}/google/rpc/code.proto"
  "${googleapis_SOURCE_DIR}/google/rpc/error_details.proto"
  "${googleapis_SOURCE_DIR}/google/rpc/status.proto"
)
set(GOOGLEAPIS_GENERATED_SRCS_DIR "${googleapis_BINARY_DIR}/generated_srcs")

file(MAKE_DIRECTORY "${GOOGLEAPIS_GENERATED_SRCS_DIR}")
set(GOOGLEAPIS_GENERATED_SRCS
  "${GOOGLEAPIS_GENERATED_SRCS_DIR}/google/rpc/code.pb.cc"
  "${GOOGLEAPIS_GENERATED_SRCS_DIR}/google/rpc/code.pb.h"
  "${GOOGLEAPIS_GENERATED_SRCS_DIR}/google/rpc/error_details.pb.cc"
  "${GOOGLEAPIS_GENERATED_SRCS_DIR}/google/rpc/error_details.pb.h"
  "${GOOGLEAPIS_GENERATED_SRCS_DIR}/google/rpc/status.pb.cc"
  "${GOOGLEAPIS_GENERATED_SRCS_DIR}/google/rpc/status.pb.h"
)
add_custom_command(
  OUTPUT
    ${GOOGLEAPIS_GENERATED_SRCS}
  COMMAND "${PROTOC_HOST}"
    "--cpp_out=${GOOGLEAPIS_GENERATED_SRCS_DIR}"
    "--proto_path=${googleapis_SOURCE_DIR}"
    "--proto_path=${PROTOBUF_PROJECT_DIR}/src"
    ${GOOGLEAPIS_RPC_PROTOS}
  DEPENDS "${PROTOC_HOST_TARGET}"
)
add_library(googleapis_rpc EXCLUDE_FROM_ALL ${GOOGLEAPIS_GENERATED_SRCS})
target_link_libraries(googleapis_rpc
  PUBLIC
    protobuf::libprotobuf
    protobuf::libprotobuf-lite
)
target_include_directories(googleapis_rpc
  PUBLIC
    "${GOOGLEAPIS_GENERATED_SRCS_DIR}"
)
