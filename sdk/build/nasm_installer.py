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
"""Downloads and installs nasm in a temporary directory."""

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile

# pylint: disable=g-import-not-at-top
# pylint: disable=W0403
sys.path.append(os.path.dirname(__file__))
import shell
# pylint: enable=g-import-not-at-top
# pylint: enable=W0403

NASM_ZIP_NAME = 'nasm.zip'


class NasmInstaller:
  """Installs nasm into a temporary directory."""

  def __init__(self, installer_url: str, installer_dir: str = None):
    """Initialize the installer instance.

    Args:
      installer_url: URL to the nasm installer.
      installer_dir: Optional path to copy nasm.
    """
    self._installer_url = installer_url
    if not installer_dir:
      self._installer_dir = tempfile.TemporaryDirectory().name
    else:
      self._installer_dir = installer_dir

    # Add nasm installation directory to path.
    os.environ['PATH'] = (self._installer_dir + os.path.pathsep +
                          os.environ['PATH'])

  @property
  def installer_path(self):
    """Get the path where nasm is going to be installed."""
    return self._installer_dir

  def install(self):
    """Install nasm to project.

    Returns:
      True when installed, false otherwise.

    Raises:
      urllib.error.URLError: If an error occurs while downloading the
        installer.
      zipfile.BadZipFile: if unzipping fails.
      subprocess.CalledProcessError: If failed to set path.
    """
    # Download installer.
    installer_filename = self._download()

    if installer_filename:
      # Unzip installer.
      self._unzip(installer_filename)
      # Add installer to path.
      self._check_nasm()
      return True
    return False

  def _download(self) -> str:
    """Download the installer and places into temporary folder.

    Returns:
      Path to the downloaded installer.

    Raises:
      urllib.error.URLError: If an error occurs while downloading the
        installer.
    """
    if not self._installer_url:
      return ''

    # Create installation directory if doesn't exist.
    os.makedirs(self._installer_dir, exist_ok=True)
    installer_filename = os.path.join(self._installer_dir, NASM_ZIP_NAME)
    with open(installer_filename, 'wb') as installer_file:
      logging.info('Copying %s --> %s', self._installer_url, installer_filename)
      with urllib.request.urlopen(self._installer_url) as urlfile:
        shutil.copyfileobj(urlfile, installer_file)
    return installer_filename

  def _unzip(self, zip_path: str) -> bool:
    """Unzips nasm package.

    Args:
      zip_path: Path to the zip file.

    Raises:
      zipfile.BadZipFile: if unzipping fails.

    """
    try:
      with zipfile.ZipFile(zip_path) as handle:
        for item_info in handle.infolist():
          # Remove first folder, so nasm.exe can be found when setting PATH.
          target_filename = os.path.join(
              self._installer_dir,
              os.path.join(*(
                  os.path.normpath(item_info.filename).split(os.path.sep)[1:])))
          # Open the file inside zip and save it on the desired location.
          with handle.open(item_info.filename, 'r') as input_file:
            os.makedirs(os.path.dirname(target_filename), exist_ok=True)
            with open(target_filename, 'wb') as output_file:
              output_file.write(input_file.read())
    except (zipfile.BadZipFile) as error:
      logging.exception('Failed to unzip %s: %s', zip_path, error)
      raise

  def _check_nasm(self) -> str:
    """Check that nasm runs on cmd.

    Raises:
      subprocess.CalledProcessError: If failed to run nasm.
    """
    try:
      shell.run_command('nasm -h')
    except subprocess.CalledProcessError as error:
      logging.exception('Failed to add nasm to path: %s', error)
      raise
