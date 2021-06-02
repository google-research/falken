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
"""Tests for model_selector."""
import collections
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized

from api import data_cache
from api import model_selection_record
from api import model_selector
from api.sampling import online_eval_sampling

import common.generate_protos  # pylint: disable=unused-import

# pylint: disable=g-bad-import-order
import session_pb2
import data_store_pb2

from data_store import resource_id


class ModelSelectorTest(parameterized.TestCase):

  offline_summary = (
      model_selection_record.OfflineEvaluationByAssignmentAndEvalId())
  offline_summary[model_selection_record.AssignmentEvalId('a1', 0)].add_score(
      'm1', 0.4)
  offline_summary[model_selection_record.AssignmentEvalId('a1', 1)].add_score(
      'm1', 0.1)
  offline_summary[model_selection_record.AssignmentEvalId('a1', 2)].add_score(
      'm1', -0.2)
  offline_summary[model_selection_record.AssignmentEvalId('a1', 3)].add_score(
      'm1', 0.8)
  offline_summary[model_selection_record.AssignmentEvalId('a2', 0)].add_score(
      'm2', 0.3)
  offline_summary[model_selection_record.AssignmentEvalId('a2', 1)].add_score(
      'm2', -0.5)
  offline_summary[model_selection_record.AssignmentEvalId('a1', 0)].add_score(
      'm3', -4.0)

  online_summary = collections.defaultdict(list, {
      'm1': [-1.0, -1.0],
      'm2': [1.0],
      'm3': [-1.0, 1.0]
  })

  summary_map = model_selection_record.SummaryMap({
      'a2': [
          model_selection_record.EvaluationSummary(
              model_id='m2',
              offline_scores={
                  1: -0.5,
                  0: 0.3
              },
              online_scores=online_summary['m2'])
      ],
      'a1': [
          model_selection_record.EvaluationSummary(
              model_id='m1',
              offline_scores={
                  3: 0.8,
                  2: -0.2,
                  1: 0.1,
                  0: 0.4
              },
              online_scores=online_summary['m1']),
          model_selection_record.EvaluationSummary(
              model_id='m3',
              offline_scores={0: -4.0},
              online_scores=online_summary['m3'])
      ]
  })

  def setUp(self):
    super().setUp()
    self._ds = mock.Mock()
    self._session_resource_id = resource_id.FalkenResourceId(
        project='p0', brain='b0', session='s0')
    self._model_selector = model_selector.ModelSelector(
        data_store=self._ds, session_resource_id=self._session_resource_id)

  @parameterized.named_parameters(
      ('interactive_training', session_pb2.INTERACTIVE_TRAINING),
      ('evaluation', session_pb2.EVALUATION),
      ('inference', session_pb2.INFERENCE))
  @mock.patch.object(data_cache, 'get_session_type')
  @mock.patch.object(model_selector.ModelSelector, '_is_session_training')
  @mock.patch.object(model_selector.ModelSelector, '_is_eval_complete')
  def test_get_training_state_completed(
      self, session_type, is_eval_complete, is_session_training,
      get_session_type):
    is_session_training.return_value = False
    is_eval_complete.return_value = True
    get_session_type.return_value = session_type

    self.assertEqual(
        self._model_selector.get_training_state(),
        session_pb2.SessionInfo.COMPLETED)

    if session_type == session_pb2.INTERACTIVE_TRAINING:
      is_session_training.assert_called_once()
    if session_type == session_pb2.EVALUATION:
      is_eval_complete.assert_called_once()
    get_session_type.assert_called_once_with(
        self._ds, project_id='p0', brain_id='b0', session_id='s0')

  @parameterized.named_parameters(
      ('interactive_training', session_pb2.INTERACTIVE_TRAINING),
      ('evaluation', session_pb2.EVALUATION))
  @mock.patch.object(data_cache, 'get_session_type')
  @mock.patch.object(model_selector.ModelSelector, '_is_session_training')
  @mock.patch.object(model_selector.ModelSelector, '_is_eval_complete')
  def test_get_training_state_training(
      self, session_type, is_eval_complete, is_session_training,
      get_session_type):
    is_session_training.return_value = True
    is_eval_complete.return_value = False
    get_session_type.return_value = session_type

    self.assertEqual(
        self._model_selector.get_training_state(),
        session_pb2.SessionInfo.TRAINING)

    if session_type == session_pb2.INTERACTIVE_TRAINING:
      is_session_training.assert_called_once()
    if session_type == session_pb2.EVALUATION:
      is_eval_complete.assert_called_once()
    get_session_type.assert_called_once_with(
        self._ds, project_id='p0', brain_id='b0', session_id='s0')

  @mock.patch.object(data_cache, 'get_session_type')
  def test_get_training_state_invalid_session_type(self, get_session_type):
    get_session_type.return_value = 20

    with self.assertRaisesWithLiteralMatch(
        ValueError, 'Unsupported session type: 20 in session projects/p0/brains'
        '/b0/sessions/s0.'):
      self._model_selector.get_training_state()

    get_session_type.assert_called_once_with(
        self._ds, project_id='p0', brain_id='b0', session_id='s0')

  def test_is_session_training(self):
    self._ds.calculate_assignment_progress.return_value = (
        {'a0': 1.0, 'a1': 1.0, 'a2': 0.0})
    # Call twice.
    self.assertTrue(self._model_selector._is_session_training())
    self.assertTrue(self._model_selector._is_session_training())
    # Assert calculate_assignment_progress was only called once.
    self._ds.calculate_assignment_progress.assert_called_once()

  def test_is_session_training_complete(self):
    self._ds.calculate_assignment_progress.return_value = (
        {'a0': 1.0, 'a1': 1.0, 'a2': 1.0})
    self.assertFalse(self._model_selector._is_session_training())

  @parameterized.named_parameters(
      ('true', 12, True),  # 12 >= _NUM_ONLINE_EVALS_PER_MODEL * 2
      ('false', 1, False))  # 1 < _NUM_ONLINE_EVALS_PER_MODEL * 2
  @mock.patch.object(model_selector.ModelSelector, '_create_model_records')
  @mock.patch.object(model_selector.ModelSelector, '_get_summary_map')
  def test_is_eval_complete(
      self, total_runs, complete, get_summary_map, create_model_records):
    get_summary_map.return_value = ModelSelectorTest.summary_map
    create_model_records.return_value = (total_runs, None, None)
    self.assertEqual(self._model_selector._is_eval_complete(), complete)

  @mock.patch.object(data_cache, 'get_starting_snapshot')
  @mock.patch.object(model_selector.ModelSelector, '_get_offline_eval_summary')
  @mock.patch.object(model_selector.ModelSelector, '_get_online_eval_summary')
  @mock.patch.object(model_selector.ModelSelector, '_generate_summary_map')
  def test_get_summary_map(
      self, get_assignment_summaries, get_online_eval_summary,
      get_offline_eval_summary, get_starting_snapshot):
    get_starting_snapshot.return_value = mock.Mock()
    get_offline_eval_summary.return_value = mock.Mock()
    get_online_eval_summary.return_value = mock.Mock()
    get_assignment_summaries.return_value = mock.Mock()
    self._ds.read.return_value = data_store_pb2.Session(
        project_id='p0', brain_id='b0', session_id='s0')
    # Snapshot session resource ID.
    self._ds.resource_id_from_proto_ids.return_value = (
        resource_id.FalkenResourceId('projects/p1/brains/b1/sessions/s1'))
    self._model_selector = model_selector.ModelSelector(
        data_store=self._ds, session_resource_id=self._session_resource_id)

    self.assertEqual(self._model_selector._get_summary_map(),
                     get_assignment_summaries.return_value)
    get_starting_snapshot.assert_called_once_with(self._ds, 'p0', 'b0', 's0')
    self._ds.resource_id_from_proto_ids.assert_called_once_with(
        project_id=get_starting_snapshot.return_value.project_id,
        brain_id=get_starting_snapshot.return_value.brain_id,
        session_id=get_starting_snapshot.return_value.session)
    get_online_eval_summary.assert_called_once_with()
    get_offline_eval_summary.assert_called_once_with(
        self._ds.resource_id_from_proto_ids.return_value)
    get_assignment_summaries.assert_called_once_with(
        get_offline_eval_summary.return_value,
        get_online_eval_summary.return_value)

  @mock.patch.object(data_cache, 'get_assignment_id')
  def test_get_offline_eval_summary(self, get_assignment_id):
    self._ds.list_by_proto_ids.side_effect = [
        ([
            resource_id.FalkenResourceId(
                'projects/p1/brains/b1/sessions/s1/models/m1/'
                'offline_evaluations/1'),
            resource_id.FalkenResourceId(
                'projects/p1/brains/b1/sessions/s1/models/m1/'
                'offline_evaluations/0'),
            resource_id.FalkenResourceId(
                'projects/p1/brains/b1/sessions/s1/models/m0/'
                'offline_evaluations/2'),
            resource_id.FalkenResourceId(
                'projects/p1/brains/b1/sessions/s1/models/m0/'
                'offline_evaluations/2'),
            resource_id.FalkenResourceId(
                'projects/p1/brains/b1/sessions/s1/models/m0/'
                'offline_evaluations/3')
        ], None),
        ([
            resource_id.FalkenResourceId(
                'projects/p1/brains/b1/sessions/s1/assignments/a1'),
            resource_id.FalkenResourceId(
                'projects/p1/brains/b1/sessions/s1/assignments/a2'),
            resource_id.FalkenResourceId(
                'projects/p1/brains/b1/sessions/s1/assignments/a3')
        ], None)
    ]
    self._ds.read.side_effect = [
        data_store_pb2.OfflineEvaluation(
            offline_evaluation_id=1, score=0.8, model_id='m1',
            assignment='a1'),
        data_store_pb2.OfflineEvaluation(
            offline_evaluation_id=0, score=-0.2, model_id='m1',
            assignment='a2'),
        data_store_pb2.OfflineEvaluation(
            offline_evaluation_id=2, score=0.7, model_id='m0',
            assignment='a2'),
        data_store_pb2.OfflineEvaluation(
            offline_evaluation_id=2, score=0.8, model_id='m0',
            assignment='a2'),  # Gets ignored because 0.8 < 0.7
        data_store_pb2.OfflineEvaluation(
            offline_evaluation_id=3, score=0.7, model_id='m0',
            assignment='a3'),
    ]
    get_assignment_id.side_effect = ['a1', 'a2', 'a3']
    starting_snapshot = data_store_pb2.Snapshot(
        project_id='p1', brain_id='b1', session='s1', snapshot_id='ss0')
    session_resource_id = resource_id.FalkenResourceId(
        f'projects/{starting_snapshot.project_id}/brains/'
        f'{starting_snapshot.brain_id}/sessions/{starting_snapshot.session}')
    summary = self._model_selector._get_offline_eval_summary(
        session_resource_id)
    key_1 = model_selection_record.AssignmentEvalId('a1', 1)
    key_2 = model_selection_record.AssignmentEvalId('a2', 2)
    key_3 = model_selection_record.AssignmentEvalId('a2', 0)
    key_4 = model_selection_record.AssignmentEvalId('a3', 3)
    self.assertSameElements(summary.keys(), [key_1, key_2, key_3, key_4])
    self.assertSameElements(
        [value._model_scores[0].model_id for value in summary.values()],
        ['m1', 'm0', 'm1', 'm0'])
    self.assertLen(summary[key_1]._model_scores, 1)
    self.assertAlmostEqual(summary[key_1]._model_scores[0].score, 0.8)
    self.assertLen(summary[key_2]._model_scores, 1)
    self.assertAlmostEqual(summary[key_2]._model_scores[0].score, 0.7)
    self.assertLen(summary[key_3]._model_scores, 1)
    self.assertAlmostEqual(summary[key_3]._model_scores[0].score, -0.2)
    self.assertLen(summary[key_4]._model_scores, 1)
    self.assertAlmostEqual(summary[key_4]._model_scores[0].score, 0.7)

    self._ds.list_by_proto_ids.assert_has_calls([
        mock.call(
            project_id='p1', brain_id='b1', session_id='s1', model_id='*',
            offline_evaluation_id='*', time_descending=True),
        mock.call(
            project_id='p1', brain_id='b1', session_id='s1', assignment_id='*')
    ])
    self._ds.read.assert_has_calls([
        mock.call(
            resource_id.FalkenResourceId(
                'projects/p1/brains/b1/sessions/s1/models/m1/'
                'offline_evaluations/1')),
        mock.call(
            resource_id.FalkenResourceId(
                'projects/p1/brains/b1/sessions/s1/models/m1/'
                'offline_evaluations/0')),
        mock.call(
            resource_id.FalkenResourceId(
                'projects/p1/brains/b1/sessions/s1/models/m0/'
                'offline_evaluations/2')),
        mock.call(
            resource_id.FalkenResourceId(
                'projects/p1/brains/b1/sessions/s1/models/m0/'
                'offline_evaluations/2')),
        mock.call(
            resource_id.FalkenResourceId(
                'projects/p1/brains/b1/sessions/s1/models/m0/'
                'offline_evaluations/3'))
    ])

  @mock.patch.object(data_cache, 'get_assignment_id')
  def test_get_offline_eval_summary_assignment_not_matching(
      self, get_assignment_id):
    self._ds.list_by_proto_ids.side_effect = [
        ([
            resource_id.FalkenResourceId(
                'projects/p1/brains/b1/sessions/s1/models/m1/'
                'offline_evaluations/1'),
        ], None),
        ([
            resource_id.FalkenResourceId(
                'projects/p1/brains/b1/sessions/s1/assignments/a1'),
        ], None)
    ]
    # Reading offline eval results in different assignment from what we expect.
    self._ds.read.side_effect = [
        data_store_pb2.OfflineEvaluation(
            offline_evaluation_id=1, score=0.8, model_id='m1',
            assignment='a2')
    ]
    starting_snapshot = data_store_pb2.Snapshot(
        project_id='p1', brain_id='b1', session='s1', snapshot_id='ss0')
    get_assignment_id.return_value = 'a1'
    with self.assertRaisesWithLiteralMatch(
        ValueError,
        'Assignment ID a2 not found in assignments for session s1.'):
      self._model_selector._get_offline_eval_summary(
          resource_id.FalkenResourceId(
              f'projects/{starting_snapshot.project_id}/brains/'
              f'{starting_snapshot.brain_id}/sessions/'
              f'{starting_snapshot.session}'))

  def test_get_online_eval_summary(self):
    self._ds.list_by_proto_ids.return_value = (
        ['projects/p0/brains/b0/sessions/s0/episode/e0/online_evaluation',
         'projects/p0/brains/b0/sessions/s0/episode/e1/online_evaluation',
         'projects/p0/brains/b0/sessions/s0/episode/e2/online_evaluation'],
        None)
    self._ds.read.side_effect = [
        data_store_pb2.OnlineEvaluation(model='m1', score=-1.0),
        data_store_pb2.OnlineEvaluation(model='m2', score=1.0),
        data_store_pb2.OnlineEvaluation(model='m1', score=-1.0)
    ]

    self.assertEqual(self._model_selector._get_online_eval_summary(),
                     {'m1': [-1.0, -1.0], 'm2': [1.0]})
    self._ds.list_by_proto_ids.assert_called_once_with(
        attribute_type=data_store_pb2.OnlineEvaluation,
        project_id='p0', brain_id='b0', session_id='s0', episode_id='*')

  def test_generate_summary_map(self):
    self.assertEqual(
        self._model_selector._generate_summary_map(
            ModelSelectorTest.offline_summary,
            ModelSelectorTest.online_summary), ModelSelectorTest.summary_map)

  def test_generate_summary_map_plenty_of_models(self):
    offline_summary = (
        model_selection_record.OfflineEvaluationByAssignmentAndEvalId())
    # One model per assignment.
    offline_summary[model_selection_record.AssignmentEvalId('a0', 0)].add_score(
        'm1', 0.4)
    offline_summary[model_selection_record.AssignmentEvalId('a0', 1)].add_score(
        'm1', -64.0)
    offline_summary[model_selection_record.AssignmentEvalId('a1', 0)].add_score(
        'm2', 0.4)
    offline_summary[model_selection_record.AssignmentEvalId('a1', 1)].add_score(
        'm2', -20.0)
    offline_summary[model_selection_record.AssignmentEvalId('a2', 0)].add_score(
        'm3', 0.4)

    online_summary = collections.defaultdict(list, {
        'm1': [-1.0, -1.0],
        'm2': [1.0],
        'm3': [-1.0, 1.0]
    })

    summary_map = model_selection_record.SummaryMap({
        'a2': [
            model_selection_record.EvaluationSummary(
                model_id='m3',
                offline_scores={0: 0.4},
                online_scores=[-1.0, 1.0])
        ],
        'a1': [
            model_selection_record.EvaluationSummary(
                model_id='m2',
                offline_scores={
                    1: -20.0,
                    0: 0.4
                },
                online_scores=[1.0])
        ],
        'a0': [
            model_selection_record.EvaluationSummary(
                model_id='m1',
                offline_scores={
                    1: -64.0,
                    0: 0.4
                },
                online_scores=[-1.0, -1.0])
        ]
    })
    self.assertEqual(
        self._model_selector._generate_summary_map(offline_summary,
                                                   online_summary), summary_map)

  def test_generate_summary_map_empty(self):
    self.assertEqual(
        self._model_selector._generate_summary_map(
            model_selection_record.OfflineEvaluationByAssignmentAndEvalId(),
            collections.defaultdict(list)), model_selection_record.SummaryMap())

  def test_add_summary(self):
    summary_map = model_selection_record.SummaryMap()
    self._model_selector._add_summary(
        'a0', 0, model_selection_record.ModelScore(model_id='m0', score=0.8),
        [1.0, -1.0], summary_map)
    self.assertSameElements(summary_map['a0'], [
        model_selection_record.EvaluationSummary(
            model_id='m0', offline_scores={0: 0.8}, online_scores=[1.0, -1.0])
    ])

  def test_add_summary_existing(self):
    summary_map = model_selection_record.SummaryMap()
    existing_summary = model_selection_record.EvaluationSummary(
        model_id='m0', offline_scores={1: -6.0}, online_scores=[1.0, -1.0])
    summary_map['a0'].append(existing_summary)
    self._model_selector._add_summary(
        'a0', 0, model_selection_record.ModelScore(model_id='m0', score=0.8),
        [1.0, -1.0], summary_map)
    self.assertSameElements(summary_map['a0'], [
        model_selection_record.EvaluationSummary(
            model_id='m0',
            offline_scores={
                1: -6.0,
                0: 0.8
            },
            online_scores=[1.0, -1.0])
    ])

  @mock.patch.object(model_selector.ModelSelector, '_get_summary_map')
  def test_create_model_records(self, get_summary_map):
    get_summary_map.return_value = ModelSelectorTest.summary_map
    self.assertEqual(
        self._model_selector._create_model_records(), (5, ['m2', 'm1', 'm3'], [
            online_eval_sampling.ModelRecord(successes=1, failures=0),
            online_eval_sampling.ModelRecord(successes=0, failures=2),
            online_eval_sampling.ModelRecord(successes=1, failures=1),
        ]))
    get_summary_map.assert_called_once_with()

  @parameterized.named_parameters(
      ('interactive_training', session_pb2.INTERACTIVE_TRAINING),
      ('evaluation', session_pb2.EVALUATION),
      ('inference', session_pb2.INFERENCE))
  @mock.patch.object(model_selector.ModelSelector, '_get_session_type')
  @mock.patch.object(model_selector.ModelSelector,
                     '_best_offline_or_starting_snapshot_model')
  @mock.patch.object(model_selector.ModelSelector, '_next_online_eval_model')
  @mock.patch.object(model_selector.ModelSelector, 'select_final_model')
  def test_select_next_model(self, session_type, select_final_model,
                             next_online_eval_model,
                             best_offline_or_starting_snapshot_model,
                             get_session_type):
    get_session_type.return_value = session_type
    select_final_model.return_value = 'm0'
    next_online_eval_model.return_value = 'm0'
    best_offline_or_starting_snapshot_model.return_value = 'm0'
    self.assertEqual(self._model_selector.select_next_model(), 'm0')

  @mock.patch.object(model_selector.ModelSelector, '_get_session_type')
  def test_select_next_model_invalid_session_type(self, get_session_type):
    get_session_type.return_value = 20
    with self.assertRaisesWithLiteralMatch(
        ValueError, 'Unsupported session type: 20 found for session s0.'):
      self._model_selector.select_next_model()

  @mock.patch.object(model_selector.ModelSelector, '_next_online_eval_model')
  @mock.patch.object(model_selector.ModelSelector, '_get_session_type')
  def test_select_next_model_empty_model_returned(self, get_session_type,
                                                  next_online_eval_model):
    get_session_type.return_value = session_pb2.EVALUATION
    next_online_eval_model.return_value = ''
    with self.assertRaisesWithLiteralMatch(
        ValueError,
        'Empty model returned by online eval sampling for session s0'):
      self._model_selector.select_next_model()

  @mock.patch.object(model_selector.ModelSelector, '_best_offline_model')
  def test_best_offline_or_starting_snapshot_model(self,
                                                   best_offline_model):
    self._ds.resource_id_from_proto_ids.return_value = 'result/res_id'
    self.assertEqual(
        self._model_selector._best_offline_or_starting_snapshot_model(),
        'result/res_id')
    best_offline_model.assert_called_once_with()

  @mock.patch.object(model_selector.ModelSelector, '_best_offline_model')
  @mock.patch.object(data_cache, 'get_starting_snapshot')
  def test_best_offline_or_starting_snapshot_model_starting_snapshot(
      self, get_starting_snapshot, best_offline_model):
    best_offline_model.side_effect = FileNotFoundError()
    get_starting_snapshot.return_value = data_store_pb2.Snapshot(
        project_id='p0', brain_id='b0', snapshot_id='sn0',
        session='s0', model='m0')
    self._ds.resource_id_from_proto_ids.return_value = 'res_id'

    self.assertEqual(
        self._model_selector._best_offline_or_starting_snapshot_model(),
        'res_id')
    self._ds.resource_id_from_proto_ids.assert_called_once_with(
        project_id='p0', brain_id='b0', session_id='s0', model_id='m0')

    best_offline_model.assert_called_once_with()
    get_starting_snapshot.assert_called_once_with(
        self._ds, self._ds.read.return_value.project_id,
        self._ds.read.return_value.brain_id,
        self._ds.read.return_value.session_id)

  @mock.patch.object(model_selector.ModelSelector, '_best_offline_model')
  @mock.patch.object(data_cache, 'get_starting_snapshot')
  def test_best_offline_or_starting_snapshot_model_not_found(
      self, get_starting_snapshot, best_offline_model):
    best_offline_model.side_effect = FileNotFoundError()
    get_starting_snapshot.side_effect = FileNotFoundError()
    self.assertIsNone(
        self._model_selector._best_offline_or_starting_snapshot_model())

  @mock.patch.object(model_selector.ModelSelector, '_get_offline_eval_summary')
  def test_best_offline_model(self, get_offline_eval_summary):
    get_offline_eval_summary.return_value = ModelSelectorTest.offline_summary
    self.assertEqual(self._model_selector._best_offline_model(), 'm1')

  @mock.patch.object(model_selector.ModelSelector, '_get_offline_eval_summary')
  def test_best_offline_model_empty_summary(self, get_offline_eval_summary):
    get_offline_eval_summary.return_value = (
        model_selection_record.OfflineEvaluationByAssignmentAndEvalId())
    with self.assertRaisesWithLiteralMatch(
        FileNotFoundError, 'No offline eval found for session s0.'):
      self._model_selector._best_offline_model()

  @mock.patch.object(data_cache, 'get_starting_snapshot')
  @mock.patch.object(online_eval_sampling.UCBSampling, 'select_next')
  @mock.patch.object(model_selector.ModelSelector, '_create_model_records')
  @mock.patch.object(model_selector.ModelSelector, '_get_summary_map')
  def test_next_online_eval_model(self, get_summary_map, create_model_records,
                                  select_next, get_starting_snapshot):
    get_summary_map.return_value = ModelSelectorTest.summary_map
    get_starting_snapshot.return_value = data_store_pb2.Snapshot(
        project_id='p0', brain_id='b0', session='snapshot_sess',
        snapshot_id='s0')
    create_model_records.return_value = (1, ['m0'], [
        online_eval_sampling.ModelRecord(successes=10, failures=2)
    ])
    select_next.return_value = 0
    self._ds.resource_id_from_proto_ids.return_value = (
        'projects/p0/brains/b0/sessions/snapshot_sess/models/m0')
    self.assertEqual(self._model_selector._next_online_eval_model(),
                     'projects/p0/brains/b0/sessions/snapshot_sess/models/m0')
    self._ds.resource_id_from_proto_ids.assert_called_once_with(
        project_id='p0', brain_id='b0', session_id='snapshot_sess',
        model_id='m0')

  @mock.patch.object(model_selector.ModelSelector, '_get_summary_map')
  def test_next_online_eval_model_no_summary_map(self, get_summary_map):
    get_summary_map.return_value = model_selection_record.SummaryMap()
    with self.assertRaisesWithLiteralMatch(
        FileNotFoundError, 'No models found for evaluation session s0.'):
      self._model_selector._next_online_eval_model()

  @parameterized.named_parameters(
      ('interactive_training', session_pb2.INTERACTIVE_TRAINING),
      ('evaluation', session_pb2.EVALUATION),
      ('inference', session_pb2.INFERENCE))
  @mock.patch.object(model_selector.ModelSelector, '_get_session_type')
  @mock.patch.object(model_selector.ModelSelector, '_best_offline_model')
  @mock.patch.object(model_selector.ModelSelector, '_best_online_model')
  @mock.patch.object(data_cache, 'get_starting_snapshot')
  def test_select_final_model(self, session_type, get_starting_snapshot,
                              best_online_model, best_offline_model,
                              get_session_type):
    get_session_type.return_value = session_type
    best_online_model.return_value = 'm0'
    best_offline_model.return_value = 'm0'
    get_starting_snapshot.return_value = data_store_pb2.Snapshot(model='m0')
    if session_type != session_pb2.INTERACTIVE_TRAINING:
      self._ds.list_from_proto_ids.return_value = (
          ['fake/resource_id'], None)
    else:
      self._ds.resource_id_from_proto_ids.return_value = (
          'fake/resource_id')
    self.assertEqual(self._model_selector.select_final_model(),
                     'fake/resource_id')

    if session_type == session_pb2.INTERACTIVE_TRAINING:
      self._ds.resource_id_from_proto_ids.assert_called_once_with(
          project_id=mock.ANY, brain_id=mock.ANY, session_id=mock.ANY,
          model_id='m0')

  @mock.patch.object(model_selector.ModelSelector, '_get_session_type')
  def test_select_final_model_invalid_session_type(self, get_session_type):
    get_session_type.return_value = 20
    with self.assertRaisesWithLiteralMatch(
        ValueError, 'Unsupported session type: 20 found for session s0.'):
      self._model_selector.select_next_model()

  @mock.patch.object(online_eval_sampling.HighestAverageSelection,
                     'select_best')
  @mock.patch.object(model_selector.ModelSelector, '_create_model_records')
  @mock.patch.object(model_selector.ModelSelector, '_get_summary_map')
  def test_best_online_eval_model(self, get_summary_map, create_model_records,
                                  select_best):
    get_summary_map.return_value = ModelSelectorTest.summary_map
    create_model_records.return_value = (1, ['m0'], [
        online_eval_sampling.ModelRecord(successes=10, failures=2)
    ])
    select_best.return_value = 0
    self.assertEqual(self._model_selector._best_online_model(), 'm0')

  @mock.patch.object(model_selector.ModelSelector, '_get_summary_map')
  def test_best_online_eval_model_no_summary_map(self, get_summary_map):
    get_summary_map.return_value = model_selection_record.SummaryMap()
    with self.assertRaisesWithLiteralMatch(
        ValueError, 'No models found for session s0. Cannot compute best.'):
      self._model_selector._best_online_model()


if __name__ == '__main__':
  absltest.main()
