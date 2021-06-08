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

"""Tests for generate_sdk_configuration."""

import copy
import os
import tempfile
from unittest import mock

from absl.testing import absltest

from tools import generate_sdk_configuration


class GenerateSdkConfigurationTest(absltest.TestCase):

  def setUp(self):
    """Copy the base local configuration for test cases."""
    super().setUp()
    self.local_config = copy.deepcopy(
        generate_sdk_configuration._LOCAL_CONNECTION_CONFIG)

  def test_read_file_to_lines(self):
    """Read lines from a file stripping trailing whitespace."""
    with tempfile.TemporaryDirectory() as temporary_directory:
      filename = os.path.join(temporary_directory, 'test.txt')
      lines = ['bish', 'bosh', 'bash', 'foo']
      with open(filename, 'wt') as test_file:
        test_file.writelines([l + '\n' for l in lines])
      self.assertEqual(
          lines, generate_sdk_configuration.read_file_to_lines(filename))

  def test_generate_client_configuration_only_cert(self):
    """Generate a client configuration dictionary with just a cert."""
    self.local_config['service']['connection']['ssl_certificate'] = [
        'foo', 'bar']
    self.assertEqual(
        generate_sdk_configuration.generate_configuration(['foo', 'bar']),
        self.local_config)

  def test_generate_client_configuration_only_project_id(self):
    """Generate a client configuration dictionary with a project ID."""
    self.local_config['project_id'] = 'cool'
    self.assertEqual(
        generate_sdk_configuration.generate_configuration(
            [], project_id='cool'),
        self.local_config)

  def test_generate_client_configuration_only_api_key(self):
    """Generate a client configuration dictionary with an API key."""
    self.local_config['api_key'] = 'beans'
    self.assertEqual(
        generate_sdk_configuration.generate_configuration(
            [], api_key='beans'),
        self.local_config)

  @mock.patch.object(generate_sdk_configuration, 'read_file_to_lines')
  def test_main(self, read_file_to_lines_mock):
    """Test the configuration generation script."""
    original_project_id = generate_sdk_configuration.FLAGS.project_id
    original_api_key = generate_sdk_configuration.FLAGS.api_key
    try:
      generate_sdk_configuration.FLAGS.project_id = 'cool'
      generate_sdk_configuration.FLAGS.api_key = 'beans'
      # Mock cert.
      read_file_to_lines_mock.return_value = ['foo', 'bar', 'baz']
      open_json_file = mock.mock_open()
      with mock.patch.object(generate_sdk_configuration, 'open', open_json_file,
                             create=True):
        generate_sdk_configuration.main([])

      open_json_file.assert_called_once_with(
          generate_sdk_configuration.FLAGS.config_json, 'wt')
      json_file_handle = open_json_file()
      json_file_handle.write.assert_called_once_with(
          '{\n'
          '  "api_key": "beans",\n'
          '  "project_id": "cool",\n'
          '  "service": {\n'
          '    "connection": {\n'
          '      "address": "[::1]:50051",\n'
          '      "ssl_certificate": [\n'
          '        "foo",\n'
          '        "bar",\n'
          '        "baz"\n'
          '      ]\n'
          '    },\n'
          '    "environment": "local"\n'
          '  }\n'
          '}')

    finally:
      generate_sdk_configuration.FLAGS.project_id = original_project_id
      generate_sdk_configuration.FLAGS.api_key = original_api_key


if __name__ == '__main__':
  absltest.main()
