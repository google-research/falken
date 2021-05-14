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

# Generates a target which recursively builds the specified target with the
# host toolchain when cross compiling. To use the binary depend upon
# the specified VAR_NAME, e.g where HOST_BINARY is passed to this function as
# VAR_NAME:
#
# add_custom_command(OUTPUT ... COMMAND ${HOST_BINARY} DEPENDS ${HOST_BINARY})
#
# VAR_NAME: Name of cache variable set by this function that references built
# binary path.
# TARGET_NAME: Binary target to build.
# BASENAME: Basename of the binary (filename excluding the extension)
# built by BINARY_TARGET_NAME.
# CMAKE_PROJECT: Path to the CMake project that builds the binary.
# CMAKE_ARGS [args]: Takes a list of arguments to pass to CMake when cross
# compiling.
function(BuildHostBinary_Declare)
  set(OPTIONS "")
  set(ONE_VALUE_OPTIONS VAR_NAME TARGET_NAME BASENAME CMAKE_PROJECT)
  set(MULTI_VALUE_OPTIONS CMAKE_ARGS)
  cmake_parse_arguments(ARGS
    "${OPTIONS}"
    "${ONE_VALUE_OPTIONS}"
    "${MULTI_VALUE_OPTIONS}"
    ${ARGN}
  )
  if(CMAKE_CROSSCOMPILING)
    set(BUILD_DIR "${CMAKE_BINARY_DIR}/host/${ARGS_TARGET_NAME}")
    set(BINARY_DIR "${BUILD_DIR}/bin")
    set(BINARY "${BINARY_DIR}/${ARGS_BASENAME}${CMAKE_EXECUTABLE_SUFFIX}")
    add_custom_command(
      OUTPUT "${BINARY}"
      COMMAND ${CMAKE_COMMAND}
        -E make_directory "${BUILD_DIR}"
      COMMAND ${CMAKE_COMMAND}
        ${ARGS_CMAKE_ARGS}
        -DCMAKE_BUILD_TYPE=Release
        -DCMAKE_RUNTIME_OUTPUT_DIRECTORY_RELEASE="${BINARY_DIR}"
        -DCMAKE_MODULE_PATH="${CMAKE_CURRENT_LIST_DIR}"
        -DCMAKE_PREFIX_PATH="${CMAKE_CURRENT_LIST_DIR}"
        -S "${ARGS_CMAKE_PROJECT}"
        -B "${BUILD_DIR}"
      COMMAND ${CMAKE_COMMAND}
        --build "${BUILD_DIR}"
        --target "${ARGS_TARGET_NAME}"
        --config Release
    )
    add_custom_target(${ARGS_TARGET_NAME}_host DEPENDS "${BINARY}")
    set(${ARGS_VAR_NAME} "${BINARY}" CACHE STRING
      "Path to ${ARGS_TARGET_NAME}"
    )
    set(${ARGS_VAR_NAME}_TARGET "${ARGS_TARGET_NAME}_host" CACHE STRING
      "Target name to make ${ARGS_VAR_NAME}"
    )
  else()
    set(${ARGS_VAR_NAME} "$<TARGET_FILE:${ARGS_TARGET_NAME}>" CACHE STRING
      "Path to ${ARGS_TARGET_NAME}"
    )
    set(${ARGS_VAR_NAME}_TARGET "${ARGS_TARGET_NAME}" CACHE STRING
      "Target name to make ${ARGS_VAR_NAME}"
    )
  endif()
endfunction()
