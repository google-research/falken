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

include(grpc)
if(grpc_POPULATED)
  set(GRPC_LIBRARIES grpc grpc++ CACHE STRING "gRPC libs")
  set(GRPC_PROJECT_DIR "${grpc_SOURCE_DIR}" CACHE STRING "gRPC source dir")
  get_target_property(GRPC_INCLUDE_DIRS grpc++ INCLUDE_DIRECTORIES)
  set(GRPC_INCLUDE_DIRS "${GRPC_INCLUDE_DIRS}" CACHE STRING
    "gRPC include dirs"
  )
  add_library(grpc::grpc ALIAS grpc)
  add_library(grpc::grpc++ ALIAS grpc++)
endif()
