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

"""Tests for online_eval_sampling."""

from absl.testing import absltest
from api.sampling import online_eval_sampling as sampling

import numpy as np


class OnlineEvalSamplingTest(absltest.TestCase):

  def test_model_record(self):
    self.assertEqual(sampling.ModelRecord(1, 2).total, 3)
    self.assertEqual(sampling.ModelRecord(2, 2).success_rate, 0.5)

  def test_uniform_sampling(self):
    sampler = sampling.UniformSampling()
    got = sampler.select_next([
        sampling.ModelRecord(1, 2),
        sampling.ModelRecord(0, 1),
        sampling.ModelRecord(1, 0),
        sampling.ModelRecord(2, 3),
    ])
    self.assertIn(got, [1, 2])

  def test_highest_average_selection(self):
    selector = sampling.HighestAverageSelection()
    got = selector.select_best([
        sampling.ModelRecord(0, 10),
        sampling.ModelRecord(5, 5),
        sampling.ModelRecord(9, 3),
        sampling.ModelRecord(2, 3)])
    self.assertEqual(got, 2)

  def test_ucb_sampling(self):
    sampler = sampling.UCBSampling()
    # Test that sampling prefers 50% with low confidence to 50% with
    # high confidence.
    self.assertEqual(
        sampler.select_next([
            sampling.ModelRecord(0, 10),
            sampling.ModelRecord(10, 10),
            sampling.ModelRecord(1, 1)]), 2)
    # Test that sampling prefers high success rate.
    self.assertEqual(
        sampler.select_next([
            sampling.ModelRecord(10, 0),
            sampling.ModelRecord(10, 10),
            sampling.ModelRecord(1, 1)]), 0)

  def test_ucb_sampling_loop(self):
    num_trials = 200
    num_evals = 60
    num_models = 10
    selector = sampling.HighestAverageSelection()

    def run_trial(sampler):
      """Return difference in success_rate to best model."""
      model_records = [sampling.ModelRecord(0, 0) for _ in range(num_models)]
      success_rates = np.random.uniform(0, 1, (num_models,))

      for _ in range(num_evals):
        selected = sampler.select_next(model_records)
        successes, failures = model_records[selected]
        if np.random.random() < success_rates[selected]:
          model_records[selected] = sampling.ModelRecord(
              successes + 1, failures)
        else:
          model_records[selected] = sampling.ModelRecord(
              successes, failures + 1)
      best = selector.select_best(model_records)
      return np.max(success_rates) - success_rates[best]

    ucb_sampler = sampling.UCBSampling()
    uniform_sampler = sampling.UniformSampling()
    mean_ucb_diff = np.mean(
        [run_trial(ucb_sampler) for _ in range(num_trials)])
    mean_uniform_diff = np.mean(
        [run_trial(uniform_sampler) for _ in range(num_trials)])

    # Check that ucb typically finds a model close to the best.
    self.assertLess(mean_ucb_diff, 0.1)
    # Check that ucb is typically better than uniform.
    self.assertLess(mean_ucb_diff, mean_uniform_diff)


if __name__ == '__main__':
  absltest.main()
