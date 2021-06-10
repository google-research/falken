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
"""Downloads and installs nasm in a temporary directory."""

import logging
import os
import signal
import subprocess
import sys
import shell

# pylint: disable=g-import-not-at-top
# pylint: disable=W0403
sys.path.append(os.path.dirname(__file__))
# pylint: enable=g-import-not-at-top
# pylint: enable=W0403

DEFAULT_SERVICE_WAIT_TIME = 60


class ServiceRunner:
  """Starts the service."""

  def __init__(self,
               service_path: str,
               python_executable: str = sys.executable,
               service_wait_time: int = DEFAULT_SERVICE_WAIT_TIME):
    """Initialize the service runner instance.

    Args:
      python_executable: Optional path to copy nasm.
      service_path: Location of service folder
      service_wait_time: Time to wait for connection.
    """
    self._service_base_path = service_path
    self._python_executable = python_executable
    self._service_subprocess = None
    self._launch_script_path = os.path.join(self._service_base_path,
                                            'launcher.py')
    self._service_wait_time = service_wait_time

  def start_service(self):
    """Run falken service.

    Returns:
      String with the location of json configuration file.
    """
    command = ' '.join([
        self._python_executable, self._launch_script_path,
        '--generate_sdk_config', '--project_ids', 'test'
    ])
    logging.info('Falken service started.')
    self._service_subprocess = shell.run_command_detached(
        command, stdout=subprocess.PIPE, universal_newlines=True)

    self.__wait_for_service(self._service_wait_time)

    # Return location of falken_config.json
    return os.path.join(self._service_base_path, 'tools', 'falken_config.json')

  def stop_service(self):
    """Stops falken service.

    Raises:
      RuntimeError if service stops before killing process.

    Returns:
      String with the location of json configuration file.
    """
    if self._service_subprocess is not None:
      if self._service_subprocess.poll() is None:
        raise RuntimeError('Falken service finished before stopping it.')
      os.killpg(os.getpgid(self._service_subprocess), signal.SIGINT)

  def __wait_for_service(self, timeout):
    """Blocks until service is ready to use.

    Args:
      timeout: time to wait for service.

    Returns:
      True if service started, False otherwise.
    """
    return True
