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
from typing import List, NamedTuple

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
  def select_next(self, model_records: List[ModelRecord]) -> int:
    """Select the next model to deploy for evaluation.

    Args:
      model_records: A list of model records.
    Returns:
      The index of the model that should be sampled next.
    """
    raise NotImplementedError()


class UniformSampling(SamplingStrategy):
  """Select the model with the least number of total evaluations."""

  def select_next(self, model_records: List[ModelRecord]) -> int:
    """Return the index of the model with the least number of evaluations."""
    totals = [record.total for record in model_records]
    return int(np.argmin(totals))  # Convert numpy int to python int.


class UCBSampling(SamplingStrategy):
  """Select the model with highest upper confidence bound on success rate.

  Models can viewed as Bernoulli distributions with a fixed but unknown success
  rate. We can model the uncertainty of the actual success rate as a Beta
  disribution Beta(A, B) where A and B are incremented with each sucessful and
  unsuccessful trials respectively. The initial values for A and B are set to
  0.5, which corresponds to the Jeffreys prior for the beta distribution. This
  prior experimentally performs better than other obvious choices, e.g.,
  1. This means, that the unknown success rate of a model with X successes and
  Y failures is represented as the Beta distribution Beta(0.5 + X, 0.5 + Y).

  When we model an unknown success rate as a distribution Beta(A, B) we can
  calculate a confidence interval on the success rate. For example, for 1
  success and 1 failure, the 90% confidence interval for the success rate,
  modeled by Beta(1.5, 1.5) is approximately [10%, 90%].

  The UCBSampling strategy selects the model for deployment that has the
  highest upper confidence bound. A high upper confidence bound can both mean
  that we are confident that the model has a high success rate, e.g., if the
  confidence interval is [0.9,0.95] or that we are highly uncertain about how
  good the success rate is, e.g., [0.35, 0.95]. This means that sampling focuses
  on obtaining more information on models that are promising candidates for
  being the best model.

  We use sampling to estimate the confidence interval using a relatively low
  number of samples. This seems to work better empirically for the overall
  selection procedure than calculating a more accurate interval.
  """

  # Jeffrey's prior for the Beta distribution.
  PRIOR = 0.5
  # We pick an intentionally low number of samples, see class comment.
  NUM_UCB_SAMPLES = 50
  # The confidence range for the model quality estimates.
  CONFIDENCE_RANGE = 0.97

  def select_next(self, model_records: List[ModelRecord]) -> int:
    """Return the model with the highest upper confidence bound."""

    # Calculate alpha and beta parameters of shape (len(model_records),)
    alpha = UCBSampling.PRIOR + np.array(
        [m.successes for m in model_records], np.float32)
    beta = UCBSampling.PRIOR + np.array(
        [m.failures for m in model_records], np.float32)

    # Produce model quality samples with shape:
    #  (NUM_UCB_SAMPLES, len(model_records))
    samples = np.random.beta(
        alpha, beta, (UCBSampling.NUM_UCB_SAMPLES, len(model_records)))

    # Produce sorted per-model samples:
    #  (len(model_records), NUM_UCB_SAMPLES)
    samples_per_model = np.sort(samples.transpose(), axis=-1)

    # Calculate percentile and index of CONFIDENCE_RANGE upper bound.
    ucb_percentile = 1 - ((1 - UCBSampling.CONFIDENCE_RANGE) / 2)
    ucb_index = int(ucb_percentile * UCBSampling.NUM_UCB_SAMPLES)

    # Select the ucb estimate for each model.
    ucbs = samples_per_model[..., ucb_index]

    # Return the index of the model with the highest ucb estimate.
    return int(np.argmax(ucbs))


class SelectionStrategy(abc.ABC):
  """Abstract base class for deciding which model to select as the winner."""

  @abc.abstractmethod
  def select_best(self, model_records: List[ModelRecord]) -> int:
    """Select the winning model from evaluation data.

    Args:
      model_records: A list of model records.
    Returns:
      The index of the model determined to be the best.
    """
    raise NotImplementedError()


class HighestAverageSelection(SelectionStrategy):
  """Select the model with the best average score."""

  def select_best(self, model_records: List[ModelRecord]) -> int:
    """Return the index of the model with the least number of evaluations."""
    success_rates = [record.success_rate for record in model_records]
    return int(np.argmax(success_rates))  # Convert numpy int to python int.
