#!/bin/bash

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

# #
#
# This script packs Falken Unity SDK for Linux, MacOS and Windows platforms.
#
# #

# Display commands being run.
set -x

# Exit on error.
set -e

# Set input, output and temp directories
FALKEN_INPUT_ARTIFACTS_DIR="./artifacts/input"
FALKEN_OUTPUT_ARTIFACTS_DIR="./artifacts/output"
FALKEN_TEMP_ARTIFACTS_DIR="./artifacts/temp"

# Set Falken source paths.
FALKEN_UNITY_SDK_SRC_PATH="./sdk/unity"

# Create the output and temp directories
mkdir -p "$FALKEN_OUTPUT_ARTIFACTS_DIR"
mkdir -p "$FALKEN_TEMP_ARTIFACTS_DIR"

# EDM4U branch name.
EDM4U_TAG="master"

# Shallow clone Unity jar resolver.
pushd "$FALKEN_TEMP_ARTIFACTS_DIR"
git clone --depth 1 --branch ${EDM4U_TAG} \
https://github.com/googlesamples/unity-jar-resolver.git
popd

# Install yaml module for python.
python3 -m pip install --user pyyaml
# Install absl module for python.
python3 -m pip install --user absl-py

# Set platform artifacts paths.
LINUX_INPUT_ARTIFACTS_DIR="${FALKEN_INPUT_ARTIFACTS_DIR}/Linux"
MACOS_INPUT_ARTIFACTS_DIR="${FALKEN_INPUT_ARTIFACTS_DIR}/Darwin"
WINDOWS_INPUT_ARTIFACTS_DIR="${FALKEN_INPUT_ARTIFACTS_DIR}/Windows"

LINUX_ASSETS_ARTIFACTS_DIR="${FALKEN_TEMP_ARTIFACTS_DIR}/Linux/Assets"
MACOS_ASSETS_ARTIFACTS_DIR="${FALKEN_TEMP_ARTIFACTS_DIR}/Darwin/Assets"
WINDOWS_ASSETS_ARTIFACTS_DIR="${FALKEN_TEMP_ARTIFACTS_DIR}/Windows/Assets"

mkdir -p "$LINUX_ASSETS_ARTIFACTS_DIR"
mkdir -p "$MACOS_ASSETS_ARTIFACTS_DIR"
mkdir -p "$WINDOWS_ASSETS_ARTIFACTS_DIR"

# Get the Assets folders and prepare them for merging.
unzip "${LINUX_INPUT_ARTIFACTS_DIR}/falken_unity_sdk-Linux.zip" \
    -d "${LINUX_ASSETS_ARTIFACTS_DIR}"
unzip "${MACOS_INPUT_ARTIFACTS_DIR}/falken_unity_sdk-Darwin.zip" \
    -d "${MACOS_ASSETS_ARTIFACTS_DIR}"
unzip "${WINDOWS_INPUT_ARTIFACTS_DIR}/falken_unity_sdk-Windows.zip" \
    -d "${WINDOWS_ASSETS_ARTIFACTS_DIR}"

# Get SDK version number.
FALKEN_SDK_VERSION=$(awk '{print $3}' \
                     "${LINUX_ASSETS_ARTIFACTS_DIR}/sdk_version.txt")

# Consolidate all the libraries in another folder. Using Darwin as base folder.
LINUX_SO="${LINUX_ASSETS_ARTIFACTS_DIR}/\
Falken/Core/Plugins/x86_64/libfalken_csharp_sdk.so"

WINDOWS_DLL="${WINDOWS_ASSETS_ARTIFACTS_DIR}/\
Falken/Core/Plugins/x86_64/falken_csharp_sdk.dll"

MULTIPLATFORM_FOLDER="${PWD}/Multiplatform"
mkdir "$MULTIPLATFORM_FOLDER"
cp -Rv ${MACOS_ASSETS_ARTIFACTS_DIR} "$MULTIPLATFORM_FOLDER"

LIB_FOLDER="$MULTIPLATFORM_FOLDER/Assets/Falken/Core/Plugins/x86_64"
cp "$LINUX_SO" "$WINDOWS_DLL" "$LIB_FOLDER"

# Run export unity script to generate the final unitypackage file.
GUIDS_FILE="$FALKEN_UNITY_SDK_SRC_PATH/export_unity_package_guids.json"
CONF_FILE="$FALKEN_UNITY_SDK_SRC_PATH/export_unity_package_config.json"

# Generate Unity package file.
python3 "$FALKEN_TEMP_ARTIFACTS_DIR"/unity-jar-resolver/source/ExportUnityPackage/\
export_unity_package.py --assets_dir "$MULTIPLATFORM_FOLDER/Assets" \
  --config_file "$CONF_FILE" --guids_file "$GUIDS_FILE" \
  --output_dir "$FALKEN_OUTPUT_ARTIFACTS_DIR" \
  --plugins_version  "${FALKEN_SDK_VERSION}" --verbosity -1 --nooutput_upm

# Generate UPM file.
python3 "$FALKEN_TEMP_ARTIFACTS_DIR"/unity-jar-resolver/source/ExportUnityPackage/\
export_unity_package.py --assets_dir "$MULTIPLATFORM_FOLDER/Assets" \
  --config_file "$CONF_FILE" --guids_file "$GUIDS_FILE" \
  --output_dir "$FALKEN_OUTPUT_ARTIFACTS_DIR" \
  --plugins_version "${FALKEN_SDK_VERSION}" --verbosity -1 --output_upm true
