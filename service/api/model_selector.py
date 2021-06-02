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
"""Selects model based on evaluation score."""

import collections
import copy
import time
import typing

from absl import logging
from api import data_cache
from api import model_selection_record
from api.sampling import online_eval_sampling

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import data_store_pb2
import session_pb2

from data_store import resource_store


EPISODE_SCORE_SUCCESS = 1
EPISODE_SCORE_FAILURE = -1

# Somewhat arbitrary constants used as a stopping heuristic.
_NUM_ONLINE_EVALS_PER_MODEL = 6
_NUM_MODELS_TO_ONLINE_EVAL_PER_ASSIGNMENT = 1
_MAXIMUM_NUMBER_OF_MODELS_TO_ONLINE_EVAL = 8


class ModelSelector:
  """Selects model based on evaluation score."""

  def __init__(self, data_store, session_resource_id):
    self._data_store = data_store
    self._session_resource_id = session_resource_id
    self._summary_map = None
    self._session = self._data_store.read(self._session_resource_id)
    self._progress = None

  def get_training_state(self) -> session_pb2.SessionInfo.TrainingState:
    """Get training state of the session for this model selector.

    Returns:
      session_pb2.SessionInfo.TrainingState enum.

    Raises:
      ValueError if the session type is not supported.
    """
    session_type = self._get_session_type()
    if session_type == session_pb2.INTERACTIVE_TRAINING:
      if self._is_session_training():
        return session_pb2.SessionInfo.TRAINING
      else:
        return session_pb2.SessionInfo.COMPLETED
    elif session_type == session_pb2.INFERENCE:
      return session_pb2.SessionInfo.COMPLETED
    elif session_type == session_pb2.EVALUATION:
      if self._is_eval_complete():
        return session_pb2.SessionInfo.COMPLETED
      else:
        return session_pb2.SessionInfo.TRAINING
    else:
      raise ValueError(f'Unsupported session type: {session_type} in session '
                       f'{self._session_resource_id}.')

  def select_next_model(self):
    """Selects next model to try.

    Returns:
      resource_id.ResourceId of the model to select next.

    Raises:
      ValueError if model was not found or if requested for an unsupported
        session type.
    """
    session_type = self._get_session_type()
    if session_type == session_pb2.INTERACTIVE_TRAINING:
      model_resource_id = self._best_offline_or_starting_snapshot_model()
      logging.info('Selected model %s for training session %s.',
                   model_resource_id,
                   self._session_resource_id)
      return model_resource_id
    elif session_type == session_pb2.INFERENCE:
      model_resource_id = self.select_final_model()
      logging.info('Selected model %s for inference session %s.',
                   model_resource_id,
                   self._session_resource_id)
      return model_resource_id
    elif session_type == session_pb2.EVALUATION:
      # Fetch the next online eval model.
      model_resource_id = self._next_online_eval_model()
      if not model_resource_id:
        raise ValueError(
            'Empty model returned by online eval sampling for session '
            f'{self._session_resource_id.session}')
      logging.info('Selected model %s for evaluation session %s.',
                   model_resource_id,
                   self._session_resource_id)
      return model_resource_id
    else:
      raise ValueError(
          f'Unsupported session type: {session_type} found for session '
          f'{self._session_resource_id.session}.')

  def _best_offline_or_starting_snapshot_model(self):
    """Return best model resource ID by offline score or starting snapshot."""
    try:
      offline_model_id = self._best_offline_model()
      res_id = self._data_store.resource_id_from_proto_ids(
          project_id=self._session.project_id,
          brain_id=self._session.brain_id,
          session_id=self._session.session_id,
          model_id=offline_model_id)
      logging.info('Selected best offline model: %s', res_id)
      return res_id
    except (FileNotFoundError, ValueError):
      # If offline model is not found, try getting the snapshot model.
      try:
        snapshot = data_cache.get_starting_snapshot(self._data_store,
                                                    self._session.project_id,
                                                    self._session.brain_id,
                                                    self._session.session_id)
        res_id = self._data_store.resource_id_from_proto_ids(
            project_id=snapshot.project_id,
            brain_id=snapshot.brain_id,
            session_id=snapshot.session,
            model_id=snapshot.model)
        logging.info('Selected model from snapshot: %s.', res_id)
        return res_id
      except (FileNotFoundError, resource_store.InternalError, ValueError):
        logging.info(
            'Failed to get offline model and model from starting snapshot for '
            'session %s. Returning empty model.', self._session.session_id)
        return None

  def _best_offline_model(self):
    """Goes through offline evaluations and returns model ID with best score."""
    offline_eval_summary = self._get_offline_eval_summary(
        self._session_resource_id)
    if not offline_eval_summary:
      raise FileNotFoundError('No offline eval found for session '
                              f'{self._session_resource_id.session}.')
    return offline_eval_summary.scores_by_offline_evaluation_id()[0][1].model_id

  def _next_online_eval_model(self):
    """Selects the next model resource ID based on the online eval results."""
    if not self._get_summary_map():
      raise FileNotFoundError('No models found for evaluation session '
                              f'{self._session_resource_id.session}.')
    _, model_ids, model_records = self._create_model_records()
    sampling = online_eval_sampling.UCBSampling()
    selected_model_index = sampling.select_next(model_records)
    if selected_model_index >= len(model_ids):
      raise ValueError(
          f'Selected model index {selected_model_index} is larger than the '
          f'number of models ({len(model_ids)}) we have available.')
    if selected_model_index < 0:
      raise ValueError(
          f'Selected model index is less than 0: {selected_model_index}')
    model_id = model_ids[selected_model_index]
    snapshot = data_cache.get_starting_snapshot(self._data_store,
                                                self._session.project_id,
                                                self._session.brain_id,
                                                self._session.session_id)
    return self._data_store.resource_id_from_proto_ids(
        project_id=snapshot.project_id,
        brain_id=snapshot.brain_id,
        session_id=snapshot.session,
        model_id=model_id)

  def _lookup_model_resource_id(self, project_id, brain_id, model_id):
    """Get model resource ID based on model ID from arbitrary session."""
    res_ids, _ = self._data_store.list_by_proto_ids(
        project_id=project_id,
        brain_id=brain_id,
        session_id='*',
        model_id=model_id,
        page_size=2)
    if len(res_ids) != 1:
      raise RuntimeError(
          f'Expected one requested model with ID {model_id} in ' +
          f'projects/{project_id}/brains/{brain_id}, but found {len(res_ids)}')
    return res_ids[0]

  def select_final_model(self):
    """Select the final model ID for each session type."""
    session_type = self._get_session_type()
    if session_type == session_pb2.INTERACTIVE_TRAINING:
      model_id = self._best_offline_model()
      return self._data_store.resource_id_from_proto_ids(
          project_id=self._session.project_id,
          brain_id=self._session.brain_id,
          session_id=self._session.session_id,
          model_id=model_id)

    snapshot = data_cache.get_starting_snapshot(self._data_store,
                                                self._session.project_id,
                                                self._session.brain_id,
                                                self._session.session_id)
    if session_type == session_pb2.INFERENCE:
      return self._lookup_model_resource_id(
          snapshot.project_id,
          snapshot.brain_id,
          snapshot.model)
    elif session_type == session_pb2.EVALUATION:
      model_id = self._best_online_model()
      return self._lookup_model_resource_id(
          snapshot.project_id,
          snapshot.brain_id,
          model_id)
    else:
      raise ValueError(f'Unsupported session type: {session_type} found for '
                       'session {self._session.session_id}.')

  def _best_online_model(self):
    """Select the model ID with the best online evaluation score."""
    if not self._get_summary_map():
      raise ValueError(
          'No models found for session '
          f'{self._session_resource_id.session}. Cannot compute best.')

    _, model_ids, model_records = self._create_model_records()
    sampling = online_eval_sampling.HighestAverageSelection()
    selected_model_index = sampling.select_best(model_records)
    if selected_model_index >= len(model_ids):
      raise ValueError(
          f'Selected model index {selected_model_index} is larger than the '
          f'number of models ({len(model_ids)}) we have available.')
    if selected_model_index < 0:
      raise ValueError(
          f'Selected model index is less than 0: {selected_model_index}')
    return model_ids[selected_model_index]

  def _get_session_type(self) -> session_pb2.SessionType:
    return data_cache.get_session_type(
        self._data_store, project_id=self._session_resource_id.project,
        brain_id=self._session_resource_id.brain,
        session_id=self._session_resource_id.session)

  @property
  def session_progress(self):
    """Get this session's progress float, lazily initialized."""
    if not self._progress:
      progress_per_assignment = self._data_store.calculate_assignment_progress(
          self._session_resource_id)
      if not progress_per_assignment:
        self._progress = 0.0
      else:
        self._progress = (
            sum(progress_per_assignment.values())/len(progress_per_assignment))
    return self._progress

  def _is_session_training(self):
    return self.session_progress < 1.0

  def _is_eval_complete(self):
    """Check that the total evals count is larger than the required number.

    The required number is defined by _NUM_ONLINE_EVALS_PER_MODEL.

    Returns:
      bool: True if the required number of online evaluations have been
        completed, False otherwise.
    """
    total_online_evals, _, _ = self._create_model_records()
    summary_map = self._get_summary_map()
    return total_online_evals >= _NUM_ONLINE_EVALS_PER_MODEL * len(summary_map)

  def _get_summary_map(self) -> typing.DefaultDict[
      str, list[model_selection_record.EvaluationSummary]]:
    """Lazily initializes map of assignment IDs to list of EvaluationSummary."""
    if not self._summary_map:
      before = time.perf_counter()
      starting_snapshot = data_cache.get_starting_snapshot(
          self._data_store, self._session.project_id, self._session.brain_id,
          self._session.session_id)
      offline_eval_summary = self._get_offline_eval_summary(
          # Use starting snapshot to create a session resource ID.
          self._data_store.resource_id_from_proto_ids(
              project_id=starting_snapshot.project_id,
              brain_id=starting_snapshot.brain_id,
              session_id=starting_snapshot.session))
      online_eval_summary = self._get_online_eval_summary()
      self._summary_map = self._generate_summary_map(offline_eval_summary,
                                                     online_eval_summary)
      logging.info(
          'Generated summary map in %d seconds.', time.perf_counter() - before)
    return self._summary_map

  def _get_offline_eval_summary(
      self, session_resource_id: str
      ) -> (model_selection_record.OfflineEvaluationByAssignmentAndEvalId):
    """Populates an OfflineEvaluationByAssignmentAndEvalId from offline evals.

    Args:
      session_resource_id: Resource ID for the session to read offline eval
        from.

    Returns:
      An instance of OfflineEvaluationByAssignmentAndEvalId, which maps
        (assignment_id, offline_evaluation_id) to ModelScores.

    Raises:
      ValueError for when the provided session does not have valid
        corresponding assignments.
    """
    # Get offline evals from the session of the starting snapshot in order of
    # descending create time.
    offline_eval_resource_ids, _ = self._data_store.list_by_proto_ids(
        project_id=session_resource_id.project,
        brain_id=session_resource_id.brain,
        session_id=session_resource_id.session,
        model_id='*',
        offline_evaluation_id='*',
        time_descending=True)
    assignment_resource_ids, _ = self._data_store.list_by_proto_ids(
        project_id=session_resource_id.project,
        brain_id=session_resource_id.brain,
        session_id=session_resource_id.session,
        assignment_id='*')
    assignment_ids = set(
        [data_cache.get_assignment_id(self._data_store, res_id)
         for res_id in assignment_resource_ids])

    offline_eval_summary = (
        model_selection_record.OfflineEvaluationByAssignmentAndEvalId())

    for offline_eval_resource_id in offline_eval_resource_ids:
      if min([len(offline_eval_summary.model_ids_for_assignment_id(a))
              for a in assignment_ids]
             ) >= _NUM_MODELS_TO_ONLINE_EVAL_PER_ASSIGNMENT:
        # Hit all the assignments with at least
        # _NUM_MODELS_TO_ONLINE_EVAL_PER_ASSIGNMENT model.
        break
      offline_eval = self._data_store.read(offline_eval_resource_id)
      if offline_eval.assignment not in assignment_ids:
        raise ValueError(
            f'Assignment ID {offline_eval.assignment} not found in '
            f'assignments for session {session_resource_id.session}.')
      models_for_assignment = offline_eval_summary.model_ids_for_assignment_id(
          offline_eval.assignment)
      if len(models_for_assignment) >= _MAXIMUM_NUMBER_OF_MODELS_TO_ONLINE_EVAL:
        # No need to look at this offline evaluation score since we have enough
        # models for the assignment.
        continue
      scores_by_assignment_and_eval_id = offline_eval_summary[
          model_selection_record.AssignmentEvalId(
              assignment_id=offline_eval.assignment,
              offline_evaluation_id=offline_eval.offline_evaluation_id)]
      scores_by_assignment_and_eval_id.add_score(
          offline_eval.model_id, offline_eval.score)
    return offline_eval_summary

  def _get_online_eval_summary(self) -> (
      typing.DefaultDict[str, typing.List[float]]):
    """Gets list of online scores per model.

    Returns:
      typing.DefaultDict[str, List[float]] mapping model_id to scores.
    """
    # This session is the evaluating session ID, so we look for online evals for
    # self._session_resource_id.
    online_eval_resource_ids, _ = self._data_store.list_by_proto_ids(
        attribute_type=data_store_pb2.OnlineEvaluation,
        project_id=self._session_resource_id.project,
        brain_id=self._session_resource_id.brain,
        session_id=self._session_resource_id.session, episode_id='*')

    online_summaries = collections.defaultdict(list)
    for online_eval_resource_id in online_eval_resource_ids:
      online_eval = self._data_store.read(online_eval_resource_id)
      online_summaries[online_eval.model].append(online_eval.score)

    return online_summaries

  def _generate_summary_map(
      self, offline_eval_summary, online_eval_summary
  ) -> typing.DefaultDict[str, list[model_selection_record.EvaluationSummary]]:
    """Joins the summaries by corresponding assignment IDs and model IDs.

    Args:
      offline_eval_summary:
        model_selection_record.OfflineEvaluationByAssignmentAndEvalId instance.
      online_eval_summary: typing.DefaultDict[string, List[float]] mapping
        model_id to scores.

    Returns:
      typing.DefaultDict[string, List[EvaluationSummary]] mapping assignment IDs
        to list of EvalutionSummary.
    """
    summary_map = model_selection_record.SummaryMap()
    # We're allowed the max of _MAXIMUM_NUMBER_OF_MODELS_TO_ONLINE_EVAL and
    # number of assignments * _NUM_MODELS_TO_ONLINE_EVAL_PER_ASSIGNMENT.
    models_budget = max(
        _MAXIMUM_NUMBER_OF_MODELS_TO_ONLINE_EVAL,
        len(offline_eval_summary) * _NUM_MODELS_TO_ONLINE_EVAL_PER_ASSIGNMENT)
    offline_summary_copy = copy.copy(offline_eval_summary)

    # First, populate with scores from top
    # _NUM_MODELS_TO_ONLINE_EVAL_PER_ASSIGNMENT models for each assignment.
    for assignment_id in offline_eval_summary.assignment_ids:
      top_model_scores_for_assignment_id = (
          offline_eval_summary.scores_by_offline_evaluation_id(
              assignment_id,
              models_limit=_NUM_MODELS_TO_ONLINE_EVAL_PER_ASSIGNMENT))
      for eval_id, model_score in top_model_scores_for_assignment_id:
        self._add_summary(assignment_id, eval_id, model_score,
                          online_eval_summary.get(model_score.model_id, []),
                          summary_map)
        offline_summary_copy.remove_score(assignment_id, eval_id, model_score)

    # If we can still add more models, populate by getting one from each
    # assignment.
    while (summary_map.models_count < models_budget and offline_summary_copy):
      for assignment_id in offline_eval_summary.assignment_ids:
        top_scores_for_assignment_id = (
            offline_eval_summary.scores_by_offline_evaluation_id(
                assignment_id, models_limit=1))  # Pick off one model at a time.
        for eval_id, model_score in top_scores_for_assignment_id:
          self._add_summary(assignment_id, eval_id, model_score,
                            online_eval_summary.get(model_score.model_id, []),
                            summary_map)
          offline_summary_copy.remove_score(assignment_id, eval_id, model_score)
    return summary_map

  def _add_summary(self, assignment_id, eval_id, model_score, online_scores,
                   summary_map):
    """Add or update an existing EvaluationSummary in the SummaryMap.

    Args:
      assignment_id: Assignment ID of the score to update the SummaryMap with.
      eval_id: Offline evaluation ID of the score to update the SummaryMap with.
      model_score: ModelScore instance containing information about the score to
        update the SummaryMap with.
      online_scores: List of online scores to update the SummaryMap with.
      summary_map: SummaryMap instance to update.
    """
    existing_eval_summary = (
        summary_map.eval_summary_for_assignment_and_model(
            assignment_id, model_score.model_id))
    if existing_eval_summary:
      existing_eval_summary.offline_scores[eval_id] = model_score.score
    else:
      summary_map[assignment_id].append(
          model_selection_record.EvaluationSummary(
              model_id=model_score.model_id,
              offline_scores={eval_id: model_score.score},
              online_scores=online_scores))

  def _create_model_records(self):
    """Creates ModelRecords for sampling and return number of total eval runs.

    Returns:
      total_runs: Number of online evaluation runs recorded.
      model_ids: List of model IDs that recorded online evaluations.
      model_records: List of online_eval_sampling.ModelRecords instances.

    Raises:
      ValueError when size of model IDs and model records don't match.
    """
    total_runs = 0
    model_ids = []
    model_records = []
    for _, eval_summaries in self._get_summary_map().items():
      for eval_summary in eval_summaries:
        successes = 0
        failures = 0
        model_ids.append(eval_summary.model_id)
        for score in eval_summary.online_scores:
          if score == EPISODE_SCORE_SUCCESS:
            successes += 1
          elif score == EPISODE_SCORE_FAILURE:
            failures += 1
          else:
            logging.error('Unknown online score %d.', score)
        total_runs += successes + failures
        model_records.append(online_eval_sampling.ModelRecord(
            successes=successes, failures=failures))
    if len(model_records) != len(model_ids):
      raise ValueError(
          'Size of model records don\'t match the size of model IDs.')
    return total_runs, model_ids, model_records
