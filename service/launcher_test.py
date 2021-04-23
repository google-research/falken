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
"""Tests for falken.service.launcher."""

import os
import subprocess
import sys
from unittest import mock

from absl.testing import absltest
import common.generate_protos
import launcher


class LauncherTest(absltest.TestCase):
  """Tests the launcher script."""

  def tearDown(self):
    """Tear down the testing environment."""
    super(LauncherTest, self).tearDown()
    common.generate_protos.clean_up()

  @mock.patch.object(subprocess, 'Popen', autospec=True)
  def test_run_api_test(self, popen):
    """Call the run_api() method and verify the correct calls."""
    launcher.run_api('mock_path')
    popen.assert_called_once_with(
        [sys.executable, '-m', 'api.falken_service', '--port', '[::]:50051',
         '--ssl_dir', None], env=os.environ, cwd='mock_path')


if __name__ == '__main__':
  absltest.main()
