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

#!/usr/bin/python

# Lint as: python3

"""Build a CMake project."""

import argparse
import logging
import multiprocessing
import os
import shutil
import subprocess
import sys
import typing
import cmake_installer
import cmake_runner
import nasm_installer
import shell

# pylint: disable=g-import-not-at-top
# pylint: disable=W0403
sys.path.append(os.path.dirname(__file__))
# pylint: enable=g-import-not-at-top
# pylint: enable=W0403

CMAKE_VERSION = '3.18.4'

CMAKE_DOWNLOAD_URL_BASE = (
    f'https://github.com/Kitware/CMake/releases/download/v{CMAKE_VERSION}')

# Default CMake installer URL for the host operating system.
CMAKE_INSTALLER_URL_BY_HOST_PLATFORM = {
    'darwin':
        (CMAKE_DOWNLOAD_URL_BASE + f'/cmake-{CMAKE_VERSION}-Darwin-x86_64.dmg'),
    'linux':
        (CMAKE_DOWNLOAD_URL_BASE + f'/cmake-{CMAKE_VERSION}-Linux-x86_64.sh'),
    'win32':
        (CMAKE_DOWNLOAD_URL_BASE + f'/cmake-{CMAKE_VERSION}-win64-x64.zip'),
}

# Default configuration targets.
CMAKE_DEFAULT_BUILD_CONFIGS = ['Debug', 'Release']

# Possible returning values of the script.
EXIT_SUCCESS = 0
EXIT_FAILURE = 1

# List of required packages for windows.
REQUIRED_PACKAGES_LINUX = [
    'autoconf', 'automake', 'bison', 'flex', 'mono-complete', 'absl-py',
    'pyyaml'
]

REQUIRED_PACKAGES_WINDOWS = ['absl-py', 'pyyaml']

REQUIRED_PACKAGES_MAC = ['absl-py', 'pyyaml']

NASM_VERSION = '2.15.05'

NASM_URL = ('https://www.nasm.us/pub/nasm/releasebuilds/'
            f'{NASM_VERSION}/win64/nasm-{NASM_VERSION}-win64.zip')


def parse_arguments(args: typing.List[str]) -> argparse.Namespace:
  """Build an argument parser for the application.

  Args:
    args: Arguments to parse.

  Returns:
    A namespace populated with parsed arguments.
  """
  parser = argparse.ArgumentParser(
      description='Build a CMake project.',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument(
      '--python', default=sys.executable, help='Python interpreter path.')
  parser.add_argument(
      '--pip_packages',
      nargs='*',
      default=[],
      help='Python pip packages to install.')
  parser.add_argument(
      '--number_of_threads',
      default=multiprocessing.cpu_count(),
      type=int,
      help='Number of threads to use to build.')
  parser.add_argument(
      '--cmake_installer',
      default=CMAKE_INSTALLER_URL_BY_HOST_PLATFORM.get(sys.platform),
      help=('URL of the CMake install script or zip file to '
            'install in a temporary directory and then use '
            'to build the specified project.'))
  parser.add_argument(
      '--cmake_source_project_root',
      default=os.path.join(os.getcwd(), 'git', 'falken'),
      help=('Root source path for CMake projects. All CMake '
            'source directories are relative to this path.'))
  parser.add_argument(
      '--cmake_copybara_variable',
      default='FALKEN_DIR',
      help=('CMake variable to set with the value of '
            'cmake_copybara_source_root at configuration '
            'time.'))
  parser.add_argument(
      '--cmake_configure_args',
      nargs='*',
      default=[],
      help='Additional args to pass to CMake configuration.')
  parser.add_argument(
      '--cmake_generator',
      default=cmake_runner.CMakeRunner.default_generator(),
      help=('CMake generator to use at configuration time. '
            'If this is not specified CMake will use the '
            'default generator for the platform.'))
  parser.add_argument(
      '--cmake_target_architecture',
      default=cmake_runner.CMakeRunner.default_architecture(
          cmake_runner.CMakeRunner.default_generator()),
      help=('Architecture to build for with the selected '
            'CMake generator.'))
  parser.add_argument(
      '--cmake_build_dir',
      default=os.path.join(os.getcwd(), 'build'),
      help=('Directory used to build the CMake project.'))
  parser.add_argument(
      '--cmake_build_configs',
      nargs='*',
      default=CMAKE_DEFAULT_BUILD_CONFIGS,
      help=('List of configurations to build.'))
  parser.add_argument(
      '--cmake_package_configs',
      nargs='*',
      default=CMAKE_DEFAULT_BUILD_CONFIGS,
      help=('List of configurations to package. This must be '
            'a superset of the list of configurations to '
            'build.'))
  parser.add_argument(
      '--cmake_package_generator',
      default='ZIP',
      help=('Package generator to use to archive each build '
            'configuration.'))
  parser.add_argument(
      '--cmake_test_regex',
      help=('Regular expression which specifies the set of '
            'tests to execute.'))
  parser.add_argument(
      '--output_dir',
      default='output',
      help=('Directory to move build artifacts to.'))
  parser.add_argument(
      '--copy_artifacts',
      nargs='*',
      help=('Artifacts relative to the CMake project build '
            'config directory to copy to output_dir.'))
  parser.add_argument(
      '--zip_artifacts',
      nargs='*',
      help=('List of directory:archive.zip strings where '
            '"directory" is a directory relative to the CMake '
            'project build to archive and "archive.zip" is '
            'the name of a zip archive to create under '
            'output_dir.'))
  parser.add_argument(
      '--falken_json_config_file',
      default=None,
      help=('Configuration file for accessing Falken SDK.'))
  return parser.parse_args(args)


def run_and_check_result(command_line: str) -> bool:
  """Runs a command and check its result.

  Args:
    command_line: Command line to execute.

  Returns:
    True if execution was successful, False otherwise
  """
  try:
    result = shell.run_command(command_line)
  except subprocess.CalledProcessError:
    return False
  if result.returncode == 0:
    return True
  return False


def ensure_xcode_available() -> bool:
  """On macOS ensure Xcode is available.

  Returns:
    True if Xcode installed, False otherwise.
  """
  logging.info('Check if Xcode is available.')
  if run_and_check_result('xcode-select --print-path'):
    logging.info('Xcode found.')
    return True
  logging.info('Xcode was not found.')
  return False


def install_pip_packages(python_executable: str,
                         pip_packages: typing.List[str]) -> bool:
  """Install pip packages for the specified python.

  Args:
    python_executable: Python executable used to install pip packages.
    pip_packages: List of pip packages to install.

  Raises:
    subprocess.CalledProcessError if package installation fails.

  Returns:
    True if packages get installed, False otherwise.
  """

  if pip_packages:
    for package in pip_packages:
      if not is_package_installed(package):
        logging.info('Package %s not installed.', package)
        command = ' '.join([python_executable, '-m', 'pip', 'install'])
        command += ' ' + package
        logging.info('Install pip package: %s', package)
        if not run_and_check_result(command):
          return False
    return True
  logging.debug('no python packages were provided for installation.')
  return True


def is_package_installed(package_name: str) -> bool:
  """Checks if package is installed on linux.

  Args:
    package_name: name of the package to check

  Returns:
    True if packages is installed, False otherwise.
  """
  return run_and_check_result('dpkg-query -l ' + package_name)


def check_requirements_linux(args: argparse.Namespace) -> bool:
  """Checks that conditions for building on Mac are met.

  Args:
    args: arguments for building the project.

  Returns:
    True when execution ran successfully, False otherwise.
  """
  return install_pip_packages(args.python, REQUIRED_PACKAGES_LINUX)


def check_requirements_mac(args: argparse.Namespace) -> bool:
  """Checks that conditions for building on Mac are met.

  Args:
    args: arguments for building the project.

  Returns:
      True when execution ran successfully, False otherwise.
  """
  if not install_pip_packages(args.python, REQUIRED_PACKAGES_MAC):
    return False
  return ensure_xcode_available()


def check_requirements_win(args: argparse.Namespace) -> bool:
  """Checks that conditions for building on Windows are met.

  Args:
    args: arguments for building the project.

  Returns:
      True when execution ran successfully, False otherwise.
  """
  if not install_pip_packages(args.python, REQUIRED_PACKAGES_WINDOWS):
    return False

  # Check if Nasm is installed at it's the default location.
  executable_found = shutil.which('nasm')
  if executable_found is None:
    installer = nasm_installer.NasmInstaller(NASM_URL)
    return installer.install()
  return True


def check_requirements(platform_name: str, args: argparse.Namespace) -> bool:
  """Checks that requirements for building on current platform.

  Args:
    platform_name: name of the current platform.
    args: arguments for building the project.

  Returns:
    True when requirements are fulfilled, False otherwise.
  """
  if platform_name == 'linux':
    return check_requirements_linux(args)
  elif platform_name == 'darwin':
    return check_requirements_mac(args)
  elif platform_name == 'win32':
    return check_requirements_win(args)
  else:
    raise ValueError(f'Platform {platform_name} is not supported')


def generate_target(runner: cmake_runner.CMakeRunner, args: argparse.Namespace,
                    build_config: str) -> bool:
  """Generates the project using the configuration provided.

  Args:
    runner: Cmake runner object.
    args: Arguments for cmake.
    build_config: Name of configuration target.

  Returns:
    True when execution ran successfully, False otherwise.
  """
  try:
    runner.configure(
        generator=args.cmake_generator,
        architecture=args.cmake_target_architecture,
        build_config=build_config,
        falken_json_config_file=args.falken_json_config_file,
        args=args.cmake_configure_args)
  except subprocess.CalledProcessError as error:
    logging.exception('Failed to configure %s CMake project %s: %s',
                      build_config, args.cmake_source_project_root, error)
    return False
  return True


def build_target(runner: cmake_runner.CMakeRunner, args: argparse.Namespace,
                 build_config: str) -> bool:
  """Generates the project using the configuration provided.

  Args:
    runner: Cmake runner object.
    args: Arguments for cmake.
    build_config: Name of configuration target.

  Returns:
    True when execution ran successfully, False otherwise.
  """
  try:
    runner.build(args=('-j', str(args.number_of_threads)))
  except subprocess.CalledProcessError as error:
    logging.exception('Failed to build %s CMake project %s: %s', build_config,
                      args.cmake_source_project_root, error)
    return False
  return True


def copy_artifacts(runner: cmake_runner.CMakeRunner, args: argparse.Namespace):
  """Copy artifacts of the project.

  Args:
    runner: Cmake runner object.
    args: Arguments for cmake.
  """
  for artifact in args.copy_artifacts:
    filename = os.path.join(runner.build_config_dir, artifact)
    logging.info('Copying build artifact: %s --> %s', filename, args.output_dir)
    shutil.copy(filename, args.output_dir)


def zip_artifacts(runner: cmake_runner.CMakeRunner,
                  args: argparse.Namespace) -> bool:
  """Zip the project.

  Args:
    runner: Cmake runner object.
    args: Arguments for cmake.

  Returns:
    True when zipping ran successfully, False otherwise.
  """
  for zip_artifact in args.zip_artifacts:
    tokens = zip_artifact.split(':')
    if len(tokens) != 2:
      logging.error('Invalid zip artifact %s', zip_artifact)
      return False
    relative_directory, zip_filename = tokens
    source_directory = os.path.join(runner.build_config_dir, relative_directory)
    zip_path = os.path.join(args.output_dir, zip_filename)
    logging.info('Archiving build artifacts: %s --> %s', source_directory,
                 zip_path)
    shutil.make_archive(zip_path, 'zip', source_directory)
  return True


def package_project(runner: cmake_runner.CMakeRunner, args: argparse.Namespace,
                    build_config: str) -> bool:
  """Package the compiled project.

  Args:
    runner: Cmake runner object.
    args: Arguments for cmake.
    build_config: Name of configuration target.

  Returns:
    True when packaging ran successfully, False otherwise.
  """
  try:
    package = runner.pack(args.cmake_package_generator)
  except (subprocess.CalledProcessError, RuntimeError) as error:
    logging.exception('Failed to package %s CMake project %s: %s', build_config,
                      args.cmake_source_project_root, error)
    return False
  if package:
    shutil.copy(package, args.output_dir)
  else:
    logging.error(
        'Packaging step of project %s config %s failed to '
        'generate a package.', args.cmake_source_project_root, build_config)
    return False
  return True


def run_tests(runner: cmake_runner.CMakeRunner, args: argparse.Namespace,
              build_config: str) -> bool:
  """Run tests for the current project.

  Args:
    runner: Cmake runner object.
    args: Arguments for cmake.
    build_config: Name of configuration target.

  Returns:
    True when testing ran successfully, False otherwise.
  """
  try:
    runner.test(args=args.cmake_test_regex)
  except (subprocess.CalledProcessError, RuntimeError) as error:
    logging.exception('Tests failed for %s CMake project %s: %s', build_config,
                      args.cmake_source_project_root, error)
    return False
  return True


def build_project(args: argparse.Namespace) -> bool:
  """Build Falken project.

  Args:
    args: building parameters.

  Returns:
    True when execution ran successfully, False otherwise.
  """
  os.makedirs(args.output_dir, exist_ok=True)

  successful = True
  with cmake_installer.CMakeInstaller(args.cmake_installer) as installer:
    runner = cmake_runner.CMakeRunner(installer.binary_dir,
                                      args.cmake_source_project_root,
                                      args.cmake_build_dir)
    for build_config in args.cmake_build_configs:
      # Configure the project.
      result = generate_target(runner, args, build_config)
      if not result:
        successful = False

      # Build the project.
      result = build_target(runner, args, build_config)
      if not result:
        successful = False

      # Copy build artifacts to the output directory.
      if args.copy_artifacts:
        copy_artifacts(runner, args)

      # Archive directories in the output directory.
      if args.zip_artifacts:
        result = zip_artifacts(runner, args)
        if not result:
          successful = False

      # Package the project and copy it to the output directory.
      if (args.cmake_package_configs and
          build_config in args.cmake_package_configs):
        package_project(runner, args, build_config)

      # Run tests.
      if args.falken_json_config_file:
        result = run_tests(runner, args, build_config)
        if not result:
          successful = False

  return successful


def main():
  """Build a CMake project.

  Returns:
    EXIT_SUCCESS when compilation was successful, EXIT_FAILURE otherwise.
  """

  logging.getLogger().setLevel(logging.INFO)

  # Print arguments.
  args = parse_arguments(sys.argv[1:])
  logging.info('Running %s with args:', sys.argv[0])
  for kv in vars(args).items():
    logging.info(kv)

  if check_requirements(sys.platform, args):
    if build_project(args):
      return EXIT_SUCCESS
    return EXIT_FAILURE
  return EXIT_FAILURE


if __name__ == '__main__':
  sys.exit(main())
