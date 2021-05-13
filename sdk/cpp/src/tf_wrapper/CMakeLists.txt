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

project(falken_tf_wrapper_internal)

find_package(absl REQUIRED)
find_package(flatbuffers REQUIRED)
find_package(tensorflow REQUIRED)

get_filename_component(FALKEN_CPP_SDK_SRC_ROOT_DIR
  "${CMAKE_CURRENT_LIST_DIR}/.."
  REALPATH
)

# We don't add model.cc and model.h to the build since we don't support
# Tensorflow builds for Windows. This force us to use TFLite only.

set(TF_WRAPPER_SRCS
  "lite_model.cc"
  "tf_wrapper.cc"
)

set(TF_WRAPPER_HDRS
  "lite_model.h"
  "tf_wrapper.h"
)

add_library(falken_tf_wrapper ${TF_WRAPPER_SRCS} ${TF_WRAPPER_HDRS})

target_link_libraries(falken_tf_wrapper
  PUBLIC
    falken_common
    absl::base
    absl::config
    absl::status
    absl::strings
    flatbuffers
    tensorflow::tensorflowlite
)

target_include_directories(falken_tf_wrapper
  PUBLIC
    "${FALKEN_CPP_SDK_SRC_ROOT_DIR}"
)

target_compile_definitions(falken_tf_wrapper
  PUBLIC
    -DFALKEN_ENABLE_TFLITE
)

set(EXAMPLE_MODEL_SRCS
  "example_model.cc"
)

set(EXAMPLE_MODEL_HDRS
  "example_model.h"
)

add_library(example_model ${EXAMPLE_MODEL_SRCS} ${EXAMPLE_MODEL_HDRS})

target_link_libraries(example_model
  PUBLIC
    falken_common
    absl::base
    absl::flags
    absl::strings
)

target_include_directories(example_model
  PUBLIC
    "${FALKEN_CPP_SDK_SRC_ROOT_DIR}"
)

# Testing.
if(CMAKE_SYSTEM_NAME MATCHES "Android")
  option(FALKEN_ENABLE_CPP_UNIT_TESTS "Build tests for this project" OFF)
elseif(CMAKE_SYSTEM_VERSION MATCHES "(CrosstoolGrte|Ggp)")
  option(FALKEN_ENABLE_CPP_UNIT_TESTS "Build tests for this project" OFF)
else()
  option(FALKEN_ENABLE_CPP_UNIT_TESTS "Build tests for this project" ON)
endif()

if(FALKEN_ENABLE_CPP_UNIT_TESTS)
  find_package(GTest REQUIRED)

  include(GoogleTest)
  include(CTest)

  # Disable tests in other projects (like Abseil) that use CTest.
  set(BUILD_TESTING OFF CACHE BOOL "Disable tests." FORCE)

  macro(tf_wrapper_build_test test_name)
    message(DEBUG "Adding test ${test_name}")
    add_executable(${test_name} ${ARGN})
    target_include_directories(${test_name}
      PUBLIC
        "${FALKEN_ROOT_DIR}"
    )
    target_link_libraries(${test_name}
      falken_tf_wrapper
      falken_cpp_sdk_static
      example_model
      absl::flags
      absl::flags_parse
      gmock_main
    )
    gtest_discover_tests(${test_name}
      EXTRA_ARGS
        --example_model_path "${CMAKE_CURRENT_LIST_DIR}/example_model"
    )
  endmacro()

  tf_wrapper_build_test(lite_model_test "lite_model_test.cc")
  # TODO(b/186531078): Enable model_comparison_test test (requires TensorFlow)
  # tf_wrapper_build_test(model_comparison_test "model_comparison_test.cc")
endif()
