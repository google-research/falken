#!/bin/bash -eu
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


# Determine whether a set of packages are installed.
#
# $*: Names of the package to search for.
#
# Prints the set of missing packages.
query_installed_packages() {
  local -a required_packages=("$@")
  local -a missing_packages=()
  for package in "${required_packages[@]}"; do
    local installed=0
    if [[ $(uname -s) == "Darwin" ]]; then
      brew ls --versions "${package}" >/dev/null && installed=1
    else
      dpkg -s "${package}" >/dev/null && installed=1
    fi
    if [[ $((installed)) -eq 0 ]]; then
      missing_packages+=("${package}")
    fi
  done
  if [[ ${#missing_packages[@]} -ne 0 ]]; then
    echo "${missing_packages[@]}"
  fi
}

# Install packages with the package manager.
#
# $*: Packages to install.
install_packages() {
  local -a install_packages=("$@")
  if [[ $(uname -s) == "Darwin" ]]; then
    brew install "${install_packages[@]}"
  else
    sudo apt-get install -y -qq "${install_packages[@]}"
  fi
}

main() {
  if [ "$#" -ne 2 ]; then
    echo "\
Usage: $(basename $0) <swig_source_path> <swig_install_path>
You need to provide the path for SWIG and the installation path." >&2
    exit 1
  fi

  readonly swig_path="$1"
  readonly swig_installation_path="$2"
  if [ -e "${swig_installation_path}/bin/swig" ]; then
    echo "Swig already built."
    exit 0
  fi
  local -a required_packages=()
  local -a missing_packages=()
  local install_packages=1
  if [[ $(uname -s) == "Darwin" ]]; then
    if [[ -n "$(which brew)" ]]; then
      required_packages=(autoconf automake pcre)
    fi
  else
    required_packages=(automake autoconf libpcre3-dev libpcre3)
  fi
  if [[ ${#required_packages[@]} -ne 0 ]]; then
    echo "Installing prerequisites to build SWIG..."
    local -a missing_packages=(
      $(query_installed_packages "${required_packages[@]}"))
    if [[ ${#missing_packages[@]} -ne 0 ]]; then
      install_packages "${missing_packages[@]}"
    fi
  fi
  mkdir -p "${swig_installation_path}"
  echo "Building SWIG at ${swig_installation_path}..."
  env -i PATH="${PATH}" "${SHELL}" -c "
    set -x;
    cd \"${swig_path}\" && \
    ./autogen.sh && \
    ./configure --prefix=\"${swig_installation_path}\" && \
    make -j && \
    make install
  "
  local result=$?
  if [[ $((result)) -ne 0 ]]; then
    echo "Failed to build SWIG ($((result)))."
    exit 1
  fi
}

main $@
