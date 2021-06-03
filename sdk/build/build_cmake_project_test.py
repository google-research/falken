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

"""Tests for the cmake builder script."""

import multiprocessing
import os
import subprocess
import sys
import unittest

from unittest import mock

# pylint: disable=g-import-not-at-top
# pylint: disable=W0403
sys.path.append(os.path.dirname(__file__))
import build_cmake_project
import cmake_installer
import cmake_runner
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

CMAKE_DEFAULT_BUILD_CONFIGS = ['Debug', 'Release']


class BuildCmakeTest(unittest.TestCase):
  """Test build cmake methods."""

  def setUp(self):
    super().setUp()
    self.args = build_cmake_project.parse_arguments([])
    self.installer = cmake_installer.CMakeInstaller(self.args.cmake_installer)

  def test_parse_arguments_default(self):
    """Check parsing default arguments."""
    self.assertEqual(self.args.python, sys.executable)
    self.assertEqual(self.args.pip_packages, [])
    self.assertEqual(self.args.number_of_threads, multiprocessing.cpu_count())
    self.assertEqual(self.args.cmake_installer,
                     CMAKE_INSTALLER_URL_BY_HOST_PLATFORM.get(sys.platform))
    self.assertEqual(self.args.cmake_source_project_root,
                     os.path.join(os.getcwd(), 'git', 'falken'))
    self.assertEqual(self.args.cmake_copybara_variable, 'FALKEN_DIR')
    self.assertEqual(self.args.cmake_configure_args, [])
    self.assertEqual(self.args.cmake_generator,
                     cmake_runner.CMakeRunner.default_generator())
    self.assertEqual(
        self.args.cmake_target_architecture,
        cmake_runner.CMakeRunner.default_architecture(
            cmake_runner.CMakeRunner.default_generator()))
    self.assertEqual(self.args.cmake_build_dir,
                     os.path.join(os.getcwd(), 'build'))
    self.assertEqual(self.args.cmake_build_configs, CMAKE_DEFAULT_BUILD_CONFIGS)
    self.assertEqual(self.args.cmake_package_configs,
                     CMAKE_DEFAULT_BUILD_CONFIGS)
    self.assertEqual(self.args.cmake_package_generator, 'ZIP')
    self.assertIsNone(self.args.cmake_test_regex)
    self.assertEqual(self.args.output_dir, 'output')
    self.assertIsNone(self.args.copy_artifacts)
    self.assertIsNone(self.args.zip_artifacts)

  def test_parse_custom_arguments(self):
    """Check parsing custom arguments."""
    arguments = build_cmake_project.parse_arguments([
        '--cmake_package_generator=7Z', '--cmake_configure_args=Xcode',
        '--number_of_threads=7'
    ])
    self.assertEqual(arguments.python, sys.executable)
    self.assertEqual(arguments.pip_packages, [])
    self.assertEqual(arguments.number_of_threads, 7)
    self.assertEqual(arguments.cmake_installer,
                     CMAKE_INSTALLER_URL_BY_HOST_PLATFORM.get(sys.platform))
    self.assertEqual(arguments.cmake_source_project_root,
                     os.path.join(os.getcwd(), 'git', 'falken'))
    self.assertEqual(arguments.cmake_copybara_variable, 'FALKEN_DIR')
    self.assertEqual(arguments.cmake_configure_args, ['Xcode'])
    self.assertEqual(arguments.cmake_generator,
                     cmake_runner.CMakeRunner.default_generator())
    self.assertEqual(
        arguments.cmake_target_architecture,
        cmake_runner.CMakeRunner.default_architecture(
            cmake_runner.CMakeRunner.default_generator()))
    self.assertEqual(arguments.cmake_build_dir,
                     os.path.join(os.getcwd(), 'build'))
    self.assertEqual(arguments.cmake_build_configs, CMAKE_DEFAULT_BUILD_CONFIGS)
    self.assertEqual(arguments.cmake_package_configs,
                     CMAKE_DEFAULT_BUILD_CONFIGS)
    self.assertEqual(arguments.cmake_package_generator, '7Z')
    self.assertIsNone(arguments.cmake_test_regex)
    self.assertEqual(arguments.output_dir, 'output')
    self.assertIsNone(arguments.copy_artifacts)
    self.assertIsNone(arguments.zip_artifacts)

  def test_run_and_check_result(self):
    """Run a command in bash without getting exceptions."""
    # Run a successful command.
    result = build_cmake_project.run_and_check_result('echo hello world')
    self.assertTrue(result)

    # Run a failure command.
    try:
      result = build_cmake_project.run_and_check_result('unexistent --command')
    except subprocess.CalledProcessError:
      self.fail('Exception thrown when running unexistent command.')
    self.assertFalse(result)

  @unittest.mock.patch('subprocess.run')
  def test_ensure_xcode_available(self, mock_run):
    """Test for checking xcode availability."""
    build_cmake_project.ensure_xcode_available()
    mock_run.assert_called_once_with(
        args='xcode-select --print-path', check=True, shell=True)

  @unittest.mock.patch('subprocess.run')
  def test_install_pip_package(self, mock_run):
    """Test for installing pip packages."""
    build_cmake_project.install_pip_packages('python3', ['logging'])
    mock_run.assert_called_with(
        args='python3 -m pip install logging', check=True, shell=True)

  @unittest.mock.patch('os.makedirs')
  @unittest.mock.patch('subprocess.run')
  def test_generate_target(self, mock_run, mock_make_dirs):
    """Test for generating configuration for target."""
    self.args.cmake_source_project_root = '/tmp/falken_src'
    self.args.cmake_build_dir = '/tmp/build_folder'
    self.args.falken_json_config_file = '/tmp/config_file.json'

    runner = cmake_runner.CMakeRunner(self.installer.binary_dir,
                                      self.args.cmake_source_project_root,
                                      self.args.cmake_build_dir)

    build_cmake_project.generate_target(runner, self.args, 'Debug')

    # Create folder.
    mock_make_dirs.assert_called_once_with(
        '/tmp/build_folder/Debug', exist_ok=True)
    # Call cmake
    mock_run.assert_called_once_with(
        args='cmake -DFALKEN_JSON_CONFIG_FILE=/tmp/config_file.json '
        '-G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Debug -S /tmp/falken_src '
        '-B /tmp/build_folder/Debug',
        check=True,
        shell=True)

  @unittest.mock.patch('subprocess.run')
  def test_build_target(self, mock_run):
    """Test for building specific target."""
    self.args.cmake_source_project_root = '/tmp/falken_src'
    self.args.cmake_build_dir = '/tmp/build_folder'
    self.args.number_of_threads = 7

    runner = cmake_runner.CMakeRunner(self.installer.binary_dir,
                                      self.args.cmake_source_project_root,
                                      self.args.cmake_build_dir)

    build_cmake_project.build_target(runner, self.args, 'Debug')

    # Call cmake
    mock_run.assert_called_once_with(
        args='cmake --build /tmp/build_folder --verbose -j 7',
        check=True,
        shell=True)

  @unittest.mock.patch('shutil.copy')
  def test_copy_artifacts(self, shutil_copy):
    """Test copying artifacts."""
    self.args.cmake_source_project_root = '/tmp/falken_src'
    self.args.cmake_build_dir = '/tmp/falken_src'
    self.args.copy_artifacts = ['file.dat']

    runner = cmake_runner.CMakeRunner(self.installer.binary_dir,
                                      self.args.cmake_source_project_root,
                                      self.args.cmake_build_dir)

    build_cmake_project.copy_artifacts(runner, self.args)

    filename = os.path.join(runner.build_config_dir,
                            self.args.copy_artifacts[0])
    shutil_copy.assert_called_with(filename, self.args.output_dir)

  @unittest.mock.patch('shutil.make_archive')
  def test_zip_artifacts(self, shutil_make):
    """Test zipping artifacts."""
    self.args.cmake_source_project_root = '/tmp/falken_src'
    self.args.cmake_build_dir = '/tmp/falken_src'
    self.args.zip_artifacts = ['/tmp/artifacts:artifact1.png']

    runner = cmake_runner.CMakeRunner(self.installer.binary_dir,
                                      self.args.cmake_source_project_root,
                                      self.args.cmake_build_dir)

    build_cmake_project.zip_artifacts(runner, self.args)

    zip_path = os.path.join(self.args.output_dir, 'artifact1.png')
    source_directory = os.path.join(runner.build_config_dir, '/tmp/artifacts')
    shutil_make.assert_called_with(zip_path, 'zip', source_directory)

  @unittest.mock.patch('subprocess.run')
  def test_package_project(self, mock_run):
    """Test packaging the project."""
    self.args.cmake_source_project_root = '/tmp/falken_src'
    self.args.cmake_build_dir = '/tmp/falken_src'

    runner = cmake_runner.CMakeRunner(self.installer.binary_dir,
                                      self.args.cmake_source_project_root,
                                      self.args.cmake_build_dir)

    return_value_mock = mock.MagicMock()
    return_value_mock.stdout = 'shell_command_result'
    mock_run.return_value = return_value_mock
    build_cmake_project.package_project(runner, self.args, 'Debug')
    mock_run.assert_called_once_with(
        args='cpack -G ZIP --verbose',
        check=True,
        cwd='/tmp/falken_src',
        encoding='utf-8',
        shell=True,
        stdout=-1)

  @unittest.mock.patch('subprocess.run')
  def test_run_tests(self, mock_run):
    """Test running tests."""
    self.args.cmake_source_project_root = '/tmp/falken_src'
    self.args.cmake_build_dir = '/tmp/falken_src'

    runner = cmake_runner.CMakeRunner(self.installer.binary_dir,
                                      self.args.cmake_source_project_root,
                                      self.args.cmake_build_dir)

    build_cmake_project.run_tests(runner, self.args, 'Debug')

    mock_run.assert_called_once_with(
        args='ctest --verbose', check=True, cwd='/tmp/falken_src', shell=True)

  @unittest.mock.patch('subprocess.run')
  def test_is_package_installed(self, mock_run):
    """Test method for checking if package is installed."""

    build_cmake_project.is_package_installed('tmux')
    mock_run.assert_called_once_with(
        args='dpkg-query -l tmux', check=True, shell=True)


if __name__ == '__main__':
  unittest.main()
