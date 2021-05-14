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

cmake_minimum_required(VERSION 3.17)

project(csharp_nunit_test C)

enable_testing()

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/..")

find_package(Unity REQUIRED)

include(nunit)
include(csharp)

# Native library to call from C#.
add_library(native SHARED native.c)

# Build a library with no references.
CSharpAddLibrary(
  greeter
  ALL
  MODULE Greeter
  FRAMEWORK_VERSION 4.5
  SOURCES Greeter.cs
)

# Build a library that references a file resource.
CSharpAddLibrary(
  greeter_from_resource
  MODULE GreeterFromResource
  FRAMEWORK_VERSION 4.5
  SOURCES GreeterFromResource.cs
  COPY_FILES goodbye.txt
)

# Build a library that references a native module.
CSharpAddLibrary(
  greeter_from_the_void
  MODULE GreeterFromTheVoid
  FRAMEWORK_VERSION 4.5
  SOURCES GreeterFromTheVoid.cs
  COPY_FILES native
)

# Build an executable.
CSharpAddExecutable(
  hello_main
  MODULE HelloMain
  FRAMEWORK_VERSION 4.5
  SOURCES HelloMain.cs
  REFERENCES
    greeter
    greeter_from_resource
    greeter_from_the_void
)

# Build a test.
CSharpAddLibrary(
  greeter_test
  MODULE GreeterTest
  FRAMEWORK_VERSION 4.5
  SOURCES GreeterTest.cs
  REFERENCES
    nunit_framework
    greeter
)

# Build a test with resource dependencies.
CSharpAddLibrary(
  greeter_with_dependencies_test
  MODULE GreeterWithDependenciesTest
  FRAMEWORK_VERSION 4.5
  SOURCES GreeterWithDependenciesTest.cs
  REFERENCES
    nunit_framework
    greeter_from_resource
    greeter_from_the_void
)

# Run a test using a target.
NUnitTest(
  run_greeter_test_using_target
  TEST_TARGET greeter_test
)

# Run a test with resource dependencies.
NUnitTest(
  run_greeter_with_dependencies_test
  ALL
  TEST_TARGET greeter_with_dependencies_test
)

# Build the greeter library with Unity's mono tools.
CSharpAddLibrary(
  greeter_unity
  ALL
  MODULE GreeterUnity
  FRAMEWORK_VERSION 3.5
  SOURCES Greeter.cs
  BUILD_EXE "${UNITY_CSHARP_BUILD_EXE}"
)

# Build a test that depends upon Unity (though it doesn't use it so we can run
# it without Unity). This is added to the ALL target so that it's easy to build
# before running the test with run_greeter_test_using_dll.
CSharpAddLibrary(
  greeter_unity_test
  ALL
  MODULE GreeterUnityTest
  FRAMEWORK_VERSION 3.5
  SOURCES GreeterTest.cs
  REFERENCES
    nunit_framework
    greeter_unity
  BUILD_EXE "${UNITY_CSHARP_BUILD_EXE}"
)

# Run a test using a path to the DLL with Unity's Mono interpreter.
get_target_property(TEST_DLL_NAME greeter_unity_test LIBRARY_OUTPUT_NAME)
get_target_property(TEST_DLL_DIR greeter_unity_test LIBRARY_OUTPUT_DIRECTORY)
NUnitTest(
  run_greeter_test_using_dll
  ALL
  TEST_DLL "${TEST_DLL_DIR}/${TEST_DLL_NAME}"
  LAUNCHER "${UNITY_MONO_EXE}"
  DEPENDS
    greeter_unity_test
)

# Test HelloMain.exe.
CSharpAddLibrary(
  hello_main_test
  MODULE HelloMainTest
  FRAMEWORK_VERSION 4.5
  SOURCES HelloMainTest.cs
  REFERENCES
    nunit_framework
  COPY_FILES
    hello_main
)

NUnitTest(
  run_hello_main_test
  TEST_TARGET hello_main_test
)
