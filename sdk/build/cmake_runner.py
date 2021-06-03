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

"""Runs CMake tools."""

import logging
import os
import re
import subprocess
import sys
import typing

# pylint: disable=g-import-not-at-top
# pylint: disable=W0403
sys.path.append(os.path.dirname(__file__))
import shell
# pylint: enable=g-import-not-at-top
# pylint: enable=W0403

# Extension for executables.
EXECUTABLE_EXTENSION = '.exe' if sys.platform == 'win32' else ''

# Multi-configuration generator.
MULTI_CONFIG_GENERATOR_RE = re.compile(
    r'^(Visual Studio.*|Xcode|Ninja Multi-Config)$')

# Default CMake generator for the host operating system.
GENERATOR_BY_HOST_PLATFORM = {
    'darwin': 'Xcode',
    'linux': 'Unix Makefiles',
    'win32': 'Visual Studio 15 2017',
}

# Default target architecture for the target platform.
ARCHITECTURE_BY_GENERATOR_RE = [
    (re.compile(r'^(Visual Studio.*)$'), 'x64')
]


class CMakeRunner:
  """Runs CMake tools.

  Attributes:
    _binary_dir: Directory containing CMake tools.
    _project_dir: Directory containing the CMake project to configure and
      build.
    _build_dir: Root directory for CMake build artifacts.
    _generator: Generator for the configured project.
    _architecture: Architecture of the generated project.
    _build_config: Currently selected build configuration.
    _build_config_dir: Directory where the project will be configured and
      built.
  """

  # Extracts the generated package path from CPack's output.
  CPACK_PACKAGE_RE = re.compile(r'.*package: (.*) generated.$')

  def __init__(self, binary_dir: str, project_dir: str, build_dir: str):
    """Initialize this instance.

    Args:
      binary_dir: Directory containing CMake tools.
      project_dir: Directory containing the CMake project to configure and
        build.
      build_dir: Directory for CMake build artifacts.
    """
    self._binary_dir = binary_dir
    self._project_dir = project_dir
    self._build_dir = build_dir
    self._generator = ''
    self._architecture = ''
    self._build_config = ''
    self._build_config_dir = build_dir

  @property
  def cmake_binary(self) -> str:
    """CMake binary path."""
    return os.path.join(self._binary_dir, f'cmake{EXECUTABLE_EXTENSION}')

  @property
  def cpack_binary(self) -> str:
    """CPack binary path."""
    return os.path.join(self._binary_dir, f'cpack{EXECUTABLE_EXTENSION}')

  @property
  def ctest_binary(self) -> str:
    """CTest binary path."""
    return os.path.join(self._binary_dir, f'ctest{EXECUTABLE_EXTENSION}')

  @staticmethod
  def default_generator() -> str:
    """Get the default CMake generator for the current platform.

    Returns:
      CMake generator name.
    """
    return GENERATOR_BY_HOST_PLATFORM[sys.platform]

  @staticmethod
  def default_architecture(generator: str) -> str:
    """Get the default target architecture for the specified generator.

    Args:
      generator: Generator to query.

    Returns:
      CMake architecture name or an empty string if there is no default.
    """
    for regex, architecture in ARCHITECTURE_BY_GENERATOR_RE:
      if regex.match(generator):
        return architecture
    return ''

  @property
  def _is_multi_config_generator(self) -> bool:
    """Whether the current CMake generator supports multi-configuration.

    Returns:
      True if the generator supports multiple projects, False otherwise.
    """
    return True if MULTI_CONFIG_GENERATOR_RE.match(self._generator) else False

  @property
  def build_config_dir(self) -> str:
    """Get the directory where the project is configured to build.

    Returns:
      Where the project is built.
    """
    return self._build_config_dir

  def configure(self,
                generator: typing.Optional[str] = None,
                architecture: typing.Optional[str] = None,
                build_config: typing.Optional[str] = None,
                properties: typing.Optional[typing.Dict[str, str]] = None,
                falken_json_config_file: str = None,
                args: typing.Optional[typing.List[str]] = None):
    """Configure the CMake project.

    Args:
      generator: CMake generator name to create the project or None to use the
        default generator.
      architecture: Target architecture or None to use the default.
      build_config: Build configuration to compile ('Debug', 'Release')
        or None to target Debug.
      properties: Dictionary of configuration variable key / value pairs
        to pass to CMake. Variables without a value are not passed to CMake's
        configuration command.
      falken_json_config_file: Configuration file for accessing Falken SDK.
      args: Additional arguments to pass to CMake.

    Raises:
      subprocess.CalledProcessError: If CPack fails.
    """
    self._generator = (
        generator if generator else CMakeRunner.default_generator())
    self._architecture = (architecture if architecture else
                          self.default_architecture(self._generator))
    self._build_config = build_config if build_config else 'Debug'
    if self._is_multi_config_generator:
      self._build_config_dir = self._build_dir
    else:
      self._build_config_dir = os.path.join(self._build_dir,
                                            self._architecture,
                                            self._build_config)
    os.makedirs(self.build_config_dir, exist_ok=True)

    command_args = []
    if properties:
      for key, value in properties.items():
        if value:
          command_args.append(f'-D{key}={value}')
    if falken_json_config_file:
      command_args.append(
          f'-DFALKEN_JSON_CONFIG_FILE={falken_json_config_file}')
    if args:
      command_args.extend(args)
    command_args.append(f'-G "{self._generator}"')
    if self._architecture:
      command_args.append(f'-A "{self._architecture}"')
    if not self._is_multi_config_generator:
      command_args.append(f'-DCMAKE_BUILD_TYPE={self._build_config}')

    logging.info('Configuring CMake project %s in %s...', self._project_dir,
                 self.build_config_dir)
    shell.run_command(' '.join(
        [self.cmake_binary] + command_args +
        ['-S', self._project_dir, '-B', self.build_config_dir]))

  def build(self, verbose: bool = True, args: typing.List[str] = None):
    """Build a configured CMake project.

    Args:
      verbose: Whether to display verbose build output.
      args: Additional arguments to pass to CMake.

    Raises:
      subprocess.CalledProcessError: If CPack fails.
    """
    logging.info('Building CMake project %s in %s...', self._project_dir,
                 self.build_config_dir)
    command_args = [self.cmake_binary, '--build', self.build_config_dir]
    if self._is_multi_config_generator:
      command_args.append(f'--config {self._build_config}')
    if verbose:
      command_args.append('--verbose')
    if args:
      command_args.extend(args)
    shell.run_command(' '.join(command_args))

  def pack(self, generator, verbose: bool = True,
           args: typing.List[str] = None) -> str:
    """Package a built CMake project.

    Args:
      generator: Generator to use.
      verbose: Display verbose output.
      args: Additional arguments to pass to CPack.

    Returns:
      Path to the package.

    Raises:
      RuntimeError: If the package path isn't found in CPack's output.
        subprocess.CalledProcessError: If CPack fails.
    """
    logging.info('Packaging CMake project %s to %s...', self._project_dir,
                 self.build_config_dir)
    command_args = [self.cpack_binary, '-G', generator]
    if self._is_multi_config_generator:
      command_args.append(f'-C {self._build_config}')
    if verbose:
      command_args.append('--verbose')
    if args:
      command_args.extend(args)
    result = shell.run_command(' '.join(command_args),
                               cwd=self.build_config_dir,
                               stdout=subprocess.PIPE, encoding='utf-8')
    sys.stdout.write(result.stdout)
    for line in result.stdout.splitlines():
      match = CMakeRunner.CPACK_PACKAGE_RE.match(line)
      if match:
        return match.groups()[0]
    raise RuntimeError(f'Package not found in CPack output\n{result.stdout}')

  def test(self, verbose: bool = True, args: typing.List[str] = None):
    """Test a built CMake project.

    Args:
      verbose: Display verbose output.
      args: Additional arguments to pass to CPack.

    Raises:
      RuntimeError: If the package path isn't found in CPack's output.
        subprocess.CalledProcessError: If CPack fails.
    """
    logging.info('Running tests for project %s...', self._project_dir)

    command_args = [self.ctest_binary]
    if self._is_multi_config_generator:
      command_args.append(f'-C {self._build_config}')
    if verbose:
      command_args.append('--verbose')
    if args:
      command_args.extend(args)
    shell.run_command(' '.join(command_args), cwd=self.build_config_dir)
