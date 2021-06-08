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
"""Tests for proto_conversion."""

from unittest import mock

from absl.testing import absltest
from api import proto_conversion
from api import test_constants

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import brain_pb2
import episode_pb2
import data_store_pb2
import session_pb2
from google.protobuf import text_format
from google.protobuf import timestamp_pb2


class ProtoConversionTest(absltest.TestCase):

  def test_brain_proto(self):
    brain_spec = text_format.Parse(test_constants.TEST_BRAIN_SPEC,
                                   brain_pb2.BrainSpec())
    data_store_brain = data_store_pb2.Brain(brain_spec=brain_spec)
    expected_common_brain = brain_pb2.Brain(
        brain_spec=brain_spec, create_time=timestamp_pb2.Timestamp(seconds=0))
    self.assertEqual(
        proto_conversion.ProtoConverter.convert_proto(
            data_store_brain), expected_common_brain)

  def test_episode_chunk_proto(self):
    expected_episode_chunk = episode_pb2.EpisodeChunk(
        episode_id='e0',
        chunk_id=2,
        steps=[episode_pb2.Step()],
        episode_state=episode_pb2.IN_PROGRESS,
        model_id='m0')
    data_store_episode_chunk = data_store_pb2.EpisodeChunk(
        data=expected_episode_chunk)
    self.assertEqual(
        proto_conversion.ProtoConverter.convert_proto(data_store_episode_chunk),
        expected_episode_chunk)

  def test_get_target_proto_brain(self):
    self.assertEqual(
        proto_conversion.ProtoConverter._get_target_proto(data_store_pb2.Brain),
        brain_pb2.Brain)

  def test_get_target_proto_session(self):
    self.assertEqual(
        proto_conversion.ProtoConverter._get_target_proto(
            data_store_pb2.Session),
        session_pb2.Session)

  def test_get_target_proto_episode_chunk(self):
    self.assertEqual(
        proto_conversion.ProtoConverter._get_target_proto(
            data_store_pb2.EpisodeChunk), episode_pb2.EpisodeChunk)

  def test_get_target_proto_not_found(self):
    with self.assertRaisesWithLiteralMatch(
        ValueError,
        'Proto <class \'data_store_pb2.OfflineEvaluation\'> could not be mapped'
        ' to any proto.'):
      proto_conversion.ProtoConverter._get_target_proto(
          data_store_pb2.OfflineEvaluation)

  def test_convert_micros_to_timestamp(self):
    mock_proto = mock.Mock()
    mock_proto.created_micros = 1619726720852543
    self.assertEqual(
        proto_conversion.ProtoConverter._convert_micros_to_timestamp(
            mock_proto, 'created_micros'),
        timestamp_pb2.Timestamp(seconds=1619726720852543 // 1000000))

  def test_convert_timestamp_to_micros(self):
    mock_proto = mock.Mock()
    mock_proto.create_time = timestamp_pb2.Timestamp(seconds=1619726720)
    self.assertEqual(
        proto_conversion.ProtoConverter._convert_timestamp_to_micros(
            mock_proto, 'create_time'), 1619726720000000)

  def test_set_field(self):
    common_brain = brain_pb2.Brain()
    proto_conversion.ProtoConverter._set_field(common_brain, 'project_id',
                                               'test_project')
    self.assertEqual(common_brain.project_id, 'test_project')

  def test_set_field_wrong_type(self):
    common_brain = brain_pb2.Brain()
    with self.assertRaises(TypeError):
      proto_conversion.ProtoConverter._set_field(
          common_brain, 'project_id', timestamp_pb2.Timestamp(seconds=1))

  def test_set_field_message(self):
    common_brain = brain_pb2.Brain()
    proto_conversion.ProtoConverter._set_field(
        common_brain, 'create_time', timestamp_pb2.Timestamp(seconds=1))
    self.assertEqual(common_brain.create_time,
                     timestamp_pb2.Timestamp(seconds=1))

  def test_get_target_type_or_name(self):
    self.assertEqual(
        proto_conversion.ProtoConverter._get_target_type_or_name(
            'created_micros', data_store_pb2.Brain, brain_pb2.Brain),
        'create_time')
    self.assertEqual(
        proto_conversion.ProtoConverter._get_target_type_or_name(
            'project_id', data_store_pb2.Brain, brain_pb2.Brain), 'project_id')

  def test_get_target_type_or_name_no_mapping(self):
    self.assertIsNone(
        proto_conversion.ProtoConverter._get_target_type_or_name(
            'cantaloupe', data_store_pb2.Brain, brain_pb2.Brain))

  def test_convert_field(self):
    self.assertEqual(
        proto_conversion.ProtoConverter._convert_field(
            data_store_pb2.Brain.DESCRIPTOR.fields_by_name['created_micros'],
            data_store_pb2.Brain(created_micros=1619726720852543),
            brain_pb2.Brain.DESCRIPTOR.fields_by_name['create_time']),
        timestamp_pb2.Timestamp(seconds=1619726720))

  def test_convert_field_no_op(self):
    self.assertEqual(
        proto_conversion.ProtoConverter._convert_field(
            data_store_pb2.Brain.DESCRIPTOR.fields_by_name['brain_id'],
            data_store_pb2.Brain(brain_id='island'),
            brain_pb2.Brain.DESCRIPTOR.fields_by_name['brain_id']), 'island')


if __name__ == '__main__':
  absltest.main()
