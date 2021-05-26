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

"""Downloads and installs CMake in a temporary directory."""

import logging
import os
import shutil
import stat
import sys
import tempfile
import typing
import urllib.parse
import urllib.request
import zipfile

# pylint: disable=g-import-not-at-top
# pylint: disable=W0403
sys.path.append(os.path.dirname(__file__))
import shell
# pylint: enable=g-import-not-at-top
# pylint: enable=W0403


class Installer:
  """Interface to run an installer.

  Attributes:
    installer_filename: Path to the file to install.
    destination_dir: Directory to install the file.
  """

  def __init__(self, installer_filename: str, destination_dir: str):
    """Initialize the instance.

    Args:
      installer_filename: Path to the file to install.
      destination_dir: Directory to install the file.
    """
    self.installer_filename = installer_filename
    self.destination_dir = destination_dir

  def install(self):
    """Remove the contents of the destination directory."""
    raise NotImplementedError('Use a derived class instead.')

  def uninstall(self):
    """Uninstall from the destination directory."""
    if os.path.exists(self.destination_dir):
      for name in os.listdir(self.destination_dir):
        filename = os.path.join(self.destination_dir, name)
        if os.path.isdir(filename):
          shutil.rmtree(filename)
        else:
          os.unlink(filename)


class DmgMounter(Installer):
  """Mounts a .dmg file in a directory."""

  def install(self):
    """Mount the .dmg in the destination directory.

    Raises:
      subprocess.CalledProcessError: If there is an error mounting the .dmg.
    """
    # Some installers (like CMake's) pop up a license page that requires the
    # user to respond "yes", so we pipe the output of 'yes' to hdiutil to mount
    # the dmg. Also, hdiutil uses 'less' to display the license which blocks
    # installation so redirect stdout to disable interactivity.
    shell.run_command('yes | hdiutil attach -readonly '
                      f'-mountpoint {self.destination_dir} '
                      f'{self.installer_filename} &>/dev/null')

  def uninstall(self):
    """Umount the .dmg from the destination directory.

    Raises:
      subprocess.CalledProcessError: If there is an error unmounting the .dmg.
    """
    shell.run_command(f'diskutil unmount force {self.destination_dir}')


class ShellScriptInstaller(Installer):
  """Installs from a self extracting archive."""

  def install(self):
    """Install using a CMake generated shell script.

    Raises:
      subprocess.CalledProcessError: If there is an error mounting the .dmg.
    """
    os.chmod(self.installer_filename, stat.S_IRWXU)
    if os.path.isabs(self.installer_filename):
      sh_file_path = self.installer_filename
    else:
      sh_file_path = os.path.join(os.curdir, self.installer_filename)
    shell.run_command(f'{sh_file_path} --skip-license '
                      f'--prefix={self.destination_dir}')


class ZipInstaller(Installer):
  """Extracts a zip file."""

  def install(self):
    """Unzip an archive."""
    with zipfile.ZipFile(self.installer_filename) as handle:
      handle.extractall(self.destination_dir)


def find_installer_class(installer_filename: str) -> typing.Type[Installer]:
  """Find the installer class for the specified filename.

  Args:
    installer_filename: Path of the file to install.

  Returns:
    Installer class.

  Raises:
    NotImplementedError if an installer isn't available.
  """
  installers = {'.dmg': DmgMounter,
                '.sh': ShellScriptInstaller,
                '.zip': ZipInstaller}
  extension = os.path.splitext(installer_filename)[1]
  installer_class = installers.get(extension)
  if not installer_class:
    raise NotImplementedError(f'Installer for {installer_filename} '
                              'not available')
  return installer_class


class CMakeInstaller:
  """Installs CMake into a temporary directory.

  Attributes:
    binary_dir: Directory containing installed CMake binaries.
    _install_dir: Directory where CMake is installed.
    _installer_url: Location of the installer.
    _installer_basename: Basename of the installer.
    _installer_dir: Temporary directory where the CMake installer is
      copied before it's installed.
    _installer_extension: Extension of the installer filename used to determine
      the install operation.
    _installer_class: Class used to install.
    _installer: Installer instance.
  """

  # Directory of the CMake binary directory relative to the install location.
  _BINARY_DIR_BY_EXTENSION = {
      '.dmg': lambda _: os.path.join('CMake.app', 'Contents', 'bin'),
      '.sh': lambda _: 'bin',
      '.zip': lambda fname: os.path.join(os.path.splitext(fname)[0], 'bin'),
  }

  def __init__(self, installer_url: str):
    """Initialize the installer instance.

    Args:
      installer_url: URL to the installer script, archive or an existing
        cmake installation.

    Raises:
      RuntimeError: If the installer is not supported.
    """
    self._installer_url = installer_url
    self._installer_basename = os.path.basename(
        urllib.parse.unquote(urllib.parse.urlparse(installer_url).path))
    self._installer_extension = os.path.splitext(self._installer_basename)[1]
    if self._installer_extension.lower() in ('', '.exe'):
      self._installer_class = None
      self.binary_dir = os.path.normpath(os.path.join(
          installer_url, os.path.pardir))
    else:
      self._installer_class = find_installer_class(self._installer_basename)
      self.binary_dir = ''
    self._installer: typing.Optional[Installer] = None
    self._installer_dir: typing.Optional[tempfile.TemporaryDirectory] = None
    self._install_dir: typing.Optional[tempfile.TemporaryDirectory] = None

  @property
  def url(self):
    """Get the installer URL."""
    return self._installer_url

  def _download(self) -> str:
    """Download the installer.

    Returns:
      Path to the downloaded installer.

    Raises:
      urllib.error.URLError: If an error occurs while downloading the
        installer.
    """
    if self.binary_dir:
      return ''

    self._installer_dir = tempfile.TemporaryDirectory()
    installer_filename = os.path.join(self._installer_dir.name,
                                      self._installer_basename)
    with open(installer_filename, 'wb') as installer_file:
      logging.info('Copying %s --> %s', self._installer_url,
                   installer_filename)
      with urllib.request.urlopen(self._installer_url) as urlfile:
        shutil.copyfileobj(urlfile, installer_file)
    return installer_filename

  def _get_binary_dir(self, install_dir: str) -> str:
    """Get the Cmake binary directory under the specified install directory.

    Args:
      install_dir: Directory which contains a CMake installation.

    Returns:
      Cmake binary directory.
    """
    return os.path.join(
        install_dir,
        CMakeInstaller._BINARY_DIR_BY_EXTENSION[self._installer_extension](
            self._installer_basename))

  def __enter__(self) -> 'CMakeInstaller':
    """Download and install CMake.

    Returns:
      This instance.

    Raises:
      urllib.error.URLError: If an error occurs while downloading the
        installer.
      subprocess.CalledProcessError: If the installer fails.
    """
    installer_filename = self._download()

    if installer_filename and self._installer_class:
      self._install_dir = tempfile.TemporaryDirectory()
      logging.info('Installing %s --> %s', installer_filename,
                   self._install_dir.name)
      self._installer = self._installer_class(installer_filename,
                                              self._install_dir.name)
      self._installer.install()
      self.binary_dir = self._get_binary_dir(self._install_dir.name)
    return self

  def __exit__(self, unused_exc_type, unused_exc_value, unused_traceback):
    """Delete the CMake installation.

    Raises:
      subprocess.CalledProcessError: If uninstallation fails.
    """
    if self._installer:
      self._installer.uninstall()
      self._installer = None
      self.binary_dir = ''

    if self._install_dir:
      self._install_dir.cleanup()
      self._install_dir = None

    if self._installer_dir:
      self._installer_dir.cleanup()
      self._installer_dir = None
