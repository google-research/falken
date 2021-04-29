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

"""Generates a SDK JSON configuration file to connect to a local service."""

import copy
import json
import os

from absl import app
from absl import flags

FLAGS = flags.FLAGS

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

flags.DEFINE_string(
    'cert', os.path.join(os.path.dirname(THIS_DIR), 'cert.pem'),
    'Path to a certificate file use to validate the service.')
flags.DEFINE_string('project_id', None, 'Falken project to use.')
flags.DEFINE_string('api_key', None,
                    'API key to authenticate the Falken project.')
flags.DEFINE_string(
    'config_json', os.path.join(THIS_DIR, 'falken_config.json'),
    'JSON configuration file to create for the client SDK to connect to the '
    'service.')


# Base configuration for a local connection.
_LOCAL_CONNECTION_CONFIG = {
    'service': {
        # Connect to localhost.
        'environment': 'local',
        'connection': {
            'address': '[::]:50051',
        },
    },
}


def read_file_to_lines(filename):
  """Read a file into a list of lines.

  Args:
    filename: File to read.

  Returns:
    List of lines read from the file with all trailing whitespace stripped.
  """
  with open(filename, 'rt') as fileobj:
    return [l.rstrip() for l in fileobj.readlines()]


def generate_configuration(cert_lines, project_id=None, api_key=None):
  """Generate a client SDK configuration.

  Args:
    cert_lines: List of strings that make up the certificate.
    project_id: ID of the project to use when connecting to the service.
    api_key: API key used to authenticate the project with the service.

  Returns:
    Dictionary in the form:
    {
      'project_id': project_id,
      'api_key': api_key,
      'service': {
        'environment': 'local',
        'connection': {
          'address': '[::]:50051',
          'ssl_certificate': cert_lines,
        },
      }
    }

    Where 'project_id', 'api_key' and 'ssl_certificate' are only populated if
    the arguments are not None or empty.
  """
  configuration = copy.deepcopy(_LOCAL_CONNECTION_CONFIG)
  if cert_lines:
    configuration['service']['connection']['ssl_certificate'] = cert_lines
  if project_id:
    configuration['project_id'] = project_id
  if api_key:
    configuration['api_key'] = api_key
  return configuration


def main(unused_argv):
  """Generate SDK configuration."""
  with open(FLAGS.config_json, 'wt') as config_json_file:
    config_json_file.write(
        json.dumps(generate_configuration(
            read_file_to_lines(FLAGS.cert),
            project_id=FLAGS.project_id,
            api_key=FLAGS.api_key), sort_keys=True, indent=2))


if __name__ == '__main__':
  app.run(main)
