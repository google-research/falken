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

# Module which exposes targets for Falken's C++ SDK.

# If the binary distribution is available for the current platform in the
# directory containing this file, use it.
set(FALKEN_CPP_IMP "")
if(CMAKE_SYSTEM_NAME MATCHES "Windows")
  set(FALKEN_CPP_LIB_DEBUG
    "${CMAKE_CURRENT_LIST_DIR}/lib/Windows/Debug/falken_cpp_sdk.dll"
  )
  set(FALKEN_CPP_IMP_DEBUG
    "${CMAKE_CURRENT_LIST_DIR}/lib/Windows/Debug/falken_cpp_sdk.lib"
  )
  set(FALKEN_CPP_LIB_RELEASE
    "${CMAKE_CURRENT_LIST_DIR}/lib/Windows/Release/falken_cpp_sdk.dll"
  )
  set(FALKEN_CPP_IMP_RELEASE
    "${CMAKE_CURRENT_LIST_DIR}/lib/Windows/Release/falken_cpp_sdk.lib"
  )
  set(FALKEN_CPP_LIB "${FALKEN_CPP_LIB_RELEASE}")
  set(FALKEN_CPP_IMP "${FALKEN_CPP_IMP_RELEASE}")
elseif(CMAKE_SYSTEM_NAME MATCHES "Darwin")
  set(FALKEN_CPP_LIB
    "${CMAKE_CURRENT_LIST_DIR}/lib/Darwin/Release/libfalken_cpp_sdk.dylib")
elseif(CMAKE_SYSTEM_NAME MATCHES "Android")
  set(FALKEN_CPP_LIB
    "${CMAKE_CURRENT_LIST_DIR}/lib/Android/Release/libfalken_cpp_sdk.so")
elseif(CMAKE_SYSTEM_NAME MATCHES "Linux" AND
  CMAKE_SYSTEM_VERSION MATCHES "Ggp")
  set(FALKEN_CPP_LIB
    "${CMAKE_CURRENT_LIST_DIR}/lib/Stadia/Release/libfalken_cpp_sdk.so")
elseif(CMAKE_SYSTEM_NAME MATCHES "Linux" AND
  CMAKE_SYSTEM_VERSION MATCHES "CrosstoolGrte")
  set(FALKEN_CPP_LIB
    "${CMAKE_CURRENT_LIST_DIR}/lib/Crosstool/Release/libfalken_cpp_sdk.so")
elseif(CMAKE_SYSTEM_NAME MATCHES "Linux")
  set(FALKEN_CPP_LIB
    "${CMAKE_CURRENT_LIST_DIR}/lib/Linux/Release/libfalken_cpp_sdk.so")
else()
  message(FATAL_ERROR "Falken is currently not supported on this platform.")
endif()
set(FALKEN_CPP_INCLUDE "${CMAKE_CURRENT_LIST_DIR}/include")
if(EXISTS "${FALKEN_CPP_INCLUDE}" AND EXISTS "${FALKEN_CPP_LIB}"
   AND ("${FALKEN_CPP_IMP}" STREQUAL "" OR EXISTS "${FALKEN_CPP_IMP}"))
  add_library(falken_cpp_sdk SHARED IMPORTED)
  target_include_directories(falken_cpp_sdk INTERFACE "${FALKEN_CPP_INCLUDE}")
  if(CMAKE_SYSTEM_NAME MATCHES "Windows")
    set_target_properties(falken_cpp_sdk PROPERTIES
      IMPORTED_LOCATION_DEBUG "${FALKEN_CPP_LIB_DEBUG}"
      IMPORTED_LOCATION_RELEASE "${FALKEN_CPP_LIB_RELEASE}"
      IMPORTED_IMPLIB_DEBUG "${FALKEN_CPP_IMP_DEBUG}"
      IMPORTED_IMPLIB_RELEASE "${FALKEN_CPP_IMP_RELEASE}"
    )
  else()
    set_target_properties(falken_cpp_sdk PROPERTIES
      IMPORTED_LOCATION "${FALKEN_CPP_LIB}"
    )
  endif()
else()
  # Try building from source.
  add_subdirectory("${CMAKE_CURRENT_LIST_DIR}"
    "falken_cpp_sdk"
    EXCLUDE_FROM_ALL
  )
  # Expose the source tree and license to the parent project.
  if(NOT "${CMAKE_PROJECT_NAME}" STREQUAL "${PROJECT_NAME}")
    set(FALKEN_DIR ${FALKEN_DIR} PARENT_SCOPE)
    set(FALKEN_CPP_LICENSE "${FALKEN_CPP_LICENSE}" PARENT_SCOPE)
  endif()
endif()
