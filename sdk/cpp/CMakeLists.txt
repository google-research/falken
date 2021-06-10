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

cmake_minimum_required(VERSION 3.17.2)

project(falken_cpp_sdk)

set(SWIG_INSTALL_DIRECTORY "" CACHE PATH
  "Path to override SWIG's installation directory."
)

set(FALKEN_CPP_SDK_SRC_DIR "${CMAKE_CURRENT_LIST_DIR}" CACHE PATH
  "Path to C++ SDK source."
)
set(FALKEN_SDK_VERSION "0.0.1" CACHE STRING
  "Version of the SDK being built."
)
set(FALKEN_LOCAL_CERT "" CACHE STRING
  "Path to cert to use for connection to the local service."
)
set(FALKEN_JSON_CONFIG_FILE "" CACHE STRING
  "JSON configuration file for integration tests."
)

# NOTE: FALKEN_SDK_TARGET is a cache variable so that it can be accessed
# by cpack.
set(FALKEN_SDK_TARGET "${CMAKE_SYSTEM_NAME}" CACHE STRING "" FORCE)

# Get the root directory of the project.
if("${FALKEN_PROJECT_ROOT_DIR}" STREQUAL "")
  get_filename_component(FALKEN_PROJECT_ROOT_DIR
    "${CMAKE_CURRENT_LIST_DIR}/../.."
    REALPATH
  )
endif()

# Disable test app build on Android systems.
if(CMAKE_SYSTEM_NAME MATCHES "Android")
  set(DEFAULT_BUILD_TESTAPP OFF)
else()
  set(DEFAULT_BUILD_TESTAPP ON)
endif()
option(FALKEN_CPP_SDK_BUILD_TESTAPP "Whether to build the test application."
  ${DEFAULT_BUILD_TESTAPP}
)
# SWIG/code generation options.
option(FALKEN_CPP_SDK_CSHARP OFF "Generate C# bindings.")
set(SWIG_VERSION "4.0.2" CACHE STRING "SWIG Version")
set(SWIG_EXECUTABLE "")
# Tools
# Configure Python binary using the PYTHON variable.
if(CMAKE_SYSTEM_NAME MATCHES "Windows")
  set(DEFAULT_PYTHON "python")
else()
  set(DEFAULT_PYTHON "python3")
endif()
set(PYTHON "${DEFAULT_PYTHON}" CACHE STRING
  "Python executable to use."
)

# Repo cloning options.
option(CLONE_GIT_REPOS "Clone git repos instead of downloading archives." OFF)

include(FetchContent)
set(FETCHCONTENT_QUIET OFF)

# Install absl-py for the build scripts.
execute_process(
  COMMAND "${PYTHON}" -m pip install --user absl-py
)

# Set the version string.
if("${FALKEN_SDK_VERSION}" STREQUAL "")
  set(FALKEN_CPP_SDK_VERSION "0.0.0")
else()
  set(FALKEN_CPP_SDK_VERSION "${FALKEN_SDK_VERSION}")
endif()

get_filename_component(FALKEN_CPP_SDK_SRC_DIR "${FALKEN_CPP_SDK_SRC_DIR}"
  REALPATH
)
set(FALKEN_CPP_SDK_SRC_DIR "${FALKEN_CPP_SDK_SRC_DIR}" CACHE STRING "" FORCE)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Since we're building a dynamic / shared library, build everything with
# position independent code.
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
# Ensure that every static library hide their symbols and just
# export any symbol that falken_sdk_cpp explicitly exported.
set(CMAKE_CXX_VISIBILITY_PRESET hidden)
set(CMAKE_VISIBILITY_INLINES_HIDDEN 1)
# See https://cmake.org/cmake/help/v3.3/policy/CMP0063.html.
# Needed so external dependencies (protobuf and flatbuffers)
# hide symbols properly.
set(CMAKE_POLICY_DEFAULT_CMP0063 NEW)

# Set output directories.
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/build/lib")
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/build/lib")
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/build/bin")

# Add the external cmake subdirectory to the list of directories to search for
# packages to include when using find_package() for both
# Find<PackageName>.cmake and <PackageName>-config.cmake files.
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/external")
list(APPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}/external")

# Optionally fetch downloadable archives instead of cloning git repos.
include(OverridableFetchContent)
if(NOT ${CLONE_GIT_REPOS})
  set(OVERRIDABLE_FETCH_CONTENT_GIT_REPOSITORY_AND_TAG_TO_URL ON)
endif()
# Make sure all repos have licenses.
set(OVERRIDABLE_FETCH_CONTENT_LICENSE_CHECK ON)

# Use the Eigen mirror so it's possible to point to a stable archive URL
# in the license file.
set(OVERRIDABLE_FETCH_CONTENT_eigen_MATCH "^https?://(.+)")
set(OVERRIDABLE_FETCH_CONTENT_eigen_REPLACE
  "https://storage.googleapis.com/mirror.tensorflow.org/\\1"
)

# If we're generating bindings configure SWIG.
if(FALKEN_CPP_SDK_CSHARP)
  include(swig)
endif()

# Get the commit of the git client.
if(EXISTS "${CMAKE_CURRENT_LIST_DIR}/../.git")
  execute_process(COMMAND
    git log -n 1 --format=%H
    OUTPUT_VARIABLE FALKEN_COMMIT_HASH
    OUTPUT_STRIP_TRAILING_WHITESPACE
  )
else()
  set(FALKEN_COMMIT_HASH 0)
endif()
# Read the changelist of the downloaded client.
if(EXISTS "${FALKEN_CPP_SDK_SRC_DIR}/changelist.txt")
  file(STRINGS "${FALKEN_CPP_SDK_SRC_DIR}/changelist.txt"
    FALKEN_CHANGELIST
    LIMIT_COUNT 1
  )
else()
  set(FALKEN_CHANGELIST 0)
endif()

# Bake the version into the C++ SDK.
add_compile_definitions(
  FALKEN_SDK_VERSION=${FALKEN_CPP_SDK_VERSION}
  FALKEN_SDK_COMMIT=${FALKEN_COMMIT_HASH}
  FALKEN_SDK_CHANGELIST=${FALKEN_CHANGELIST}
)

enable_testing()
set(BINARY_DIR "${CMAKE_BINARY_DIR}/falken_bin")
add_subdirectory("${FALKEN_CPP_SDK_SRC_DIR}/src/core" "${BINARY_DIR}/core")
add_subdirectory("${FALKEN_CPP_SDK_SRC_DIR}/src/tf_wrapper"
  "${BINARY_DIR}/tf_wrapper"
)
if(FALKEN_CPP_SDK_BUILD_TESTAPP)
  add_subdirectory("${FALKEN_CPP_SDK_SRC_DIR}/testapp" "${BINARY_DIR}/testapp")
endif()

# If the C++ SDK project generates C# files export the list to the parent scope.
if(FALKEN_CSHARP_SOURCES)
  set(FALKEN_CSHARP_SOURCES_DIR "${FALKEN_CSHARP_SOURCES_DIR}" PARENT_SCOPE)
  set(FALKEN_CSHARP_SOURCES "${FALKEN_CSHARP_SOURCES}"
    PARENT_SCOPE
  )
  set(FALKEN_CSHARP_SOURCES_RELATIVE_PATHS
    "${FALKEN_CSHARP_SOURCES_RELATIVE_PATHS}"
    PARENT_SCOPE
  )
endif()

# Generate a combined license file from all dependencies.
get_property(OVERRIDABLE_FETCH_CONTENT_LIST GLOBAL PROPERTY
    OVERRIDABLE_FETCH_CONTENT_LIST
)
list(SORT OVERRIDABLE_FETCH_CONTENT_LIST)
set(LICENSE_DIR "${CMAKE_CURRENT_BINARY_DIR}/licenses")
set(AGGREGATE_LICENSE_FILE "${LICENSE_DIR}/LICENSE")
if(NOT EXISTS "${AGGREGATE_LICENSE_FILE}")
  file(MAKE_DIRECTORY "${LICENSE_DIR}")
  foreach(CONTENT_NAME ${OVERRIDABLE_FETCH_CONTENT_LIST})
    OverridableFetchContent_GetProperties("${CONTENT_NAME}")

    file(READ "${${CONTENT_NAME}_SOURCE_DIR}/${${CONTENT_NAME}_LICENSE_FILE}"
      LICENSE_CONTENT
    )
    file(APPEND "${AGGREGATE_LICENSE_FILE}"
      "==== ${CONTENT_NAME}\n"
      "${${CONTENT_NAME}_ARCHIVE_URL}\n"
      "${${CONTENT_NAME}_LICENSE_URL}\n\n"
      "${LICENSE_CONTENT}\n\n"
    )
  endforeach()
endif()
if(NOT "${CMAKE_PROJECT_NAME}" STREQUAL "${PROJECT_NAME}")
  set(FALKEN_CPP_LICENSE "${AGGREGATE_LICENSE_FILE}" PARENT_SCOPE)
endif()

# Download all source archives for dependencies that need to be redistributed
# as source (nothing at the moment).
set(REDISTRIBUTE_SOURCE_PACKAGES "")
if(REDISTRIBUTE_SOURCE_PACKAGES)
  set(SOURCE_REDIST_DIR "${CMAKE_CURRENT_BINARY_DIR}/third_party_sources")
  set(SOURCE_REDIST_README "${SOURCE_REDIST_DIR}/README.md")
  file(MAKE_DIRECTORY "${SOURCE_REDIST_DIR}")
  set(SOURCE_REDIST_FILES "${SOURCE_REDIST_README}")
  if(NOT EXISTS "${SOURCE_REDIST_README}")
    file(WRITE "${SOURCE_REDIST_README}"
      "3rd party libraries that need to be redistributed as source:\n"
    )
  endif()
  foreach(CONTENT_NAME ${OVERRIDABLE_FETCH_CONTENT_LIST})
    if("${CONTENT_NAME}" IN_LIST REDISTRIBUTE_SOURCE_PACKAGES)
      OverridableFetchContent_GetProperties("${CONTENT_NAME}")
      set(ARCHIVE_URL "${${CONTENT_NAME}_ARCHIVE_URL}")
      get_filename_component(EXTENSION "${ARCHIVE_URL}" EXT)
      set(ARCHIVE_NAME "${CONTENT_NAME}${EXTENSION}")
      set(ARCHIVE_FILENAME "${SOURCE_REDIST_DIR}/${ARCHIVE_NAME}")
      if(NOT EXISTS "${ARCHIVE_FILENAME}")
        message(STATUS "Downloading ${CONTENT_NAME} to ${ARCHIVE_NAME}...")
        file(DOWNLOAD "${ARCHIVE_URL}" "${ARCHIVE_FILENAME}")
        file(APPEND "${SOURCE_REDIST_README}"
          "* ${ARCHIVE_NAME}: ${ARCHIVE_URL}\n"
        )
      endif()
      list(APPEND SOURCE_REDIST_FILES "${ARCHIVE_FILENAME}")
    endif()
  endforeach()
  if(NOT "${CMAKE_PROJECT_NAME}" STREQUAL "${PROJECT_NAME}")
    set(FALKEN_SOURCE_REDIST_FILES "${SOURCE_REDIST_FILES}" PARENT_SCOPE)
  endif()
endif()

# Set CPack variables.
set(CPACK_PACKAGE_NAME "${PROJECT_NAME}")
set(CPACK_PACKAGE_VENDOR "Google")
set(CPACK_PACKAGE_DIRECTORY "${CMAKE_BINARY_DIR}/build/packaging")
set(CPACK_PACKAGE_DESCRIPTION "Falken")
set(CPACK_PACKAGE_VERSION "${FALKEN_CPP_SDK_VERSION}")
set(CPACK_PACKAGE_FILE_NAME
  "${CPACK_PACKAGE_NAME}-${CPACK_PACKAGE_VERSION}-${FALKEN_SDK_TARGET}"
)
set(CPACK_SOURCE_GENERATOR "ZIP")
set(CPACK_INCLUDE_TOPLEVEL_DIRECTORY OFF)
set(CPACK_COMPONENTS_ALL falken_cpp_sdk)
# Add the build type to the package name on Windows since we need to
# redistribute libraries built against the Debug and Release runtime libraries.
if(CMAKE_SYSTEM_NAME MATCHES "Windows")
  set(CPACK_PACKAGE_FILE_NAME
    "${CPACK_PACKAGE_FILE_NAME}-\${CPACK_BUILD_CONFIG}"
  )
endif()

# Create version.txt with git commit hash and CL number
set(FALKEN_CPP_VERSION_TXT
  "${CMAKE_CURRENT_BINARY_DIR}/falken_cpp_version.txt"
)
if(NOT "${CMAKE_PROJECT_NAME}" STREQUAL "${PROJECT_NAME}")
  set(FALKEN_CPP_VERSION_TXT "${FALKEN_CPP_VERSION_TXT}" PARENT_SCOPE)
endif()
set(FALKEN_CPP_VERSION_TEMPLATE_TXT
  "${CMAKE_CURRENT_BINARY_DIR}/falken_cpp_version-template.txt"
)
set(FALKEN_CPP_VERSION_CONTENTS "\
Version: ${FALKEN_CPP_SDK_VERSION}
Changelist: ${FALKEN_CHANGELIST}
Commit: ${FALKEN_COMMIT_HASH}
")
file(WRITE "${FALKEN_CPP_VERSION_TEMPLATE_TXT}"
  "${FALKEN_CPP_VERSION_CONTENTS}"
)
configure_file("${FALKEN_CPP_VERSION_TEMPLATE_TXT}"
  "${FALKEN_CPP_VERSION_TXT}"
  NEWLINE_STYLE UNIX
)

install(
  FILES
    "${FALKEN_CPP_VERSION_TXT}"
    "${CMAKE_CURRENT_LIST_DIR}/Findfalken.cmake"
    "${AGGREGATE_LICENSE_FILE}"
    "${CMAKE_CURRENT_LIST_DIR}/README.md"
  DESTINATION
    "."
  COMPONENT
    falken_cpp
)
if(FALKEN_DOCS_DIR)
  install(
    DIRECTORY
      "${FALKEN_DOCS_DIR}"
    DESTINATION
      "."
    COMPONENT
      falken_cpp
  )
endif()
if(SOURCE_REDIST_FILES)
  install(
    FILES
      ${SOURCE_REDIST_FILES}
    DESTINATION
      "third_party_sources"
    COMPONENT
      falken_cpp
  )
endif()

if(CMAKE_SYSTEM_NAME MATCHES "Darwin")
  # Generate a list of files to sign.
  set(FALKEN_CPP_FILELIST "${CMAKE_CURRENT_BINARY_DIR}/FILELIST")
  file(WRITE "${FALKEN_CPP_FILELIST}"
    "lib/Darwin/Release/libfalken_cpp_sdk.dylib\n"
  )
  install(
    FILES
      "${FALKEN_CPP_FILELIST}"
    DESTINATION
      "."
    COMPONENT
      falken_cpp
  )
endif()

# Always leave this install target at the end. Every install rule
# is called in the order they were added, so we can ensure that everything
# is ready to be modified when calling this cmake script.
install(SCRIPT ${CMAKE_CURRENT_LIST_DIR}/transform_install.cmake)
include(CPack)
