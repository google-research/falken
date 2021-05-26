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

"""Tests for the CMake installer."""

import os
import stat
import sys
import tempfile
import unittest
import unittest.mock

# pylint: disable=g-import-not-at-top
# pylint: disable=W0403
sys.path.append(os.path.dirname(__file__))
import cmake_installer
# pylint: enable=g-import-not-at-top
# pylint: enable=W0403


def create_test_files(directory: str):
  """Create a file and some directories in the specified directory.

  Args:
    directory: Where to put test files.
  """
  os.makedirs(os.path.join(directory, 'hello', 'world'))
  with open(os.path.join(directory, 'afile.txt'), 'wt') as text:
    text.write('goodbye Dave')


class TestInstallers(unittest.TestCase):
  """Test methods that install CMake built packages."""

  def test_uninstall(self):
    """Uninstall should remove the contents of a directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
      create_test_files(temp_dir)
      installer = cmake_installer.Installer('', temp_dir)
      installer.uninstall()
      self.assertCountEqual(os.listdir(temp_dir), [])

    installer = cmake_installer.Installer('', '/tmp/nothisdoesnotexist')
    installer.uninstall()

  @unittest.mock.patch('shell.run_command')
  def test_mount_dmg(self, mock_run: unittest.mock.Mock):
    """Mount a .dmg in a directory."""
    mounter = cmake_installer.DmgMounter('foo.dmg', '/tmp/bar')
    mounter.install()
    mounter.uninstall()

    mock_run.assert_has_calls([
        unittest.mock.call(
            'yes | hdiutil attach -readonly -mountpoint /tmp/bar '
            'foo.dmg &>/dev/null'),
        unittest.mock.call(
            'diskutil unmount force /tmp/bar')])

  @unittest.mock.patch('os.chmod')
  @unittest.mock.patch('shell.run_command')
  def test_install_sh(self, mock_run: unittest.mock.Mock,
                      mock_chmod: unittest.mock.Mock,):
    """Execution a shell script from a relative path to install a package."""
    with tempfile.TemporaryDirectory() as temp_dir:
      for installer_filename, expected_filename in (
          ('install.sh', os.path.join(os.curdir, 'install.sh')),
          ('/some/where/install.sh', '/some/where/install.sh')):
        mock_chmod.reset_mock()
        mock_run.reset_mock()

        installer = cmake_installer.ShellScriptInstaller(installer_filename,
                                                         temp_dir)
        installer.install()
        create_test_files(temp_dir)
        installer.uninstall()
        self.assertCountEqual(os.listdir(temp_dir), [])

        mock_chmod.assert_called_once_with(installer_filename, stat.S_IRWXU)
        mock_run.assert_called_once_with(
            f'{expected_filename} --skip-license --prefix={temp_dir}')

  @unittest.mock.patch('zipfile.ZipExtFile')
  @unittest.mock.patch('zipfile.ZipFile')
  def test_unzip(self, mock_zipfile: unittest.mock.Mock,
                 mock_zipextfile: unittest.mock.Mock,):
    """Unzip an archive to a directory."""
    mock_zipfile.return_value.__enter__.return_value = mock_zipextfile

    with tempfile.TemporaryDirectory() as temp_dir:
      installer = cmake_installer.ZipInstaller('foo.zip', temp_dir)
      installer.install()
      create_test_files(temp_dir)
      installer.uninstall()
      self.assertCountEqual(os.listdir(temp_dir), [])

      mock_zipfile.assert_called_once_with('foo.zip')
      mock_zipextfile.extractall.assert_called_once_with(temp_dir)

  def test_find_installer_class(self):
    """Find installer classes."""
    self.assertEqual(cmake_installer.find_installer_class('foo.dmg'),
                     cmake_installer.DmgMounter)
    self.assertEqual(cmake_installer.find_installer_class('foo.sh'),
                     cmake_installer.ShellScriptInstaller)
    self.assertEqual(cmake_installer.find_installer_class('foo.zip'),
                     cmake_installer.ZipInstaller)

  def test_find_installer_class_unsupported(self):
    """Ensure a failure if an unsupported installer filename is provided."""
    with self.assertRaises(NotImplementedError):
      cmake_installer.find_installer_class('foo.rar')


class CMakeInstallerTest(unittest.TestCase):
  """Test downloading and installing CMake."""

  def test_construct_from_supported_type(self):
    """Construct an installer for a supported type."""
    url = 'https://test.org/cmake-1.2.3.zip'
    installer = cmake_installer.CMakeInstaller(url)
    self.assertEqual(installer.url, url)

  def test_construct_from_local_install(self):
    """Construct an installer from a local installation."""
    url = '/usr/local/bin/cmake'
    installer = cmake_installer.CMakeInstaller(url)
    self.assertEqual(installer.url, url)

  def test_construct_unsupported_type(self):
    """Construct an installer with an unsupported type."""
    with self.assertRaises(RuntimeError):
      cmake_installer.CMakeInstaller('https://test.org/cmake-1.2.3.rar')

  def test_download(self):
    """Download an installer."""
    mock_urlopen = unittest.mock.mock_open(read_data=b'some test data')
    with unittest.mock.patch('urllib.request.urlopen', mock_urlopen):
      installer = cmake_installer.CMakeInstaller(
          'https://test.org/cmake-1.2.3.zip')
      installer_filename = installer._download()

      mock_urlopen.assert_called_once_with('https://test.org/cmake-1.2.3.zip')
      self.assertTrue(os.path.exists(installer_filename))
      self.assertEqual(os.path.basename(installer_filename), 'cmake-1.2.3.zip')
      with open(installer_filename, 'rb') as installer_file:
        self.assertEqual(installer_file.read(), b'some test data')

  def test_get_binary_dir(self):
    """Get the binary directory for a CMake installation."""
    install_dir = '/foo/bar'
    for filename, expected in (
        ('cmake-1.2.3.dmg', os.path.join(install_dir, 'CMake.app', 'Contents',
                                         'bin')),
        ('cmake-1.2.3.sh', os.path.join(install_dir, 'bin')),
        ('cmake-1.2.3.zip', os.path.join(install_dir, 'cmake-1.2.3', 'bin'))):
      installer = cmake_installer.CMakeInstaller(filename)
      self.assertEqual(installer._get_binary_dir(install_dir), expected)

  @unittest.mock.patch('cmake_installer.DmgMounter')
  @unittest.mock.patch('cmake_installer.CMakeInstaller._get_binary_dir',
                       return_value='/tmp/somewhere/bin')
  @unittest.mock.patch('cmake_installer.CMakeInstaller._download',
                       return_value='/tmp/cmake-1.2.3.dmg')
  def test_install(self, mock_download: unittest.mock.Mock,
                   mock_get_binary_dir: unittest.mock.Mock,
                   mock_installer: unittest.mock.Mock):
    """Download and install."""
    install_dir = ''
    with cmake_installer.CMakeInstaller(
        'https://test.org/cmake-1.2.3.dmg') as installer:
      install_dir = (installer._install_dir.name
                     if installer._install_dir else '')
      self.assertTrue(os.path.exists(install_dir))
      mock_download.assert_called_once()
      mock_installer.assert_called_once_with('/tmp/cmake-1.2.3.dmg',
                                             install_dir)
      mock_installer.return_value.install.assert_called_once()
      mock_get_binary_dir.assert_called_once_with(install_dir)
      self.assertEqual(installer.binary_dir, '/tmp/somewhere/bin')
    mock_installer.return_value.uninstall.assert_called_once()
    self.assertFalse(os.path.exists(install_dir))

  def test_install_using_local_installation(self):
    """Use a local installation."""
    for filename, binary_dir in (
        ('/Program Files/CMake/bin/cmake.exe', '/Program Files/CMake/bin'),
        ('/usr/local/bin/cmake', '/usr/local/bin')):
      with cmake_installer.CMakeInstaller(filename) as installer:
        self.assertEqual(installer.binary_dir, binary_dir)

if __name__ == '__main__':
  unittest.main()
