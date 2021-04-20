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
"""Logging wrapper for Falken."""

import collections
import sys

from absl import flags
from absl import logging

FLAGS = flags.FLAGS


def _register_frame_to_skip():
  """Registers the frames to skip in stack while logging."""
  frame = sys._getframe()  # pylint: disable=protected-access
  caller_frame = frame.f_back if frame.f_back else frame
  caller_filename = caller_frame.f_globals['__file__']
  caller_func_name = caller_frame.f_code.co_name
  logging.get_absl_logger().register_frame_to_skip(
      caller_filename, caller_func_name)


_LOG_KWARGS = collections.OrderedDict((
    ('project_id', None),
    ('brain_id', None),
    ('brain_spec', None),
    ('session_id', None),
    ('episode_id', None),
    ('episode_chunk_id', None),
    ('assignment_id', None),
    ('subtask_id', None),
    ('model_id', None),
    ('model_path', None),
    ('checkpoint_directory_path', None),
    ('summary_directory_path', None),
    ('policy_path', None),
    ('database_name', None),
    ('key', None),
    ('timestamp', None),
    ('eval_list', None),
))


def _log_items_to_string(log_items):
  """Validate kwargs associated with a log message and convert to a string.

  Args:
    log_items: Dictionary of items to validate against _LOG_KWARGS and
      convert to a string of key / value pairs.

  Returns:
    Multi-line string representation of kwargs.
  """
  for key in log_items:
    if key not in _LOG_KWARGS:
      logging.error('Tried to log a message using an invalid key %s with value '
                    '%s.', key, log_items[key])
  lines = []
  for key in _LOG_KWARGS:
    value = log_items.get(key)
    if value:
      lines.append(f' {key}: {value}')
  return '\n'.join(lines)


def error(message: str, **kwargs):
  """Logs an error message."""
  _register_frame_to_skip()
  logging.error('\n'.join([message, _log_items_to_string(kwargs)]))


def warn(message: str, **kwargs):
  """Logs a warning message."""
  _register_frame_to_skip()
  logging.warn('\n'.join([message, _log_items_to_string(kwargs)]))


def info(message: str, **kwargs):
  """Logs an info message."""
  _register_frame_to_skip()
  logging.info('\n'.join([message, _log_items_to_string(kwargs)]))
