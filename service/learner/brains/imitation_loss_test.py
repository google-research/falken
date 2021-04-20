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
"""Tests for ImitationLoss class."""

from absl.testing import absltest
from learner.brains import imitation_loss

import numpy as np
import tensorflow_probability as tfp


class DistributionLossTest(absltest.TestCase):
  """Tests distribution loss produces tensors of the right shape."""

  def test_categorical_loss(self):
    distribution = tfp.distributions.Categorical(logits=[[0.5]])
    targets = [0]
    self.assertEqual(
        imitation_loss.distribution_loss(distribution, targets).shape,
        [1])

  def test_normal_loss(self):
    distribution = tfp.distributions.Normal(loc=0., scale=1.)
    targets = [0]
    self.assertEqual(
        imitation_loss.distribution_loss(distribution, targets).shape,
        [1])


class DictLossTest(absltest.TestCase):
  """Tests dict_loss produces a tensor of the right shape."""

  def test_dict_loss(self):
    distributions = {
        'categorical': [tfp.distributions.Categorical(
            logits=[[0.5, 0.5], [0.5, 0.5]])],
        'normal': tfp.distributions.Normal(loc=[0., 0.], scale=[1., 1.]),
    }
    targets = {
        'categorical': np.array([0, 1]),
        'normal': np.array([0, 0]),
    }
    self.assertEqual(
        imitation_loss.dict_loss(distributions, targets).shape,
        [2])

  def test_dict_loss_dictionary_mismatch(self):
    distributions = {
        'categorical': [tfp.distributions.Categorical(logits=[[0.5]])],
        'normal': tfp.distributions.Normal(loc=0., scale=1.),
    }
    targets = {
        'normal_1': np.array([0]),
        'normal_2': np.array([0]),
    }
    with self.assertRaises(ValueError):
      imitation_loss.dict_loss(distributions, targets)


if __name__ == '__main__':
  absltest.main()
