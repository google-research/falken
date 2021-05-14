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

# Find NUnit (C# testing framework) assemblies and tools.
#
# Cache variables set by this module:
#  NUNIT_VERSION: NUnit's version.
#  NUNIT_FRAMEWORK_DLL: NUnit's framework DLL.
#  NUNIT_CONSOLE: NUnit console's .NET executable.
#  NUNIT_CONSOLE_LAUNCHER: Launcher for the NUnit console.
#
# Targets added by this module:
#  nunit_framework: C# target that exposes NUnit's framework DLL.

find_package(Mono REQUIRED)

include(csharp)

include(FetchContent)

# The desired version.
set(NUNIT_VERSION_MAJOR "3")
set(NUNIT_VERSION_MINOR "11")
set(NUNIT_VERSION_REVISION "0")
set(NUNIT_VERSION_MAJOR_MINOR
  "${NUNIT_VERSION_MAJOR}.${NUNIT_VERSION_MINOR}"
)
set(NUNIT_VERSION
  "${NUNIT_VERSION_MAJOR_MINOR}.${NUNIT_VERSION_REVISION}"
  CACHE STRING "NUnit version."
)

# NUnit download URL.
string(CONCAT NUNIT_DOWNLOAD_URL
  "https://github.com/nunit/nunit-console/releases/download"
  "/v${NUNIT_VERSION_MAJOR_MINOR}"
  "/NUnit.Console-${NUNIT_VERSION}.zip"
)

# Download NUnit.
FetchContent_Declare(
  nunit
  URL "${NUNIT_DOWNLOAD_URL}"
  SOURCE_DIR "${CMAKE_BINARY_DIR}/nunit"
)
FetchContent_GetProperties(nunit)
if(NOT nunit_POPULATED)
  FetchContent_Populate(nunit)
endif()

set(NUNIT_BIN_DIR "${nunit_SOURCE_DIR}/bin")
# Search order for NUnit assemblies and tools.
if(NOT NUNIT_DOT_NET_FOLDER_SEARCH_ORDER)
  set(NUNIT_DOT_NET_FOLDER_SEARCH_ORDER
    net35
    net20
  )
endif()

find_file(
  NUNIT_FRAMEWORK_DLL nunit.framework.dll
  HINTS "${NUNIT_BIN_DIR}"
  PATH_SUFFIXES ${NUNIT_DOT_NET_FOLDER_SEARCH_ORDER}
  DOC "NUnit framework assembly."
)

if(EXISTS "${NUNIT_FRAMEWORK_DLL}" AND NOT TARGET nunit_framework)
  # Expose a target for the NUnit framework assembly.
  CSharpAddExternalDll(nunit_framework "${NUNIT_FRAMEWORK_DLL}")
endif()

find_file(
  NUNIT_CONSOLE nunit3-console.exe
  HINTS "${NUNIT_BIN_DIR}"
  PATH_SUFFIXES ${NUNIT_DOT_NET_FOLDER_SEARCH_ORDER}
  DOC "NUnit console unit test runner."
)

set(NUNIT_CONSOLE_LAUNCHER
  "${MONO_EXE}" CACHE STRING
  "Launcher for the NUnit console." FORCE
)

if(NOT EXISTS "${NUNIT_CONSOLE}" OR
   NOT EXISTS "${NUNIT_FRAMEWORK_DLL}")
  message(FATAL_ERROR "Failed to find nunit3-console or nunit.framework.dll")
endif()

include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(NUnit DEFAULT_MSG
  NUNIT_CONSOLE
  NUNIT_CONSOLE_LAUNCHER
  NUNIT_FRAMEWORK_DLL
)
mark_as_advanced(
  NUNIT_CONSOLE
  NUNIT_CONSOLE_LAUNCHER
  NUNIT_FRAMEWORK_DLL
)
