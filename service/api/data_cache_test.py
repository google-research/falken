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
"""Tests for data_cache."""

from unittest import mock

from absl.testing import absltest
from api import data_cache


class DataCacheTest(absltest.TestCase):

  def test_get_brain(self):
    mock_ds = mock.Mock()
    mock_ds.read_brain.return_value = mock.Mock()
    # Call twice.
    self.assertEqual(
        data_cache.get_brain(mock_ds, 'test_project_id', 'test_brain_id'),
        mock_ds.read_brain.return_value)
    self.assertEqual(
        data_cache.get_brain(mock_ds, 'test_project_id', 'test_brain_id'),
        mock_ds.read_brain.return_value)
    # Read brain only called once.
    mock_ds.read_brain.assert_called_once_with(
        'test_project_id', 'test_brain_id')

  @mock.patch.object(data_cache, 'get_brain')
  def test_get_brain_spec(self, get_brain):
    get_brain.return_value = mock.Mock()
    get_brain.return_value.brain_spec = mock.Mock()
    mock_ds = mock.Mock()

    self.assertEqual(
        data_cache.get_brain_spec(mock_ds, 'test_project_id', 'test_brain_id'),
        get_brain.return_value.brain_spec)
    get_brain.assert_called_once_with(
        mock_ds, 'test_project_id', 'test_brain_id')

if __name__ == '__main__':
  absltest.main()
