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

"""Tests for ResourceStore."""

import time
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from data_store import file_system
from data_store import resource_id
from data_store import resource_store


class ResourceStoreTest(parameterized.TestCase):

  def setUp(self):
    """Create a datastore object that uses a temporary directory."""
    super().setUp()
    self._fs = file_system.FakeFileSystem()
    self._mock_resource_encoder = mock.Mock()
    self._mock_resource_resolver = mock.Mock()
    self._resource_store = resource_store.ResourceStore(
        self._fs, self._mock_resource_encoder,
        self._mock_resource_resolver, dict)

  @parameterized.named_parameters(
      ('Create Timestamp',
       4221, 0, 0, 4221),
      ('Use Resource Id Timestamp',
       0, 1234, 0, 1234),
      ('Read Resource Timestamp',
       0, 0, 9876, 9876),)
  @mock.patch.object(time, 'time')
  def test_write(self, current_timestamp, resource_timestamp,
                 read_timestamp, expected_timestamp, mock_time):
    """Write an object using the current time."""
    with mock.patch.object(self._fs, 'write_file') as mock_write_file:
      with mock.patch.object(self._resource_store, 'read_timestamp_micros') as (
          mock_read_timestamp_micros):
        mock_time.return_value = current_timestamp / 1_000_000
        self._mock_resource_resolver.get_timestamp_micros.return_value = (
            resource_timestamp)
        mock_read_timestamp_micros.return_value = read_timestamp

        mock_resource = mock.Mock()
        mock_resource_id = mock.MagicMock()
        resource_path = 'a/resource/path'
        mock_resource_id.__str__.return_value = resource_path
        self._mock_resource_resolver.to_resource_id.return_value = (
            mock_resource_id)
        mock_resource_data = mock.Mock()
        self._mock_resource_encoder.encode_resource.return_value = (
            mock_resource_data)

        self._resource_store.write(mock_resource)

        self._mock_resource_resolver.to_resource_id.assert_called_once_with(
            mock_resource)
        (self._mock_resource_resolver.get_timestamp_micros
         .assert_called_once_with(mock_resource))
        # If the resource doesn't have have a timestamp,read the from the
        # filesystem.
        if not resource_timestamp:
          mock_read_timestamp_micros.assert_called_once_with(mock_resource_id)
        else:
          mock_read_timestamp_micros.assert_not_called()
        self._mock_resource_encoder.encode_resource.assert_called_once_with(
            mock_resource_id, mock_resource)
        mock_write_file.assert_called_once_with(
            self._resource_store._get_path(resource_path, expected_timestamp),
            mock_resource_data)

  @parameterized.named_parameters(
      ('File not found', None, None, 0),
      ('Found file', 'a_resource', 3, 26))
  def test_read(self, read_data, decoded_data, timestamp):
    with mock.patch.object(self._fs, 'read_file') as mock_read_file:
      with mock.patch.object(self._resource_store, 'read_timestamp_micros') as (
          mock_read_timestamp_micros):

        if read_data:
          mock_read_file.return_value = read_data
        else:
          def raise_file_not_found_error(unused_path):
            raise FileNotFoundError()

          mock_read_file.side_effect = raise_file_not_found_error

        mock_read_timestamp_micros.return_value = timestamp
        self._mock_resource_encoder.decode_resource.return_value = decoded_data

        mock_resource_id = 'a/resource'
        if read_data:
          self.assertEqual(decoded_data,
                           self._resource_store.read(mock_resource_id))
          self._mock_resource_encoder.decode_resource.assert_called_once_with(
              mock_resource_id, read_data)
        else:
          with self.assertRaises(resource_store.NotFoundError):
            self._resource_store.read(mock_resource_id)
        mock_read_file.assert_called_once_with(
            self._resource_store._get_path(mock_resource_id, timestamp))

  def test_read_by_proto_ids(self):
    with mock.patch.object(self._resource_store, 'read') as mock_read:
      with mock.patch.object(self._resource_store,
                             'resource_id_from_proto_ids') as (
                                 mock_resource_id_from_proto_ids):
        mock_attribute_type = mock.Mock()
        mock_read.return_value = 42
        mock_resource_id_from_proto_ids.return_value = 'a_resource_id'
        self.assertEqual(
            self._resource_store.read_by_proto_ids(
                mock_attribute_type, foo='bar', bish='bosh'), 42)
        mock_resource_id_from_proto_ids.assert_called_once_with(
            attribute_type=mock_attribute_type, foo='bar', bish='bosh')
        mock_read.assert_called_once_with('a_resource_id')

  def test_list_by_proto_ids(self):
    with mock.patch.object(self._resource_store, 'list') as mock_list:
      with mock.patch.object(self._resource_store,
                             'resource_id_from_proto_ids') as (
                                 mock_resource_id_from_proto_ids):
        mock_attribute_type = mock.Mock()
        list_result = ([10, 20, 30], 'a_pagination_token')
        mock_list.return_value = list_result
        mock_resource_id_from_proto_ids.return_value = 'a_resource_id'
        self.assertEqual(
            list_result,
            self._resource_store.list_by_proto_ids(
                attribute_type=mock_attribute_type, min_timestamp_micros=22,
                page_token='previous_pagination_token', page_size=123,
                time_descending=True, foo='bar', bish='bosh'))
        mock_resource_id_from_proto_ids.assert_called_once_with(
            attribute_type=mock_attribute_type, foo='bar', bish='bosh')
        mock_list.assert_called_once_with(
            'a_resource_id', min_timestamp_micros=22,
            page_token='previous_pagination_token', page_size=123,
            time_descending=True)

  @mock.patch.object(time, 'time')
  def test_get_timestamp_in_microseconds(self, mock_time):
    """Test getting the timestamp in microseconds."""
    mock_time.return_value = 0.123
    self.assertEqual(
        resource_store.ResourceStore.get_timestamp_in_microseconds(), 123000)

  @parameterized.named_parameters(
      ('No items', None, None, None),
      ('Has items', [5, 4, 3], 'page_token', 3))
  def test_get_most_recent(self, listed_resource_ids, page_token,
                           expected_resource_id):
    with mock.patch.object(self._resource_store, 'list') as mock_list:
      mock_resource_id_glob = mock.Mock()
      mock_list.return_value = (listed_resource_ids, page_token)
      self.assertEqual(
          self._resource_store.get_most_recent(mock_resource_id_glob),
          expected_resource_id)
      mock_list.assert_called_once_with(mock_resource_id_glob,
                                        page_size=mock.ANY)

  def test_decode_token(self):
    self.assertEqual((12, 'ab'), self._resource_store._decode_token('12:ab'))
    self.assertEqual((-1, ''), self._resource_store._decode_token(None))

  def test_encode_token(self):
    self.assertEqual('12:ab', self._resource_store._encode_token(12, 'ab'))

  def test_to_resource_id(self):
    mock_resource = mock.Mock()
    mock_resource_id = 42
    self._mock_resource_resolver.to_resource_id.return_value = mock_resource_id
    self.assertEqual(self._resource_store.to_resource_id(mock_resource),
                     mock_resource_id)
    self._mock_resource_resolver.to_resource_id.assert_called_with(
        mock_resource)

  @parameterized.named_parameters(
      ('No Attribute',
       None,
       dict(foo='bar', bish='bosh'),
       {'foo_id': 'BAR', 'bish_id': 'BOSH'}),
      ('Attribute',
       mock.MagicMock(),
       dict(hello='goodbye', hola='adios'),
       {resource_id.ATTRIBUTE: 'anattribute',
        'hello_id': 'GOODBYE', 'hola_id': 'ADIOS'}),)
  def test_resource_id_from_proto_ids(self, mock_attribute_type, proto_ids,
                                      expected_resource_id):
    self._mock_resource_resolver.resolve_attribute_name.return_value = (
        'anattribute')
    self._mock_resource_resolver.encode_proto_field.side_effect = (
        lambda field, value: (field + '_id', value.upper()))

    rid = self._resource_store.resource_id_from_proto_ids(
        attribute_type=mock_attribute_type, **proto_ids)
    self.assertEqual(rid, expected_resource_id)

    if mock_attribute_type:
      (self._mock_resource_resolver.resolve_attribute_name
       .assert_called_once_with(mock_attribute_type))
    self._mock_resource_resolver.encode_proto_field.assert_has_calls(
        [mock.call(*item) for item in proto_ids.items()])


if __name__ == '__main__':
  absltest.main()
