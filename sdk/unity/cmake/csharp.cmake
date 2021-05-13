# Copyright 2019 Google LLC
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

# Integration with the C# build system.
#
# This module provides the following rules:
#  CSharpAddExternalProject: Import a C# project as a build target.
#  CSharpAddExternalDll: Import a C# assembly as a build target.
#  CSharpAddLibrary: Compile a C# library assembly.
#  CSharpAddExecutable: Compile a C# executable assembly.

set(CSHARP_PROJECT_TEMPLATE
  "${CMAKE_CURRENT_LIST_DIR}/csharp_project_csproj.template"
)

set(CSHARP_BUILD_VERBOSITY "minimal" CACHE STRING
  "Verbosity of C# build tool. [quiet|minimal|normal|detailed|diagnostic]"
)

define_property(TARGET
  PROPERTY
    CSHARP_LIBRARY_TYPE
  BRIEF_DOCS
    "Type of library/project to build [csproj|dll]"
  FULL_DOCS
    "This can be used to determine the type of a C# target."
)

define_property(TARGET
  PROPERTY
    CSHARP_LIBRARY_REFERENCES
  BRIEF_DOCS
    "Targets that this target depends on."
  FULL_DOCS
    "List of C# library targets referenced by this target."
)

define_property(TARGET
  PROPERTY
    CSHARP_FILE_REFERENCES
  BRIEF_DOCS
    "Files that are referenced by this target."
  FULL_DOCS
    "List of asset file paths that this target requires."
)

define_property(TARGET
  PROPERTY
    CSHARP_LIBRARY_DOCUMENTATION
  BRIEF_DOCS
    "Assembly documentation filename."
  FULL_DOCS
    "Documentation filename relative to LIBRARY_OUTPUT_DIRECTORY."
)

define_property(TARGET
  PROPERTY
    CSHARP_LIBRARY_SYMBOLS
  BRIEF_DOCS
    "Assembly symbols filename."
  FULL_DOCS
    "Symbols filename relative to LIBRARY_OUTPUT_DIRECTORY."
)

# Get the absolute path of a file.
# OUTPUT_VARIABLE: Variable to store the result.
# FILENAME: Filename to convert to an absolute path.
function(_CSharpGetAbsolutePath OUTPUT_VARIABLE FILENAME)
  if(IS_ABSOLUTE "${FILENAME}")
    set(${OUTPUT_VARIABLE} "${FILENAME}" PARENT_SCOPE)
  else()
    get_filename_component(ABSOLUTE_PATH "${FILENAME}" ABSOLUTE)
    set(${OUTPUT_VARIABLE} "${ABSOLUTE_PATH}" PARENT_SCOPE)
  endif()
endfunction()

# Set a variable to ALL or an empty string.
# OUTPUT_VARIABLE: Variable to store the result.
# BOOLEAN_VALUE: If this value is set return "ALL" otherwise an empty string.
function(_CSharpGetAllParameter OUTPUT_VARIABLE BOOLEAN_VALUE)
  set(${OUTPUT_VARIABLE} "" PARENT_SCOPE)
  if(BOOLEAN_VALUE)
    set(${OUTPUT_VARIABLE} "ALL" PARENT_SCOPE)
  endif()
endfunction()

# Get the output filename from a C# target.
# OUTPUT_VARIABLE: Variable to store the result. If the specified target is not
# a C# target this variable is set to an empty string.
# TARGET_NAME: Name of the target to query.
function(_CSharpGetTargetOutputFilename OUTPUT_VARIABLE TARGET_NAME)
  set(${OUTPUT_VARIABLE} "" PARENT_SCOPE)
  if(TARGET ${TARGET_NAME})
    get_target_property(IS_CSHARP_TARGET "${TARGET_NAME}" CSHARP_LIBRARY_TYPE)
    if(IS_CSHARP_TARGET)
      get_target_property(DLL_NAME "${TARGET_NAME}" LIBRARY_OUTPUT_NAME)
      get_target_property(DLL_DIR "${TARGET_NAME}" LIBRARY_OUTPUT_DIRECTORY)
      set(${OUTPUT_VARIABLE} "${DLL_DIR}/${DLL_NAME}" PARENT_SCOPE)
    endif()
  endif()
endfunction()

# Get the transitive set of file references for a C# target.
# OUTPUT_VARIABLE: List of transitive file references for the specified target.
# TARGET_NAME: Name of the target to query.
function(_CSharpGetFileReferences OUTPUT_VARIABLE TARGET_NAME)
  set(FILENAMES_OR_TARGETS "")
  get_target_property(FILE_REFERENCES ${TARGET_NAME} CSHARP_FILE_REFERENCES)
  foreach(FILENAME_OR_TARGET ${FILE_REFERENCES})
    if(TARGET FILENAME_OR_TARGET)
      _CSharpGetFileReferences(CHILD_FILE_REFERENCES ${FILENAME_OR_TARGET})
      list(APPEND FILENAMES_OR_TARGETS ${CHILD_FILE_REFERENCES})
    else()
      list(APPEND FILENAMES_OR_TARGETS ${FILENAME_OR_TARGET})
    endif()
  endforeach()
  set(${OUTPUT_VARIABLE} ${FILENAMES_OR_TARGETS} PARENT_SCOPE)
endfunction()

# Adds an existing CSharp project as a target that can be used as a dependency
# and also is compiled into a library.
#
# Required positional arguments:
#  NAME: Target name
#  PROJECT_PATH: Path to the .csproj file
#
# Optional named arguments:
#  ALL: Add the test target to the "all" / default target's dependencies.
#  OUTPUT_NAME <output_name>: Name of the output file with extension created by
#    this project. If this is not specified the basename of the PROJECT_PATH is
#    used as the output DLL name. For example, given foo.bar.csproj, OUTPUT_NAME
#    will be set to foo.bar.dll.
#  BINARY_DIR <binary_dir>: Directory where the project will place build
#    artifacts. If this isn't specified, the value of CMAKE_CURRENT_BINARY_DIR
#    is used.
#  DOCUMENTATION_NAME <filename>: Name of the documentation file with extension
#    relative to BINARY_DIR created by this project.
#  SYMBOLS_NAME <filename>: Name of the symbols file with extension relative to
#    BINARY_DIR created by this project.
#  SOURCES <sources ...>: Source files to add to target to show up in project
#    generators like visual studio solution.
#  COPY_FILES <files ...>: Files to copy into the directory of build artifacts.
#  BUILD_EXE <build_tool>: Path to msbuild or xbuild executable. Defaults to
#    the value of MONO_CSHARP_BUILD_EXE.
#  SET_ASSEMBLY_NAME: Whether to set the assembly name to the basename of the
#    OUTPUT_NAME. This is useful when overriding the AssemblyName property in
#    the project.
function(CSharpAddExternalProject NAME PROJECT_PATH)
  set(NO_VALUE_ARGS ALL SET_ASSEMBLY_NAME)
  set(SINGLE_VALUE_ARGS OUTPUT_NAME BUILD_EXE BINARY_DIR DOCUMENTATION_NAME
    SYMBOLS_NAME
  )
  set(MULTI_VALUE_ARGS SOURCES COPY_FILES)
  cmake_parse_arguments(
    ARG
    "${NO_VALUE_ARGS}"
    "${SINGLE_VALUE_ARGS}"
    "${MULTI_VALUE_ARGS}"
    ${ARGN}
  )

  # Get the build tool path.
  if("${ARG_BUILD_EXE}" STREQUAL "")
    if(MONO_CSHARP_BUILD_EXE)
      set(ARG_BUILD_EXE "${MONO_CSHARP_BUILD_EXE}")
    else()
      message(FATAL_ERROR "No C# build tool (BUILD_EXE) set.")
    endif()
  endif()

  # If an output name isn't set, use the project basename.
  if("${ARG_OUTPUT_NAME}" STREQUAL "")
    get_filename_component(DLL_NAME "${PROJECT_PATH}" NAME_WLE)
    set(OUTPUT_FILE "${DLL_NAME}.dll")
  else()
    set(OUTPUT_FILE "${ARG_OUTPUT_NAME}")
  endif()

  # If the binary directory isn't specified, default to the current binary
  # output directory.
  if("${ARG_BINARY_DIR}" STREQUAL "")
    set(ARG_BINARY_DIR "${CMAKE_CURRENT_BINARY_DIR}")
  endif()

  set(BINARY_DIR "${ARG_BINARY_DIR}/bin")
  set(OBJECT_DIR "${ARG_BINARY_DIR}/obj")
  set(OUTPUT_PATH "${BINARY_DIR}/${OUTPUT_FILE}")
  set(OUTPUT_ARTIFACTS "${OUTPUT_PATH}")
  set(TARGET_PROPERTIES "")
  if(ARG_DOCUMENTATION_NAME)
    set(DOCUMENTATION_PATH "${BINARY_DIR}/${ARG_DOCUMENTATION_NAME}")
    list(APPEND OUTPUT_ARTIFACTS "${DOCUMENTATION_PATH}")
    list(APPEND TARGET_PROPERTIES
      CSHARP_LIBRARY_DOCUMENTATION "${ARG_DOCUMENTATION_NAME}"
    )
  endif()
  if(ARG_SYMBOLS_NAME)
    set(SYMBOLS_PATH "${BINARY_DIR}/${ARG_SYMBOLS_NAME}")
    list(APPEND OUTPUT_ARTIFACTS "${SYMBOLS_PATH}")
    list(APPEND TARGET_PROPERTIES CSHARP_LIBRARY_SYMBOLS "${ARG_SYMBOLS_NAME}")
  endif()

  _CSharpGetAllParameter(ADD_TO_ALL "${ARG_ALL}")

  # Expose named target to build the project.
  add_custom_target(${NAME}
    ${ADD_TO_ALL}
    SOURCES
      "${PROJECT_PATH}"
    DEPENDS
      ${OUTPUT_ARTIFACTS}
      ${ARG_SOURCES}
  )

  # The Roslyn compiler (csc) on Windows does not create output directories
  # so generate them at configuration time.
  file(MAKE_DIRECTORY "${BINARY_DIR}")
  file(MAKE_DIRECTORY "${OBJECT_DIR}")

  # Rules to copy files to the binary directory.
  set(COPY_FILE_TARGETS "")
  foreach(FILENAME_OR_TARGET ${ARG_COPY_FILES})
    if(TARGET ${FILENAME_OR_TARGET})
      set(SOURCE_FILENAME "$<TARGET_FILE:${FILENAME_OR_TARGET}>")
    else()
      _CSharpGetAbsolutePath(SOURCE_FILENAME "${FILENAME_OR_TARGET}")
    endif()
    add_custom_command(TARGET ${NAME}
      POST_BUILD
      COMMAND
        ${CMAKE_COMMAND} -E make_directory "${BINARY_DIR}"
      COMMAND
        ${CMAKE_COMMAND} -E copy "${SOURCE_FILENAME}" "${BINARY_DIR}"
      DEPENDS
        ${FILENAME_OR_TARGET}
    )
    list(APPEND COPY_FILE_TARGETS "${FILENAME_OR_TARGET}")
  endforeach()

  set(ASSEMBLY_NAME_ARG "")
  if(ARG_SET_ASSEMBLY_NAME)
    get_filename_component(ASSEMBLY_NAME "${OUTPUT_FILE}" NAME_WLE)
    set(ASSEMBLY_NAME_ARG "/p:AssemblyName=${ASSEMBLY_NAME}")
  endif()

  # Note: DebugType "Full" is not supported on Windows with the
  # Roslyn compiler https://github.com/dotnet/roslyn/issues/8217
  _CSharpGetAbsolutePath(PROJECT_PATH_ABSOLUTE "${PROJECT_PATH}")
  add_custom_command(
    OUTPUT
      ${OUTPUT_ARTIFACTS}
    COMMAND
      # Unfortunately, Xcode sets the TARGETNAME environment variable to the
      # name of the build target. This variable is read by msbuild / xbuild,
      # which overrides the $(TargetName) variable (primary output file for the
      # build). So if the target name is "foo_bar" an output library name ends
      # up as "foo_bar.dll" rather than output filename baked into the project.
      ${CMAKE_COMMAND} -E env TARGETNAME=""
        "${ARG_BUILD_EXE}"
          /nologo
          /p:AllowUnsafeBlocks=true
          /p:Configuration=Release
          /p:IntermediateOutputPath="${OBJECT_DIR}/"
          /p:OutDir="${BINARY_DIR}/"
          /p:OutputPath="${BINARY_DIR}/"
          /p:Platform=AnyCPU
          /p:DebugSymbols=true
          /p:DebugType=Full
          ${ASSEMBLY_NAME_ARG}
          /verbosity:minimal
          "${PROJECT_PATH_ABSOLUTE}"
    DEPENDS
      "${PROJECT_PATH}"
      ${ARG_SOURCES}
      ${COPY_FILE_TARGETS}
    COMMENT
      "Building csproj for ${OUTPUT_FILE}"
  )

  set_target_properties(${NAME}
    PROPERTIES
      LIBRARY_OUTPUT_NAME "${OUTPUT_FILE}"
      LIBRARY_OUTPUT_DIRECTORY "${BINARY_DIR}"
      CSHARP_LIBRARY_TYPE "csproj"
      CSHARP_FILE_REFERENCES "${COPY_FILE_TARGETS}"
      ${TARGET_PROPERTIES}
  )
endfunction()

# Adds an existing C# assembly as a target that can be used as a dependency.
#
# Required positional arguments:
#  NAME: Target name.
#  DLL_PATH: Path to the dll file.
#
# Optional named arguments:
#  ALL: Add the test target to the "all" / default target's dependencies.
function(CSharpAddExternalDll NAME DLL_PATH)
  cmake_parse_arguments(ARG "ALL" "" "" ${ARGN})
  if(NOT EXISTS "${DLL_PATH}")
    message(FATAL_ERROR "${DLL_PATH} does not exist for target ${NAME}.")
  endif()

  get_filename_component(DLL_NAME "${DLL_PATH}" NAME)
  get_filename_component(DLL_DIR "${DLL_PATH}" DIRECTORY)
  _CSharpGetAbsolutePath(DLL_DIR_ABSOLUTE "${DLL_DIR}")

  _CSharpGetAllParameter(ADD_TO_ALL "${ARG_ALL}")

  add_custom_target(${NAME} ${ADD_TO_ALL} DEPENDS "${DLL_PATH}")

  set_target_properties(${NAME}
    PROPERTIES
      LIBRARY_OUTPUT_NAME "${DLL_NAME}"
      LIBRARY_OUTPUT_DIRECTORY "${DLL_DIR_ABSOLUTE}"
      CSHARP_LIBRARY_TYPE "dll"
      FOLDER "CSharp External"
  )
endfunction()

# Creates a target that compiles a C# assembly and can be used as a
# C# dependency.
#
# Required positional arguments:
#  NAME: Target name
#
# Required named arguments:
#  MODULE <module>: CSharp library output name
#  SOURCES <src_file...>: CSharp source code files
#
# Optional named arguments:
#  ALL: Add the test target to the "all" / default target's dependencies.
#  REFERENCES <targets..>: CMake C# library targets this depends on.
#  SYSTEM_REFERENCES <references...>: System C# libraries this depends on.
#  DEPENDS <targets...>: Targets this target depends on and need to be
#    linked/built first
#  PROJECT_GUID <guid>: MSBuild project guid (for use with solution files)
#  FRAMEWORK_VERSION <framework_version>: .net framework version, defaults to
#    3.5.
#  DEFINES <defines...>: Extra defines to add to the project file.
#  ASSEMBLY_NAME <assembly_name>: Name of the output assembly. Defaults to
#    the MODULE name.
#  GENERATE_DOCUMENTATION: If this argument is present a documentation XML file
#    will be generated with the assembly.
#  BINARY_DIR <binary_dir>: Directory where the project will place build
#    artifacts. If this isn't specified, the value of CMAKE_CURRENT_BINARY_DIR
#    is used.
#  BUILD_EXE <build_tool>: Path to msbuild or xbuild executable. Defaults to
#    the value of MONO_CSHARP_BUILD_EXE.
function(CSharpAddLibrary NAME)
  _CSharpGenerateProjectAndAddBuildTarget(${NAME} "Library" ${ARGN})
  set_target_properties(${NAME} PROPERTIES FOLDER "CSharp Library DLL")
endfunction()

# Creates a target that compiles a C# executable.
#
# Required positional arguments:
#  NAME: Target name
#
# Required named arguments:
#  MODULE <module>: CSharp library output name
#  SOURCES <src_file...>: CSharp source code files
#
# Optional named arguments:
#  ALL: Add the test target to the "all" / default target's dependencies.
#  REFERENCES <targets..>: CMake C# library targets this depends on.
#  SYSTEM_REFERENCES <references...>: System C# libraries this depends on.
#  DEPENDS <targets...>: Targets this target depends on and need to be
#    linked/built first
#  PROJECT_GUID <guid>: MSBuild project guid (for use with solution files)
#  FRAMEWORK_VERSION <framework_version>: .net framework version, defaults to
#    3.5.
#  DEFINES <defines...>: Extra defines to add to the project file.
#  ASSEMBLY_NAME <assembly_name>: Name of the output assembly. Defaults to
#    the MODULE name.
#  GENERATE_DOCUMENTATION: If this argument is present a documentation XML file
#    will be generated with the assembly.
#  BINARY_DIR <binary_dir>: Directory where the project will place build
#    artifacts. If this isn't specified, the value of CMAKE_CURRENT_BINARY_DIR
#    is used.
#  BUILD_EXE <build_tool>: Path to msbuild or xbuild executable. Defaults to
#    the value of MONO_CSHARP_BUILD_EXE.
function(CSharpAddExecutable NAME)
  _CSharpGenerateProjectAndAddBuildTarget(${NAME} "Exe" ${ARGN})
  set_target_properties(${NAME} PROPERTIES FOLDER "CSharp Binary DLL")
endfunction()

# Generates a C# project (csproj) and adds a build target to build the project.
#
# Required positional arguments:
#  NAME: Target name
#  OUTPUT_TYPE: C# build target type can be either "Library" or "Exe".
#
# Required named arguments:
#  MODULE <module>: CSharp library output name
#  SOURCES <src_file...>: CSharp source code files
#
# Optional named arguments:
#  ALL: Add the test target to the "all" / default target's dependencies.
#  REFERENCES <targets..>: CMake C# library targets this depends on.
#  SYSTEM_REFERENCES <references...>: System C# libraries this depends on.
#  DEPENDS <targets...>: Targets this target depends on and need to be
#    linked/built first
#  PROJECT_GUID <guid>: MSBuild project guid (for use with solution files)
#  FRAMEWORK_VERSION <framework_version>: .net framework version, defaults to
#    3.5.
#  DEFINES <defines...>: Extra defines to add to the project file.
#  ASSEMBLY_NAME <assembly_name>: Name of the output assembly. Defaults to
#    the MODULE name.
#  COPY_FILES <files ...>: Files to copy into the directory of build artifacts.
#  GENERATE_DOCUMENTATION: If this argument is present a documentation XML file
#    will be generated with the assembly.
#  BINARY_DIR <binary_dir>: Directory where the project will place build
#    artifacts. If this isn't specified, the value of CMAKE_CURRENT_BINARY_DIR
#    is used.
#  BUILD_EXE <build_tool>: Path to msbuild or xbuild executable. Defaults to
#    the value of MONO_CSHARP_BUILD_EXE.
function(_CSharpGenerateProjectAndAddBuildTarget NAME OUTPUT_TYPE)
  set(NO_VALUE_ARGS
    ALL
    GENERATE_DOCUMENTATION
  )
  set(MULTI_VALUE_ARGS
    MODULE
    SOURCES
    REFERENCES
    SYSTEM_REFERENCES
    DEPENDS
    PROJECT_GUID
    FRAMEWORK_VERSION
    DEFINES
    ASSEMBLY_NAME
    COPY_FILES
    BINARY_DIR
    BUILD_EXE
  )
  cmake_parse_arguments(ARG
    "${NO_VALUE_ARGS}"
    ""
    "${MULTI_VALUE_ARGS}"
    ${ARGN}
  )

  if("${ARG_MODULE}" STREQUAL "")
    message(FATAL_ERROR "MODULE must be specified.")
  endif()
  if(NOT ARG_BUILD_EXE)
    set(ARG_BUILD_EXE "${MONO_CSHARP_BUILD_EXE}")
  endif()

  set(CSHARP_PROJECT_FILE
    "${CMAKE_CURRENT_BINARY_DIR}/csharp_projects/${NAME}.csproj"
  )

  if ("${ARG_PROJECT_GUID}" STREQUAL "")
    # If this target doesn't have a GUID, generate one.
    if("${${NAME}_GUID}" STREQUAL "")
      string(UUID ARG_PROJECT_GUID
        # Randomly generated UUID used as the seed for the GUID.
        NAMESPACE "efe0ef8c-b556-437b-8e72-8cc4afda60f5"
        NAME ${NAME}
        TYPE MD5
      )
      set(${${NAME}_GUID} "${ARG_PROJECT_GUID}" CACHE STRING
        "Project GUID for ${CSHARP_PROJECT_FILE}"
      )
    endif()
  endif()

  if ("${ARG_FRAMEWORK_VERSION}" STREQUAL "")
    set(ARG_FRAMEWORK_VERSION "3.5")
  endif()

  if ("${ARG_ASSEMBLY_NAME}" STREQUAL "")
    set(ARG_ASSEMBLY_NAME ${ARG_MODULE})
  endif()

  # Output file extension.
  if("${OUTPUT_TYPE}" STREQUAL "Library")
    set(OUTPUT_EXTENSION ".dll")
  elseif("${OUTPUT_TYPE}" STREQUAL "Exe")
    set(OUTPUT_EXTENSION ".exe")
  else()
    message(FATAL_ERROR "Invalid OUTPUT_TYPE: ${OUTPUT_TYPE}")
  endif()

  # Add C# system libraries to the set of system references for all generated
  # projects.
  list(APPEND ARG_SYSTEM_REFERENCES "System" "System.Core")

  # Generate the C# project file.
  set(VAR_PROJECT_GUID "${ARG_PROJECT_GUID}")
  set(VAR_ROOT_NAMESPACE "${ARG_MODULE}")
  set(VAR_ASSEMBLY_NAME "${ARG_ASSEMBLY_NAME}")
  set(VAR_FRAMEWORK_VERSION "${ARG_FRAMEWORK_VERSION}")
  set(VAR_REFERENCE "")
  set(VAR_COMPILE "")
  set(VAR_DEFINES "TRACE")
  set(VAR_OUTPUT_TYPE "${OUTPUT_TYPE}")
  if (${ARG_GENERATE_DOCUMENTATION})
    set(VAR_GENERATE_DOCUMENTATION "true")
  else()
    set(VAR_GENERATE_DOCUMENTATION "false")
  endif()

  # Add system assembly references.
  foreach(REFERENCE ${ARG_SYSTEM_REFERENCES})
    string(APPEND VAR_REFERENCE "    <Reference Include=\"${REFERENCE}\" />\n")
  endforeach()

  # Build list of required DLLs.
  set(DLL_FILES "")
  foreach(TARGET_REFERENCE ${ARG_REFERENCES})
    get_target_property(DLL_NAME ${TARGET_REFERENCE} LIBRARY_OUTPUT_NAME)
    get_target_property(DLL_DIR ${TARGET_REFERENCE} LIBRARY_OUTPUT_DIRECTORY)
    set(DLL_FILENAME "${DLL_DIR}/${DLL_NAME}")
    list(APPEND DLL_FILES "${DLL_FILENAME}")

    set(INCLUDE_NAME "${DLL_NAME}")
    string(REPLACE ".dll" "" INCLUDE_NAME "${DLL_NAME}")
    string(REPLACE "_" ";" INCLUDE_NAME "${INCLUDE_NAME}")
	list(GET INCLUDE_NAME 0 INCLUDE_NAME)

    string(REPLACE "/" "\\" DLL_FILENAME_WIN "${DLL_FILENAME}")
    string(APPEND VAR_REFERENCE "    <!-- ${TARGET_REFERENCE} -->\n")
    string(APPEND VAR_REFERENCE "    <Reference Include=\"${INCLUDE_NAME}\" >\n")
    string(APPEND VAR_REFERENCE "      <SpecificVersion>False</SpecificVersion>\n")
    string(APPEND VAR_REFERENCE "      <HintPath>${DLL_FILENAME_WIN}</HintPath>\n")
    string(APPEND VAR_REFERENCE "    </Reference>\n")
  endforeach()

  string(REPLACE "/" "\\" VAR_CURRENT_DIR "${CMAKE_CURRENT_SOURCE_DIR}")

  set(SOURCE_FILES "")
  foreach(SOURCE_FILE ${ARG_SOURCES})
    _CSharpGetAbsolutePath(SOURCE_FILE_ABSOLUTE "${SOURCE_FILE}")
    list(APPEND SOURCE_FILES "${SOURCE_FILE_ABSOLUTE}")
    string(REPLACE "/" "\\" SOURCE_FILE_WIN "${SOURCE_FILE_ABSOLUTE}")

    if("${SOURCE_FILE}" MATCHES "\.resx$")
      get_filename_component(GENERATED_CS "${SOURCE_FILE}" NAME)
      string(REPLACE ".resx" ".Designer.cs" GENERATED_CS "${GENERATED_CS}")

      string(APPEND VAR_COMPILE
        "    <EmbeddedResource Include=\"${SOURCE_FILE_WIN}\">\n"
      )
      string(APPEND VAR_COMPILE
        "      <Generator>ResXFileCodeGenerator</Generator>\n"
      )
      string(APPEND VAR_COMPILE
        "      <LastGenOutput>${GENERATED_CS}</LastGenOutput>\n"
      )
      string(APPEND VAR_COMPILE
        "    </EmbeddedResource>\n"
      )
    elseif("${SOURCE_FILE}" MATCHES "\.Designer\.cs$")
      get_filename_component(GENERATED_RESX "${SOURCE_FILE}" NAME)
      string(REPLACE ".Designer.cs" ".resx" GENERATED_RESX "${GENERATED_CS}")

      string(APPEND VAR_COMPILE
        "    <Compile Include=\"${SOURCE_FILE_WIN}\">\n"
      )
      string(APPEND VAR_COMPILE
        "      <AutoGen>True</AutoGen>\n"
      )
      string(APPEND VAR_COMPILE
        "      <DesignTime>True</DesignTime>\n"
      )
      string(APPEND VAR_COMPILE
        "      <DependentUpon>${GENERATED_RESX}</DependentUpon>\n"
      )
      string(APPEND VAR_COMPILE
        "    </Compile>\n"
      )
    else()
      string(APPEND VAR_COMPILE
        "    <Compile Include=\"${SOURCE_FILE_WIN}\" />\n"
      )
    endif()
  endforeach()

  foreach(DEFINE ${ARG_DEFINES})
    string(APPEND VAR_DEFINES ";${DEFINE}")
  endforeach()

  # Finally, generate the C# project file.
  configure_file("${CSHARP_PROJECT_TEMPLATE}" "${CSHARP_PROJECT_FILE}"
    @ONLY
    NEWLINE_STYLE CRLF
  )
  unset(VAR_PROJECT_GUID)
  unset(VAR_ROOT_NAMESPACE)
  unset(VAR_ASSEMBLY_NAME)
  unset(VAR_FRAMEWORK_VERSION)
  unset(VAR_COMPILE)
  unset(VAR_DEFINES)
  unset(VAR_OUTPUT_TYPE)

  # Gather the transitive set of files to copy from all referenced targets.
  set(COPY_FILES "")
  foreach(CSHARP_TARGET ${ARG_REFERENCES})
    _CSharpGetFileReferences(TARGET_COPY_FILES ${CSHARP_TARGET})
    if(TARGET_COPY_FILES)
      list(APPEND COPY_FILES ${TARGET_COPY_FILES})
    endif()
  endforeach()
  # Extract target filenames for C# targets.
  foreach(FILENAME_OR_TARGET ${ARG_COPY_FILES})
    _CSharpGetTargetOutputFilename(CSHARP_OUTPUT_FILENAME
      "${FILENAME_OR_TARGET}"
    )
    if(CSHARP_OUTPUT_FILENAME)
      _CSharpGetFileReferences(TARGET_COPY_FILES ${FILENAME_OR_TARGET})
      list(APPEND COPY_FILES "${CSHARP_OUTPUT_FILENAME}" ${TARGET_COPY_FILES})
    else()
      list(APPEND COPY_FILES "${FILENAME_OR_TARGET}")
    endif()
  endforeach()

  set(OPTIONAL_ARGS "")
  if(ARG_BINARY_DIR)
    list(APPEND OPTIONAL_ARGS BINARY_DIR "${ARG_BINARY_DIR}")
  endif()
  if(ARG_GENERATE_DOCUMENTATION)
    list(APPEND OPTIONAL_ARGS DOCUMENTATION_NAME
      "${ARG_ASSEMBLY_NAME}.xml"
    )
  endif()
  # Infer that the Roslyn (csc) isn't available if only xbuild is available
  # in the Mono distribution. In this case the compiler will generated mdb file
  # rather than pdb symbols.
  if("${ARG_BUILD_EXE}" MATCHES ".*/xbuild$")
    list(APPEND OPTIONAL_ARGS SYMBOLS_NAME
      "${ARG_ASSEMBLY_NAME}.dll.mdb"
    )
  else()
    list(APPEND OPTIONAL_ARGS SYMBOLS_NAME
      "${ARG_ASSEMBLY_NAME}.pdb"
    )
  endif()

  _CSharpGetAllParameter(ADD_TO_ALL "${ARG_ALL}")

  CSharpAddExternalProject(${NAME} ${CSHARP_PROJECT_FILE}
    ${ADD_TO_ALL}
    OUTPUT_NAME
      "${ARG_ASSEMBLY_NAME}${OUTPUT_EXTENSION}"
    SET_ASSEMBLY_NAME
    SOURCES
      ${SOURCE_FILES}
      ${DLL_FILES}
    COPY_FILES
      ${COPY_FILES}
    BUILD_EXE
      ${ARG_BUILD_EXE}
    ${OPTIONAL_ARGS}
  )

  if(ARG_DEPENDS)
    add_dependencies(${NAME} ${ARG_DEPENDS})
  endif()

  foreach(REFERENCE ${ARG_REFERENCES})
    add_dependencies(${NAME} "${REFERENCE}")
  endforeach()

  set_target_properties(${NAME} PROPERTIES
    CSHARP_LIBRARY_REFERENCES "${ARG_REFERENCES}"
  )
endfunction()
