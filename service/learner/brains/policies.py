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

"""Falken specific policies."""

import tensorflow as tf

from tf_agents.policies import greedy_policy
from tf_agents.policies import tf_policy
from tf_agents.trajectories import policy_step


class PostprocessedPolicy(tf_policy.TFPolicy):
  """Wraps a TFPolicy object and postprocesses output distributions."""

  def __init__(self, policy, postprocess_func, name=None):
    """Builds a wrapped TFPolicy which post-processes distributions.

    Note that as of now, postprocessing may not introduce new TF variables.

    Implementation is based on greedy_policy.GreedyPolicy.

    Args:
      policy: A policy implementing the tf_policy.TFPolicy interface.
      postprocess_func: A function that maps a distribution to a distribution.
      name: The name of this policy. All variables in this module will fall
        under that name. Defaults to the class name.
    """
    super().__init__(
        policy.time_step_spec,
        policy.action_spec,
        policy.policy_state_spec,
        policy.info_spec,
        emit_log_probability=policy.emit_log_probability,
        name=name)
    self._wrapped_policy = policy
    self._postprocess_func = postprocess_func

  @property
  def wrapped_policy(self):
    return self._wrapped_policy

  def _variables(self):
    return self._wrapped_policy.variables()

  def _distribution(self, time_step, policy_state):
    distribution_step = self._wrapped_policy.distribution(
        time_step, policy_state)
    return policy_step.PolicyStep(
        tf.nest.map_structure(self._postprocess_func, distribution_step.action),
        distribution_step.state, distribution_step.info)


class GreedyFloatPolicy(PostprocessedPolicy):
  """A policy that applies a greedy strategy to float-valued distributions."""

  def __init__(self, policy):
    def postprocess_fn(dist):
      try:
        if not dist.dtype.is_floating:
          return dist
        greedy_action = dist.mode()
      except NotImplementedError:
        raise ValueError("Your network's distribution does not implement mode "
                         "making it incompatible with a greedy policy.")
      return greedy_policy.DeterministicWithLogProb(loc=greedy_action)

    super().__init__(policy, postprocess_fn)
