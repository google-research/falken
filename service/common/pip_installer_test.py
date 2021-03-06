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
# pylint: disable=g-bad-import-order, g-import-not-at-top
"""Tests that protos are generated after importing generate_protos module."""

import os
import platform
import subprocess
import sys
import tempfile

from unittest import mock
from absl.testing import absltest

# Set the environment variable to false so the test can call the method to
# install dependencies explicitly.
os.environ['FALKEN_AUTO_INSTALL_DEPENDENCIES'] = '0'
from common import pip_installer


class PipInstallerTest(absltest.TestCase):
  """Test generate_protos module."""

  # Module to install in the local Python site-library to test installation.
  _TEST_MODULE = 'pip-install-test'

  def tearDown(self):
    """Reset global state between tests."""
    super().tearDown()
    pip_installer._clear_installed_modules_cache()

  @classmethod
  def _uninstall_test_module(cls):
    """Uninstall the test Python module."""
    subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y',
                    cls._TEST_MODULE], check=False)

  def test_find_module_by_name(self):
    """Test checking for a module that can be imported by name."""
    self.assertFalse(pip_installer.find_module_by_name('budgemoor'))
    self.assertTrue(pip_installer.find_module_by_name('time'))
    tempdir = tempfile.TemporaryDirectory()
    try:
      with open(os.path.join(tempdir.name, 'budgemoor.py'), 'w') as f:
        f.write('print("Fore!")')
      self.assertTrue(pip_installer.find_module_by_name(
          'budgemoor', search_path=tempdir.name))
    finally:
      tempdir.cleanup()

  def test_module_installed_with_pip(self):
    """Test checking for an installed module with pip."""
    try:
      self._uninstall_test_module()
      self.assertFalse(pip_installer._module_installed(self._TEST_MODULE, ''))
      subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--user',
                             self._TEST_MODULE])
      pip_installer._clear_installed_modules_cache()
      self.assertTrue(pip_installer._module_installed(self._TEST_MODULE, ''))
    finally:
      self._uninstall_test_module()

  @mock.patch.object(pip_installer, 'find_module_by_name')
  def test_module_installed_with_import(self, mock_find_module_by_name):
    """Test checking for a module that can be imported."""
    mock_find_module_by_name.return_value = True
    self.assertTrue(pip_installer._module_installed('', 'time'))
    mock_find_module_by_name.assert_called_once_with('time')

  def test_install_module(self):
    """Test module installation."""
    try:
      self._uninstall_test_module()
      pip_installer._install_module(self._TEST_MODULE, '')
      subprocess.check_call([sys.executable, '-m', 'pip', 'show',
                             self._TEST_MODULE])
    finally:
      self._uninstall_test_module()

  @mock.patch.object(platform, 'architecture')
  @mock.patch.object(platform, 'system')
  def test_check_platform_constraints_none(self, mock_platform_system,
                                           mock_platform_architecture):
    """Test checking platform constraints with no constraints."""
    mock_platform_system.return_value = 'linux'
    mock_platform_architecture.return_value = ['x86_64']
    pip_installer._check_platform_constraints('tensorflow',
                                              {'windows': ['arm64']})

  @mock.patch.object(platform, 'architecture')
  @mock.patch.object(platform, 'system')
  def test_check_platform_constraints_supported(self, mock_platform_system,
                                                mock_platform_architecture):
    """Test checking platform constraints with an unsupported platform."""
    mock_platform_system.return_value = 'windows'
    mock_platform_architecture.return_value = ['64bit', 'WindowsPE']
    pip_installer._check_platform_constraints('tensorflow',
                                              {'windows': ['64bit']})

  @mock.patch.object(platform, 'architecture')
  @mock.patch.object(platform, 'system')
  def test_check_platform_constraints_unsupported(self, mock_platform_system,
                                                  mock_platform_architecture):
    """Test checking platform constraints with an unsupported platform."""
    mock_platform_system.return_value = 'windows'
    mock_platform_architecture.return_value = ['32bit', 'WindowsPE']
    with self.assertRaisesRegex(pip_installer.PlatformConstraintError,
                                r'.* tensorflow .* \[.64bit.\] on windows '
                                r'.* \[.32bit.*WindowsPE.\].*'):
      pip_installer._check_platform_constraints(
          'tensorflow', {'windows': ['64bit']})

  @mock.patch.object(pip_installer, '_clear_installed_modules_cache')
  @mock.patch.object(pip_installer, '_module_installed')
  @mock.patch.object(pip_installer, '_install_module')
  def test_install_dependencies(self, mock_install_module,
                                mock_module_installed,
                                mock_clear_installed_modules_cache):
    """Install all module dependencies."""
    mock_module_installed.return_value = False
    pip_installer.install_dependencies()

    mock_module_installed.assert_has_calls([
        mock.call(info.pip_module_name, info.import_module_name)
        for info in pip_installer._REQUIRED_PYTHON_MODULES
    ])
    mock_install_module.assert_has_calls([
        mock.call(info.pip_module_name, info.version_constraint)
        for info in pip_installer._REQUIRED_PYTHON_MODULES
    ])
    mock_clear_installed_modules_cache.assert_called()

  @mock.patch.object(pip_installer, '_clear_installed_modules_cache')
  @mock.patch.object(pip_installer, '_module_installed')
  @mock.patch.object(pip_installer, '_install_module')
  @mock.patch.object(pip_installer, '_REQUIRED_PYTHON_MODULES',
                     [pip_installer.ModuleInfo(pip_module_name='foo'),
                      pip_installer.ModuleInfo(pip_module_name='bar')])
  def test_install_missing_dependencies(self, mock_install_module,
                                        mock_module_installed,
                                        mock_clear_installed_modules_cache):
    """Only install modules that are missing."""
    mock_module_installed.side_effect = lambda module, _: module == 'bar'

    pip_installer.install_dependencies()
    mock_install_module.assert_called_with('foo', '')
    mock_clear_installed_modules_cache.assert_called()

  @mock.patch.object(pip_installer, '_clear_installed_modules_cache')
  @mock.patch.object(pip_installer, '_module_installed')
  @mock.patch.object(pip_installer, '_install_module')
  @mock.patch.object(pip_installer, '_REQUIRED_PYTHON_MODULES',
                     [pip_installer.ModuleInfo(pip_module_name='foo'),
                      pip_installer.ModuleInfo(pip_module_name='bar')])
  def test_install_no_dependencies(self, mock_install_module,
                                   mock_module_installed,
                                   mock_clear_installed_modules_cache):
    """Install no modules if they're all installed."""
    mock_module_installed.return_value = True

    pip_installer.install_dependencies()
    mock_install_module.assert_not_called()
    mock_clear_installed_modules_cache.assert_not_called()


if __name__ == '__main__':
  absltest.main()
