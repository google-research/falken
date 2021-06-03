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
# This script packs Falken C++ SDK for Linux, MacOS and Windows platforms.
#
# #

# Display commands being run.
set -x

# Exit on error.
set -e

# Set input and output directories
FALKEN_INPUT_ARTIFACTS_DIR="./artifacts/input"
FALKEN_OUTPUT_ARTIFACTS_DIR="./artifacts/output"

# Create the output directory
mkdir -p "$FALKEN_OUTPUT_ARTIFACTS_DIR"

# Set platform artifacts paths.
LINUX_INPUT_ARTIFACTS_DIR="${FALKEN_INPUT_ARTIFACTS_DIR}/Linux"
MACOS_INPUT_ARTIFACTS_DIR="${FALKEN_INPUT_ARTIFACTS_DIR}/Darwin"
WINDOWS_INPUT_ARTIFACTS_DIR="${FALKEN_INPUT_ARTIFACTS_DIR}/Windows"

# Get SDK version number from the linux build package name
VERSION=$(echo ${LINUX_INPUT_ARTIFACTS_DIR}/falken_cpp_sdk*-Linux.zip | \
          sed -E 's@.*falken_cpp_sdk-(.+)\-Linux.zip$@\1@')

# Get C++ SDK path for each platform.
LINUX_CPP_SDK="\
$LINUX_INPUT_ARTIFACTS_DIR/\
falken_cpp_sdk-${VERSION}-Linux.zip"

MACOS_CPP_SDK="\
$MACOS_INPUT_ARTIFACTS_DIR/\
falken_cpp_sdk-${VERSION}-Darwin.zip"

WINDOWS_CPP_SDK_REL="\
$WINDOWS_INPUT_ARTIFACTS_DIR/\
falken_cpp_sdk-${VERSION}-Windows-Release.zip"

WINDOWS_CPP_SDK_DBG="\
$WINDOWS_INPUT_ARTIFACTS_DIR/\
falken_cpp_sdk-${VERSION}-Windows-Debug.zip"

# Remove the LICENSE file from the Windows binary. This is required because
# eigen is downloaded from a different repo for windows, which ends in a
# differente LICENSE file and raising an error when merging the 3 binaries.
zip -d "$WINDOWS_CPP_SDK_REL" LICENSE
zip -d "$WINDOWS_CPP_SDK_DBG" LICENSE

# Install absl module.
pip3 install --user absl-py

# Merge and zip binaries.
OUTPUT_FILE="${FALKEN_OUTPUT_ARTIFACTS_DIR}/falken_cpp_sdk-${VERSION}.zip"

python3 "./sdk/cpp/merge_zipfiles.py" \
   --inputs "${LINUX_CPP_SDK} \
             ${MACOS_CPP_SDK} \
             ${WINDOWS_CPP_SDK_REL} \
             ${WINDOWS_CPP_SDK_DBG}" \
   --output "${OUTPUT_FILE}"