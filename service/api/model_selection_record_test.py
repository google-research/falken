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
"""Tests for model_selection_record."""

from absl.testing import absltest

from api import model_selection_record


class ModelScoresTest(absltest.TestCase):

  def test_model_scores_sorted_by_score(self):
    scores = model_selection_record.ModelScores()
    scores.add_score('model_id_0', 20.0)
    scores.add_score('model_id_1', 0.2)
    scores.add_score('model_id_2', -0.2)
    scores.add_score('model_id_3', 30.0)
    self.assertEqual(scores,
                     [model_selection_record.ModelScore('model_id_2', -0.2),
                      model_selection_record.ModelScore('model_id_1', 0.2),
                      model_selection_record.ModelScore('model_id_0', 20.0),
                      model_selection_record.ModelScore('model_id_3', 30.0)])

  def test_model_ids(self):
    scores = model_selection_record.ModelScores()
    scores.add_score('model_id_0', 20.0)
    scores.add_score('model_id_1', 0.2)
    scores.add_score('model_id_2', -0.2)
    scores.add_score('model_id_2', 0.9)
    self.assertEqual(scores.model_ids,
                     set(['model_id_0', 'model_id_1', 'model_id_2']))

  def test_remove_model(self):
    scores = model_selection_record.ModelScores()
    scores.add_score('model_id_0', 20.0)
    scores.add_score('model_id_1', 0.2)
    scores.remove_model('model_id_0')
    self.assertEqual(scores,
                     [model_selection_record.ModelScore('model_id_1', 0.2)])


class OfflineEvaluationByAssignmentAndEvalIdTest(absltest.TestCase):

  def test_scores_by_offline_evaluation_id(self):
    scores = model_selection_record.OfflineEvaluationByAssignmentAndEvalId()
    scores[model_selection_record.AssignmentEvalId('a0', 0)].add_score(
        'model_id_0', 0.8)
    scores[model_selection_record.AssignmentEvalId('a0', 1)].add_score(
        'model_id_1', -76.0)
    scores[model_selection_record.AssignmentEvalId('a2', 2)].add_score(
        'model_id_2', -0.2)
    scores[model_selection_record.AssignmentEvalId('a2', 0)].add_score(
        'model_id_3', -30)
    scores[model_selection_record.AssignmentEvalId('a2', 1)].add_score(
        'model_id_3', -0.2)
    scores[model_selection_record.AssignmentEvalId('a2', 0)].add_score(
        'model_id_4', 1.0)
    scores[model_selection_record.AssignmentEvalId('a2', 0)].add_score(
        'model_id_5', 1.5)
    self.assertSequenceEqual(
        scores.scores_by_offline_evaluation_id('a0'),
        [(1, model_selection_record.ModelScore(model_id='model_id_1',
                                               score=-76.0)),
         (0, model_selection_record.ModelScore(model_id='model_id_0',
                                               score=0.8))])
    self.assertSequenceEqual(
        scores.scores_by_offline_evaluation_id('a2'),
        [(2, model_selection_record.ModelScore(model_id='model_id_2',
                                               score=-0.2)),
         (1, model_selection_record.ModelScore(model_id='model_id_3',
                                               score=-0.2)),
         (0, model_selection_record.ModelScore(model_id='model_id_4',
                                               score=1.0)),
         (0, model_selection_record.ModelScore(model_id='model_id_5',
                                               score=1.5))])

    # Limit number of model IDs.
    self.assertSequenceEqual(
        scores.scores_by_offline_evaluation_id('a2', 2),
        [(2, model_selection_record.ModelScore(model_id='model_id_2',
                                               score=-0.2)),
         (1, model_selection_record.ModelScore(model_id='model_id_3',
                                               score=-0.2))])

  def test_model_ids_for_assignment_id(self):
    scores = model_selection_record.OfflineEvaluationByAssignmentAndEvalId()
    scores[model_selection_record.AssignmentEvalId('a0', 0)].add_score(
        'model_id_0', 0.8)
    scores[model_selection_record.AssignmentEvalId('a0', 0)].add_score(
        'model_id_1', -76.0)
    scores[model_selection_record.AssignmentEvalId('a2', 1)].add_score(
        'model_id_2', -22.0)
    scores[model_selection_record.AssignmentEvalId('a2', 1)].add_score(
        'model_id_3', -0.2)
    self.assertEqual(
        scores.model_ids_for_assignment_id('a0'),
        set(['model_id_0', 'model_id_1']))

  def test_assignment_ids(self):
    scores = model_selection_record.OfflineEvaluationByAssignmentAndEvalId()
    scores[model_selection_record.AssignmentEvalId('a0', 0)].add_score(
        'model_id_0', 0.8)
    scores[model_selection_record.AssignmentEvalId('a0', 0)].add_score(
        'model_id_1', -76.0)
    scores[model_selection_record.AssignmentEvalId('a2', 1)].add_score(
        'model_id_2', -22.0)
    scores[model_selection_record.AssignmentEvalId('a2', 1)].add_score(
        'model_id_3', -0.2)
    self.assertEqual(scores.assignment_ids, set(['a0', 'a2']))

  def test_remove_model(self):
    scores = model_selection_record.OfflineEvaluationByAssignmentAndEvalId()
    scores[model_selection_record.AssignmentEvalId('a0', 0)].add_score(
        'model_id_0', 0.8)
    scores[model_selection_record.AssignmentEvalId('a0', 0)].add_score(
        'model_id_1', -76.0)
    scores[model_selection_record.AssignmentEvalId('a1', 1)].add_score(
        'model_id_1', -42.0)
    scores.remove_model('model_id_1')

    expected = model_selection_record.OfflineEvaluationByAssignmentAndEvalId()
    expected[model_selection_record.AssignmentEvalId('a0', 0)].add_score(
        'model_id_0', 0.8)
    self.assertDictEqual(scores, expected)

    scores.remove_model('model_id_0')
    self.assertEmpty(scores)


class SummaryMapTest(absltest.TestCase):

  def test_eval_summary_for_assignment_and_model(self):
    summary_map = model_selection_record.SummaryMap()
    summary_map['a0'].append(
        model_selection_record.EvaluationSummary(
            model_id='m0', offline_scores={1: -6.0}, online_scores=[1.0, -1.0]))
    summary_map['a0'].append(
        model_selection_record.EvaluationSummary(
            model_id='m1', offline_scores={1: -22.0}, online_scores=[1.0]))
    summary_map['a0'].append(
        model_selection_record.EvaluationSummary(
            model_id='m2', offline_scores={0: -6.0}, online_scores=[-1.0]))
    summary_map['a1'].append(
        model_selection_record.EvaluationSummary(
            model_id='m3', offline_scores={0: -6.0}, online_scores=[-1.0]))
    self.assertEqual(summary_map.models_count, 4)
    self.assertEqual(
        summary_map.eval_summary_for_assignment_and_model('a0', 'm1'),
        model_selection_record.EvaluationSummary(
            model_id='m1', offline_scores={1: -22.0}, online_scores=[1.0]))
    self.assertIsNone(summary_map.eval_summary_for_assignment_and_model(
        'a2', 'm1'))

if __name__ == '__main__':
  absltest.main()
