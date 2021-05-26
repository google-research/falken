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

"""Test CMakeRunner."""

import os
import subprocess
import sys
import unittest
import unittest.mock

# pylint: disable=g-import-not-at-top
# pylint: disable=W0403
sys.path.append(os.path.dirname(__file__))
import cmake_runner
# pylint: enable=g-import-not-at-top
# pylint: enable=W0403


class CMakeRunnerTest(unittest.TestCase):
  """Test CMakeRunner."""

  def test_default_generator(self):
    """Get the default generator for each platform."""
    with unittest.mock.patch('sys.platform', 'linux') as _:
      self.assertEqual('Unix Makefiles',
                       cmake_runner.CMakeRunner.default_generator())
    with unittest.mock.patch('sys.platform', 'win32') as _:
      self.assertEqual('Visual Studio 15 2017',
                       cmake_runner.CMakeRunner.default_generator())
    with unittest.mock.patch('sys.platform', 'darwin') as _:
      self.assertEqual('Xcode',
                       cmake_runner.CMakeRunner.default_generator())

  def test_default_architecture(self):
    """Get the default architecture for each platform."""
    self.assertEqual('', cmake_runner.CMakeRunner.default_architecture(
        'Unix Makefiles'))
    self.assertEqual('x64', cmake_runner.CMakeRunner.default_architecture(
        'Visual Studio 12 2010'))

  def test_is_multi_config_generator(self):
    """Verify multi-config generators are detected."""
    for multi_config, generator in ((False, 'Borland Makefiles'),
                                    (False, 'MSYS Makefiles'),
                                    (False, 'MinGW Makefiles'),
                                    (False, 'NMake Makefiles'),
                                    (False, 'Unix Makefiles'),
                                    (False, 'Watcom WMake'),
                                    (False, 'Ninja'),
                                    (True, 'Ninja Multi-Config'),
                                    (True, 'Visual Studio 6'),
                                    (True, 'Visual Studio 7'),
                                    (True, 'Visual Studio 7 .NET 2003'),
                                    (True, 'Visual Studio 8 2005'),
                                    (True, 'Visual Studio 9 2008'),
                                    (True, 'Visual Studio 10 2010'),
                                    (True, 'Visual Studio 11 2012'),
                                    (True, 'Visual Studio 12 2013'),
                                    (True, 'Visual Studio 14 2015'),
                                    (True, 'Visual Studio 15 2017'),
                                    (True, 'Visual Studio 16 2019'),
                                    (True, 'Xcode')):
      runner = cmake_runner.CMakeRunner('/tmp/foo', '/home/my/project',
                                        '/tmp/build')
      runner._generator = generator
      self.assertEqual(multi_config, runner._is_multi_config_generator,
                       msg=generator)

  def test_construct(self):
    """Construct a runner and verify binary locations."""
    runner = cmake_runner.CMakeRunner('/tmp/foo', '/home/my/project',
                                      '/tmp/build')
    self.assertEqual(runner.cmake_binary,
                     os.path.join('/tmp/foo',
                                  f'cmake{cmake_runner.EXECUTABLE_EXTENSION}'))
    self.assertEqual(runner.cpack_binary,
                     os.path.join('/tmp/foo',
                                  f'cpack{cmake_runner.EXECUTABLE_EXTENSION}'))

  @unittest.mock.patch('cmake_runner.CMakeRunner.default_generator')
  @unittest.mock.patch('cmake_runner.CMakeRunner.default_architecture')
  @unittest.mock.patch('shell.run_command')
  def test_configure_default_generator_and_architecture(self, mock_run,
                                                        mock_architecture,
                                                        mock_generator):
    """Configure a project with no arguments."""
    mock_generator.return_value = 'Ninja'
    mock_architecture.return_value = 'arm64'
    runner = cmake_runner.CMakeRunner('/tmp/foo', '/home/my/project',
                                      '/tmp/build')
    runner.configure()
    mock_run.assert_called_once_with(
        f'{runner.cmake_binary} -G "Ninja" -A "arm64" '
        '-DCMAKE_BUILD_TYPE=Debug -S /home/my/project '
        '-B /tmp/build/arm64/Debug')

  @unittest.mock.patch('cmake_runner.CMakeRunner.default_architecture')
  @unittest.mock.patch('shell.run_command')
  def test_configure_default_architecture(self, mock_run, mock_architecture):
    """Configure a project using the default architecture for a generator."""
    mock_architecture.return_value = 'armeabi-v7a'
    runner = cmake_runner.CMakeRunner('/tmp/foo', '/home/my/project',
                                      '/tmp/build')
    runner.configure(generator='Ninja')
    mock_run.assert_called_once_with(
        f'{runner.cmake_binary} -G "Ninja" -A "armeabi-v7a" '
        '-DCMAKE_BUILD_TYPE=Debug -S /home/my/project '
        '-B /tmp/build/armeabi-v7a/Debug')

  @unittest.mock.patch('shell.run_command')
  def test_configure_single_config(self, mock_run):
    """Configure a project using a single config generator."""
    for build_config, expected_config in ((None, 'Debug'), ('Debug', 'Debug'),
                                          ('Release', 'Release')):
      mock_run.reset_mock()
      runner = cmake_runner.CMakeRunner('/tmp/foo', '/home/my/project',
                                        '/tmp/build')
      runner.configure(generator='Unix Makefiles', build_config=build_config)
      mock_run.assert_called_once_with(
          f'{runner.cmake_binary} -G "Unix Makefiles" '
          f'-DCMAKE_BUILD_TYPE={expected_config} '
          f'-S /home/my/project -B /tmp/build/{expected_config}')

  @unittest.mock.patch('shell.run_command')
  def test_configure_multi_config(self, mock_run):
    """Configure a project using a multi config generator."""
    for build_config, expected_config in ((None, 'Debug'), ('Debug', 'Debug'),
                                          ('Release', 'Release')):
      mock_run.reset_mock()
      runner = cmake_runner.CMakeRunner('/tmp/foo', '/home/my/project',
                                        '/tmp/build')
      runner.configure(generator='Visual Studio 14 2015',
                       architecture='Win32',
                       build_config=build_config)
      mock_run.assert_called_once_with(
          f'{runner.cmake_binary} -G "Visual Studio 14 2015" -A "Win32" '
          '-S /home/my/project -B /tmp/build')
      self.assertEqual(runner._build_config, expected_config)

  @unittest.mock.patch('shell.run_command')
  def test_configure_with_properties(self, mock_run):
    """Configure a project with some properties."""
    runner = cmake_runner.CMakeRunner('/tmp/foo', '/home/my/project',
                                      '/tmp/build')
    runner.configure(generator='Unix Makefiles',
                     properties={'TRANSPORTER': 'ON', 'SHIELDS': 'OFF'})
    mock_run.assert_called_once_with(
        f'{runner.cmake_binary} -DTRANSPORTER=ON -DSHIELDS=OFF '
        '-G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Debug '
        '-S /home/my/project -B /tmp/build/Debug')

  @unittest.mock.patch('shell.run_command')
  def test_configure_with_generator_and_architecture(self, mock_run):
    """Configure a project with a non-default generator and architecture."""
    runner = cmake_runner.CMakeRunner('/tmp/foo', '/home/my/project',
                                      '/tmp/build')
    runner.configure(generator='Ninja', architecture='mips64')
    mock_run.assert_called_once_with(
        f'{runner.cmake_binary} -G "Ninja" -A "mips64" '
        '-DCMAKE_BUILD_TYPE=Debug -S /home/my/project '
        '-B /tmp/build/mips64/Debug')

  @unittest.mock.patch('shell.run_command')
  def test_configure_with_custom_args(self, mock_run):
    """Configure a project with custom arguments."""
    runner = cmake_runner.CMakeRunner('/tmp/foo', '/home/my/project',
                                      '/tmp/build')
    runner.configure(generator='Xcode', args=('-Wno-dev', '-Wdeprecated'))
    mock_run.assert_called_once_with(
        f'{runner.cmake_binary} -Wno-dev -Wdeprecated -G "Xcode" '
        '-S /home/my/project -B /tmp/build')

  @unittest.mock.patch('shell.run_command')
  def test_build_single_config(self, mock_run):
    """Build a project with a single config generator."""
    runner = cmake_runner.CMakeRunner('/tmp/foo', '/home/my/project',
                                      '/tmp/build')
    runner.configure(generator='Unix Makefiles', build_config='Debug')
    mock_run.reset_mock()
    runner.build()
    mock_run.assert_called_once_with(
        f'{runner.cmake_binary} --build /tmp/build/Debug --verbose')

  @unittest.mock.patch('shell.run_command')
  def test_build_single_config_quiet_output(self, mock_run):
    """Build a project with a single config generator."""
    runner = cmake_runner.CMakeRunner('/tmp/foo', '/home/my/project',
                                      '/tmp/build')
    runner.configure(generator='Unix Makefiles', build_config='Debug')
    mock_run.reset_mock()
    runner.build(verbose=False)
    mock_run.assert_called_once_with(
        f'{runner.cmake_binary} --build /tmp/build/Debug')

  @unittest.mock.patch('shell.run_command')
  def test_build_multi_config(self, mock_run):
    """Build a project with a multi config generator."""
    runner = cmake_runner.CMakeRunner('/tmp/foo', '/home/my/project',
                                      '/tmp/build')
    runner.configure(generator='Xcode', build_config='Release')
    mock_run.reset_mock()
    runner.build()
    mock_run.assert_called_once_with(
        f'{runner.cmake_binary} --build /tmp/build --config Release --verbose')

  @unittest.mock.patch('shell.run_command')
  def test_build_with_custom_args(self, mock_run):
    """Build a project with custom arguments."""
    runner = cmake_runner.CMakeRunner('/tmp/foo', '/home/my/project',
                                      '/tmp/build')
    runner.configure(generator='Unix Makefiles', build_config='Debug')
    mock_run.reset_mock()
    runner.build(verbose=False, args=('-j', '64', '--clean-first'))
    mock_run.assert_called_once_with(
        f'{runner.cmake_binary} --build /tmp/build/Debug -j 64 '
        '--clean-first')

  @unittest.mock.patch('shell.run_command')
  def test_pack(self, mock_run):
    """Package build artifacts."""
    runner = cmake_runner.CMakeRunner('/tmp/foo', '/home/my/project',
                                      '/tmp/build')
    runner.configure(generator='Unix Makefiles', build_config='Debug')
    mock_run.reset_mock()

    completed_process = unittest.mock.MagicMock(subprocess.CompletedProcess)
    completed_process.stdout = (
        'CPack: Create package using ZIP\n'
        'CPack: Install projects\n'
        'CPack: - Run preinstall target for: myproj\n'
        'CPack: - Install project: myproj []\n'
        'CPack: Create package\n'
        'CPack: - package: /tmp/build/Debug/packaging/myproj-1.2.3.zip '
        'generated.\n'
    )
    mock_run.return_value = completed_process
    package_location = runner.pack('ZIP')
    mock_run.assert_called_once_with(
        f'{runner.cpack_binary} -G ZIP --verbose', cwd='/tmp/build/Debug',
        stdout=subprocess.PIPE, encoding='utf-8')
    self.assertEqual(package_location,
                     '/tmp/build/Debug/packaging/myproj-1.2.3.zip')

  @unittest.mock.patch('shell.run_command')
  def test_ctest(self, mock_run):
    """Test project."""
    runner = cmake_runner.CMakeRunner('/tmp/foo', '/home/my/project',
                                      '/tmp/build')
    runner.configure(generator='Unix Makefiles', build_config='Debug')

    mock_run.reset_mock()
    runner.test(args=('-R', '"falken.*"'))
    mock_run.assert_called_once_with(
        f'{runner.ctest_binary} --verbose -R "falken.*"',
        cwd='/tmp/build/Debug')


if __name__ == '__main__':
  unittest.main()
