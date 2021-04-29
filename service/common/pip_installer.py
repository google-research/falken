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

# Lint as: python3
"""Installs dependencies using pip."""

import logging
import os
import subprocess
import sys

# Modules required to execute service modules and tests.
_REQUIRED_PYTHON_MODULES = [
    ('absl-py', ''),
    ('tensorflow', ''),
    ('tf-agents', '==0.8.0rc1'),
    ('grpcio-tools', ''),
    ('googleapis-common-protos', ''),
    ('flatbuffers', ''),
]

_PIP_INSTALL_ARGS = [sys.executable, '-m', 'pip', 'install']
_PIP_SHOW_ARGS = [sys.executable, '-m', 'pip', '-q', 'show']
# Cache of installed modules populated by _module_installed().
_INSTALLED_MODULE_LIST = []


def _clear_installed_modules_cache():
  """Flush cache of installed modules."""
  global _INSTALLED_MODULE_LIST
  _INSTALLED_MODULE_LIST = []


def _module_installed(module):
  """Determine whether a module is installed.

  Args:
    module: Name of the Python module to query.

  Returns:
    True if installed, False otherwise.

  Raises:
    subprocess.CalledProcessError: If pip fails to list modules.
  """
  global _INSTALLED_MODULE_LIST
  if not _INSTALLED_MODULE_LIST:
    result = subprocess.run([sys.executable, '-m', 'pip', 'list'],
                            stdout=subprocess.PIPE, check=True)
    # Each line consists of "module_name\w+version", extract the module name
    # from each line.
    _INSTALLED_MODULE_LIST = [
        l.split()[0] for l in result.stdout.decode('utf-8').splitlines()]
  return module in _INSTALLED_MODULE_LIST


def _install_module(module, version):
  """Install a Python module.

  Args:
    module: Name of the module to install.
    version: Version constraints for the module to install or an empty string
      to install the latest.

  Raises:
    subprocess.CalledProcessError: If module installation fails.
  """
  logging.info('Installing Python module %s...', module)
  subprocess.check_call(_PIP_INSTALL_ARGS + [f'{module}{version}'])


def install_dependencies():
  """Install all Python module dependencies."""
  modules_installed = False
  for module, version in _REQUIRED_PYTHON_MODULES:
    if not _module_installed(module):
      _install_module(module, version)
      modules_installed = True
  if modules_installed:
    _clear_installed_modules_cache()


if int(os.environ.get('FALKEN_AUTO_INSTALL_DEPENDENCIES', 1)):
  install_dependencies()
