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
"""Tests for logging module."""

from unittest import mock

from absl import logging
from absl.testing import absltest

import falken_logging


class LoggingTest(absltest.TestCase):
  """Test for falken_logging."""

  def test_log_items_to_string(self):
    """Test conversion of valid items to a string."""
    self.assertEqual(
        falken_logging._log_items_to_string({
            'project_id': 'magic',
            'brain_id': 'pinky',
            'brain_spec': 'special',
            'session_id': 'starting',
            'episode_id': '1234',
            'episode_chunk_id': '5678',
            'assignment_id': '9012',
            'subtask_id': '0101',
            'model_id': '1010',
            'model_path': 'foo/bar/1010.pb',
            'checkpoint_directory_path': 'checkpoints/for/pinky',
            'summary_directory_path': 'summaries/for/pinky',
            'policy_path': 'policies/for/pinky',
            'database_name': 'datastore',
            'key': 'efef',
            'timestamp': '4432121',
            'eval_list': '5,6,7,8',
        }),
        ' project_id: magic\n'
        ' brain_id: pinky\n'
        ' brain_spec: special\n'
        ' session_id: starting\n'
        ' episode_id: 1234\n'
        ' episode_chunk_id: 5678\n'
        ' assignment_id: 9012\n'
        ' subtask_id: 0101\n'
        ' model_id: 1010\n'
        ' model_path: foo/bar/1010.pb\n'
        ' checkpoint_directory_path: checkpoints/for/pinky\n'
        ' summary_directory_path: summaries/for/pinky\n'
        ' policy_path: policies/for/pinky\n'
        ' database_name: datastore\n'
        ' key: efef\n'
        ' timestamp: 4432121\n'
        ' eval_list: 5,6,7,8')

  @mock.patch.object(logging, 'error')
  def test_log_invalid_items_to_string(self, mock_log_error):
    """Test conversion of invalid items to a string."""
    falken_logging._log_items_to_string({'unknown': 'foo'})
    mock_log_error.assert_called_with(
        'Tried to log a message using an invalid key %s with value %s.',
        'unknown', 'foo')

  @mock.patch.object(logging, 'error')
  def test_error(self, mock_log_error):
    """Test error logging."""
    falken_logging.error('test', project_id='foo', brain_id='bar')
    mock_log_error.assert_called_with(
        'test\n'
        ' project_id: foo\n'
        ' brain_id: bar')

  @mock.patch.object(logging, 'warn')
  def test_warn(self, mock_log_warn):
    """Test warning logging."""
    falken_logging.warn('hello', brain_id='pinky', session_id='dance')
    mock_log_warn.assert_called_with(
        'hello\n'
        ' brain_id: pinky\n'
        ' session_id: dance')

  @mock.patch.object(logging, 'info')
  def test_info(self, mock_log_info):
    """Test info logging."""
    falken_logging.info('narf', brain_id='pinky', session_id='dance',
                        episode_id='1234')
    mock_log_info.assert_called_with(
        'narf\n'
        ' brain_id: pinky\n'
        ' session_id: dance\n'
        ' episode_id: 1234')

if __name__ == '__main__':
  absltest.main()
