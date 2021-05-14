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
set(CMAKE_CXX_STANDARD 11)

# Add the external CMake subdirectory to the list of directories to search for
# packages to include when using find_package() for both
# Find<PackageName>.cmake and <PackageName>-config.cmake files.
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/external")
list(APPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}/external")

project(HelloFalken)

find_package(SDL2 REQUIRED)

list(APPEND COMMON_HF_FILES
  src/game.cc
  src/game.h
  src/main.cc
  src/math_utils.h
  src/render.cc
  src/render.h
  src/ship.cc
  src/ship.h
  src/glplatform.h
  src/keyboard.cc
  src/keyboard.h
  src/input_device.h
)

list(APPEND HF_FILES
  src/falken_player.cc
  src/falken_player.h
)

list(APPEND DYNAMIC_HF_FILES
  src/falken_player_dynamic.cc
  src/falken_player_dynamic.h
)

if(ANDROID)
  # Build an Android application.

  # Try to get the path to the Falken C++ SDK from the FALKEN_CPP_SDK_DIR
  # environment variable.
  if (NOT "$ENV{FALKEN_CPP_SDK_DIR}" STREQUAL "")
    set(FALKEN_CPP_SDK_DIR "$ENV{FALKEN_CPP_SDK_DIR}")
    if(NOT EXISTS ${FALKEN_CPP_SDK_DIR})
      message(FATAL_ERROR "The Falken C++ SDK directory does not exist: "
        "${FALKEN_CPP_SDK_DIR}."
      )
    endif()
  endif()

  # Add the Falken C++ SDK path to the list of directories to search for
  # packages to include when using find_package() for Find<PackageName>.cmake.
  list(APPEND CMAKE_MODULE_PATH "${FALKEN_CPP_SDK_DIR}")
  list(APPEND CMAKE_PREFIX_PATH "${FALKEN_CPP_SDK_DIR}")

  find_package(falken REQUIRED)
  find_library(OPENGL_LIBRARIES GLESv3 REQUIRED)

  # Define the target as a shared library, as that is what gradle expects.
  add_library(main SHARED
    ${COMMON_HF_FILES}
    ${HF_FILES}
    src/gamepad.cc
    src/gamepad.h
  )

  target_link_libraries(main PUBLIC
    log
    android
    ${OPENGL_LIBRARIES}
    ${SDL2_LIBRARIES}
    falken_cpp_sdk
  )
else()
  # Build a desktop application.

  # Add the C++ SDK cmake subdirectory to the list of directories to search for
  # packages to include when using find_package() for Find<PackageName>.cmake.
  list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../..")

  find_package(falken REQUIRED)
  find_package(OpenGL REQUIRED)

  if(CMAKE_SYSTEM_NAME MATCHES "Windows")
    include_directories(${CMAKE_CURRENT_LIST_DIR}/src/third_party/include)
  endif()

  add_executable(HelloFalken
    ${COMMON_HF_FILES}
    ${HF_FILES}
  )

  add_executable(HelloFalkenDynamic
    ${COMMON_HF_FILES}
    ${DYNAMIC_HF_FILES}
  )

  target_link_libraries(HelloFalken
    ${OPENGL_LIBRARIES}
    ${SDL2_LIBRARIES}
    falken_cpp_sdk
  )

  target_link_libraries(HelloFalkenDynamic
    ${OPENGL_LIBRARIES}
    ${SDL2_LIBRARIES}
    falken_cpp_sdk
  )

  # Copy Falken C++ SDK shared library into the binary's build directory on
  # Windows.
  if(CMAKE_SYSTEM_NAME MATCHES "Windows")
    add_custom_command(TARGET HelloFalken
      POST_BUILD
      COMMAND ${CMAKE_COMMAND} -E copy
        $<TARGET_FILE:falken_cpp_sdk>
        "$<TARGET_FILE_DIR:HelloFalken>"
      DEPENDS
        falken_cpp_sdk
    )
    add_custom_command(TARGET HelloFalkenDynamic
      POST_BUILD
      COMMAND ${CMAKE_COMMAND} -E copy
        $<TARGET_FILE:falken_cpp_sdk>
        "$<TARGET_FILE_DIR:HelloFalkenDynamic>"
      DEPENDS
        falken_cpp_sdk
    )
  endif()
endif()
