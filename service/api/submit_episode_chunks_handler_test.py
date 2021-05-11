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
"""Tests for submit_episode_chunks_handler."""
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from api import data_cache
from api import submit_episode_chunks_handler

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import action_pb2
import episode_pb2
import observation_pb2
import falken_service_pb2
from google.rpc import code_pb2
from learner.brains import specs


class SubmitEpisodeChunksHandler(parameterized.TestCase):

  @mock.patch.object(submit_episode_chunks_handler,
                     '_check_episode_data_with_brain_spec')
  def test_submit_episode_chunks_checks(self, check_episode_data):
    mock_context = mock.Mock()
    mock_context.abort.side_effect = Exception()
    check_episode_data.side_effect = specs.TypingError('Failure.')
    with self.assertRaises(Exception):
      submit_episode_chunks_handler.submit_episode_chunks(
          falken_service_pb2.SubmitEpisodeChunksRequest(),
          mock_context, None)
    mock_context.abort.assert_called_once_with(
        code_pb2.INVALID_ARGUMENT,
        'Episode data failed did not match the brain spec for the session. '
        'Failure.')
    check_episode_data.assert_called_once_with(None, '', '', mock.ANY)
    self.assertEmpty(check_episode_data.call_args[0][3])

  @mock.patch.object(data_cache, 'get_brain_spec')
  def test_check_episode_data_with_brain_spec_empty_in_progress(
      self, get_brain_spec):
    mock_ds = mock.Mock()
    get_brain_spec.return_value = mock.Mock()
    chunks = [episode_pb2.EpisodeChunk(
        episode_id='ep0', chunk_id=0, steps=[],
        episode_state=episode_pb2.IN_PROGRESS, model_id='m0')]
    with self.assertRaisesWithLiteralMatch(
        specs.TypingError,
        'Received an empty chunk that does not close the episode at '
        'chunk_index: 0.'):
      submit_episode_chunks_handler._check_episode_data_with_brain_spec(
          mock_ds, 'p0', 'b0', chunks)
    get_brain_spec.assert_called_once_with(mock_ds, 'p0', 'b0')

  @mock.patch.object(data_cache, 'get_brain_spec')
  def test_check_episode_data_with_brain_spec_empty_at_id_0(
      self, get_brain_spec):
    mock_ds = mock.Mock()
    get_brain_spec.return_value = mock.Mock()
    chunks = [episode_pb2.EpisodeChunk(
        episode_id='ep0', chunk_id=0, steps=[],
        episode_state=episode_pb2.FAILURE, model_id='m0')]

    with self.assertRaisesWithLiteralMatch(
        specs.TypingError, 'Received an empty episode at chunk_index: 0.'):
      submit_episode_chunks_handler._check_episode_data_with_brain_spec(
          mock_ds, 'p0', 'b0', chunks)
    get_brain_spec.assert_called_once_with(mock_ds, 'p0', 'b0')

  @parameterized.named_parameters(
      ('action', 'action_spec'),
      ('observation', 'observation_spec'))
  @mock.patch.object(specs, 'BrainSpec')
  @mock.patch.object(data_cache, 'get_brain_spec')
  def test_check_episode_data_with_brain_spec_check_fails(
      self, field, get_brain_spec, brain_spec_proto_node):
    mock_ds = mock.Mock()
    get_brain_spec.return_value = mock.Mock()
    step_0 = episode_pb2.Step(observation=observation_pb2.ObservationData(),
                              action=action_pb2.ActionData())
    chunks = [episode_pb2.EpisodeChunk(
        episode_id='ep0', chunk_id=0, steps=[step_0],
        episode_state=episode_pb2.FAILURE, model_id='m0')]
    mock_brain_spec_node = mock.Mock()
    brain_spec_proto_node.return_value = mock_brain_spec_node
    getattr(mock_brain_spec_node,
            field).proto_node.data_to_proto_nest.side_effect = (
                specs.TypingError('data_to_proto_nest failed.'))

    with self.assertRaisesWithLiteralMatch(
        specs.TypingError,
        'Brainspec check failed in chunk 0, step 0: data_to_proto_nest '
        'failed.'):
      submit_episode_chunks_handler._check_episode_data_with_brain_spec(
          mock_ds, 'p0', 'b0', chunks)

    get_brain_spec.assert_called_once_with(mock_ds, 'p0', 'b0')
    mock_brain_spec_node.action_spec.proto_node.data_to_proto_nest.assert_called_once_with(
        chunks[0].steps[0].action)
    if field == 'observation_spec':
      (mock_brain_spec_node.observation_spec.proto_node.data_to_proto_nest
       .assert_called_once_with(chunks[0].steps[0].observation))
    brain_spec_proto_node.assert_called_once_with(get_brain_spec.return_value)

if __name__ == '__main__':
  absltest.main()
