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
"""Tests for the nasm installer script."""

import os
import sys
import unittest

from unittest import mock

# pylint: disable=g-import-not-at-top
# pylint: disable=W0403
sys.path.append(os.path.dirname(__file__))
import nasm_installer
# pylint: enable=g-import-not-at-top
# pylint: enable=W0403

NASM_VERSION = '2.15.05'
NASM_ZIP_NAME = 'nasm.zip'

NASM_URL = ('https://www.nasm.us/pub/nasm/releasebuilds/'
            f'{NASM_VERSION}/win64/nasm-{NASM_VERSION}-win64.zip')


class NasmInstallerTest(unittest.TestCase):
  """Test build cmake methods."""

  def setUp(self):
    super().setUp()
    self.nasm_installer = nasm_installer.NasmInstaller(NASM_URL)

  @unittest.mock.patch('os.makedirs')
  def test_download(self, mock_makedirs: unittest.mock.Mock):
    """Download an installer."""
    mock_urlopen = unittest.mock.mock_open(read_data=b'some test data')
    mock_open = unittest.mock.mock_open(read_data=b'some test data')

    with unittest.mock.patch('builtins.open', mock_open):
      with unittest.mock.patch('urllib.request.urlopen', mock_urlopen):
        installer_filename = self.nasm_installer._download()
        # Check creation of download folder.
        mock_makedirs.assert_called_once_with(
            self.nasm_installer.installer_path, exist_ok=True)
        # Open downloaded file.
        mock_open.assert_called_once_with(
            os.path.join(self.nasm_installer.installer_path, NASM_ZIP_NAME),
            'wb')
        # Download from URL.
        mock_urlopen.assert_called_once_with(
            'https://www.nasm.us/pub/nasm/releasebuilds/'
            f'{NASM_VERSION}/win64/nasm-{NASM_VERSION}-win64.zip')
        # Check contents.
        with open(installer_filename, 'rb') as installer_file:
          self.assertEqual(installer_file.read(), b'some test data')

  @unittest.mock.patch('zipfile.ZipExtFile')
  @unittest.mock.patch('zipfile.ZipFile')
  def test_unzip(self, mock_zipfile: unittest.mock.Mock,
                 mock_zipextfile: unittest.mock.Mock):
    """Unzip an archive to a directory."""
    path_list = ['nasm-2.15.05', 'testing', 'path', 'foo.txt']
    testing_zip_path = os.path.join(*path_list)
    # Set mocks.
    return_value_mock = mock.MagicMock()
    return_value_mock.filename = testing_zip_path
    mock_zipextfile.infolist.return_value = [return_value_mock]
    input_file_mock = unittest.mock.mock_open(read_data=b'some test data')
    mock_zipextfile.open = input_file_mock
    mock_zipfile.return_value.__enter__.return_value = mock_zipextfile
    mock_open_write = unittest.mock.mock_open(read_data=b'some other test data')
    return_open_mock = mock.MagicMock()
    mock_open_write.return_value.__enter__.return_value = return_open_mock

    with unittest.mock.patch('builtins.open', mock_open_write):
      self.nasm_installer._unzip(testing_zip_path)
      mock_zipfile.assert_called_once_with(testing_zip_path)
      # Open output file.
      output_file_path = os.path.join(self.nasm_installer.installer_path,
                                      *path_list[1:])
      mock_open_write.assert_called_once_with(output_file_path, 'wb')
      # Write output file.
      return_open_mock.write.assert_called_once_with(b'some test data')

  @unittest.mock.patch('subprocess.run')
  def test_check_nasm(self, mock_run):
    """Test for checking nasm was installed correctly."""
    self.nasm_installer._check_nasm()

    mock_run.assert_called_once_with(args='nasm -h', check=True, shell=True)


if __name__ == '__main__':
  unittest.main()
