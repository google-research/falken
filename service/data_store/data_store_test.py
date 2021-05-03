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

"""Tests for DataStore."""

import os.path
import time
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from data_store import data_store
from data_store import file_system

import common.generate_protos  # pylint: disable=g-bad-import-order,unused-import

import data_store_pb2


class DataStoreTest(parameterized.TestCase):

  def setUp(self):
    """Create a datastore object that uses a temporary directory."""
    super().setUp()
    self._fs = file_system.FakeFileSystem()
    self._data_store = data_store.DataStore(self._fs)

  def tearDown(self):
    """Clean up the temporary directory and datastore."""
    super().tearDown()
    self._data_store = None
    self._fs = None

  def test_read_write_project(self):
    self._data_store.write_project(data_store_pb2.Project(project_id='p1'))
    self.assertEqual('p1', self._data_store.read_project('p1').project_id)

  def test_read_write_brain(self):
    self._data_store.write_brain(
        data_store_pb2.Brain(project_id='p1', brain_id='b1'))
    self.assertEqual('b1', self._data_store.read_brain('p1', 'b1').brain_id)

  def test_read_write_snapshot(self):
    self._data_store.write_snapshot(data_store_pb2.Snapshot(
        project_id='p1', brain_id='b1', snapshot_id='s1'))
    self.assertEqual(
        's1', self._data_store.read_snapshot('p1', 'b1', 's1').snapshot_id)

  def test_read_write_session(self):
    self._data_store.write_session(data_store_pb2.Session(
        project_id='p1', brain_id='b1', session_id='s1'))
    self.assertEqual(
        's1', self._data_store.read_session('p1', 'b1', 's1').session_id)

  def test_read_write_episode_chunk(self):
    self._data_store.write_episode_chunk(data_store_pb2.EpisodeChunk(
        project_id='p1', brain_id='b1', session_id='s1', episode_id='e1',
        chunk_id=3))
    self.assertEqual(3, self._data_store.read_episode_chunk(
        'p1', 'b1', 's1', 'e1', 3).chunk_id)

  def test_read_write_online_evaluation(self):
    self._data_store.write_online_evaluation(
        data_store_pb2.OnlineEvaluation(
            project_id='p1', brain_id='b1', session_id='s1', episode_id='e1'))
    self.assertEqual(
        'e1',
        self._data_store.read_online_evaluation('p1', 'b1', 's1',
                                                'e1').episode_id)

  def test_read_write_assignment(self):
    self._data_store.write_assignment(
        data_store_pb2.Assignment(
            project_id='p1', brain_id='b1', session_id='s1',
            assignment_id='a1'))
    self.assertEqual(
        'a1',
        self._data_store.read_assignment('p1', 'b1', 's1', 'a1').assignment_id)

  def test_read_write_model(self):
    self._data_store.write_model(data_store_pb2.Model(
        project_id='p1', brain_id='b1', session_id='s1', model_id='m1'))
    self.assertEqual(
        'm1', self._data_store.read_model('p1', 'b1', 's1', 'm1').model_id)

  def test_read_write_serialized_model(self):
    self._data_store.write_serialized_model(data_store_pb2.SerializedModel(
        project_id='p1', brain_id='b1', session_id='s1', model_id='m1'))
    self.assertEqual('m1', self._data_store.read_serialized_model(
        'p1', 'b1', 's1', 'm1').model_id)

  def test_read_write_offline_evaluation(self):
    self._data_store.write_offline_evaluation(
        data_store_pb2.OfflineEvaluation(
            project_id='p1',
            brain_id='b1',
            session_id='s1',
            model_id='m1',
            evaluation_set_id=2))
    self.assertEqual(
        2,
        self._data_store.read_offline_evaluation('p1', 'b1', 's1', 'm1',
                                                 2).evaluation_set_id)

  @mock.patch.object(time, 'time', autospec=True)
  def test_read_write_proto(self, mock_time):
    """Test read, writing, updating a proto."""
    mock_time.return_value = 0.123
    self._data_store._write_proto(
        'a/b/c_*.pb', data_store_pb2.Project(project_id='p1'))

    self.assertEqual(['a/b/c_123000.pb'], self._fs.glob('a/b/c_*.pb'))

    data = self._data_store._read_proto('a/b/c_*.pb', data_store_pb2.Project)
    self.assertEqual('p1', data.project_id)
    self.assertEqual(123000, data.created_micros)

    # Verify updating the proto works, and doesn't update the timestamp.
    data.project_id = 'p2'
    mock_time.return_value = 0.456
    self._data_store._write_proto('a/b/c_*.pb', data)

    self.assertEqual(['a/b/c_123000.pb'], self._fs.glob('a/b/c_*.pb'))

    data = self._data_store._read_proto('a/b/c_*.pb', data_store_pb2.Project)
    self.assertEqual('p2', data.project_id)
    self.assertEqual(123000, data.created_micros)

    with self.assertRaisesWithLiteralMatch(
        ValueError,
        'There was an attempt to create a file from a new timestamp at '
        '\'a/b/c_*.pb\', but the following list of files with timestamps was '
        'found: [\'a/b/c_123000.pb\'].'):
      self._data_store._write_proto(
          'a/b/c_*.pb', data_store_pb2.Project(project_id='p3'))

    with self.assertRaisesWithLiteralMatch(
        data_store.NotFoundError,
        'Could not update file a/b/c_50.pb as it doesn\'t exist.'):
      self._data_store._write_proto(
          'a/b/c_*.pb', data_store_pb2.Project(created_micros=50))

  def test_get_most_recent_model(self):
    self._data_store._list_resources = mock.Mock()
    self._data_store._list_resources.return_value = (
        ['m1', 'm2', 'm3', 'm4'], None)
    self.assertEqual(
        'm4',
        self._data_store.get_most_recent_model('p1', 'b1', 's1'))
    self._data_store._list_resources.assert_called_with(
        self._data_store._get_resource_list_glob('model', ['p1', 'b1', 's1']),
        page_size=None)

  def test_get_most_recent_snapshot(self):
    self._data_store._list_resources = mock.Mock()
    self._data_store._list_resources.return_value = (
        ['s1', 's2', 's3', 's4'], None)
    self.assertEqual(
        's4',
        self._data_store.get_most_recent_snapshot('p1', 'b1'))
    self._data_store._list_resources.assert_called_with(
        self._data_store._get_resource_list_glob('snapshot', ['p1', 'b1']),
        page_size=None)

  def test_check_type(self):
    self._data_store._check_type(
        data_store_pb2.Session(), data_store_pb2.Session)

    with self.assertRaises(ValueError):
      self._data_store._check_type(
          data_store_pb2.Project(), data_store_pb2.Session)

  def test_decode_token(self):
    self.assertEqual((12, 'ab'), self._data_store._decode_token('12:ab'))
    self.assertEqual((-1, ''), self._data_store._decode_token(None))

  def test_encode_token(self):
    self.assertEqual('12:ab', self._data_store._encode_token(12, 'ab'))

  @mock.patch.object(time, 'time', autospec=True)
  def test_list_resources(self, mock_time):
    brains_pattern = os.path.join(
        self._data_store._get_project_glob('p1'), 'brains', '*',
        data_store._BRAIN_FILE_PATTERN)

    brain_ids = [f'b{i:02}' for i in range(20)]
    # Many repeated 5s.
    timestamps = [0, 1, 2, 3, 4, 5, 5, 5, 5, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,
                  15]
    for i in range(len(brain_ids)):
      mock_time.return_value = timestamps[i] / 1_000_000
      self._data_store.write_brain(
          data_store_pb2.Brain(project_id='p1', brain_id=brain_ids[i]))

    self.assertEqual(
        (['b00', 'b01', 'b02'], '3:b03'),
        self._data_store._list_resources(brains_pattern, 3))

    self.assertEqual(
        (['b03', 'b04', 'b05', 'b06', 'b07', 'b08', 'b09', 'b10', 'b11', 'b12'
         ], '9:b13'),
        self._data_store._list_resources(
            brains_pattern, 10, data_store.ListOptions('3:b03')))

    self.assertEqual(
        (['b03', 'b04', 'b05', 'b06'], '5:b07'),
        self._data_store._list_resources(
            brains_pattern, 4, data_store.ListOptions('3:b03')))

    self.assertEqual(
        (['b07', 'b08', 'b09', 'b10'], '7:b11'),
        self._data_store._list_resources(
            brains_pattern, 4, data_store.ListOptions('5:b07')))

    self.assertEqual(
        (brain_ids, None),
        self._data_store._list_resources(brains_pattern, 20))

    self.assertEqual(
        (brain_ids, None),
        self._data_store._list_resources(brains_pattern, 30))

    self.assertEqual(
        (brain_ids, None),
        self._data_store._list_resources(brains_pattern, None))

    self.assertEqual(
        (brain_ids[:-1], '15:b19'),
        self._data_store._list_resources(brains_pattern, 19))

    self.assertEqual(
        (['b19'], None),
        self._data_store._list_resources(
            brains_pattern, 10, data_store.ListOptions('15:b19')))

    self.assertEqual(
        ([], None),
        self._data_store._list_resources(
            brains_pattern, 10, data_store.ListOptions('700:bzzz')))

    self.assertEqual(
        ([], None),
        self._data_store._list_resources(
            brains_pattern, 0, data_store.ListOptions('2:b02')))

    self.assertEqual(
        (['b03', 'b04', 'b05', 'b06'], '5:b07'),
        self._data_store._list_resources(
            brains_pattern, 4, data_store.ListOptions(minimum_timestamp=3)))

    with self.assertRaisesWithLiteralMatch(
        ValueError,
        'At least one of page_token and from_timestamp should be None.'):
      data_store.ListOptions(page_token='5:b07', minimum_timestamp=10)

  def test_list_brains(self):
    self._data_store._list_resources = mock.Mock()
    self._data_store._list_resources.return_value = (['b1'], 'next_token')
    self.assertEqual(self._data_store._list_resources.return_value,
                     self._data_store.list_brains(
                         'p1', 2, data_store.ListOptions('start_token')))
    self._data_store._list_resources.assert_called_with(
        self._data_store._get_resource_list_glob('brain', ['p1']), 2,
        data_store.ListOptions('start_token'))

  def test_list_sessions(self):
    self._data_store._list_resources = mock.Mock()
    self._data_store._list_resources.return_value = (['s1'], 'next_token')
    self.assertEqual(
        self._data_store._list_resources.return_value,
        self._data_store.list_sessions(
            'p1', 'b1', 2, data_store.ListOptions('start_token')))
    self._data_store._list_resources.assert_called_with(
        self._data_store._get_resource_list_glob('session', ['p1', 'b1']), 2,
        data_store.ListOptions('start_token'))

  def test_list_episode_chunks(self):
    self._data_store._list_resources = mock.Mock()
    self._data_store._list_resources.return_value = ([1], 'next_token')
    self.assertEqual(
        self._data_store._list_resources.return_value,
        self._data_store.list_episode_chunks(
            'p1', 'b1', 's1', 'e1', 2, data_store.ListOptions('start_token')))
    self._data_store._list_resources.assert_called_with(
        self._data_store._get_resource_list_glob(
            'episode_chunk', ['p1', 'b1', 's1', 'e1']),
        2, data_store.ListOptions('start_token'))

  def test_list_online_evaluations(self):
    self._data_store._list_resources = mock.Mock()
    self._data_store._list_resources.return_value = (['e00'], 'next_token')
    self.assertEqual(
        self._data_store._list_resources.return_value,
        self._data_store.list_online_evaluations(
            'p1', 'b1', 's1', 2, data_store.ListOptions('start_token')))
    self._data_store._list_resources.assert_called_with(
        self._data_store._get_resource_list_glob(
            'online_evaluation', ['p1', 'b1', 's1']), 2,
        data_store.ListOptions('start_token'))

  def test_get_resource_id(self):
    self.assertEqual(
        self._data_store._get_resource_id(
            'something/something/4567/somefile.pb'),
        '4567')

  def test_get_timestamp(self):
    self.assertEqual(
        1234,
        data_store.DataStore._get_timestamp('/tmp/bla_50/something_1234.pb'))

  def test_get_project_glob(self):
    self.assertEqual(
        self._data_store._get_project_glob('p1'),
        'projects/p1')

  def test_get_brain_glob(self):
    self.assertEqual(
        self._data_store._get_brain_glob('p1', 'b1'), 'projects/p1/brains/b1')

  def test_get_snapshot_glob(self):
    self.assertEqual(
        self._data_store._get_snapshot_glob('p1', 'b1', 's1'),
        'projects/p1/brains/b1/snapshots/s1')

  def test_get_session_glob(self):
    self.assertEqual(
        self._data_store._get_session_glob('p1', 'b1', 's1'),
        'projects/p1/brains/b1/sessions/s1')

  def test_get_episode_glob(self):
    self.assertEqual(
        self._data_store._get_episode_glob('p1', 'b1', 's1', 'e1'),
        'projects/p1/brains/b1/sessions/s1/episodes/e1')

  def test_get_chunk_glob(self):
    self.assertEqual(
        self._data_store._get_chunk_glob('p1', 'b1', 's1', 'e1', 'c1'),
        'projects/p1/brains/b1/sessions/s1/episodes/e1/chunks/c1')

  def test_get_assignment_glob(self):
    self.assertStartsWith(
        self._data_store._get_assignment_glob('p1', 'b1', 's1', 'a1'),
        'projects/p1/brains/b1/sessions/s1/assignments/')

  def test_get_model_glob(self):
    self.assertEqual(
        self._data_store._get_model_glob('p1', 'b1', 's1', 'm1'),
        'projects/p1/brains/b1/sessions/s1/models/m1')

  def test_get_offline_evaluation_glob(self):
    self.assertEqual(
        self._data_store._get_offline_evaluation_glob('p1', 'b1', 's1', 'm1',
                                                      'o1'),
        'projects/p1/brains/b1/sessions/s1/models/m1/offline_evaluations/o1')

  def test_any_and_braced_path_arguments_to_glob(self):
    self.assertEqual(
        self._data_store._get_offline_evaluation_glob(['p1', 'p2'], None,
                                                      ['s1', 's2'], None,
                                                      ['o1', 'o2']),
        'projects/{p1,p2}/brains/*/sessions/{s1,s2}/models/*/' +
        'offline_evaluations/{o1,o2}')


if __name__ == '__main__':
  absltest.main()
