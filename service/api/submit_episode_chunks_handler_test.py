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
from api import model_selector
from api import submit_episode_chunks_handler
from data_store import resource_id

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import action_pb2
import data_store_pb2
import episode_pb2
import observation_pb2
import falken_service_pb2
from google.rpc import code_pb2
from learner.brains import specs


class SubmitEpisodeChunksHandlerTest(parameterized.TestCase):

  def _chunks(self, include_steps=True):
    steps = []
    if include_steps:
      steps = [
          episode_pb2.Step(
              observation=observation_pb2.ObservationData(),
              action=action_pb2.ActionData())
      ]
    return [
        episode_pb2.EpisodeChunk(
            episode_id='ep0',
            chunk_id=0,
            steps=steps,
            episode_state=episode_pb2.IN_PROGRESS,
            model_id='m0')
    ]

  def _data_store_chunk(self):
    return data_store_pb2.EpisodeChunk(
        project_id='p0',
        brain_id='b0',
        session_id='s0',
        episode_id='ep0',
        data=self._chunks()[0],
        steps_type=data_store_pb2.ONLY_DEMONSTRATIONS)

  @mock.patch.object(submit_episode_chunks_handler,
                     '_check_episode_data_with_brain_spec')
  def test_submit_episode_chunks_check_fails(self, check_episode_data):
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
    chunks = self._chunks(False)
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
    chunks = self._chunks(False)
    chunks[0].episode_state = episode_pb2.FAILURE

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
    chunks = self._chunks()
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

  @mock.patch.object(submit_episode_chunks_handler, '_record_online_evaluation')
  @mock.patch.object(submit_episode_chunks_handler, '_get_steps_type')
  def test_store_episode_chunks(self, get_steps_type, record_online_evaluation):
    mock_ds = mock.Mock()
    chunks = self._chunks()
    episode_resource_id = resource_id.FalkenResourceId(
        'projects/p0/brains/b0/sessions/s0/episodes/ep0')
    get_steps_type.return_value = data_store_pb2.ONLY_DEMONSTRATIONS

    _ = submit_episode_chunks_handler._store_episode_chunks(
        mock_ds, chunks, episode_resource_id)

    mock_ds.write_episode_chunk.assert_called_once_with(
        data_store_pb2.EpisodeChunk(
            project_id='p0',
            brain_id='b0',
            session_id='s0',
            episode_id='ep0',
            chunk_id=0,
            data=chunks[0],
            steps_type=get_steps_type.return_value))
    record_online_evaluation.assert_called_once_with(mock_ds,
                                                     self._data_store_chunk(),
                                                     episode_resource_id)
    get_steps_type.assert_called_once_with(chunks[0])

  @mock.patch.object(submit_episode_chunks_handler, '_get_steps_type')
  def test_store_episode_chunks_failure_at_get_steps_type(self, get_steps_type):
    mock_ds = mock.Mock()
    chunks = self._chunks()
    episode_resource_id = resource_id.FalkenResourceId(
        'projects/p0/brains/b0/sessions/s0/episodes/ep0')
    get_steps_type.side_effect = ValueError('Unsupported step type.')

    with self.assertRaisesWithLiteralMatch(
        ValueError,
        'Encountered error while getting steps type for episode ep0 chunk 0. '
        'Unsupported step type.'):
      submit_episode_chunks_handler._store_episode_chunks(
          mock_ds, chunks, episode_resource_id)

    mock_ds.write_episode_chunk.assert_not_called()
    get_steps_type.assert_called_once_with(chunks[0])

  @mock.patch.object(submit_episode_chunks_handler, '_record_online_evaluation')
  @mock.patch.object(submit_episode_chunks_handler, '_get_steps_type')
  def test_store_episode_chunks_failure_at_record_online_evaluation(
      self, get_steps_type, record_online_evaluation):
    mock_ds = mock.Mock()
    chunks = self._chunks()
    episode_resource_id = resource_id.FalkenResourceId(
        'projects/p0/brains/b0/sessions/s0/episodes/ep0')
    get_steps_type.return_value = data_store_pb2.ONLY_DEMONSTRATIONS
    record_online_evaluation.side_effect = ValueError('Episode incomplete.')

    with self.assertRaisesWithLiteralMatch(
        ValueError,
        'Encountered error while recording online evaluation for episode ep0 '
        'chunk 0. Episode incomplete.'):
      submit_episode_chunks_handler._store_episode_chunks(
          mock_ds, chunks, episode_resource_id)

    mock_ds.write_episode_chunk.assert_called_once_with(
        data_store_pb2.EpisodeChunk(
            project_id='p0',
            brain_id='b0',
            session_id='s0',
            episode_id='ep0',
            chunk_id=0,
            data=chunks[0],
            steps_type=get_steps_type.return_value))
    record_online_evaluation.assert_called_once_with(mock_ds,
                                                     self._data_store_chunk(),
                                                     episode_resource_id)
    get_steps_type.assert_called_once_with(chunks[0])

  def test_get_steps_type_mixed(self):
    chunk = episode_pb2.EpisodeChunk(steps=[
        episode_pb2.Step(
            action=action_pb2.ActionData(
                source=action_pb2.ActionData.HUMAN_DEMONSTRATION)),
        episode_pb2.Step(
            action=action_pb2.ActionData(
                source=action_pb2.ActionData.BRAIN_ACTION))
    ])
    self.assertEqual(
        submit_episode_chunks_handler._get_steps_type(chunk),
        data_store_pb2.MIXED)

  def test_get_steps_type_only_demos(self):
    chunk = episode_pb2.EpisodeChunk(steps=[
        episode_pb2.Step(
            action=action_pb2.ActionData(
                source=action_pb2.ActionData.HUMAN_DEMONSTRATION))
    ])
    self.assertEqual(
        submit_episode_chunks_handler._get_steps_type(chunk),
        data_store_pb2.ONLY_DEMONSTRATIONS)

  def test_get_steps_type_only_inferences(self):
    chunk = episode_pb2.EpisodeChunk(steps=[
        episode_pb2.Step(
            action=action_pb2.ActionData(
                source=action_pb2.ActionData.NO_SOURCE)),
        episode_pb2.Step(
            action=action_pb2.ActionData(
                source=action_pb2.ActionData.BRAIN_ACTION))
    ])
    self.assertEqual(
        submit_episode_chunks_handler._get_steps_type(chunk),
        data_store_pb2.ONLY_INFERENCES)

  def test_get_steps_type_only_unknown(self):
    chunk = episode_pb2.EpisodeChunk(steps=[])
    self.assertEqual(
        submit_episode_chunks_handler._get_steps_type(chunk),
        data_store_pb2.UNKNOWN)

  def test_get_steps_type_unsupported(self):
    chunk = episode_pb2.EpisodeChunk(steps=[
        episode_pb2.Step(
            action=action_pb2.ActionData(
                source=action_pb2.ActionData.SOURCE_UNKNOWN))
    ])
    with self.assertRaisesWithLiteralMatch(ValueError,
                                           'Unsupported step type: 0'):
      submit_episode_chunks_handler._get_steps_type(chunk)

  @mock.patch.object(submit_episode_chunks_handler, '_get_episode_steps_type')
  @mock.patch.object(submit_episode_chunks_handler, '_episode_score')
  @mock.patch.object(submit_episode_chunks_handler, '_episode_complete')
  def test_record_online_evaluation(self, episode_complete, episode_score,
                                    get_episode_steps_type):
    episode_complete.return_value = True
    episode_score.return_value = 1
    get_episode_steps_type.return_value = (data_store_pb2.ONLY_INFERENCES,
                                           ['m0', 'm1'])

    mock_ds = mock.Mock()
    chunk = self._chunks()[0]
    episode_resource_id = resource_id.FalkenResourceId(
        'projects/p0/brains/b0/sessions/s0/episodes/ep0')
    _ = submit_episode_chunks_handler._record_online_evaluation(
        mock_ds, chunk, episode_resource_id)
    mock_ds.write_online_evaluation.called_once_with()
    episode_complete.called_once_with(chunk)
    episode_score.called_once_with(chunk)
    get_episode_steps_type.called_once_with(mock_ds, chunk, episode_resource_id)

  @mock.patch.object(submit_episode_chunks_handler, '_episode_complete')
  def test_record_online_evaluation_failure_at_episode_complete(
      self, episode_complete):
    episode_complete.side_effect = ValueError('Unsupported episode state 0.')

    chunk = self._chunks()[0]
    with self.assertRaisesWithLiteralMatch(ValueError,
                                           'Unsupported episode state 0.'):
      submit_episode_chunks_handler._record_online_evaluation(
          mock.Mock(), chunk, mock.Mock())
    episode_complete.called_once_with(chunk)

  @mock.patch.object(submit_episode_chunks_handler, '_episode_score')
  @mock.patch.object(submit_episode_chunks_handler, '_episode_complete')
  def test_record_online_evaluation_failure_at_episode_score(
      self, episode_complete, episode_score):
    episode_complete.return_value = True
    episode_score.side_effect = ValueError(
        'Incomplete episode can\'t be scored.')
    chunk = self._chunks()[0]

    with self.assertRaisesWithLiteralMatch(
        ValueError, 'Incomplete episode can\'t be scored.'):
      submit_episode_chunks_handler._record_online_evaluation(
          mock.Mock(), chunk, mock.Mock())

    episode_complete.called_once_with(chunk)
    episode_score.called_once_with(chunk)

  @parameterized.named_parameters(
      ('no_steps_type_no_model_ids', (None, [])),
      ('not_inference', (data_store_pb2.MIXED, ['m0', 'm1'])))
  @mock.patch.object(submit_episode_chunks_handler, '_get_episode_steps_type')
  @mock.patch.object(submit_episode_chunks_handler, '_episode_score')
  @mock.patch.object(submit_episode_chunks_handler, '_episode_complete')
  def test_record_online_evaluation_no_write(self,
                                             get_episode_steps_return_value,
                                             episode_complete, episode_score,
                                             get_episode_steps_type):
    episode_complete.return_value = True
    episode_score.return_value = 1
    get_episode_steps_type.return_value = get_episode_steps_return_value

    mock_ds = mock.Mock()
    chunk = self._chunks()[0]
    episode_resource_id = resource_id.FalkenResourceId(
        'projects/p0/brains/b0/sessions/s0/episodes/ep0')
    _ = submit_episode_chunks_handler._record_online_evaluation(
        mock_ds, chunk, episode_resource_id)
    episode_complete.called_once_with(chunk)
    episode_score.called_once_with(chunk)
    get_episode_steps_type.called_once_with(mock_ds, chunk, episode_resource_id)
    mock_ds.write_online_evaluation.assert_not_called()

  @parameterized.named_parameters(('success', episode_pb2.SUCCESS),
                                  ('failure', episode_pb2.FAILURE),
                                  ('gave_up', episode_pb2.GAVE_UP))
  def test_episode_complete(self, state):
    self.assertTrue(
        submit_episode_chunks_handler._episode_complete(
            data_store_pb2.EpisodeChunk(
                data=episode_pb2.EpisodeChunk(episode_state=state))))

  @parameterized.named_parameters(('in_progress', episode_pb2.IN_PROGRESS),
                                  ('unspecified', episode_pb2.UNSPECIFIED),
                                  ('aborted', episode_pb2.ABORTED))
  def test_episode_incomplete(self, state):
    self.assertFalse(
        submit_episode_chunks_handler._episode_complete(
            data_store_pb2.EpisodeChunk(
                data=episode_pb2.EpisodeChunk(episode_state=state))))

  def test_episode_complete_unsupported(self):
    with self.assertRaisesWithLiteralMatch(
        ValueError, 'Unsupported episode state 8 in episode ep0 chunk 0.'):
      submit_episode_chunks_handler._episode_complete(
          data_store_pb2.EpisodeChunk(
              data=episode_pb2.EpisodeChunk(episode_state=8),
              chunk_id=0,
              episode_id='ep0'))

  @parameterized.named_parameters(
      ('success', episode_pb2.SUCCESS, model_selector.EPISODE_SCORE_SUCCESS),
      ('failure', episode_pb2.FAILURE, model_selector.EPISODE_SCORE_FAILURE),
      ('gave_up', episode_pb2.GAVE_UP, model_selector.EPISODE_SCORE_FAILURE))
  def test_episode_score(self, state, expected_score):
    self.assertEqual(
        submit_episode_chunks_handler._episode_score(
            data_store_pb2.EpisodeChunk(
                data=episode_pb2.EpisodeChunk(episode_state=state))),
        expected_score)

  @parameterized.named_parameters(('unspecified', episode_pb2.UNSPECIFIED),
                                  ('in_progress', episode_pb2.IN_PROGRESS),
                                  ('aborted', episode_pb2.ABORTED))
  def test_episode_score_incomplete(self, state):
    with self.assertRaisesWithLiteralMatch(
        ValueError, 'Incomplete episode ep0 chunk 0 can\'t be scored.'):
      submit_episode_chunks_handler._episode_score(
          data_store_pb2.EpisodeChunk(
              data=episode_pb2.EpisodeChunk(episode_state=state),
              episode_id='ep0',
              chunk_id=0))

  @parameterized.named_parameters(
      ('used_in_inference', data_store_pb2.MIXED, {'m0'}),
      ('not_used_in_inference', data_store_pb2.ONLY_DEMONSTRATIONS, set()))
  def test_get_episode_steps_type_chunk_id_0(self, steps_type, expected_models):
    mock_ds = mock.Mock()
    chunk = self._data_store_chunk()
    chunk.steps_type = steps_type
    self.assertEqual(
        submit_episode_chunks_handler._get_episode_steps_type(
            mock_ds, chunk, mock.Mock()), (steps_type, expected_models))

  @mock.patch.object(submit_episode_chunks_handler, '_merge_steps_types')
  def test_get_episode_steps_type(self, merge_steps_types):
    mock_ds = mock.Mock()
    mock_ds.list_episode_chunks.return_value = ([0, 1], None)
    mock_ds.read_episode_chunk.side_effect = [
        data_store_pb2.EpisodeChunk(
            chunk_id=0,
            data=episode_pb2.EpisodeChunk(model_id='m0', chunk_id=0),
            steps_type=data_store_pb2.ONLY_INFERENCES),
        data_store_pb2.EpisodeChunk(
            chunk_id=1,
            data=episode_pb2.EpisodeChunk(model_id='m1', chunk_id=1),
            steps_type=data_store_pb2.ONLY_INFERENCES)
    ]
    merge_steps_types.return_value = data_store_pb2.ONLY_INFERENCES
    chunk = data_store_pb2.EpisodeChunk(
        chunk_id=2,
        data=episode_pb2.EpisodeChunk(model_id='m2', chunk_id=2),
        steps_type=data_store_pb2.ONLY_INFERENCES)
    episode_resource_id = resource_id.FalkenResourceId(
        'projects/p0/brains/b0/sessions/s0/episodes/ep0')

    self.assertEqual(
        submit_episode_chunks_handler._get_episode_steps_type(
            mock_ds, chunk, episode_resource_id),
        (merge_steps_types.return_value, {'m2', 'm0', 'm1'}))

    mock_ds.list_episode_chunks.assert_called_once_with('p0', 'b0', 's0', 'ep0')
    mock_ds.read_episode_chunk.assert_has_calls([
        mock.call('p0', 'b0', 's0', 'ep0', 0),
        mock.call('p0', 'b0', 's0', 'ep0', 1)
    ])
    merge_steps_types.assert_has_calls([
        mock.call(data_store_pb2.UNKNOWN, data_store_pb2.ONLY_INFERENCES),
        mock.call(data_store_pb2.ONLY_INFERENCES,
                  data_store_pb2.ONLY_INFERENCES)
    ])

  @mock.patch.object(submit_episode_chunks_handler, '_merge_steps_types')
  def test_get_episode_steps_type_count_mismatch(self, merge_steps_types):
    mock_ds = mock.Mock()
    mock_ds.list_episode_chunks.return_value = ([0], None)
    mock_ds.read_episode_chunk.side_effect = [
        data_store_pb2.EpisodeChunk(
            chunk_id=0,
            data=episode_pb2.EpisodeChunk(model_id='m0', chunk_id=0),
            steps_type=data_store_pb2.ONLY_INFERENCES),
    ]
    merge_steps_types.return_value = data_store_pb2.ONLY_INFERENCES
    chunk = data_store_pb2.EpisodeChunk(
        chunk_id=2,
        data=episode_pb2.EpisodeChunk(model_id='m2', chunk_id=2),
        steps_type=data_store_pb2.ONLY_INFERENCES)
    episode_resource_id = resource_id.FalkenResourceId(
        'projects/p0/brains/b0/sessions/s0/episodes/ep0')

    with self.assertRaisesWithLiteralMatch(
        FileNotFoundError,
        'Did not find all previous chunks for chunk id 2, only got 1 chunks.'):
      submit_episode_chunks_handler._get_episode_steps_type(
          mock_ds, chunk, episode_resource_id)

    mock_ds.list_episode_chunks.assert_called_once_with('p0', 'b0', 's0', 'ep0')
    mock_ds.read_episode_chunk.assert_called_once_with('p0', 'b0', 's0', 'ep0',
                                                       0)
    merge_steps_types.assert_called_once_with(data_store_pb2.UNKNOWN,
                                              data_store_pb2.ONLY_INFERENCES)

  merge_step_map = {
      data_store_pb2.UNKNOWN: {
          data_store_pb2.UNKNOWN:
              data_store_pb2.UNKNOWN,
          data_store_pb2.ONLY_DEMONSTRATIONS:
              data_store_pb2.ONLY_DEMONSTRATIONS,
          data_store_pb2.ONLY_INFERENCES:
              data_store_pb2.ONLY_INFERENCES,
          data_store_pb2.MIXED:
              data_store_pb2.MIXED
      },
      data_store_pb2.ONLY_DEMONSTRATIONS: {
          data_store_pb2.UNKNOWN:
              data_store_pb2.ONLY_DEMONSTRATIONS,
          data_store_pb2.ONLY_DEMONSTRATIONS:
              data_store_pb2.ONLY_DEMONSTRATIONS,
          data_store_pb2.ONLY_INFERENCES:
              data_store_pb2.MIXED,
          data_store_pb2.MIXED:
              data_store_pb2.MIXED
      },
      data_store_pb2.ONLY_INFERENCES: {
          data_store_pb2.UNKNOWN: data_store_pb2.ONLY_INFERENCES,
          data_store_pb2.ONLY_DEMONSTRATIONS: data_store_pb2.MIXED,
          data_store_pb2.ONLY_INFERENCES: data_store_pb2.ONLY_INFERENCES,
          data_store_pb2.MIXED: data_store_pb2.MIXED
      },
      data_store_pb2.MIXED: {
          data_store_pb2.UNKNOWN: data_store_pb2.MIXED,
          data_store_pb2.ONLY_DEMONSTRATIONS: data_store_pb2.MIXED,
          data_store_pb2.ONLY_INFERENCES: data_store_pb2.MIXED,
          data_store_pb2.MIXED: data_store_pb2.MIXED
      }
  }

  @parameterized.product(
      type_left=[
          data_store_pb2.UNKNOWN, data_store_pb2.ONLY_DEMONSTRATIONS,
          data_store_pb2.ONLY_INFERENCES, data_store_pb2.MIXED
      ],
      type_right=[
          data_store_pb2.UNKNOWN, data_store_pb2.ONLY_DEMONSTRATIONS,
          data_store_pb2.ONLY_INFERENCES, data_store_pb2.MIXED
      ])
  def test_merge_steps_types(self, type_left, type_right):
    self.assertEqual(
        submit_episode_chunks_handler._merge_steps_types(type_left, type_right),
        SubmitEpisodeChunksHandlerTest.merge_step_map[type_left][type_right])


if __name__ == '__main__':
  absltest.main()