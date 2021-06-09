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
"""Run commands in the system shell."""

import logging
import subprocess
import typing


def run_command(command_line: str, **kwargs) -> subprocess.CompletedProcess:
  """Run a command in the shell and throw an exception if it fails.

  Args:
    command_line: Command line to execute.
    **kwargs: Additional arguments for subprocess.run().

  Returns:
    Result from the command.

  Raises:
    subprocess.CalledProcessError if the process fails.
  """
  # kwargs = {'check', 'True'}
  logging.info(command_line)
  if 'check' not in kwargs:
    kwargs['check'] = True
  parsed_commands = parse_arguments(command_line, **kwargs)
  # pylint: disable=subprocess-run-check
  return subprocess.run(**parsed_commands)


def run_command_detached(command_line: str,
                         **kwargs) -> subprocess.CompletedProcess:
  """Run a command in the shell, without waiting for the command to finish.

  Args:
    command_line: Command line to execute.
    **kwargs: Additional arguments for subprocess.run().

  Returns:
    Result from the command.

  Raises:
    subprocess.CalledProcessError if the process fails.
  """
  logging.info(command_line)
  parsed_commands = parse_arguments(command_line, **kwargs)
  # pylint: disable=subprocess-run-check
  return subprocess.Popen(**parsed_commands)


def parse_arguments(command_line: str, **kwargs):
  """Run a command in the shell, without waiting for the command to finish.

  Args:
    command_line: Command line to execute.
    **kwargs: Additional arguments for subprocess.run().

  Returns:
    Result from the command.

  Raises:
    subprocess.CalledProcessError if the process fails.
  """
  run_kwargs: typing.Dict[str, typing.Any] = {'shell': True}
  if kwargs:
    run_kwargs.update(kwargs)
  run_kwargs['args'] = command_line
  return run_kwargs
