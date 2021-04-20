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

"""Tests for the policies module."""

from absl.testing import absltest
from learner.brains import policies

import numpy as np
import tensorflow as tf
import tensorflow_probability as tfp

from tf_agents.policies import tf_policy
from tf_agents.specs import tensor_spec
from tf_agents.trajectories import policy_step
from tf_agents.trajectories import time_step as ts


class ConstantExamplePolicy(tf_policy.TFPolicy):

  def __init__(self):
    obs_spec = tensor_spec.TensorSpec([1], tf.float32)
    time_step_spec = ts.time_step_spec(obs_spec)
    action_spec = [
        tensor_spec.BoundedTensorSpec((), tf.int32, 0, 2),
        tensor_spec.BoundedTensorSpec((), tf.float32, 0, 1.0)]
    super().__init__(time_step_spec, action_spec)

  def _distribution(self, time_step, policy_state):
    actions = [
        # A categorical distribution with equal probability for 3 categories.
        tfp.distributions.Categorical(logits=[1, 1, 1]),
        # A standard normal distribution with mean 0 and stddev 1.
        tfp.distributions.Normal(0, 1)]
    return policy_step.PolicyStep(
        action=actions,
        state=policy_state,
        info=())


class PoliciesTest(absltest.TestCase):

  def test_greedy_float(self):
    wrapped = ConstantExamplePolicy()
    greedy_float = policies.GreedyFloatPolicy(wrapped)

    timestep = ts.transition(
        1.0,   # observation
        0.0,   # reward
        0.99)  # discount

    actions = []
    for _ in range(100):
      # Actions come back as a list containing an int tensor and a float tensor.
      # We cast both to float for easier data munging.
      actions.append(np.array(
          greedy_float.action(timestep, ()).action, dtype=np.float32))
    actions = np.array(actions, dtype=np.float32)

    # actions is 100 x 2, where actions[:, 0] are outputs from the int action
    # and actions[:,1] are outputs from the float action.
    int_action_values = set(actions[:, 0])
    float_action_values = set(actions[:, 1])

    # Stochastic action should have all three categories
    self.assertEqual(int_action_values, {0.0, 1.0, 2.0})
    # Greedy float action should have only the distribution mode
    self.assertEqual(float_action_values, {0.0})


if __name__ == '__main__':
  absltest.main()
