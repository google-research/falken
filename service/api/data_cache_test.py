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

import common.generate_protos  # pylint: disable=unused-import
import data_store_pb2


class DataCacheTest(absltest.TestCase):

  def test_get_brain(self):
    mock_ds = mock.Mock()
    mock_ds.read_by_proto_ids.return_value = mock.Mock()
    # Call twice.
    self.assertEqual(
        data_cache.get_brain(mock_ds, 'test_project_id', 'test_brain_id'),
        mock_ds.read_by_proto_ids.return_value)
    self.assertEqual(
        data_cache.get_brain(mock_ds, 'test_project_id', 'test_brain_id'),
        mock_ds.read_by_proto_ids.return_value)
    # Datastore read only called once.
    mock_ds.read_by_proto_ids.assert_called_once_with(
        project_id='test_project_id', brain_id='test_brain_id')

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

  def test_get_session_type(self):
    mock_ds = mock.Mock()
    mock_ds.read_by_proto_ids.return_value = mock.Mock()
    # Call twice.
    self.assertEqual(
        data_cache.get_session_type(mock_ds, 'test_project_id', 'test_brain_id',
                                    'test_session_id'),
        mock_ds.read_by_proto_ids.return_value.session_type)
    self.assertEqual(
        data_cache.get_session_type(mock_ds, 'test_project_id', 'test_brain_id',
                                    'test_session_id'),
        mock_ds.read_by_proto_ids.return_value.session_type)
    # Datastore read only called once.
    mock_ds.read_by_proto_ids.assert_called_once_with(
        project_id='test_project_id', brain_id='test_brain_id',
        session_id='test_session_id')

  def test_get_starting_snapshot(self):
    mock_ds = mock.Mock()
    mock_session = data_store_pb2.Session(
        session_id='s0', starting_snapshots=['ss0'])
    mock_snapshot = mock.Mock()
    mock_ds.read_by_proto_ids.side_effect = [mock_session, mock_snapshot]
    # Call twice.
    self.assertEqual(
        data_cache.get_starting_snapshot(
            mock_ds, 'test_project_id', 'test_brain_id', 's0'),
        mock_snapshot)
    self.assertEqual(
        data_cache.get_starting_snapshot(
            mock_ds, 'test_project_id', 'test_brain_id', 's0'),
        mock_snapshot)
    # Datastore read only called once.
    mock_ds.read_by_proto_ids.assert_has_calls([
        mock.call(
            project_id='test_project_id',
            brain_id='test_brain_id', session_id='s0'),
        mock.call(
            project_id='test_project_id', brain_id='test_brain_id',
            session_id='s0', snapshot_id='ss0')])

  def test_get_starting_snapshot_wrong_length(self):
    mock_ds = mock.Mock()
    mock_session = data_store_pb2.Session(
        session_id='s0', starting_snapshots=[])
    mock_snapshot = mock.Mock()
    mock_ds.read_by_proto_ids.side_effect = [mock_session, mock_snapshot]
    with self.assertRaisesWithLiteralMatch(
        ValueError, 'Require exactly 1 starting snapshot, got 0 for session '
        's0.'):
      data_cache.get_starting_snapshot(
          mock_ds, 'test_project_id', 'test_brain_id', 's0')
    mock_ds.read_by_proto_ids.assert_called_once_with(
        project_id='test_project_id', brain_id='test_brain_id', session_id='s0')


if __name__ == '__main__':
  absltest.main()
