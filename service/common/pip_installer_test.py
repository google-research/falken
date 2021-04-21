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
import pip_installer


class PipInstallerTest(absltest.TestCase):
  """Test generate_protos module."""

  @mock.patch.object(subprocess, 'check_call', autospec=True)
  def test_install_dependencies(self, check_call):
    """Import the install_dependencies module and verify install."""
    pip_installer.install_dependencies()
    expected_call_args_list = [
        mock.call([sys.executable, '-m', 'pip', '-q', 'install', module])
        for module in pip_installer._REQUIRED_PYTHON_MODULES
    ]
    check_call.assert_has_calls(expected_call_args_list)


if __name__ == '__main__':
  absltest.main()
