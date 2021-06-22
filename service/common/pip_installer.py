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

import importlib
import logging
import os
import platform
import subprocess
import sys
from typing import Dict, List, NamedTuple


  # A dictionary where the key is a platform name
  # returned by platform.system() and the value contains a list of supported
  # architectures for the package. If no constraints are found for the current
  # platform it is assumed the package is available for the platform.
PlatformConstraints = Dict[str, List[str]]


class ModuleInfo(NamedTuple):
  """PIP module installation information and constraints."""
  # Name of the module to install.
  pip_module_name: str
  # Name of the optional module to import to determine whether the required
  # pip package is installed. pip_installer searches the module path for this
  # module to determine whether the PIP module pip_module_name is installed.
  # By setting this value pip_installer can avoid using `pip list`, which is
  # a very slow operation, to determine whether a module is installed.
  import_module_name: str = ''
  # An optional version constraint for the pip module.
  version_constraint: str  = ''
  # Constraints that need to be satisfied for the host platform before trying
  # to install the module.
  platform_constraints: PlatformConstraints = {}


# Modules required to execute service modules and tests.
_REQUIRED_PYTHON_MODULES = [
    ModuleInfo(pip_module_name='absl-py', import_module_name='absl'),
    ModuleInfo(pip_module_name='braceexpand', import_module_name='braceexpand'),
    ModuleInfo(pip_module_name='numpy', import_module_name='numpy'),
    ModuleInfo(pip_module_name='tensorflow', import_module_name='tensorflow',
               version_constraint='>=2.5.0',
               platform_constraints={'windows': ['64bit']}),
    ModuleInfo(pip_module_name='tf-agents', import_module_name='tf_agents',
               version_constraint='==0.8.0rc1'),
    ModuleInfo(pip_module_name='grpcio-tools',
               import_module_name='grpc.tools.protoc'),
    ModuleInfo(pip_module_name='googleapis-common-protos',
               import_module_name='google.rpc.status_pb2'),
    ModuleInfo(pip_module_name='flatbuffers', import_module_name='flatbuffers'),
    ModuleInfo(pip_module_name='flufl.lock', import_module_name='flufl.lock'),
]

_PIP_INSTALL_ARGS = [sys.executable, '-m', 'pip', 'install', '--user']
# Cache of installed modules populated by _module_installed().
_INSTALLED_MODULE_LIST = []


class PlatformConstraintError(RuntimeError):
  """Raised if the current platform doesn't support a package."""
  pass


def _clear_installed_modules_cache():
  """Flush cache of installed modules."""
  global _INSTALLED_MODULE_LIST
  _INSTALLED_MODULE_LIST = []
  importlib.invalidate_caches()


def find_module_by_name(import_module_name: str, search_path: str = ''):
  """Determine whether a module can be imported.

  After calling this method if a module is subsequently installed or made
  available via sys.path, the caller must call importlib.invalidate_caches()
  before trying to import the newly available module.

  Args:
    import_module_name: Name of the module to import or check whether it's
      installed.
    search_path: Optional additional path to add to sys.path to search.

  Returns:
    True if the module can be imported, False otherwise.
  """
  if search_path:
    original_sys_path = list(sys.path)
    sys.path.append(search_path)
  else:
    original_sys_path = sys.path

  try:
    if importlib.util.find_spec(import_module_name):
      return True
  except ModuleNotFoundError:
    pass
  finally:
    sys.path = original_sys_path
  return False


def _module_installed(pip_module_name: str, import_module_name: str):
  """Determine whether a module is installed.

  Args:
    pip_module_name: Name of the Python module to query.
    import_module_name: Optional name of a module to import to check whether
      it's installed.

  Returns:
    True if installed, False otherwise.

  Raises:
    subprocess.CalledProcessError: If pip fails to list modules.
  """
  if import_module_name and find_module_by_name(import_module_name):
    return True
  global _INSTALLED_MODULE_LIST
  if not _INSTALLED_MODULE_LIST and not getattr(sys, 'frozen', False):
    logging.debug('Listing installed pip packages')
    result = subprocess.run([sys.executable, '-m', 'pip', 'list'],
                            stdout=subprocess.PIPE, check=True)
    # Each line consists of "module_name\w+version", extract the module name
    # from each line.
    _INSTALLED_MODULE_LIST = [
        l.split()[0] for l in result.stdout.decode('utf-8').splitlines()]
    logging.debug('Found following installed packages: %s',
                  _INSTALLED_MODULE_LIST)
  return pip_module_name in _INSTALLED_MODULE_LIST


def _install_module(module: str, version: str):
  """Install a Python module if the application isn't frozen.

  Args:
    module: Name of the module to install.
    version: Version constraints for the module to install or an empty string
      to install the latest.

  Raises:
    subprocess.CalledProcessError: If module installation fails.
  """
  if not getattr(sys, 'frozen', False):
    logging.info('Installing Python module %s...', module)
    subprocess.check_call(_PIP_INSTALL_ARGS + [f'{module}{version}'])


def _check_platform_constraints(module: str, constraints: PlatformConstraints):
  """Check platform constraints for a module.

  Args:
    module: Name of the module.
    constraints: Platform constraints dictionary, where the key is a platform
      name returned by platform.system() and the value contains a list of
      supported architectures for the package. If no constraints are found for
      the current platform it is assumed the package is available for the
      platform.

  Raises:
    PlatformConstraintError: If the platform doesn't meet the specified
      constraints.
  """
  system_name = platform.system().lower()
  architecture = platform.architecture()
  platform_constraints = constraints.get(system_name)
  supported = (not platform_constraints or
               any(a for a in architecture if a in platform_constraints))
  if not supported:
    raise PlatformConstraintError(
        f'pip package {module} requires architecture {platform_constraints} '
        f'on {system_name} but the current Python environment has '
        f'architecture {architecture}. Try installing a different interpreter.')


def install_dependencies():
  """Install all Python module dependencies."""
  modules_installed = False
  for info in _REQUIRED_PYTHON_MODULES:
    _check_platform_constraints(info.pip_module_name, info.platform_constraints)
    if not _module_installed(info.pip_module_name, info.import_module_name):
      _install_module(info.pip_module_name, info.version_constraint)
      modules_installed = True
  if modules_installed:
    _clear_installed_modules_cache()


if int(os.environ.get('FALKEN_AUTO_INSTALL_DEPENDENCIES', 1)):
  install_dependencies()
