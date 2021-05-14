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

import time
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from data_store import data_store
from data_store import file_system
from data_store import resource_id

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
    self._data_store.write(data_store_pb2.Project(project_id='p1'))
    self.assertEqual(
        self._data_store.read(resource_id.FalkenResourceId(
            project='p1')).project_id,
        'p1')

  def test_read_write_brain(self):
    self._data_store.write(
        data_store_pb2.Brain(project_id='p1', brain_id='b1'))
    self.assertEqual(
        self._data_store.read(resource_id.FalkenResourceId(
            project='p1',
            brain='b1')).brain_id,
        'b1')

  def test_read_write_snapshot(self):
    self._data_store.write(data_store_pb2.Snapshot(
        project_id='p1', brain_id='b1', snapshot_id='s1'))
    self.assertEqual(
        self._data_store.read(resource_id.FalkenResourceId(
            project='p1',
            brain='b1',
            snapshot='s1')).snapshot_id,
        's1')

  def test_read_write_session(self):
    self._data_store.write(data_store_pb2.Session(
        project_id='p1', brain_id='b1', session_id='s1'))
    self.assertEqual(
        self._data_store.read(resource_id.FalkenResourceId(
            project='p1',
            brain='b1',
            session='s1')).session_id,
        's1')

  def test_read_write_episode_chunk(self):
    self._data_store.write(data_store_pb2.EpisodeChunk(
        project_id='p1', brain_id='b1', session_id='s1', episode_id='e1',
        chunk_id=3))
    self.assertEqual(
        self._data_store.read(resource_id.FalkenResourceId(
            project='p1',
            brain='b1',
            session='s1',
            episode='e1',
            chunk=3)).chunk_id,
        3)

  def test_read_write_online_evaluation(self):
    self._data_store.write(
        data_store_pb2.OnlineEvaluation(
            project_id='p1', brain_id='b1', session_id='s1', episode_id='e1'))
    self.assertEqual(
        self._data_store.read(resource_id.FalkenResourceId(
            project='p1',
            brain='b1',
            session='s1',
            episode='e1',
            attribute='online_evaluation')).episode_id,
        'e1')

  def test_read_write_assignment(self):
    rid = self._data_store.write(
        data_store_pb2.Assignment(
            project_id='p1', brain_id='b1', session_id='s1',
            assignment_id='a1'))
    self.assertEqual(self._data_store.read(rid).assignment_id, 'a1')

  def test_read_write_model(self):
    self._data_store.write(data_store_pb2.Model(
        project_id='p1', brain_id='b1', session_id='s1', model_id='m1'))
    self.assertEqual(
        self._data_store.read(resource_id.FalkenResourceId(
            project='p1',
            brain='b1',
            session='s1',
            model='m1')).model_id,
        'm1')

  def test_read_write_serialized_model(self):
    self._data_store.write(data_store_pb2.SerializedModel(
        project_id='p1', brain_id='b1', session_id='s1', model_id='m1'))
    self.assertEqual(
        self._data_store.read(resource_id.FalkenResourceId(
            project='p1',
            brain='b1',
            session='s1',
            model='m1',
            attribute='serialized_model')).model_id,
        'm1')

  def test_read_write_offline_evaluation(self):
    self._data_store.write(
        data_store_pb2.OfflineEvaluation(
            project_id='p1',
            brain_id='b1',
            session_id='s1',
            model_id='m1',
            offline_evaluation_id=2))
    self.assertEqual(
        self._data_store.read(resource_id.FalkenResourceId(
            project='p1',
            brain='b1',
            session='s1',
            model='m1',
            offline_evaluation=2)).offline_evaluation_id,
        2)

  def test_resource_id_from_proto_id(self):
    rid = self._data_store.resource_id_from_proto_ids(
        project_id='p0',
        brain_id='b0',
        session_id='s0',
        assignment_id='a0')
    self.assertStartsWith(str(rid),
                          'projects/p0/brains/b0/sessions/s0/assignments')

    self.assertNotEmpty(rid.assignment)  # Check assignment_id encoding.
    self.assertNotEqual(rid.assignment, 'a0')

  def test_read_by_proto_id(self):
    keys = dict(
        project_id='p0', brain_id='b0', session_id='s0', assignment_id='a0')

    assignment = data_store_pb2.Assignment(**keys)
    self._data_store.write(assignment)
    self.assertEqual(
        self._data_store.read_by_proto_ids(**keys),
        assignment)

  def test_list_by_proto_ids(self):
    id_dict = dict(project_id='p1', brain_id='b1',
                   session_id='s1')

    res_ids = []
    for i in range(10):
      id_dict['assignment_id'] = f'a{i}'
      proto = data_store_pb2.Assignment(**id_dict)
      res_id = self._data_store.write(proto)
      list_result, _ = self._data_store.list_by_proto_ids(**id_dict)
      self.assertEqual(list_result, [res_id])
      res_ids.append(res_id)

    id_dict['assignment_id'] = '*'
    list_result, _ = self._data_store.list_by_proto_ids(**id_dict)

    self.assertCountEqual(list_result, res_ids)

  def test_get_attribute_by_resource_id(self):
    id_dict = dict(project_id='p1', brain_id='b1',
                   session_id='s1', episode_id='e1')

    self.assertEqual(
        self._data_store.resource_id_from_proto_ids(**id_dict),
        'projects/p1/brains/b1/sessions/s1/episodes/e1')

    self.assertEqual(
        self._data_store.resource_id_from_proto_ids(
            attribute_type=data_store_pb2.OnlineEvaluation,
            **id_dict),
        'projects/p1/brains/b1/sessions/s1/episodes/e1/online_evaluation')

    online_eval = data_store_pb2.OnlineEvaluation(**id_dict)
    self._data_store.write(online_eval)

    read_eval = self._data_store.read_by_proto_ids(
        attribute_type=data_store_pb2.OnlineEvaluation,
        **id_dict)

    self.assertEqual(online_eval, read_eval)

    list_eval, _ = self._data_store.list_by_proto_ids(
        attribute_type=data_store_pb2.OnlineEvaluation,
        **id_dict)

    self.assertEqual(
        ['projects/p1/brains/b1/sessions/s1/episodes/e1/online_evaluation'],
        list_eval)

  @mock.patch.object(time, 'time', autospec=True)
  def test_timestamp_logic(self, mock_time):
    """Test read, writing, updating a proto."""
    mock_time.return_value = 0.123

    # Check auto timestamp creation.
    self._data_store.write(data_store_pb2.Project(project_id='p1'))
    self.assertEqual(
        self._data_store.read(resource_id.FalkenResourceId(
            project='p1')).created_micros,
        123_000)
    self.assertEqual(
        self._data_store.read_timestamp_micros(
            resource_id.FalkenResourceId(project='p1')),
        123_000)

    # Reriting with a different timestamp raises an error.
    with self.assertRaises(ValueError):
      self._data_store.write(data_store_pb2.Project(
          project_id='p1',
          created_micros=567))

    mock_time.return_value = 0.456
    # Writing with the same timestamp is fine.
    self._data_store.write(data_store_pb2.Project(
        project_id='p1',
        created_micros=123_000))
    self.assertEqual(
        self._data_store.read_timestamp_micros(
            resource_id.FalkenResourceId(project='p1')),
        123_000)

    # Writing with no timestamp will use the existing timestamp.
    self._data_store.write(data_store_pb2.Project(project_id='p1'))
    self.assertEqual(
        self._data_store.read_timestamp_micros(
            resource_id.FalkenResourceId(project='p1')),
        123_000)
    self.assertEqual(
        self._data_store.read_timestamp_micros(
            resource_id.FalkenResourceId(project='p1')),
        123_000)

  def test_get_most_recent_snapshot(self):
    for i in range(10):
      self._data_store.write(data_store_pb2.Snapshot(
          project_id='p1',
          brain_id='b1',
          snapshot_id=f's{i}'))
    self.assertEqual(
        'projects/p1/brains/b1/snapshots/s9',
        self._data_store.get_most_recent_snapshot('p1', 'b1'))

  def test_decode_token(self):
    self.assertEqual((12, 'ab'), self._data_store._decode_token('12:ab'))
    self.assertEqual((-1, ''), self._data_store._decode_token(None))

  def test_encode_token(self):
    self.assertEqual('12:ab', self._data_store._encode_token(12, 'ab'))

  # pylint: disable=g-long-lambda
  @parameterized.named_parameters(
      ('project', lambda x: data_store_pb2.Project(project_id=str(x)),
       'projects/*'),
      ('brain', lambda x: data_store_pb2.Brain(
          project_id='p1', brain_id=str(x)),
       'projects/p1/brains/*'),
      ('session', lambda x: data_store_pb2.Session(
          project_id='p1', brain_id='b1', session_id=str(x)),
       'projects/p1/brains/b1/sessions/*'),
      ('episode_chunk', lambda x: data_store_pb2.EpisodeChunk(
          project_id='p1', brain_id='b1', session_id='s1',
          episode_id='e1', chunk_id=x),
       'projects/p1/brains/b1/sessions/s1/episodes/e1/chunks/*'),
      ('online_evaluation', lambda x: data_store_pb2.OnlineEvaluation(
          project_id='p1', brain_id='b1', session_id='s1',
          episode_id=str(x)),
       'projects/p1/brains/b1/sessions/s1/episodes/*/online_evaluation'))
  @mock.patch.object(time, 'time', autospec=True)
  def test_list(self, creation_fun, rid_glob, mock_time):
    rid_glob = resource_id.FalkenResourceId(rid_glob)
    rids = []
    for i in range(100):
      mock_time.return_value = i / 1e6
      rids.append(self._data_store.write(creation_fun(i)))

    rid_strings = [str(rid) for rid in rids]
    result, _ = self._data_store.list(rid_glob)
    self.assertEqual(result, rid_strings)

    # Test min_timestamp
    result, _ = self._data_store.list(rid_glob, min_timestamp_micros=50)
    self.assertEqual(result, rid_strings[50:])

    # Test pagination + min_timestamp
    result = []
    page_token = None
    i = 0
    while True:
      page, page_token = self._data_store.list(
          rid_glob, page_size=10, page_token=page_token,
          min_timestamp_micros=5)
      self.assertLessEqual(len(page), 10)
      self.assertLessEqual(i, 10)
      result += page
      last_page_index = min(len(rid_strings) -1, 5 + (i + 1) * 10 - 1)
      want_token = f'{last_page_index}:{rid_strings[last_page_index]}'
      i += 1
      if not page_token:
        break
      self.assertEqual(page_token, want_token)
    self.assertEqual(result, rid_strings[5:])

  @parameterized.parameters(range(1, 10))
  @mock.patch.object(time, 'time', autospec=True)
  def test_pagination_overlapping_timestamps(
      self, timestamp_repeat, mock_time):
    min_timestamp = 3
    rids = []
    expected_results = 0
    for i in range(200):
      # timestamp_repeat indicates how many successive timestamps are identical.
      time_stamp = i // timestamp_repeat
      mock_time.return_value = time_stamp / 1e6
      if time_stamp >= min_timestamp:
        expected_results += 1
      rids.append(self._data_store.write(
          data_store_pb2.Project(project_id=f'{i:04}')))
    rid_glob = resource_id.FalkenResourceId(rids[0].parts[:-1] + ['*'])

    # Test pagination + min_timestamp
    result = []
    i = 0
    page_token = None
    while True:
      page, page_token = self._data_store.list(
          rid_glob, page_size=3, page_token=page_token,
          min_timestamp_micros=min_timestamp)
      result += page
      if not page_token:
        break
      self.assertLen(page, 3)
      i += 1

    # Check ordering of returned elements.
    for rid, rid_next in zip(result, result[1:]):
      self.assertLess(rid, rid_next)

    self.assertEqual(len(set(result)), len(result))
    self.assertLen(result, expected_results)

  def test_assignment_callback(self):
    """Tests assignment callback system."""
    assignment_callback = mock.Mock()

    self._data_store._fs = mock.Mock()
    self._data_store.add_assignment_callback(assignment_callback)

    self._data_store._fs.add_file_callback.assert_called_once_with(mock.ANY)
    file_callback = self._data_store._fs.add_file_callback.call_args.args[0]
    assignment_callback.assert_not_called()
    file_callback('x')
    assignment_callback.assert_called_once()

    self._data_store.remove_assignment_callback(assignment_callback)
    self._data_store._fs.remove_file_callback.assert_called_with(file_callback)

  def test_datastore_to_resource_id(self):
    proto = data_store_pb2.Session(
        project_id='p0',
        brain_id='b0',
        session_id='s0')
    res_id = self._data_store.to_resource_id(proto)
    self.assertEqual(
        res_id,
        'projects/p0/brains/b0/sessions/s0')

  @parameterized.parameters(
      ({'project_id': 'p0'}, 'projects/p0'),
      ({'project_id': 'p0', 'brain_id': 'b0',
        'session_id': 's0', 'assignment_id': 'a0'},
       'projects/p0/brains/b0/sessions/s0/assignments/.+'),
      ({'project_id': 'p0', 'brain_id': 'b0',
        'session_id': 's0', 'assignment_id': '*'},
       r'projects/p0/brains/b0/sessions/s0/assignments/\*'))
  def test_resource_id_from_proto_ids(self, key_dict, want_regex):
    res_id = self._data_store.resource_id_from_proto_ids(**key_dict)
    self.assertRegex(str(res_id), want_regex)

  def test_list_resource_with_subdirs(self):
    self._data_store.write(data_store_pb2.Project(project_id='p0'))
    self._data_store.write(data_store_pb2.Brain(project_id='p0', brain_id='b0'))
    result, _ = self._data_store.list_by_proto_ids(project_id='*')
    self.assertEqual(['projects/p0'], result)


if __name__ == '__main__':
  absltest.main()
