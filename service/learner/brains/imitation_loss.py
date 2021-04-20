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
"""Defines useful losses for imitation learning."""
import tensorflow as tf
import tensorflow_probability as tfp


def distribution_loss(dist, targets):
  """Provides loss for a distribution given the targets."""
  if isinstance(dist, tfp.distributions.Categorical):
    return tf.compat.v1.nn.sparse_softmax_cross_entropy_with_logits(
        logits=dist.logits, labels=targets)
  elif isinstance(dist, tfp.distributions.Normal):
    return -dist.log_prob(targets)
  elif isinstance(dist, tfp.distributions.MultivariateNormalDiag):
    # We need to add a 1 dim at the end since we represent a scalar action as
    # a vector of size 1.
    return tf.expand_dims(-dist.log_prob(targets), axis=-1)
  else:
    raise ValueError('dist must be a tfp.distributions.Categorical or a '
                     'tfp.distributions.Normal')


def dict_loss(values, targets):
  """Provides loss for our multi-dimensional action setup.

  This function blends discrete and continuous actions into one single loss.

  Args:
      values: A dictionary of tfp.distributions.Distribution objects.
      targets: A dictionary of target actions. It can also be a tensor
        if there is a single action.

  Returns:
    The loss tensor.

  Raises:
    ValueError: whenever the dictionary keys don't match.
  """
  if not isinstance(values, dict):
    raise ValueError(f'values must be a dictionary, but is a {type(values)}.')
  if not isinstance(targets, dict) and len(values) > 1:
    raise ValueError(
        f'values has size {len(values)}, so targets must be a dictionary, '
        f'but it is a {type(targets)}.')
  if isinstance(targets, dict) and values.keys() != targets.keys():
    raise ValueError(
        f'Keys of values and targets must match, but are different: '
        f'{values.keys()} vs. {targets.keys()}.')

  flat_values = tf.nest.flatten(values)
  flat_targets = tf.nest.flatten(targets)

  losses = tf.nest.map_structure(distribution_loss, flat_values, flat_targets)

  # Accumulate across actions.
  return tf.add_n(losses)
