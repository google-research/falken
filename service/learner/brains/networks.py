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

"""Networks for use in falken brains."""

from learner.brains import action_postprocessor
from learner.brains import observation_preprocessor
from learner.brains import weights_initializer
import tensorflow as tf
from tf_agents.networks import network
from tf_agents.networks import sequential
from tf_agents.utils import nest_utils


class FalkenNetwork(network.DistributionNetwork,
                    weights_initializer.WeightInitializationInterface):
  """A network that produces action distributions from observations."""

  def __init__(self, brain_spec, hparams):
    """Create a new Falken network.

    Args:
      brain_spec: A specs.BrainSpec describing observations and actions.
      hparams: A dictionary of hyperparameters.
    """
    self._brain_spec = brain_spec
    self._hparams = hparams

    # Add internal layers
    self._preprocessor = observation_preprocessor.ObservationPreprocessor(
        brain_spec, hparams)
    fc_layers = self._hparams['fc_layers']
    dropout_layers = _get_dropout(self._hparams)
    activation_fn = _get_activation_fn(self._hparams)

    self._postprocessor = action_postprocessor.ActionPostprocessor(
        brain_spec, hparams)

    layers = []
    kernel_initializer = tf.keras.initializers.get(
        self._hparams.get('initializer', 'glorot_uniform'))
    for num_units, dropout in zip(fc_layers, dropout_layers):
      layers.append(
          tf.keras.layers.Dense(
              num_units,
              activation=activation_fn,
              kernel_initializer=kernel_initializer,
              dtype=tf.float32))
      if dropout:
        layers.append(tf.keras.layers.Dropout(dropout))

    self._mlp = sequential.Sequential(layers)

    output_spec = self._postprocessor.output_spec

    super().__init__(
        brain_spec.observation_spec.tfa_spec,
        state_spec=(),
        output_spec=output_spec,
        name=self.__class__.__name__)

  def initialize_weights(self):
    """Initialize layer weights."""
    for layer_or_model in [self._preprocessor, self._mlp, self._postprocessor]:
      weights_initializer.WeightsInitializer.initialize_layer_or_model(
          layer_or_model)

  def call(self,
           observations,
           step_type=None,
           network_state=None,
           training=False):
    """Process observations and get actions.

    Args:
      observations: A nest of observation tensors.
      step_type: The tf-agents step type. This argument is unused and present
        only to make the signature compatible for use as the cloning network
        of a tfagents BehavioralCloningAgent.
      network_state: The state of the network at time of call (for RNNs).
      training: Whether we are training or performing inference.

    Returns:
      Action distributions matching brain_spec.action_spec.tfa_spec.
    """
    # Get batch dimensions by comparing spec to observations input.
    outer_rank = nest_utils.get_outer_rank(
        observations,
        self.input_tensor_spec)

    # Preprocess using observation preprocessor.
    state, network_state = self._preprocessor(
        observations,
        network_state=network_state,
        training=training)

    def _apply_with_batch(net, state, network_state):
      """Ensure that net is called on a batched input."""
      if outer_rank == 0:
        # Expand dimension to create a dummy batch of size 1.
        state = tf.nest.map_structure(lambda t: tf.expand_dims(t, 0), state)
        network_state = tf.nest.map_structure(lambda t: tf.expand_dims(t, 0),
                                              network_state)

      state, network_state = net(state, network_state=network_state)

      if outer_rank == 0:
        # Remove dummy batch dimension if it was created earlier.
        state = tf.nest.map_structure(lambda t: tf.squeeze(t, 0), state)
        network_state = tf.nest.map_structure(lambda t: tf.squeeze(t, 0),
                                              network_state)
      return state, network_state

    # Apply multi-layer-perceptron. It contains Dense layers which require a
    # batch dimension, hence we create one if the input is unbatched and then
    # squeeze it out of the result again if necessary.
    state, network_state = _apply_with_batch(self._mlp, state, network_state)

    # Create output action distributions from mlp outputs.
    output_actions, _ = self._postprocessor(state, observations=observations)
    return output_actions, network_state


class UnknownHParamError(Exception):
  """Raised if there is an unknown hyperparameter in the assignment."""


def _get_activation_fn(hparams):
  try:
    return tf.keras.activations.get(hparams.get('activation_fn'))
  except ValueError as e:
    raise UnknownHParamError(str(e))


def _get_dropout(hparams):
  if hparams['dropout'] is None:
    return [None] * len(hparams['fc_layers'])
  if isinstance(hparams['dropout'], list):
    return hparams['dropout']
  else:
    assert isinstance(hparams['dropout'], float)
    return [hparams['dropout']] * len(hparams['fc_layers'])
