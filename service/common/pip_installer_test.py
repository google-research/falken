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
import subprocess
import sys

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

  def test_module_installed(self):
    """Test checking for an installed module."""
    try:
      self._uninstall_test_module()
      self.assertFalse(pip_installer._module_installed(self._TEST_MODULE))
      subprocess.check_call([sys.executable, '-m', 'pip', 'install',
                             self._TEST_MODULE])
      pip_installer._clear_installed_modules_cache()
      self.assertTrue(pip_installer._module_installed(self._TEST_MODULE))
    finally:
      self._uninstall_test_module()

  def test_install_module(self):
    """Test module installation."""
    try:
      self._uninstall_test_module()
      pip_installer._install_module(self._TEST_MODULE, '')
      subprocess.check_call([sys.executable, '-m', 'pip', 'show',
                             self._TEST_MODULE])
    finally:
      self._uninstall_test_module()

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
        mock.call(m) for m, _ in pip_installer._REQUIRED_PYTHON_MODULES
    ])
    mock_install_module.assert_has_calls([
        mock.call(m, v) for m, v in pip_installer._REQUIRED_PYTHON_MODULES
    ])
    mock_clear_installed_modules_cache.assert_called()

  @mock.patch.object(pip_installer, '_clear_installed_modules_cache')
  @mock.patch.object(pip_installer, '_module_installed')
  @mock.patch.object(pip_installer, '_install_module')
  @mock.patch.object(pip_installer, '_REQUIRED_PYTHON_MODULES',
                     [('foo', ''), ('bar', '')])
  def test_install_missing_dependencies(self, mock_install_module,
                                        mock_module_installed,
                                        mock_clear_installed_modules_cache):
    """Only install modules that are missing."""
    mock_module_installed.side_effect = lambda module: module == 'bar'

    pip_installer.install_dependencies()
    mock_install_module.assert_called_with('foo', '')
    mock_clear_installed_modules_cache.assert_called()

  @mock.patch.object(pip_installer, '_clear_installed_modules_cache')
  @mock.patch.object(pip_installer, '_module_installed')
  @mock.patch.object(pip_installer, '_install_module')
  @mock.patch.object(pip_installer, '_REQUIRED_PYTHON_MODULES',
                     [('foo', ''), ('bar', '')])
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
