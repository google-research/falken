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

# protobuf and grpc use find_package for this package, so override the system
# installation and build from source instead.
include(zlib)
if(zlib_POPULATED)
  get_target_property(ZLIB_INCLUDE_DIRS zlibstatic INCLUDE_DIRECTORIES)
  list(APPEND ZLIB_INCLUDE_DIRS "${zlib_SOURCE_DIR}")
  set(ZLIB_INCLUDE_DIRS "${ZLIB_INCLUDE_DIRS}" CACHE STRING "zlib include dirs")
  add_library(ZLIB::ZLIB ALIAS zlibstatic)
  # protobuf has install targets that require zlib to be installed.
  install(TARGETS zlib zlibstatic EXPORT zlib-targets)
  install(EXPORT zlib-targets DESTINATION "${zlib_BINARY_DIR}"
    NAMESPACE ZLIB::
  )
  export(TARGETS zlib zlibstatic
    NAMESPACE ZLIB::
    FILE ${zlib_BINARY_DIR}/zlib-targets.cmake
  )
endif()
