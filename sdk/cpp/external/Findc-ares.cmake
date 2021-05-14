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
include(c-ares)
if(c-ares_POPULATED)
  set(CARES_LIBRARIES c-ares CACHE STRING "c-ares libs")
  get_target_property(CARES_INCLUDE_DIRS c-ares INCLUDE_DIRECTORIES)
  set(CARES_INCLUDE_DIRS ${CARES_INCLUDE_DIRS} CACHE STRING
    "c-ares include dirs"
  )
  add_library(c-ares::cares ALIAS c-ares)
endif()
