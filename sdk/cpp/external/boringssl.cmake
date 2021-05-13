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

if(TARGET bssl OR boringssl_POPULATED)
  return()
endif()

include(OverridableFetchContent)

OverridableFetchContent_Declare(
  boringssl
  GIT_REPOSITORY https://github.com/google/boringssl
  # Based on https://github.com/grpc/grpc/blob/v1.30.0/bazel/grpc_deps.bzl
  GIT_TAG 3ab047a8e377083a9b38dc908fe1612d5743a021
  # It's not currently (cmake 3.17) possible to shallow clone with a GIT TAG
  # as cmake attempts to git checkout the commit hash after the clone
  # which doesn't work as it's a shallow clone hence a different commit hash.
  # https://gitlab.kitware.com/cmake/cmake/-/issues/17770
  # GIT_SHALLOW TRUE
  GIT_PROGRESS TRUE
  SOURCE_DIR "${CMAKE_BINARY_DIR}/boringssl"
)
OverridableFetchContent_GetProperties(boringssl)
if(NOT boringssl_POPULATED)
  OverridableFetchContent_Populate(boringssl)
endif()

add_subdirectory(
  "${boringssl_SOURCE_DIR}"
  "${boringssl_BINARY_DIR}"
  EXCLUDE_FROM_ALL
)
