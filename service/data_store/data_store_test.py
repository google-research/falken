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
"""Tests for data store mix-ins."""

import time
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from data_store import data_store
from data_store import file_system
from data_store import resource_id
from data_store import resource_store

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import data_store_pb2


def create_data_store_mixin(mixin_class):
  """Constructs a datastore class with a mix-in.

  Args:
    mixin_class: Mixin class to create a DataStore from.

  Returns:
    DataStore instance with a mocked FileSystem and the Mixin applied.
  """

  class MixinDataStore(resource_store.ResourceStore, mixin_class):

    def __init__(self):
      super().__init__(mock.Mock(), data_store._ResourceEncoder(),
                       data_store._ResourceResolver(),
                       resource_id.FalkenResourceId)

  return MixinDataStore()


class SnapshotDataStoreMixinTest(absltest.TestCase):
  """Test SnapshotDataStoreMixin."""

  def test_get_most_recent_snapshot(self):
    data_store_mixin = create_data_store_mixin(
        data_store.SnapshotDataStoreMixin)
    with mock.patch.object(data_store_mixin, 'get_most_recent') as (
        mock_get_most_recent):
      expected_snapshot = data_store_pb2.Snapshot(project_id='p0',
                                                  brain_id='b0')
      mock_get_most_recent.return_value = expected_snapshot
      self.assertEqual(
          data_store_mixin.get_most_recent_snapshot(project_id='p0',
                                                    brain_id='b0'),
          expected_snapshot)
      mock_get_most_recent.assert_called_once_with(
          data_store_mixin.resource_id_from_proto_ids(
              project_id='p0', brain_id='b0', snapshot_id='*'))


class SessionDataStoreMixinTest(absltest.TestCase):
  """Test SessionDataStoreMixin."""

  @mock.patch.object(time, 'time')
  def test_write_stopped_session(self, mock_time):
    data_store_mixin = create_data_store_mixin(data_store.SessionDataStoreMixin)
    with mock.patch.object(data_store_mixin, 'write') as mock_write:
      session_resource_id = resource_id.FalkenResourceId(
          project='p0', brain='b0', session='s0')
      session_proto = data_store_pb2.Session(project_id='p0', brain_id='b0',
                                             session_id='s0')
      mock_time.return_value = 123
      mock_write.return_value = session_resource_id
      self.assertEqual(data_store_mixin.write_stopped_session(session_proto),
                       session_resource_id)
      mock_write.assert_called_once_with(
          data_store_pb2.Session(project_id='p0', brain_id='b0',
                                 session_id='s0', ended_micros=123000000))


class DataStoreTest(parameterized.TestCase):
  """Test DataStore."""

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
        self._data_store.read(self._data_store.resource_id_from_proto_ids(
            project_id='p1')).project_id, 'p1')

  def test_read_write_brain(self):
    self._data_store.write(
        data_store_pb2.Brain(project_id='p1', brain_id='b1'))
    self.assertEqual(
        self._data_store.read(self._data_store.resource_id_from_proto_ids(
            project_id='p1', brain_id='b1')).brain_id, 'b1')

  def test_read_write_snapshot(self):
    self._data_store.write(data_store_pb2.Snapshot(
        project_id='p1', brain_id='b1', snapshot_id='s1'))
    self.assertEqual(
        self._data_store.read(self._data_store.resource_id_from_proto_ids(
            project_id='p1', brain_id='b1', snapshot_id='s1')).snapshot_id,
        's1')

  def test_read_write_session(self):
    self._data_store.write(data_store_pb2.Session(
        project_id='p1', brain_id='b1', session_id='s1'))
    self.assertEqual(
        self._data_store.read(self._data_store.resource_id_from_proto_ids(
            project_id='p1', brain_id='b1', session_id='s1')).session_id, 's1')

  def test_read_write_episode_chunk(self):
    self._data_store.write(data_store_pb2.EpisodeChunk(
        project_id='p1', brain_id='b1', session_id='s1', episode_id='e1',
        chunk_id=3))
    self.assertEqual(
        self._data_store.read(self._data_store.resource_id_from_proto_ids(
            project_id='p1', brain_id='b1', session_id='s1', episode_id='e1',
            chunk_id=3)).chunk_id, 3)

  def test_read_write_online_evaluation(self):
    self._data_store.write(
        data_store_pb2.OnlineEvaluation(
            project_id='p1', brain_id='b1', session_id='s1', episode_id='e1'))
    self.assertEqual(
        self._data_store.read(self._data_store.resource_id_from_proto_ids(
            data_store_pb2.OnlineEvaluation, project_id='p1', brain_id='b1',
            session_id='s1', episode_id='e1')).episode_id, 'e1')

  def test_list_online_evaluation_by_resource_id(self):
    """List a resource with an attribute from the data store."""
    id_dict = dict(project_id='p1', brain_id='b1',
                   session_id='s1', episode_id='e1')
    online_eval = data_store_pb2.OnlineEvaluation(**id_dict)
    self._data_store.write(online_eval)
    list_eval, _ = self._data_store.list_by_proto_ids(
        attribute_type=data_store_pb2.OnlineEvaluation,
        **id_dict)
    self.assertEqual(
        ['projects/p1/brains/b1/sessions/s1/episodes/e1/online_evaluation'],
        list_eval)

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
        self._data_store.read(self._data_store.resource_id_from_proto_ids(
            project_id='p1', brain_id='b1', session_id='s1',
            model_id='m1')).model_id, 'm1')

  def test_read_write_serialized_model(self):
    self._data_store.write(data_store_pb2.SerializedModel(
        project_id='p1', brain_id='b1', session_id='s1', model_id='m1'))
    self.assertEqual(
        self._data_store.read(self._data_store.resource_id_from_proto_ids(
            data_store_pb2.SerializedModel, project_id='p1', brain_id='b1',
            session_id='s1', model_id='m1')).model_id, 'm1')

  def test_read_write_offline_evaluation(self):
    self._data_store.write(
        data_store_pb2.OfflineEvaluation(
            project_id='p1', brain_id='b1', session_id='s1', model_id='m1',
            offline_evaluation_id=2))
    self.assertEqual(
        self._data_store.read(self._data_store.resource_id_from_proto_ids(
            project_id='p1', brain_id='b1', session_id='s1', model_id='m1',
            offline_evaluation_id=2)).offline_evaluation_id, 2)

  def test_to_resource_id(self):
    """Test the resolver's conversion from a proto to a resource ID."""
    proto = data_store_pb2.Session(
        project_id='p0',
        brain_id='b0',
        session_id='s0')
    res_id = self._data_store.to_resource_id(proto)
    self.assertEqual(
        res_id,
        'projects/p0/brains/b0/sessions/s0')

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
  def test_list(self, creation_function, rid_glob, mock_time):
    rid_glob = resource_id.FalkenResourceId(rid_glob)
    rids = []
    for i in range(100):
      mock_time.return_value = i / 1e6
      rids.append(self._data_store.write(creation_function(i)))

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

  @parameterized.named_parameters(
      ('descending', True),
      ('ascending', False))
  def test_list_resource_with_subdirs(self, descending):
    self._data_store.write(data_store_pb2.Project(project_id='p0'))
    self._data_store.write(data_store_pb2.Brain(project_id='p0', brain_id='b0'))
    result, _ = self._data_store.list_by_proto_ids(
        project_id='*', time_descending=descending)
    self.assertEqual(['projects/p0'], result)

  @parameterized.named_parameters(
      ('descending', True),
      ('ascending', False))
  @mock.patch.object(time, 'time', autospec=True)
  def test_list_order_time(self, descending, mock_time):
    rids = []

    for i in range(100):
      mock_time.return_value = i / 1e6
      rids.append(self._data_store.write(
          data_store_pb2.Project(project_id=f'{i:04}')))
    rid_glob = resource_id.FalkenResourceId(rids[0].parts[:-1] + ['*'])

    # Test time_descending
    result, _ = self._data_store.list(rid_glob, time_descending=descending)
    if descending:
      self.assertCountEqual(result, list(reversed(rids)))
    else:
      self.assertCountEqual(result, rids)

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
      self.assertLess(str(rid), str(rid_next))

    self.assertEqual(len(set(result)), len(result))
    self.assertLen(result, expected_results)


if __name__ == '__main__':
  absltest.main()
