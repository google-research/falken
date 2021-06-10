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

project(falken_core_internal)

option(FALKEN_CPP_SDK_GENERATE_API_REFERENCE ON
  "Generate API reference if Doxygen is available."
)
option(FALKEN_CPP_SDK_CSHARP OFF "Generate C# bindings.")

#
set(FALKEN_PROJECT_ID "" CACHE STRING "Project ID for integration tests.")
set(FALKEN_API_KEY "" CACHE STRING "API Key for integration tests.")
set(FALKEN_JSON_CONFIG_FILE "" CACHE STRING
  "JSON configuration file for integration tests. This can be used instead of
  FALKEN_PROJECT_ID and FALKEN_API_KEY."
)

# Whether to enable tests.
if(CMAKE_SYSTEM_NAME MATCHES "Android")
  option(FALKEN_ENABLE_CPP_UNIT_TESTS "Build tests for this project" OFF)
elseif(CMAKE_SYSTEM_VERSION MATCHES "(CrosstoolGrte|Ggp)")
  option(FALKEN_ENABLE_CPP_UNIT_TESTS "Build tests for this project" OFF)
else()
  option(FALKEN_ENABLE_CPP_UNIT_TESTS "Build tests for this project" ON)
endif()

option(FALKEN_ENABLE_CPP_SERVICE_TESTS
  "Build service tests for this project" OFF
)

find_package(absl REQUIRED)
find_package(Protobuf REQUIRED)
find_package(grpc REQUIRED)
find_package(Googleapis REQUIRED)

if(CMAKE_SYSTEM_NAME MATCHES "Android")
  find_library(ANDROID_LOG log REQUIRED)
endif()

set(FALKEN_CPP_SDK_PUBLIC_DEFINES "")
set(FALKEN_CPP_SDK_PRIVATE_DEFINES "")

# Get the project's root directory, assuming this file is under
# sdk/cpp/src/core.
if("${FALKEN_PROJECT_ROOT_DIR}" STREQUAL "")
  get_filename_component(FALKEN_PROJECT_ROOT_DIR
    "${CMAKE_CURRENT_LIST_DIR}/../../.."
    REALPATH
  )
endif()

#

# Get the root directory of the C++ SDK assuming this file is under
# sdk/cpp/src/core, this should reference sdk/cpp.
get_filename_component(FALKEN_CPP_SDK_DIR
  "${CMAKE_CURRENT_LIST_DIR}/../.."
  REALPATH
)

# Configure Python binary using the PYTHON variable.
if(CMAKE_SYSTEM_NAME MATCHES "Windows")
  set(DEFAULT_PYTHON "python")
else()
  set(DEFAULT_PYTHON "python3")
endif()
set(PYTHON "${DEFAULT_PYTHON}" CACHE STRING
  "Python executable to use."
)

set(CORE_SOURCE_DIR "${CMAKE_CURRENT_LIST_DIR}")
set(CORE_SOURCE_GENERATED_DIR
  "${CMAKE_CURRENT_BINARY_DIR}/generated_source"
)
set(PUBLIC_CPP_API_SOURCE_DIR
  "${CORE_SOURCE_DIR}/public/include"
)

set(PROTO_OUTPUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated_protos")
file(MAKE_DIRECTORY "${PROTO_OUTPUT_DIR}")

set(EXPORT_SYMBOLS_FILE_LINUX
  "${CMAKE_CURRENT_LIST_DIR}/exported_symbols_linux.lds"
)
set(UNEXPORT_SYMBOLS_FILE_MAC
  "${CMAKE_CURRENT_LIST_DIR}/unexported_symbols_mac.lds"
)

set(SERVICE_INTERFACE_SRCS_DIR "${FALKEN_PROJECT_ROOT_DIR}/service/proto")
set(SERVICE_INTERFACE_PATH "service/proto")
file(MAKE_DIRECTORY "${PROTO_OUTPUT_DIR}/${SERVICE_INTERFACE_PATH}")
set(SERVICE_INTERFACE_DEPENDENCIES "googleapis_rpc")

set(SERVICE_INTERFACE_GRPC_PROTO_SRCS
  "${SERVICE_INTERFACE_SRCS_DIR}/falken_service.proto"
)
set(SERVICE_INTERFACE_GRPC_GENERATED_SRCS
  "${PROTO_OUTPUT_DIR}/${SERVICE_INTERFACE_PATH}/falken_service.grpc.pb.cc"
  "${PROTO_OUTPUT_DIR}/${SERVICE_INTERFACE_PATH}/falken_service.grpc.pb.h"
)
set(SERVICE_INTERFACE_PROTO_SRCS
  ${SERVICE_INTERFACE_GRPC_PROTO_SRCS}
  "${SERVICE_INTERFACE_SRCS_DIR}/action.proto"
  "${SERVICE_INTERFACE_SRCS_DIR}/brain.proto"
  "${SERVICE_INTERFACE_SRCS_DIR}/episode.proto"
  "${SERVICE_INTERFACE_SRCS_DIR}/observation.proto"
  "${SERVICE_INTERFACE_SRCS_DIR}/primitives.proto"
  "${SERVICE_INTERFACE_SRCS_DIR}/serialized_model.proto"
  "${SERVICE_INTERFACE_SRCS_DIR}/session.proto"
  "${SERVICE_INTERFACE_SRCS_DIR}/snapshot.proto"
)
set(SERVICE_INTERFACE_GENERATED_SRCS "")
foreach(PROTO ${SERVICE_INTERFACE_PROTO_SRCS})
  get_filename_component(BASENAME "${PROTO}" NAME_WE)
  list(APPEND SERVICE_INTERFACE_GENERATED_SRCS
    "${PROTO_OUTPUT_DIR}/${SERVICE_INTERFACE_PATH}/${BASENAME}.pb.cc"
    "${PROTO_OUTPUT_DIR}/${SERVICE_INTERFACE_PATH}/${BASENAME}.pb.h"
  )
endforeach()

#

# Generate service interface protos.
add_custom_command(
  PRE_BUILD
  OUTPUT
    ${SERVICE_INTERFACE_GENERATED_SRCS}
  COMMAND "${PROTOC_HOST}"
    "--cpp_out=${PROTO_OUTPUT_DIR}/${SERVICE_INTERFACE_PATH}"
    "--proto_path=${SERVICE_INTERFACE_SRCS_DIR}"
    "--proto_path=${PROTOBUF_PROJECT_DIR}/src"
    ${SERVICE_INTERFACE_PROTO_SRCS}
  DEPENDS
    "${PROTOC_HOST_TARGET}"
)

# Generate gRPC interface file.
add_custom_command(
  PRE_BUILD
  OUTPUT
    ${SERVICE_INTERFACE_GRPC_GENERATED_SRCS}
  COMMAND "${PROTOC_HOST}"
    "--cpp_out=${PROTO_OUTPUT_DIR}/${SERVICE_INTERFACE_PATH}"
    "--proto_path=${SERVICE_INTERFACE_SRCS_DIR}"
    "--proto_path=${PROTOBUF_PROJECT_DIR}/src"
    "--grpc_out=${PROTO_OUTPUT_DIR}/service/proto"
    "--grpc_opt=services_namespace=grpc_gen"
    "--plugin=protoc-gen-grpc=${GRPC_CPP_PLUGIN}"
    ${SERVICE_INTERFACE_GRPC_PROTO_SRCS}
  DEPENDS
    "${PROTOC_HOST_TARGET}"
    "${GRPC_CPP_PLUGIN_TARGET}"
)

add_library(falken_proto
  ${SERVICE_INTERFACE_GENERATED_SRCS}
  ${SERVICE_INTERFACE_GRPC_GENERATED_SRCS}
  "${CORE_SOURCE_DIR}/protos.h"
)

target_include_directories(falken_proto
  PUBLIC
    "${PROTO_OUTPUT_DIR}"
    # gRPC generated files include files relative to the parent directoy of
    # the gRPC project. e.g grpc/include/grpcpp/grpcpp.h
    # Unfortunately, grpc++ does not add the correct include path either so
    # manually set it here.
    "${grpc_SOURCE_DIR}/.."
)

target_link_libraries(falken_proto
  PUBLIC
    protobuf::libprotobuf
    protobuf::libprotobuf-lite
    grpc++
    ${SERVICE_INTERFACE_DEPENDENCIES}
)

if(FALKEN_CPP_SDK_PUBLIC_DEFINES)
  target_compile_definitions(falken_proto
    PUBLIC
      ${FALKEN_CPP_SDK_PUBLIC_DEFINES}
  )
endif()

set(PYTHON_BINARY_TO_ARRAY_SCRIPT
  "${CMAKE_CURRENT_LIST_DIR}/../tools/binary_to_array.py"
)

if("${FALKEN_LOCAL_CERT}" STREQUAL "")
  # Get the path to the cert, assuming it's under the project root.
  set(FALKEN_LOCAL_CERT "${FALKEN_PROJECT_ROOT_DIR}/service/cert.pem")
endif()

if(NOT EXISTS "${FALKEN_LOCAL_CERT}")
  message(FATAL_ERROR "FALKEN_LOCAL_CERT references file ${FALKEN_LOCAL_CERT} \
    that does not exist. A local SSL cert is required to connect to Falken.")
endif()

set(CERTS_OUTPUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated_certs")
file(MAKE_DIRECTORY "${CERTS_OUTPUT_DIR}/src/core")
set(PUBLIC_CERT_SRC
  "${CERTS_OUTPUT_DIR}/src/core/public_grpc_roots_pem.cc"
  "${CERTS_OUTPUT_DIR}/src/core/public_grpc_roots_pem.h"
)
set(TEST_CERT_SRC
  "${CERTS_OUTPUT_DIR}/src/core/local_grpc_roots_pem.cc"
  "${CERTS_OUTPUT_DIR}/src/core/local_grpc_roots_pem.h"
)

add_custom_command(
  OUTPUT
    ${PUBLIC_CERT_SRC}
  COMMAND
    "${PYTHON}" ${PYTHON_BINARY_TO_ARRAY_SCRIPT}
    --output_header=${CERTS_OUTPUT_DIR}/src/core/public_grpc_roots_pem.h
    --output_source=${CERTS_OUTPUT_DIR}/src/core/public_grpc_roots_pem.cc
    --cpp_namespace=falken::core
    --array=public_grpc_roots_pem_data
    --array_size=public_grpc_roots_pem_size
    --filename_identifier=public_grpc_roots_pem_filename
    --input "${GRPC_PROJECT_DIR}/etc/roots.pem"
)

add_custom_command(
  OUTPUT
    ${TEST_CERT_SRC}
  COMMAND
    "${PYTHON}" ${PYTHON_BINARY_TO_ARRAY_SCRIPT}
    --output_header=${CERTS_OUTPUT_DIR}/src/core/local_grpc_roots_pem.h
    --output_source=${CERTS_OUTPUT_DIR}/src/core/local_grpc_roots_pem.cc
    --cpp_namespace=falken::core
    --array=local_grpc_roots_pem_data
    --array_size=local_grpc_roots_pem_size
    --filename_identifier=local_grpc_roots_pem_filename
    --input "${FALKEN_LOCAL_CERT}"
)

add_library(falken_grpc_roots_pem
  ${PUBLIC_CERT_SRC}
  ${TEST_CERT_SRC}
)

target_include_directories(falken_grpc_roots_pem
  PUBLIC
    "${CERTS_OUTPUT_DIR}"
)

if(FALKEN_CPP_SDK_CSHARP)
  # When building for a garbage collected language like C# we serialize the
  # destruction of all objects to prevent C++ destructors that access shared
  # resources from executing on garbage collection threads in parallel.
  list(APPEND FALKEN_CPP_SDK_PRIVATE_DEFINES "-DFALKEN_SYNC_DESTRUCTION=1")
  # Enable C# specific logic.
  list(APPEND FALKEN_CPP_SDK_PRIVATE_DEFINES "-DFALKEN_CSHARP")
endif()

# List of .cc files that should be compiled as Obj-C++ on macOS.
#
# We have Obj-C++ in .cc files for compatibility with internal cc_library()
# build rules. As of version 3.17.x CMake doesn't allow per file language
# configuration that works reliably across generators. Setting the LANGUAGE
# file property to OBJCXX breaks debug configuration in Xcode builds and does
# not work in Makefiles builds. Setting adding -ObjC++ to target compilation
# options is overridden by the target language. The following approach of
# copy and renaming source files allows sources to be stored in .cc files but
# compiled as Obj-C++ (.mm) files.
# Additionaly, some xcode versions require that the static and shared
# versions of the library do not share these mm files, so this macro
# is used to create a copy for each.
#
# FALKEN_CORE_OBJCXX_FILES: Variable with a list of files that need to be
#   copied/renamed.
# FALKEN_CORE_C_OBJCXX_FILES: Output variable where a list of the generated
#   source files is stored.
# PREFIX: Type of library the libraries will be used with [STATIC|SHARED].
macro(create_cppobj_source_copy_files
          FALKEN_CORE_OBJCXX_FILES
          FALKEN_CORE_C_OBJCXX_FILES
          PREFIX)
  set(${FALKEN_CORE_C_OBJCXX_FILES} "")
  foreach(INPUT_FILENAME ${${FALKEN_CORE_OBJCXX_FILES}})
    file(RELATIVE_PATH FILENAME "${CORE_SOURCE_DIR}" "${INPUT_FILENAME}")
    get_filename_component(DIRECTORY "${FILENAME}" DIRECTORY)
    get_filename_component(BASENAME "${FILENAME}" NAME_WE)
    if(CMAKE_SYSTEM_NAME STREQUAL "Darwin")
      set(OUTPUT_FILENAME
        "${CORE_SOURCE_GENERATED_DIR}/${DIRECTORY}/${PREFIX}${BASENAME}.mm"
      )
    else()
      set(OUTPUT_FILENAME
        "${CORE_SOURCE_GENERATED_DIR}/${DIRECTORY}/${PREFIX}${BASENAME}.cc"
      )
    endif()
    add_custom_command(OUTPUT "${OUTPUT_FILENAME}"
      COMMAND ${CMAKE_COMMAND} -E copy "${INPUT_FILENAME}" "${OUTPUT_FILENAME}"
      DEPENDS "${INPUT_FILENAME}"
    )
    list(APPEND ${FALKEN_CORE_C_OBJCXX_FILES} "${OUTPUT_FILENAME}")
  endforeach()
endmacro()

set(FALKEN_CORE_OBJCXX_FILES
  "${CORE_SOURCE_DIR}/temp_file.cc"
)

add_library(falken_common STATIC
  "${CORE_SOURCE_DIR}/model_signature.cc"
  "${CORE_SOURCE_DIR}/model_signature.h"
  "${CORE_SOURCE_DIR}/status_macros.h"
  "${CORE_SOURCE_DIR}/statusor.h"
  "${CORE_SOURCE_DIR}/tensor.cc"
  "${CORE_SOURCE_DIR}/tensor.h"
)
target_include_directories(falken_common
  PUBLIC
    "${FALKEN_CPP_SDK_DIR}"
)
target_link_libraries(falken_common
  PUBLIC
    falken_proto
    absl::status
)

set(FALKEN_CORE_C_SRC
  "${CORE_SOURCE_DIR}/absl_log_sink.cc"
  "${CORE_SOURCE_DIR}/active_session.cc"
  "${CORE_SOURCE_DIR}/callback.cc"
  "${CORE_SOURCE_DIR}/client_info.cc"
  "${CORE_SOURCE_DIR}/falken_core.cc"
  "${CORE_SOURCE_DIR}/falken_core_options.cc"
  "${CORE_SOURCE_DIR}/file_logger.cc"
  "${CORE_SOURCE_DIR}/grpc_utils.cc"
  "${CORE_SOURCE_DIR}/log.cc"
  "${CORE_SOURCE_DIR}/logger_base.cc"
  "${CORE_SOURCE_DIR}/logger_notifier.cc"
  "${CORE_SOURCE_DIR}/model.cc"
  "${CORE_SOURCE_DIR}/option_accessor.cc"
  "${CORE_SOURCE_DIR}/scheduler.cc"
  "${CORE_SOURCE_DIR}/service_environment.cc"
  "${CORE_SOURCE_DIR}/specs.cc"
  "${CORE_SOURCE_DIR}/status_converter.cc"
  "${CORE_SOURCE_DIR}/stdout_logger.cc"
  "${CORE_SOURCE_DIR}/system_logger.cc"
  "${CORE_SOURCE_DIR}/unpack_model.cc"
  "${CORE_SOURCE_DIR}/uuid4.cc"
)

set(FALKEN_CORE_C_HDRS
  "${CORE_SOURCE_DIR}/absl_log_sink.h"
  "${CORE_SOURCE_DIR}/active_session.h"
  "${CORE_SOURCE_DIR}/assert.h"
  "${CORE_SOURCE_DIR}/callback.h"
  "${CORE_SOURCE_DIR}/child_resource_map.h"
  "${CORE_SOURCE_DIR}/client_info.h"
  "${CORE_SOURCE_DIR}/falken_core.h"
  "${CORE_SOURCE_DIR}/falken_core_options.h"
  "${CORE_SOURCE_DIR}/grpc_utils.h"
  "${CORE_SOURCE_DIR}/log.h"
  "${CORE_SOURCE_DIR}/logger_base.h"
  "${CORE_SOURCE_DIR}/macros.h"
  "${CORE_SOURCE_DIR}/model.h"
  "${CORE_SOURCE_DIR}/option_accessor.h"
  "${CORE_SOURCE_DIR}/scheduler.h"
  "${CORE_SOURCE_DIR}/service_environment.h"
  "${CORE_SOURCE_DIR}/specs.h"
  "${CORE_SOURCE_DIR}/status_converter.h"
  "${CORE_SOURCE_DIR}/stdout_logger.h"
  "${CORE_SOURCE_DIR}/temp_file.h"
  "${CORE_SOURCE_DIR}/unpack_model.h"
  "${CORE_SOURCE_DIR}/uuid4.h"
  "${CORE_SOURCE_DIR}/vector_search.h"
)

set(TF_WRAPPER_SOURCE_DIR "${CMAKE_CURRENT_LIST_DIR}/../tf_wrapper")

set(CPP_SDK_SRCS
  "${CORE_SOURCE_DIR}/action_proto_converter.cc"
  "${CORE_SOURCE_DIR}/actions.cc"
  "${CORE_SOURCE_DIR}/allocator.cc"
  "${CORE_SOURCE_DIR}/attribute.cc"
  "${CORE_SOURCE_DIR}/attribute_proto_converter.cc"
  "${CORE_SOURCE_DIR}/brain.cc"
  "${CORE_SOURCE_DIR}/brain_spec.cc"
  "${CORE_SOURCE_DIR}/brain_spec_proto_converter.cc"
  "${CORE_SOURCE_DIR}/entity.cc"
  "${CORE_SOURCE_DIR}/entity_proto_converter.cc"
  "${CORE_SOURCE_DIR}/episode.cc"
  "${CORE_SOURCE_DIR}/globals.cc"
  "${CORE_SOURCE_DIR}/observation_proto_converter.cc"
  "${CORE_SOURCE_DIR}/observations.cc"
  "${CORE_SOURCE_DIR}/primitives.cc"
  "${CORE_SOURCE_DIR}/service.cc"
  "${CORE_SOURCE_DIR}/session.cc"
)

set(CPP_SDK_PUBLIC_HEADERS
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/actions.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/allocator.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/attribute_base.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/attribute_container.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/attribute.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/bool_attribute.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/brain.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/brain_spec.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/categorical_attribute.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/config.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/entity.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/episode.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/falken.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/feelers_attribute.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/fixed_size_vector.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/joystick_attribute.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/log.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/number_attribute.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/observations.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/position_attribute.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/primitives.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/rotation_attribute.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/service.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/session.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/types.h"
  "${PUBLIC_CPP_API_SOURCE_DIR}/falken/unconstrained_attribute.h"
)

set(CPP_SDK_HDRS
  "${CORE_SOURCE_DIR}/action_proto_converter.h"
  "${CORE_SOURCE_DIR}/attribute_internal.h"
  "${CORE_SOURCE_DIR}/attribute_proto_converter.h"
  "${CORE_SOURCE_DIR}/brain_spec_proto_converter.h"
  "${CORE_SOURCE_DIR}/entity_proto_converter.h"
  "${CORE_SOURCE_DIR}/episode_internal.h"
  "${CORE_SOURCE_DIR}/globals.h"
  "${CORE_SOURCE_DIR}/observation_proto_converter.h"
  "${CORE_SOURCE_DIR}/session_internal.h"
  "${CPP_SDK_PUBLIC_HEADERS}"
)

# Macro that generates a library target called TARGET_NAME that is
# either shared or static dependent upon the value of LIBRARY_TYPE.
#
# TARGET_NAME: Name of the library target to add.
# LIBRARY_TYPE: Type of library can be one of [STATIC | SHARED].
macro(falken_cpp_sdk_library TARGET_NAME LIBRARY_TYPE)
  if(NOT ("${LIBRARY_TYPE}" MATCHES "(SHARED|STATIC)"))
    message(FATAL_ERROR
      "Unsupported library type ${LIBRARY_TYPE} for target ${TARGET_NAME}"
    )
  endif()

  create_cppobj_source_copy_files(
    FALKEN_CORE_OBJCXX_FILES FALKEN_CORE_C_OBJCXX_FILES ${LIBRARY_TYPE})

  add_library(${TARGET_NAME} ${LIBRARY_TYPE}
    ${CPP_SDK_SRCS}
    ${CPP_SDK_HDRS}
    ${FALKEN_CORE_C_SRC}
    ${FALKEN_CORE_C_OBJCXX_FILES}
  )

  # Enable the Hardened Runtime on macOS dynamic library targets.
  if(CMAKE_SYSTEM_NAME STREQUAL "Darwin")
    set(MACOS_DYLIB_TARGET_PROPERTIES
      XCODE_ATTRIBUTE_ENABLE_HARDENED_RUNTIME YES)
  endif()

  set_target_properties(${TARGET_NAME}
    PROPERTIES
      PUBLIC_HEADER "${CPP_SDK_PUBLIC_HEADERS}"
      ${MACOS_DYLIB_TARGET_PROPERTIES}
  )

  set(FALKEN_STATIC_LIBRARY_DEPENDENCIES
    falken_common
    falken_proto
    falken_grpc_roots_pem
    falken_tf_wrapper
    absl::status
    absl::strings
    absl::synchronization
    absl::time
  )
  set(FALKEN_SHARED_LIBRARY_DEPENDENCIES "")

  if(CMAKE_SYSTEM_NAME MATCHES "Android")
    list(APPEND FALKEN_STATIC_LIBRARY_DEPENDENCIES ${ANDROID_LOG})
  endif()

  target_link_libraries(${TARGET_NAME}
    PUBLIC
      ${FALKEN_STATIC_LIBRARY_DEPENDENCIES}
      ${FALKEN_SHARED_LIBRARY_DEPENDENCIES}
  )

  # temp_file.cc uses Obj-C++ and depends upon the Foundation framework.
  set(FALKEN_LINK_OPTIONS "")
  if(CMAKE_SYSTEM_NAME STREQUAL "Darwin")
    list(APPEND FALKEN_LINK_OPTIONS -framework Foundation)
  endif()
  target_link_options(${TARGET_NAME} PUBLIC ${FALKEN_LINK_OPTIONS})

  target_include_directories(${TARGET_NAME}
    PUBLIC
      "${PUBLIC_CPP_API_SOURCE_DIR}"
    PRIVATE
      "${FALKEN_CPP_SDK_DIR}"
  )

  set(PRIVATE_DEFINES ${FALKEN_CPP_SDK_PRIVATE_DEFINES})
  set(PUBLIC_DEFINES ${FALKEN_CPP_SDK_PUBLIC_DEFINES})

  if("${LIBRARY_TYPE}" STREQUAL "SHARED")
    # Enable export of symbols from DLL.
    list(APPEND PRIVATE_DEFINES "-DFALKEN_BUILD_DLL=1")
  else()
    # Do not mark public symbols for export / import when building or using the
    # library.
    list(APPEND PUBLIC_DEFINES "-DFALKEN_STATIC_LIBRARY=1")
  endif()

  if(PRIVATE_DEFINES)
    target_compile_definitions(${TARGET_NAME} PRIVATE ${PRIVATE_DEFINES})
  endif()
  if(PUBLIC_DEFINES)
    target_compile_definitions(${TARGET_NAME} PUBLIC ${PUBLIC_DEFINES})
  endif()

  # Only expose public API symbols in dynamic libraries.
  if("${LIBRARY_TYPE}" STREQUAL "SHARED")
    if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
      target_link_options(${TARGET_NAME}
        PUBLIC
          ${FALKEN_LINK_OPTIONS}
        PRIVATE
          "-Wl,-version-script,${EXPORT_SYMBOLS_FILE_LINUX}")
    elseif(CMAKE_SYSTEM_NAME STREQUAL "Darwin")
      # We have to use unexported_symbols_list instead of exported_symbols_list
      # since using the latter shows a bunch of warning messages if we
      # want to filter symbols by using "falken" as keyword only.
      target_link_options(${TARGET_NAME}
        PUBLIC
          ${FALKEN_LINK_OPTIONS}
        PRIVATE
        "-Wl,-unexported_symbols_list,${UNEXPORT_SYMBOLS_FILE_MAC}")

      # Make sure that only C symbols starting with _FC and C++ symbols
      # containing falken are exported.
      set(CHECK_SYMBOLS "${CMAKE_CURRENT_BINARY_DIR}/check_symbols.awk")
      file(WRITE "${CHECK_SYMBOLS}" "\
         BEGIN { c = 0; }
         {
           skip = 0;
           for (i = 3; i <= NF; i++) {
             if ($i ~ /^(_FC|falken)/) {
               skip = 1;
               break;
             }
           }
           if (skip) next;
         }
         { c += 1; print \"Found unexpected exported symbol: \" \$0; }
         END { if (c > 0) { exit 1; } }"
      )
      set(EXPORTED_SYMBOLS "${CMAKE_CURRENT_BINARY_DIR}/exported_symbols.txt")
      add_custom_command(
        TARGET ${TARGET_NAME}
        POST_BUILD
        # Dump demangled exported symbols to a file.
        COMMAND ${CMAKE_NM} -gU --demangle $<TARGET_FILE:${TARGET_NAME}>
          > "${EXPORTED_SYMBOLS}"
        # Check no unexpected symbols were found.
        COMMAND awk -f "${CHECK_SYMBOLS}" "${EXPORTED_SYMBOLS}"
        BYPRODUCTS
          "${EXPORTED_SYMBOLS}"
        VERBATIM
      )
    elseif(CMAKE_SYSTEM_NAME STREQUAL "Windows")
      string(CONCAT FALKEN_CPP_SDK_BASENAME
        "$<TARGET_FILE_DIR:${TARGET_NAME}>/"
        "$<TARGET_FILE_PREFIX:${TARGET_NAME}>"
        "$<TARGET_FILE_BASE_NAME:${TARGET_NAME}>"
      )
      set(FALKEN_CPP_SDK_PDB ${FALKEN_CPP_SDK_BASENAME}.pdb)
      # Generate symbols in all build configurations.
      target_compile_options(${TARGET_NAME} PRIVATE /Zi)
      target_link_options(${TARGET_NAME}
        PUBLIC
          ${FALKEN_LINK_OPTIONS}
        PRIVATE
          /DEBUG
          /PDB:${FALKEN_CPP_SDK_BASENAME}_full.pdb
          /PDBSTRIPPED:${FALKEN_CPP_SDK_PDB}
       )
    else()
      target_link_options(${TARGET_NAME} PUBLIC ${FALKEN_LINK_OPTIONS})
    endif()
    # When compiling as a shared library, the library transitively links all
    # required dependencies so disable linking of static library dependencies.
    set_target_properties(${TARGET_NAME} PROPERTIES INTERFACE_LINK_DEPENDS "")
    if(FALKEN_SHARED_LIBRARY_DEPENDENCIES)
      set_target_properties(${TARGET_NAME} PROPERTIES
        INTERFACE_LINK_LIBRARIES ${FALKEN_SHARED_LIBRARY_DEPENDENCIES}
        LINK_INTERFACE_LIBRARIES ${FALKEN_SHARED_LIBRARY_DEPENDENCIES}
      )
    else()
      set_target_properties(${TARGET_NAME} PROPERTIES
        INTERFACE_LINK_LIBRARIES ""
        LINK_INTERFACE_LIBRARIES ""
      )
    endif()
  else()
    target_link_options(${TARGET_NAME} PUBLIC ${FALKEN_LINK_OPTIONS})
  endif()
endmacro()

falken_cpp_sdk_library(falken_cpp_sdk SHARED)
falken_cpp_sdk_library(falken_cpp_sdk_static STATIC)

# Add the platform name to the install directory since we may need to
# redistribute separate libraries for different platforms with the same name.
if(CMAKE_SYSTEM_NAME MATCHES "Windows")
  set(LIB_INSTALL_DIR "lib/Windows")
elseif(CMAKE_SYSTEM_NAME MATCHES "Darwin")
  set(LIB_INSTALL_DIR "lib/Darwin")
elseif(CMAKE_SYSTEM_NAME MATCHES "Android")
  set(LIB_INSTALL_DIR "lib/Android")
elseif(CMAKE_SYSTEM_NAME MATCHES "Linux" AND
  CMAKE_SYSTEM_VERSION MATCHES "Ggp")
  set(LIB_INSTALL_DIR "lib/Stadia")
elseif(CMAKE_SYSTEM_NAME MATCHES "Linux" AND
  CMAKE_SYSTEM_VERSION MATCHES "CrosstoolGrte")
  set(LIB_INSTALL_DIR "lib/Crosstool")
elseif(CMAKE_SYSTEM_NAME MATCHES "Linux")
  set(LIB_INSTALL_DIR "lib/Linux")
else()
  message(WARNING "Platform currently unsupported: \
    ${CMAKE_SYSTEM_NAME}-${CMAKE_SYSTEM_VERSION}.")
  set(LIB_INSTALL_DIR "lib/${CMAKE_SYSTEM_NAME}-${CMAKE_SYSTEM_VERSION}")
endif()

# Add the build type to the install directory since we may need to redistribute
# separate libraries built against Debug vs. Release runtime libraries.
set(BUILD_CONFIGS Debug Release)
foreach(CONFIG ${BUILD_CONFIGS})
  set(LIB_INSTALL_PATH "${LIB_INSTALL_DIR}/${CONFIG}")
  install(TARGETS falken_cpp_sdk
    CONFIGURATIONS "${CONFIG}"
    RUNTIME DESTINATION "${LIB_INSTALL_PATH}"
    LIBRARY DESTINATION "${LIB_INSTALL_PATH}"
    ARCHIVE DESTINATION "${LIB_INSTALL_PATH}"
    COMPONENT falken_cpp
    PUBLIC_HEADER DESTINATION "include"
  )
  if(CMAKE_SYSTEM_NAME MATCHES "Windows")
    install(FILES ${FALKEN_CPP_SDK_PDB}
      CONFIGURATIONS "${CONFIG}"
      DESTINATION "${LIB_INSTALL_PATH}"
      COMPONENT falken_cpp
    )
  endif()
endforeach()

if(FALKEN_CPP_SDK_CSHARP)
  message(STATUS "Creating C# SWIG library")
  find_package(SWIG REQUIRED)
  include(UseSWIG)
  set(SWIG_FALKEN_MODULE_FILE
    "${CORE_SOURCE_DIR}/swig/falken_module.i"
  )
  set(SWIG_FALKEN_INTERFACE_FILES
    "${CORE_SOURCE_DIR}/swig/actions.i"
    "${CORE_SOURCE_DIR}/swig/allocator.i"
    "${CORE_SOURCE_DIR}/swig/attribute_base.i"
    "${CORE_SOURCE_DIR}/swig/attribute_container.i"
    "${CORE_SOURCE_DIR}/swig/attribute.i"
    "${CORE_SOURCE_DIR}/swig/bool_attribute.i"
    "${CORE_SOURCE_DIR}/swig/brain.i"
    "${CORE_SOURCE_DIR}/swig/brain_spec.i"
    "${CORE_SOURCE_DIR}/swig/categorical_attribute.i"
    "${CORE_SOURCE_DIR}/swig/config.i"
    "${CORE_SOURCE_DIR}/swig/entity.i"
    "${CORE_SOURCE_DIR}/swig/episode.i"
    "${CORE_SOURCE_DIR}/swig/falken_module.i"
    "${CORE_SOURCE_DIR}/swig/feelers_attribute.i"
    "${CORE_SOURCE_DIR}/swig/fixed_size_vector.i"
    "${CORE_SOURCE_DIR}/swig/log.i"
    "${CORE_SOURCE_DIR}/swig/null_check_this.i"
    "${CORE_SOURCE_DIR}/swig/number_attribute.i"
    "${CORE_SOURCE_DIR}/swig/observations.i"
    "${CORE_SOURCE_DIR}/swig/position_attribute.i"
    "${CORE_SOURCE_DIR}/swig/primitives.i"
    "${CORE_SOURCE_DIR}/swig/rotation_attribute.i"
    "${CORE_SOURCE_DIR}/swig/service.i"
    "${CORE_SOURCE_DIR}/swig/session.i"
    "${CORE_SOURCE_DIR}/swig/types.i"
    "${CORE_SOURCE_DIR}/swig/unconstrained_attribute.i"
    "${SWIG_FALKEN_MODULE_FILE}"
  )

  # Copy of the module file that is updated when any interface files change.
  set(SWIG_FALKEN_MODULE_FILE_INTERMEDIATE
    "${CMAKE_CURRENT_BINARY_DIR}/falken_module.i"
  )
  add_custom_command(
    OUTPUT
      "${SWIG_FALKEN_MODULE_FILE_INTERMEDIATE}"
    COMMAND
      "${CMAKE_COMMAND}" -E copy "${SWIG_FALKEN_MODULE_FILE}"
        "${SWIG_FALKEN_MODULE_FILE_INTERMEDIATE}"
    DEPENDS
      ${SWIG_FALKEN_INTERFACE_FILES}
  )

  foreach(SWIG_FILENAME ${SWIG_FALKEN_INTERFACE_FILES}
                        ${SWIG_FALKEN_MODULE_FILE_INTERMEDIATE})
    set_property(SOURCE ${SWIG_FILENAME} PROPERTY CPLUSPLUS ON)
    # -dllimport falken_csharp_sdk: Sets all P/Invoke import statements to use
    # falken_csharp_sdk rather than the basename of the library filename e.g
    # "libfalken_csharp" for "libfalken_csharp.so" on Linux. This makes it
    # possible for the C# runtime to load the library without a dllmap
    # (see https://www.mono-project.com/docs/advanced/pinvoke/dllmap/) on
    # all target platforms.
    set_property(SOURCE ${SWIG_FILENAME} PROPERTY COMPILE_OPTIONS
      -dllimport falken_csharp_sdk
    )
  endforeach(SWIG_FILENAME)
  set(FALKEN_CSHARP_SOURCES_DIR "${CMAKE_CURRENT_BINARY_DIR}/falken_csharp")

  swig_add_library(falken_csharp_sdk
    TYPE SHARED
    LANGUAGE csharp
    OUTPUT_DIR "${FALKEN_CSHARP_SOURCES_DIR}"
    OUTFILE_DIR "${FALKEN_CSHARP_SOURCES_DIR}"
    SOURCES "${SWIG_FALKEN_MODULE_FILE_INTERMEDIATE}"
  )
  set_property(TARGET falken_csharp_sdk
    PROPERTY SWIG_USE_TARGET_INCLUDE_DIRECTORIES TRUE
  )
  # Workaround https://gitlab.kitware.com/cmake/cmake/-/issues/21542
  # by manually setting the library prefix.
  # This makes it possible for the C# runtime to load the library without a
  # dllmap (see https://www.mono-project.com/docs/advanced/pinvoke/dllmap/) on
  # all target platforms.
  set_property(TARGET falken_csharp_sdk PROPERTY PREFIX
    "${CMAKE_SHARED_LIBRARY_PREFIX}"
  )
  # -namespace FalkenInternal moves all generated code into the FalkenInternal
  # C# namespace.
  # -DSWIG_CSHARP_NO_IMCLASS_STATIC_CONSTRUCTOR disables static constructor
  # generation for the P/Invoke module so that it can instead be customized
  # in falken_module.i.
  # -Werror treats warnings as errors.
  set_property(TARGET falken_csharp_sdk
    PROPERTY SWIG_COMPILE_OPTIONS
      -namespace FalkenInternal
      -DSWIG_CSHARP_NO_IMCLASS_STATIC_CONSTRUCTOR
      -Werror
  )
  target_include_directories(falken_csharp_sdk
    PUBLIC
      "${FALKEN_CPP_SDK_DIR}"
  )
  target_link_libraries(falken_csharp_sdk PRIVATE falken_cpp_sdk_static)
  target_compile_definitions(falken_csharp_sdk PRIVATE -DFALKEN_CSHARP)
  if(CMAKE_SYSTEM_NAME STREQUAL "Darwin")
    set_target_properties(falken_csharp_sdk
      PROPERTIES
        ${MACOS_DYLIB_TARGET_PROPERTIES}
    )
  endif()

  set(FALKEN_CSHARP_SOURCES_RELATIVE_PATHS
    falken/ActionsBase.cs
    falken/AttributeBase.cs
    falken/AttributeContainer.cs
    falken/AxesMode.cs
    falken/BoolAttribute.cs
    falken/BrainBase.cs
    falken/BrainSpecBase.cs
    falken/CategoricalAttribute.cs
    falken/ControlFrame.cs
    falken/ControlledEntity.cs
    falken/EntityBase.cs
    falken/EntityContainer.cs
    falken/Episode.cs
    falken/EulerAngles.cs
    falken/FeelersAttribute.cs
    falken/FileLogger.cs
    falken/FixedSizeCategoricalAttributeVector.cs
    falken/FixedSizeNumberAttributeVector.cs
    falken/JoystickAttribute.cs
    falken/LogLevel.cs
    falken/LoggerBase.cs
    falken/LoggerNotifier.cs
    falken/NumberAttribute.cs
    falken/ObservationsBase.cs
    falken/Position.cs
    falken/PositionAttribute.cs
    falken/PositionAttributeBase.cs
    falken/Rotation.cs
    falken/RotationAttribute.cs
    falken/RotationAttributeBase.cs
    falken/Service.cs
    falken/Session.cs
    falken/SystemLogger.cs
    falken/Vector3.cs
    falken_module.cs
    falken_modulePINVOKE.cs
    std/AttributeVector.cs
    std/BrainPtr.cs
    std/BrainVector.cs
    std/CategoricalAttributeVector.cs
    std/EntityBaseVector.cs
    std/EpisodePtr.cs
    std/EpisodeVector.cs
    std/NumberAttributeVector.cs
    std/ServicePtr.cs
    std/SessionPtr.cs
    std/SessionVector.cs
    std/StringSet.cs
    std/StringVector.cs
  )
  set(FALKEN_CSHARP_SOURCES "")
  foreach(CSHARP_SOURCE ${FALKEN_CSHARP_SOURCES_RELATIVE_PATHS})
    list(APPEND FALKEN_CSHARP_SOURCES
      "${FALKEN_CSHARP_SOURCES_DIR}/${CSHARP_SOURCE}"
    )
  endforeach()
  set_source_files_properties(FALKEN_CSHARP_SOURCES
      PROPERTIES GENERATED TRUE
  )
  # Expose FALKEN_CSHARP_SOURCES and related variables to other parts
  # of the project.
  if(NOT "${CMAKE_PROJECT_NAME}" STREQUAL "${PROJECT_NAME}")
    set(FALKEN_CSHARP_SOURCES_DIR "${FALKEN_CSHARP_SOURCES_DIR}" PARENT_SCOPE)
    set(FALKEN_CSHARP_SOURCES "${FALKEN_CSHARP_SOURCES}"
      PARENT_SCOPE
    )
    set(FALKEN_CSHARP_SOURCES_RELATIVE_PATHS
      "${FALKEN_CSHARP_SOURCES_RELATIVE_PATHS}"
      PARENT_SCOPE
    )
  endif()
endif()

# Build documentation.
set(FALKEN_DOCS_DIR "${CMAKE_CURRENT_BINARY_DIR}/docs" CACHE INTERNAL "")
file(MAKE_DIRECTORY "${FALKEN_DOCS_DIR}")

if(FALKEN_CPP_SDK_GENERATE_API_REFERENCE)
  find_package(Doxygen)
  if(DOXYGEN_FOUND)
    set(DOXYGEN_PROJECT_NAME "Falken C++ SDK")
    set(DOXYGEN_PROJECT_NUMBER "${FALKEN_SDK_VERSION}")
    set(DOXYGEN_OUTPUT_DIRECTORY "${FALKEN_DOCS_DIR}")

    doxygen_add_docs(
      generate_docs_target
      ${CPP_SDK_PUBLIC_HEADERS}
      ALL
      COMMENT "Generate C++ SDK API docs for Falken."
    )
  else()
    message(WARNING "Doxygen or Graphviz not installed. "
      "Unable to generate documentation."
    )
  endif()
endif()

if(FALKEN_ENABLE_CPP_UNIT_TESTS)
  enable_testing()
  find_package(GTest REQUIRED)

  include(GoogleTest)
  include(CTest)

  # Disable tests in other projects (like Eigen) that use CTest.
  set(BUILD_TESTING OFF CACHE BOOL "Disable tests." FORCE)

  # The test resource_id_test requires two extra files which are not included
  # in the main library.
  add_library(resource_id
    "${CORE_SOURCE_DIR}/resource_id.cc"
    "${CORE_SOURCE_DIR}/resource_id.h"
  )
  target_include_directories(resource_id
    PUBLIC
      "${PUBLIC_CPP_API_SOURCE_DIR}"
      "${PROTO_OUTPUT_DIR}"
      "${FALKEN_CPP_SDK_DIR}"
  )
  target_compile_definitions(resource_id
    PUBLIC
      ${FALKEN_CPP_SDK_PUBLIC_DEFINES}
    PRIVATE
      ${FALKEN_CPP_SDK_PRIVATE_DEFINES}
  )
  target_link_libraries(resource_id PUBLIC falken_cpp_sdk_static)

  # Generate rules to build and run a C++ SDK test file TEST_SRC_FILE.
  #
  # Each unit test case is run in a separate process unless
  # the DISABLE_TEST_DISCOVERY option is specified which runs all unit tests in
  # the same process.
  #
  # Arguments for a test executable can be specified after the TEST_ARGS option.
  function(cpp_build_test TEST_SRC_FILE)
    set(OPTIONS DISABLE_TEST_DISCOVERY)
    set(MULTI_VALUE_KEYWORDS TEST_ARGS)
    cmake_parse_arguments(ARGS
      "${OPTIONS}"
      ""
      "${MULTI_VALUE_KEYWORDS}"
      ${ARGN}
    )
    get_filename_component(TARGET_NAME ${TEST_SRC_FILE} NAME_WE)

    message("Adding test ${TARGET_NAME}")
    add_executable(${TARGET_NAME} ${TEST_SRC_FILE})
    target_include_directories(${TARGET_NAME}
      PRIVATE
        "${FALKEN_CPP_SDK_DIR}"
        "${PROTO_OUTPUT_DIR}"
    )
    target_compile_definitions(${TARGET_NAME}
      PRIVATE
        ${FALKEN_CPP_SDK_PRIVATE_DEFINES}
    )
    target_link_libraries(${TARGET_NAME}
      absl_flags
      absl_flags_parse
      falken_cpp_sdk_static
      example_model
      absl::base
      absl::flags
      absl::flags_parse
      resource_id
      gmock_main
    )
    target_link_options(${TARGET_NAME} PUBLIC ${FALKEN_LINK_OPTIONS})

    if(ARGS_DISABLE_TEST_DISCOVERY)
      add_test(
        NAME ${TARGET_NAME}
        COMMAND ${TARGET_NAME}
          ${ARGS_TEST_ARGS}
      )
    else()
      gtest_discover_tests(${TARGET_NAME}
        EXTRA_ARGS
          ${ARGS_TEST_ARGS}
      )
    endif()
  endfunction()

  cpp_build_test("${CORE_SOURCE_DIR}/absl_log_sink_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/action_proto_converter_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/actions_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/allocator_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/attribute_proto_converter_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/attribute_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/brain_spec_proto_converter_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/callback_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/child_resource_map_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/client_info_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/entity_proto_converter_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/entity_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/file_logger_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/grpc_utils_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/log_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/logger_base_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/logger_notifier_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/model_signature_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/model_test.cc"
    TEST_ARGS
      --example_model_path
      "${CMAKE_CURRENT_LIST_DIR}/../tf_wrapper/example_model"
  )
  cpp_build_test("${CORE_SOURCE_DIR}/observation_proto_converter_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/observations_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/option_accessor_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/primitives_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/scheduler_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/semaphore_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/resource_id_test.cc")

  if(FALKEN_ENABLE_CPP_SERVICE_TESTS)
    set(FLAGS "")
    #
    if(NOT "${FALKEN_PROJECT_ID}" STREQUAL "")
      list(APPEND FLAGS "--project_id" "${FALKEN_PROJECT_ID}")
    endif()
    if(NOT "${FALKEN_API_KEY}" STREQUAL "")
      list(APPEND FLAGS "--api_key" "${FALKEN_API_KEY}")
    endif()
    if(NOT "${FALKEN_JSON_CONFIG_FILE}" STREQUAL "")
      list(APPEND FLAGS "--json_config_file" "${FALKEN_JSON_CONFIG_FILE}")
    endif()
    cpp_build_test("${CORE_SOURCE_DIR}/service_test.cc"
      DISABLE_TEST_DISCOVERY
      TEST_ARGS
        ${FLAGS}
    )
  endif()

  cpp_build_test("${CORE_SOURCE_DIR}/specs_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/status_converter_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/status_macros_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/system_logger_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/temp_file_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/tensor_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/unpack_model_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/uuid4_test.cc")
  cpp_build_test("${CORE_SOURCE_DIR}/vector_search_test.cc")
endif()
