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

# Fetch SDL2.
include(FetchContent)
FetchContent_Declare(
  SDL2
  GIT_REPOSITORY https://github.com/libsdl-org/SDL.git
  # The release tag must be the same as the one used on the Java side
  # (see hello_falken/build.gradle).
  GIT_TAG release-2.0.14
  GIT_SHALLOW TRUE
  GIT_PROGRESS TRUE
)

FetchContent_GetProperties(SDL2)
if(NOT sdl2_POPULATED)
  FetchContent_Populate(SDL2)
endif()

# Change the name of the "uninstall" target in sdl to avoid
# a target name clash with a different target in Eigen
set(SDL2_CMAKELISTS_FILE "${sdl2_SOURCE_DIR}/CMakeLists.txt")
file(READ "${SDL2_CMAKELISTS_FILE}" SDL2_CMAKELISTS)
string(REPLACE
  "add_custom_target(uninstall"
  "add_custom_target(sdl2_uninstall"
  SDL2_CMAKELISTS
  "${SDL2_CMAKELISTS}"
)
file(WRITE "${SDL2_CMAKELISTS_FILE}" "${SDL2_CMAKELISTS}")

add_subdirectory(${sdl2_SOURCE_DIR} ${sdl2_BINARY_DIR})
