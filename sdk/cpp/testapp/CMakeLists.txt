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

cmake_minimum_required(VERSION 3.17)

set(FALKEN_PROJECT_ID "" CACHE STRING "Project ID for integration tests.")
set(FALKEN_API_KEY "" CACHE STRING "API Key for integration tests.")
set(FALKEN_TESTAPP_ENABLE_TEST ON CACHE BOOL
  "Whether to add testapp as a ctest target."
)

# Windows runtime mode, either MD or MT depending on whether you are using
# /MD or /MT. For more information see:
# https://msdn.microsoft.com/en-us/library/2kzt1wy3.aspx
set(MSVC_RUNTIME_MODE MD)

project(falken_cpp_test)

# Sample source files.
set(SAMPLE_COMMON_SRCS
  src/main.h
  src/common_main.cc
)

# The include directory for the testapp.
include_directories(src)

# Sample uses some features that require C++ 11.
set(CMAKE_CXX_STANDARD 11)

# If this project is being built as part of the C++ SDK.
if(TARGET falken_cpp_sdk)
  # We already have Falken's C++ SDK target.

  # Fetch Abseil C++.
  find_package(absl REQUIRED)
else()
  # Fetch Falken C++ SDK.
  # Try to read the path to the Falken C++ SDK from an environment variable.
  if (NOT "$ENV{FALKEN_CPP_SDK_DIR}" STREQUAL "")
    set(DEFAULT_FALKEN_CPP_SDK_DIR "$ENV{FALKEN_CPP_SDK_DIR}")
  else()
    set(DEFAULT_FALKEN_CPP_SDK_DIR "falken_cpp_sdk")
  endif()
  if ("${FALKEN_CPP_SDK_DIR}" STREQUAL "")
    set(FALKEN_CPP_SDK_DIR ${DEFAULT_FALKEN_CPP_SDK_DIR})
  endif()
  if(NOT EXISTS ${FALKEN_CPP_SDK_DIR})
    message(FATAL_ERROR "The Falken C++ SDK directory does not exist: "
      "${FALKEN_CPP_SDK_DIR}."
    )
  endif()

  # Add the Falken library to the target.
  list(APPEND CMAKE_MODULE_PATH "${FALKEN_CPP_SDK_DIR}")
  find_package(falken REQUIRED)

  # Fetch Abseil C++.
  include(FetchContent)
  FetchContent_Declare(
    abseil-cpp
    GIT_REPOSITORY https://github.com/abseil/abseil-cpp.git
    GIT_TAG 20200225.2
    GIT_SHALLOW TRUE
    GIT_PROGRESS TRUE
  )
  FetchContent_MakeAvailable(abseil-cpp)
endif()

if(ANDROID)
  # Build an Android application.

  # Source files used for the Android build.
  set(SAMPLE_ANDROID_SRCS
    src/android/android_main.cc
  )

  # Build native_app_glue as a static lib
  add_library(native_app_glue STATIC
    ${ANDROID_NDK}/sources/android/native_app_glue/android_native_app_glue.c)

  # Export ANativeActivity_onCreate(),
  # Refer to: https://github.com/android-ndk/ndk/issues/381.
  set(CMAKE_SHARED_LINKER_FLAGS
      "${CMAKE_SHARED_LINKER_FLAGS} -u ANativeActivity_onCreate")

  # Define the target as a shared library, as that is what gradle expects.
  set(target_name "android_test_app")
  add_library(${target_name} SHARED
    ${SAMPLE_ANDROID_SRCS}
    ${SAMPLE_COMMON_SRCS}
  )

  target_link_libraries(${target_name} PUBLIC
    log android atomic native_app_glue
  )

  target_include_directories(${target_name} PRIVATE
    ${ANDROID_NDK}/sources/android/native_app_glue)

  set(ADDITIONAL_LIBS)
else()
  # Build a desktop application.

  # Windows runtime mode, either MD or MT depending on whether you are using
  # /MD or /MT. For more information see:
  # https://msdn.microsoft.com/en-us/library/2kzt1wy3.aspx
  set(MSVC_RUNTIME_MODE MD)

  # Platform abstraction layer for the desktop sample.
  set(SAMPLE_DESKTOP_SRCS
    src/desktop/desktop_main.cc
  )

  set(target_name "test_app")
  add_executable(${target_name}
    ${SAMPLE_DESKTOP_SRCS}
    ${SAMPLE_COMMON_SRCS}
  )

  if(APPLE)
    set(ADDITIONAL_LIBS pthread)
  elseif(MSVC)
    set(ADDITIONAL_LIBS)
  else()
    set(ADDITIONAL_LIBS pthread)
  endif()
endif()

# Enable all warnings as errors.
if(CMAKE_SYSTEM_NAME STREQUAL "Windows")
  target_compile_options(${target_name}
    PRIVATE
      /W4 /WX
  )
else()
  target_compile_options(${target_name}
    PRIVATE
      -Wall -Werror
  )
endif()

target_link_libraries(${target_name}
  PUBLIC
    falken_cpp_sdk
    absl_flags
    absl_flags_parse
    absl_strings
    absl_time
    ${ADDITIONAL_LIBS}
)

if(NOT ANDROID)
  # If the API project ID and API key are specified add the test target.
  if(FALKEN_TESTAPP_ENABLE_TEST AND FALKEN_PROJECT_ID AND FALKEN_API_KEY)
    add_test(
      NAME falken_cpp_sdk_test_app
      COMMAND "${target_name}"
        --env prod
        --api_key "${FALKEN_API_KEY}"
        --project_id "${FALKEN_PROJECT_ID}"
        --milliseconds_between_steps 0
    )
  endif()
endif()
