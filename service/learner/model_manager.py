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
"""Manages models and their improvement across training.

The ModelManager keeps track of the best model, and keeps track of the
improvement of these models, judging whether the assignment processor should
stop training on the assignment.
"""

from log import falken_logging

# How many models to train if there is not enough data for an eval set.
_NO_EVAL_MODEL_LIMIT = 10

# Progress required to count as improvement
_IMPROVEMENT_EPSILON = 5e-2

# How many models to train without improvement before giving up.
_NO_IMPROVEMENT_MODEL_LIMIT = 3


class ModelManager:
  """Helper class to manage tracking a best model."""

  def __init__(self):
    self._best_model_id = None
    self._best_model_path = None
    self._best_eval_version = None
    self._best_score = None
    self._models_recorded = 0
    self._models_without_improvement = 0

  def _reached_no_eval_limit(self):
    return (not self._best_eval_version and
            self._models_recorded > _NO_EVAL_MODEL_LIMIT)

  def _reached_no_improvement_limit(self):
    return self._models_without_improvement > _NO_IMPROVEMENT_MODEL_LIMIT

  def reset_counters(self):
    self._models_recorded = 0
    self._models_without_improvement = 0

  def should_stop(self):
    """Returns true if the manager indicates that we should stop training."""
    if self._reached_no_eval_limit():
      return 'too many models without an eval set.'
    if self._reached_no_improvement_limit():
      return 'too many models without improvement.'
    return None

  @property
  def best_model_id(self):
    return self._best_model_id

  @property
  def best_eval_version(self):
    return self._best_eval_version

  def _set_best(self, model_id, version, score):
    if (score is None or self._best_score is None
        or self._best_score - score > _IMPROVEMENT_EPSILON
        or self._best_eval_version != version):
      self._models_without_improvement = 0  # Reset counter
    self._best_model_id = model_id
    self._best_eval_version = version
    self._best_score = score

  def record_new_model(self, model_id, full_eval):
    """Record evaluation of a new model."""
    self._models_recorded += 1
    if not self._best_eval_version:
      # Prefer newer models if no eval data is available.
      version, score = (None, None) if not full_eval else full_eval[-1]
      falken_logging.info('No previous eval, updating best model.'
                          f'v{version}:{score}',
                          model_id=model_id)
      self._set_best(model_id, version, score)
    else:
      # Compare new model against previous best and possibly update.
      version, score = full_eval[-1]
      # Eval version expected to increase.
      assert version >= self._best_eval_version
      if self._best_eval_version < version:
        # A new eval version is available, replace previous best.
        falken_logging.info('Newer eval set available. Updating best model: '
                            f'v{version}:{score}', model_id=model_id)
        self._set_best(model_id, version, score)
        return

      falken_logging.info('New model vs. previous best score on eval set '
                          f'{version}: {score} vs {self._best_score}')
      if self._best_score - score < _IMPROVEMENT_EPSILON:
        self._models_without_improvement += 1
      if score < self._best_score:
        self._set_best(model_id, version, score)
        falken_logging.info('Updated local best model.', model_id=model_id)
      else:
        falken_logging.info('No significant improvement for '
                            f'{self._models_without_improvement} steps.')
