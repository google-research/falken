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
"""Algorithms to sample models for online evaluation."""

import abc
from typing import NamedTuple

import numpy as np


class ModelRecord(NamedTuple):
  """Represents a record of online model evaluations."""
  successes: int
  failures: int

  @property
  def total(self) -> int:
    """Return the total number of evaluations."""
    return self.successes + self.failures

  @property
  def success_rate(self) -> float:
    """Return the empirical success rate or 0.0 if no evaluations."""
    if self.total:
      return self.successes / self.total
    else:
      return 0.0


class SamplingStrategy(abc.ABC):
  """Abstract base class for deciding which model to sample next."""

  @abc.abstractmethod
  def select_next(self, model_records: list[ModelRecord]) -> int:
    """Select the next model to deploy for evaluation.

    Args:
      model_records: A list of model records.
    Returns:
      The index of the model that should be sampled next.
    """
    raise NotImplementedError()


class UniformSampling(SamplingStrategy):
  """Select the model with the least number of total evaluations."""

  def select_next(self, model_records: list[ModelRecord]) -> int:
    """Return the index of the model with the least number of evaluations."""
    totals = [record.total for record in model_records]
    return int(np.argmin(totals))  # Convert numpy int to python int.


class UCBSampling(SamplingStrategy):
  """Select the model highest upper confidence bound on quality."""

  def select_next(self, model_records: list[ModelRecord]) -> int:
    """Return the model with the highest upper confidence bound."""
    raise NotImplementedError('Not yet implemented.')


class SelectionStrategy(abc.ABC):
  """Abstract base class for deciding which model to select as the winner."""

  @abc.abstractmethod
  def select_best(self, model_records: list[ModelRecord]) -> int:
    """Select the winning model from evaluation data.

    Args:
      model_records: A list of model records.
    Returns:
      The index of the model determined to be the best.
    """
    raise NotImplementedError()


class HighestAverageSelection(SelectionStrategy):
  """Select the model with the best average score."""

  def select_best(self, model_records: list[ModelRecord]) -> int:
    """Return the index of the model with the least number of evaluations."""
    success_rates = [record.success_rate for record in model_records]
    return int(np.argmax(success_rates))  # Convert numpy int to python int.
