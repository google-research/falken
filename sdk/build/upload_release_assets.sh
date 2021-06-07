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
# This script created a github release and uploads the assets received
# through the input folder
#
# #

# Display commands being run.
set -x

# Exit on error.
set -e

# Set input directory path
FALKEN_INPUT_ARTIFACTS_DIR="./artifacts/input"

# release data file location
RELEASE_DATA_FILE="./release_data.txt"

# Extract the tagname from the REF in an externally set envvar TAG
TAG_NAME="${TAG##*/}"

#
# Create the release data file. This file has in the first line
# the title of the release, and the rest of the body is the message.
#

# Add the title.
echo "Falken ${TAG_NAME}" > ${RELEASE_DATA_FILE}
echo >> ${RELEASE_DATA_FILE}

# This is a workaround because actions/checkout@v2 does not preserve
# tag annotations. See https://github.com/actions/checkout/issues/290
git fetch -f origin ${TAG}:${TAG}
# Add the tag annotation to the release data file as message
git tag -l --format="%(contents)" ${TAG_NAME} >> ${RELEASE_DATA_FILE}

# Create the assets command line arguments from the contents of the
# input folder
ASSET_ARGS=()
for NEW_ASSET in ${FALKEN_INPUT_ARTIFACTS_DIR}/*; do
   ASSET_ARGS+=("-a" "${NEW_ASSET}")
done

# Create the release using the hub command line tool
hub release create "${ASSET_ARGS[@]}" \
      -F "${RELEASE_DATA_FILE}" \
      "${TAG_NAME}"
