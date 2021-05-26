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

"""Tests for the shell command runner."""

import os
import sys
import unittest
import unittest.mock

# pylint: disable=g-import-not-at-top
# pylint: disable=W0403
sys.path.append(os.path.dirname(__file__))
import shell
# pylint: enable=g-import-not-at-top
# pylint: enable=W0403


class ShellTest(unittest.TestCase):
  """Test shell methods."""

  @unittest.mock.patch('subprocess.run')
  def test_run_command(self, mock_run):
    """Run a command."""
    shell.run_command('echo hello world')
    mock_run.assert_called_once_with(args='echo hello world', shell=True,
                                     check=True)

  @unittest.mock.patch('subprocess.run')
  def test_run_command_no_check(self, mock_run):
    """Run a command without throwing an exception on a failure."""
    shell.run_command('echo hello world', check=False)
    mock_run.assert_called_once_with(args='echo hello world', shell=True,
                                     check=False)

  @unittest.mock.patch('subprocess.run')
  def test_run_command_with_cwd(self, mock_run):
    """Run a command in a different directory."""
    shell.run_command('echo hello world', cwd='hawaii')
    mock_run.assert_called_once_with(args='echo hello world', shell=True,
                                     check=True, cwd='hawaii')

if __name__ == '__main__':
  unittest.main()
