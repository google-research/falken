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

  def test_select_best(self):
    selector = sampling.HighestAverageSelection()
    got = selector.select_best([
        sampling.ModelRecord(0, 10),
        sampling.ModelRecord(5, 5),
        sampling.ModelRecord(9, 3),
        sampling.ModelRecord(2, 3)])
    self.assertEqual(got, 2)


if __name__ == '__main__':
  absltest.main()
