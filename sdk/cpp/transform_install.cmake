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

# Clean up unnecessary files that were installed by gRPC and other
# third party projects.
if(NOT CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
  message(STATUS "Cleaning up installed targets")
  file(REMOVE_RECURSE
    ${CMAKE_INSTALL_PREFIX}/lib/cmake
    ${CMAKE_INSTALL_PREFIX}/lib/pkgconfig
    ${CMAKE_INSTALL_PREFIX}/share
    ${CMAKE_INSTALL_PREFIX}/include/ares.h
    ${CMAKE_INSTALL_PREFIX}/include/ares_build.h
    ${CMAKE_INSTALL_PREFIX}/include/ares_dns.h
    ${CMAKE_INSTALL_PREFIX}/include/ares_rules.h
    ${CMAKE_INSTALL_PREFIX}/include/ares_version.h
    ${CMAKE_INSTALL_PREFIX}/include/google
    ${CMAKE_INSTALL_PREFIX}/include/grpc
    ${CMAKE_INSTALL_PREFIX}/include/grpc++
    ${CMAKE_INSTALL_PREFIX}/include/grpcpp
    ${CMAKE_INSTALL_PREFIX}/include/flatbuffers)
  file(GLOB FALKEN_HEADER_FILES "${CMAKE_INSTALL_PREFIX}/include/*.h")
  if(FALKEN_HEADER_FILES)
    file(MAKE_DIRECTORY "${CMAKE_INSTALL_PREFIX}/include/falken")
    foreach(FALKEN_HEADER_FILE IN LISTS FALKEN_HEADER_FILES)
      get_filename_component(BASE_FILE_NAME "${FALKEN_HEADER_FILE}" NAME)
      file(RENAME "${FALKEN_HEADER_FILE}"
        "${CMAKE_INSTALL_PREFIX}/include/falken/${BASE_FILE_NAME}")
    endforeach()
  endif()
  if(EXISTS "${CMAKE_INSTALL_PREFIX}/bin/falken_cpp_sdk.dll")
    file(RENAME
      ${CMAKE_INSTALL_PREFIX}/bin/falken_cpp_sdk.dll
      ${CMAKE_INSTALL_PREFIX}/lib/falken_cpp_sdk.dll)
    file(REMOVE_RECURSE ${CMAKE_INSTALL_PREFIX}/bin)
  endif()
endif()
