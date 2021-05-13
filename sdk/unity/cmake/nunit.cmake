# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Module that exposes functions to run NUnit tests.
#
# - Functions:
#   - NUnitTest: Generates a target that executes NUnit tests.

find_package(NUnit REQUIRED)

# Generates a target that executes a NUnit test.
#
# Positional arguments:
#  TARGET_NAME: Name of the target to create which will run the test.
#
# Required named arguments:
#  TEST_DLL <test_dll_name>: Path to the test DLL to execute. Either this
#    or TEST_TARGET must be specified.
#  TEST_TARGET <test_dll_target_name>: Target that references the test DLL to
#    execute. Either this or TEST_DLL must be specified.
#
# Optional named arguments:
#  ALL: Add the test target to the "all" / default target's dependencies.
#  SHOW_LABELS <verbosity>: Configure whether to display test labels as tests
#    are executed, can be one of
#    [Off, OnOutputOnly, Before, After, BeforeAndAfter], defaults to
#    BeforeAndAfter.
#  NUNIT_CONSOLE_ARGS <arguments...>: Additional arguments to pass to
#    nunit3-console.
#  MONO_EXE <mono_binary>: Interpreter to run NUnit console. This defaults to
#    the value of the NUNIT_CONSOLE_LAUNCHER variable.
#  DEPENDS <targets...>: Additional dependencies that need to be built for this
#    test.
function(NUnitTest TARGET_NAME)
  cmake_parse_arguments(ARGS
    "ALL"
    "TEST_DLL;TEST_TARGET;SHOW_LABELS;MONO_EXE"
    "NUNIT_CONSOLE_ARGS;DEPENDS"
    ${ARGN}
  )

  # Get the test DLL.
  set(DLL_FILENAME "")
  set(DLL_DIR "")
  if(ARGS_TEST_DLL)
    set(DLL_FILENAME "${ARGS_TEST_DLL}")
    get_filename_component(DLL_DIR "${DLL_FILENAME}" DIRECTORY)
  elseif(ARGS_TEST_TARGET)
    get_target_property(DLL_NAME "${ARGS_TEST_TARGET}" LIBRARY_OUTPUT_NAME)
    get_target_property(DLL_DIR "${ARGS_TEST_TARGET}" LIBRARY_OUTPUT_DIRECTORY)
    set(DLL_FILENAME "${DLL_DIR}/${DLL_NAME}")
  endif()
  if("${DLL_FILENAME}" STREQUAL "" OR "${DLL_DIR}" STREQUAL "")
    message(FATAL_ERROR "TEST_DLL or TEST_TARGET must specify an assembly.")
  endif()

  # Whether to show test labels.
  set(SHOW_LABELS "BeforeAndAfter")
  if(ARGS_SHOW_LABELS)
    set(SHOW_LABELS "${ARGS_SHOW_LABELS}")
  endif()

  # Configure an argument to add the target to ALL.
  set(ADD_TO_ALL "")
  if(ARGS_ALL)
    set(ADD_TO_ALL "ALL")
  endif()

  set(LAUNCHER "${NUNIT_CONSOLE_LAUNCHER}")
  if(ARGS_LAUNCHER)
    set(LAUNCHER "${ARGS_LAUNCHER}")
  endif()

  # Build a list of dependencies.
  set(DEPENDS ${ARGS_DEPENDS})
  if(ARGS_TEST_TARGET)
    list(APPEND DEPENDS ${ARGS_TEST_TARGET})
  endif()

  # Setup the path to the test output file.
  set(OUTPUT_DIR
    "${CMAKE_CURRENT_BINARY_DIR}/nunit_test_results/${TARGET_NAME}"
  )
  file(MAKE_DIRECTORY "${OUTPUT_DIR}")
  set(LOG_FILENAME "${OUTPUT_DIR}/TestResult.xml")

  # Build arguments for NUnit console.
  set(NUNIT_CONSOLE_ARGS "${DLL_FILENAME}")
  list(APPEND NUNIT_CONSOLE_ARGS --noheader)
  list(APPEND NUNIT_CONSOLE_ARGS --labels "${SHOW_LABELS}")
  list(APPEND NUNIT_CONSOLE_ARGS --result "${LOG_FILENAME}")
  # Default to running tests in the same process as the runner so that it's far
  # easier to inspect with a debugger.
  if(NOT "--process" IN_LIST ARGS_NUNIT_CONSOLE_ARGS)
    list(APPEND NUNIT_CONSOLE_ARGS --process Single)
  endif()
  list(APPEND NUNIT_CONSOLE_ARGS ${ARGS_NUNIT_CONSOLE_ARGS})

  # Create a target to run the test.
  add_test(
    NAME
      ${TARGET_NAME}
    COMMAND
      ${LAUNCHER} "${NUNIT_CONSOLE}" ${NUNIT_CONSOLE_ARGS}
    WORKING_DIRECTORY
      "${DLL_DIR}"
    COMMAND_EXPAND_LISTS
  )

  # CTest has a long standing issue where it doesn't build test dependencies:
  # https://gitlab.kitware.com/cmake/cmake/-/issues/8774
  # To work around this, the following uses a test target to recursively launch
  # cmake to build the test's dependencies before launching the test.
  if(DEPENDS)
    set(BUILD_TEST_TARGET_NAME ${TARGET_NAME}_build)
    add_test(
      NAME
        ${BUILD_TEST_TARGET_NAME}
      COMMAND
        "${CMAKE_COMMAND}"
        --build "${CMAKE_BINARY_DIR}"
        --target ${DEPENDS}
      COMMAND_EXPAND_LISTS
    )
    set_tests_properties(${TARGET_NAME} PROPERTIES DEPENDS
      ${BUILD_TEST_TARGET_NAME}
    )
  endif()
endfunction()
