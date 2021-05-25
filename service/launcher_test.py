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
import tempfile
from unittest import mock

from absl.testing import absltest
import common.generate_protos  # pylint: disable=unused-import
import launcher


class LauncherTest(absltest.TestCase):
  """Tests the launcher script."""

  def setUp(self):
    super(LauncherTest, self).setUp()
    self._hyperparameters = launcher.FLAGS.hyperparameters
    self.temp_dir = tempfile.TemporaryDirectory()
    launcher.FLAGS.ssl_dir = os.path.join(self.temp_dir.name, 'ssl_dir')
    os.makedirs(launcher.FLAGS.ssl_dir)
    launcher.FLAGS.root_dir = os.path.join(self.temp_dir.name, 'root_dir')
    os.makedirs(launcher.FLAGS.root_dir)

  def tearDown(self):
    """Tear down the testing environment."""
    self.temp_dir.cleanup()
    self.temp_dir = None
    launcher.FLAGS.hyperparameters = self._hyperparameters
    super(LauncherTest, self).tearDown()

  @mock.patch.object(subprocess, 'Popen', autospec=True)
  def test_run_api_test(self, popen):
    """Call the run_api() method and verify the correct calls."""
    launcher.FLAGS.hyperparameters = ['{"foo": 1}', '{"bar": 1000}']
    launcher.run_api('mock_path')
    popen.assert_called_once_with(
        [sys.executable, '-m', 'api.falken_service',
         '--root_dir', launcher.FLAGS.root_dir, '--port', '50051',
         '--ssl_dir', launcher.FLAGS.ssl_dir,
         '--verbosity', '0', '--alsologtostderr',
         '--hyperparameters', '{"foo": 1}',
         '--hyperparameters', '{"bar": 1000}'],
        env=os.environ, cwd='mock_path')

  @mock.patch.object(subprocess, 'run', autospec=True)
  def test_check_ssl(self, run):
    fake_key_file = os.path.join(launcher.FLAGS.ssl_dir, 'key.pem')
    fake_cert_file = os.path.join(launcher.FLAGS.ssl_dir, 'cert.pem')
    def _generate_fake_files(*unused_args, **unused_kwargs):
      with open(fake_key_file, 'w') as f:
        f.write('fake key')
      with open(fake_cert_file, 'w') as f:
        f.write('fake cert')
    run.side_effect = _generate_fake_files
    launcher.check_ssl()
    run.assert_called_once_with(
        ['openssl', 'req', '-x509', '-newkey', 'rsa:4096', '-keyout',
         fake_key_file, '-out', fake_cert_file, '-days', '365', '-nodes',
         '-subj', '/CN=localhost'], check=True)

  @mock.patch.object(subprocess, 'Popen', autospec=True)
  def test_run_learner_test(self, popen):
    launcher.run_learner('mock_path')
    popen.assert_called_once_with(
        [sys.executable, '-m', 'learner.learner_service',
         '--root_dir', launcher.FLAGS.root_dir, '--verbosity', '0',
         '--alsologtostderr'],
        env=os.environ, cwd='mock_path')


if __name__ == '__main__':
  absltest.main()
