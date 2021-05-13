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

if(SWIG_VERSION STREQUAL "" OR NOT DEFINED SWIG_VERSION)
  set(SWIG_VERSION "4.0.2")
endif()

set(SWIG_DIR_INTERNAL "${SWIG_INSTALL_DIRECTORY}")

# SWIG_EXECUTABLE is set by FindSWIG.cmake if SWIG has already been found.
if(SWIG_DIR_INTERNAL STREQUAL "" AND SWIG_EXECUTABLE STREQUAL "")
  set(SWIG_DOWNLOAD_LINK "")
  if(CMAKE_HOST_SYSTEM_NAME MATCHES "Windows")
    set(SWIG_DOWNLOAD_LINK
      "https://sourceforge.net/projects/swig/files/swigwin/swigwin-${SWIG_VERSION}/swigwin-${SWIG_VERSION}.zip/download")
  else()
    set(SWIG_DOWNLOAD_LINK
      "https://github.com/swig/swig/archive/v${SWIG_VERSION}.tar.gz")
  endif()

  include(FetchContent)

  FetchContent_Declare(
    swig
    URL ${SWIG_DOWNLOAD_LINK}
    SOURCE_DIR "${CMAKE_BINARY_DIR}/swig/src"
    UPDATE_COMMAND ""
    CONFIGURE_COMMAND ""
    BUILD_COMMAND ""
    INSTALL_COMMAND ""
    TEST_COMMAND ""
  )

  FetchContent_GetProperties(swig)
  if(NOT swig_POPULATED)
    FetchContent_Populate(swig)
  endif()

  set(SWIG_DIR_INTERNAL ${swig_SOURCE_DIR})

  # Patch Mono AOT directors compatibility
  # https://github.com/swig/swig/pull/1262
  set(SWIG_CMAKE_PROJECT_DIR "${CMAKE_CURRENT_LIST_DIR}/swig")
  set(SWIG_PATCHES_DIR "${SWIG_CMAKE_PROJECT_DIR}/patches")
  file(GLOB_RECURSE SWIG_PATCHED_FILES
    LIST_DIRECTORIES NO
    RELATIVE "${SWIG_PATCHES_DIR}"
    "${SWIG_PATCHES_DIR}/*"
  )
  foreach(PATCHED_FILE ${SWIG_PATCHED_FILES})
    get_filename_component(OUTPUT_DIR "${PATCHED_FILE}" DIRECTORY)
    file(COPY "${SWIG_PATCHES_DIR}/${PATCHED_FILE}" DESTINATION
      "${swig_SOURCE_DIR}/${OUTPUT_DIR}"
    )
  endforeach()
endif()

# If SWIG is installed in SWIG_DIR_INTERAL but SWIG_EXECUTABLE isn't set,
# set SWIG_EXECUTABLE to the path of the SWIG executable and configure
# the SWIG CMake module to configure variables for SWIG build commands.
if(NOT "${SWIG_DIR_INTERNAL}" STREQUAL "" AND SWIG_EXECUTABLE STREQUAL "")
  if(CMAKE_HOST_SYSTEM_NAME MATCHES "Windows")
    set(SWIG_EXECUTABLE "${SWIG_DIR_INTERNAL}/swig.exe" CACHE STRING "" FORCE)
  else()
    set(SWIG_SCRIPT_PATH ${CMAKE_CURRENT_LIST_DIR}/swig/install_swig.sh)
    set(SWIG_INSTALLATION_PATH ${SWIG_DIR_INTERNAL}/installation_swig)
    if(CMAKE_CROSSCOMPILING)
      # Do not use the cross compiler to build SWIG.
      set(ORIGINAL_CC $ENV{CC})
      set(ORIGINAL_CXX $ENV{CXX})
      unset(ENV{CC})
      unset(ENV{CXX})
    endif()
    execute_process(
      COMMAND
      ${SWIG_SCRIPT_PATH} ${SWIG_DIR_INTERNAL} ${SWIG_INSTALLATION_PATH}
      RESULT_VARIABLE SWIG_INSTALL_RESULT)
    if (NOT ${SWIG_INSTALL_RESULT} EQUAL 0)
      message(FATAL_ERROR
        "SWIG could not be installed. Ensure that you have installed pcre")
    endif()
    set(SWIG_EXECUTABLE "${SWIG_INSTALLATION_PATH}/bin/swig" CACHE STRING ""
      FORCE
    )
    if(CMAKE_CROSSCOMPILING)
      set(ENV{CC} "${ORIGINAL_CC}")
      set(ENV{CXX} "${ORIGINAL_CXX}")
    endif()
  endif()
  # Initialize the SWIG module from SWIG_EXECUTABLE.
  find_package(SWIG REQUIRED)
endif()
