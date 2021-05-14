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

# grpc uses find_package for this package, so override the system installation
# and build from source instead.
include(protobuf)
if(protobuf_POPULATED)
  set(PROTOBUF_FOUND TRUE CACHE BOOL "protobuf found") # Requried for gRPC.
  set(PROTOBUF_LIBRARIES libprotobuf libprotoc CACHE STRING "protobuf libs")
  set(PROTOBUF_PROTOC_LIBRARIES protobuf::libprotoc CACHE STRING "protoc libs")
  set(PROTOBUF_PROJECT_DIR "${protobuf_SOURCE_DIR}" CACHE STRING
    "protobuf project directory"
  )
  set(PROTOBUF_INCLUDE_DIRS "${PROTOBUF_PROJECT_DIR}/src" CACHE STRING
    "protobuf source directory"
  )
  get_target_property(PROTOBUF_INCLUDE_DIRS libprotobuf INCLUDE_DIRECTORIES)
  add_executable(protobuf::protoc ALIAS protoc)
  add_library(protobuf::libprotoc ALIAS libprotoc)
  add_library(protobuf::libprotobuf ALIAS libprotobuf)
  add_library(protobuf::libprotobuf-lite ALIAS libprotobuf-lite)
endif()
