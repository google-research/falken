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
"""Tests for api_keys."""

from unittest import mock

from absl.testing import absltest
from api import api_keys
from api import unique_id
from data_store import test_data_store

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import data_store_pb2


class ApiKeysTest(absltest.TestCase):

  def setUp(self):
    self.data_store = test_data_store.TestDataStore()
    super().setUp()

  def test_get_or_create_api_key_project_exists(self):
    """Test get_or_create_api_key if the requested project exists."""
    project = data_store_pb2.Project(project_id='p0', api_key='1234')
    self.data_store.write(project)
    api_key = api_keys.get_or_create_api_key(self.data_store, 'p0')
    self.assertEqual(api_key, '1234')

  @mock.patch.object(unique_id, 'generate_base64_id')
  def test_get_or_create_api_key_project_new(self, generate_id_mock):
    """Test get_or_create_api_key if the requested project does not exist."""
    generate_id_mock.return_value = '5678'
    api_key = api_keys.get_or_create_api_key(self.data_store, 'p0')
    self.assertEqual(api_key, '5678')


if __name__ == '__main__':
  absltest.main()
