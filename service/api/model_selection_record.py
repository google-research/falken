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
"""Contains classes that contains records for model selection."""
import collections
import typing


class EvaluationSummary(typing.NamedTuple):
  """Contains results of evaluations for a model ID."""
  model_id: str
  offline_scores: typing.Dict[int, float]
  online_scores: typing.List[float]


class AssignmentEvalId(typing.NamedTuple):
  assignment_id: str
  offline_evaluation_id: int


class ModelScore(typing.NamedTuple):
  model_id: str
  score: float


class ModelScores:
  """Tracks a set of offline evaluation scores."""

  def __init__(self):
    self._model_scores = []

  def add_score(self, model_id: str, score: float):
    """Adds a score for a model ID in the ModelScores object.

    Only add the score to the list if the score is better (smaller) than the
    worst score on the list.

    Args:
      model_id: Model ID corresponding the offline evaluation.
      score: Score corresponding the offline evaluation.
    """
    if self._model_scores and score >= self._model_scores[-1].score:
      return
    self._model_scores.append(ModelScore(model_id, score))
    self._model_scores.sort(key=lambda model_score: model_score.score)

  def remove_score(self, model_score):
    """Removes the specified model_score from its model scores."""
    self._model_scores.remove(model_score)

  @property
  def model_scores(self):
    """List of ModelScores by sorted by ascending score."""
    return self._model_scores

  @property
  def model_ids(self):
    """Returns the set of model IDs stored in this object."""
    return set([model_score.model_id for model_score in self._model_scores])


class OfflineEvaluationByAssignmentAndEvalId(collections.defaultdict):
  """Maps ModelScores by key AssignmentEvalId in a defaultdict."""

  def __init__(self, *args):
    super().__init__(ModelScores, *args)

  def __copy__(self):
    return type(self)(self.items())

  def scores_by_offline_evaluation_id(
      self,
      assignment_id: typing.Optional[str] = None,
      models_limit: typing.Optional[int] = None):
    """Returns a list of eval_id to ModelScore ordered by eval ID and score.

    Args:
      assignment_id: Optional assignment ID of the scores that need to be
        returned. Used to filter the items in the dictionary.
      models_limit: Optional number to limit to the results to a certain number
        of unique models.

    Returns:
      List of (offline_evaluation_id, ModelScore) ordered by descending
        offline evaluation ID and ascending score in ModelScore.
    """
    # Filter by assignment ID and order by descending evaluation ID.
    scores_ordered_by_eval = sorted([
        item for item in self.items()
        if not assignment_id or item[0].assignment_id == assignment_id
    ],
                                    key=lambda x: x[0].offline_evaluation_id,
                                    reverse=True)

    # Flatten into a list.
    result = []
    model_ids_added = set()
    for (_, eval_id), model_record in scores_ordered_by_eval:
      if models_limit and len(model_ids_added) >= models_limit:
        break
      for model_score in model_record.model_scores:
        result.append((eval_id, model_score))
        model_ids_added.add(model_score.model_id)
    return result

  def model_ids_for_assignment_id(self, assignment_id: str):
    """Returns a set of model IDs for an assignment ID."""
    model_id_set = set()
    for assignment_and_eval_id, model_scores in self.items():
      if assignment_and_eval_id.assignment_id == assignment_id:
        model_id_set.update(model_scores.model_ids)
    return model_id_set

  def remove_score(self, assignment_id, eval_id, model_score):
    """Remove a ModelScore for an assignment ID and evaluation ID."""
    self[(assignment_id, eval_id)].remove_score(model_score)
    if not self[(assignment_id, eval_id)].model_scores:
      self.pop((assignment_id, eval_id))

  @property
  def assignment_ids(self):
    """Returns assignment IDs in the keys of this dictionary."""
    return set([key.assignment_id for key in self.keys()])


class SummaryMap(collections.defaultdict):
  """Maps assignment IDs to list of EvalutionSummary."""

  def __init__(self, *args):
    super().__init__(list, *args)

  def eval_summary_for_assignment_and_model(self, assignment_id: str,
                                            model_id: str) -> EvaluationSummary:
    """Returns a single EvaluationSummary for an assignment and model ID."""
    items_for_assignment_id = self[assignment_id]
    matching_model_id = [
        item for item in items_for_assignment_id if item.model_id == model_id
    ]
    if not matching_model_id:
      return None
    if len(matching_model_id) != 1:
      raise ValueError(
          'Expected exactly one evaluation summary for an assignment and '
          f'model pair, found {len(matching_model_id)}.')
    return matching_model_id[0]

  @property
  def models_count(self):
    return sum(len(eval_summaries) for eval_summaries in self.values())
