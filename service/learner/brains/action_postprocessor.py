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

"""Processes hidden layer outputs and creates a nest of action distributions."""

from learner.brains import egocentric
from learner.brains import weights_initializer
import numpy as np
import tensorflow as tf
from tf_agents.networks import categorical_projection_network
from tf_agents.networks import network
from tf_agents.networks import normal_projection_network
from tf_agents.utils import nest_utils

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import action_pb2
import primitives_pb2


def _normal_projection_net(action_spec,
                           init_action_stddev=0.35,
                           init_means_output_factor=0.1):
  std_bias_initializer_value = np.log(np.exp(init_action_stddev) - 1)

  return normal_projection_network.NormalProjectionNetwork(
      action_spec,
      init_means_output_factor=init_means_output_factor,
      std_bias_initializer_value=std_bias_initializer_value,
      scale_distribution=False)


def _categorical_projection_net(action_spec, logits_init_output_factor=0.1):
  return categorical_projection_network.CategoricalProjectionNetwork(
      action_spec, logits_init_output_factor=logits_init_output_factor)


class JoystickActionProjection(
    normal_projection_network.NormalProjectionNetwork):
  """Projects a hidden layer to a joystick action output.

  Depending on the joystick type, will perform geometric transformations to
  translate egocentric outputs into other-entity-centric (e.g., camera centric)
  outputs.
  """

  def __init__(self, proto_spec, tf_action_spec):
    """Create a new JoystickActionProjection network.

    Args:
      proto_spec: An action_pb2.JoystickType describing the joystick.
      tf_action_spec: A tensorspec of the action output shape.
    Raises:
      InvalidTypeError: If an invalid proto_spec type is provided.
    """
    if not isinstance(proto_spec, action_pb2.JoystickType):
      raise InvalidTypeError(
          'JoystickActionProjection expects a JoystickType.')

    if proto_spec.controlled_entity not in ('player', 'camera'):
      raise InvalidTypeError(
          f'Unsupported controlled_entity: {proto_spec.controlled_entity}')

    if proto_spec.axes_mode == action_pb2.DIRECTION_XZ:
      if proto_spec.control_frame not in ('player', 'camera', ''):
        raise InvalidTypeError(
            f'Unsupported control_frame: {proto_spec.control_frame}')

    self._proto_spec = proto_spec
    init_action_stddev = 0.35  # Default value from tf-agents code.
    std_bias_initializer_value = np.log(np.exp(init_action_stddev) - 1)
    super().__init__(tf_action_spec,
                     init_means_output_factor=0.1,
                     std_bias_initializer_value=std_bias_initializer_value)

  def get_entity_rotation(self, observations, entity_name):
    assert entity_name in ('player', 'camera')
    if entity_name not in observations:
      raise InvalidDataError(f'Expected "{entity_name}" in observations.')
    entity = observations[entity_name]
    if 'rotation' not in entity:
      raise InvalidDataError(
          f'Expected "{entity_name}/rotation" in observations.')
    return entity['rotation']

  def call(self, inputs, observations,
           outer_rank,
           mean_transform=None,
           training=False):
    """Create an output distribution for the joystick action.

    Args:
      inputs: The network inputs (e.g., MLP hidden states) as a nest.
      observations: A tensor nest that contains entity rotation information
          at paths <entity_name>/rotation for all entities referenced in the
          proto spec that was used to initialize this instance of
          JoystickActionProjection.
      outer_rank: Number of batch dimensions.
      mean_transform: Function to apply to egocentric mean before geometric
          transforms.
      training: Whether this is called during training.

    Returns:
      A pair (d, s) consisting of tfp.Distribution d and a network state s.
    """
    def _transform_means(means):
      """Transform means to camera frame."""
      if mean_transform is not None:
        means = mean_transform(means)
      if (self._proto_spec.axes_mode == action_pb2.DELTA_PITCH_YAW or
          self._proto_spec.controlled_entity == self._proto_spec.control_frame):
        # If axes-mode is delta pitch yaw or if the control frame is already
        # equal to the controlled object, then no translation between
        # frames of reference is necessary.
        return means

      orientation = self.get_entity_rotation(
          observations,
          self._proto_spec.controlled_entity)

      # Figure out control_frame orientation
      if self._proto_spec.control_frame:
        # Use entity-centric orientation.
        frame_orientation = self.get_entity_rotation(
            observations,
            self._proto_spec.control_frame)
      else:
        # Use world-centric control-frame.
        batch_dims = means.shape[:-1]
        # Create neutral orientation quaternions for each batch entry.
        frame_orientation = tf.broadcast_to(
            tf.constant([0, 0, 0, 1], dtype=tf.float32),
            tf.concat([batch_dims, [4]], axis=0))

      # Postprocess signal to be in control frame.
      return egocentric.egocentric_signal_to_target_frame(
          orientation, frame_orientation, means)

    # Get egocentric distribution.
    dist, network_state = super().call(
        inputs, outer_rank=outer_rank, training=training)

    # Return control-frame centric distribution from ego-centric distribution.
    return self.output_spec.build_distribution(
        loc=_transform_means(dist.mean()), scale=dist.stddev()), network_state


class InvalidTypeError(Exception):
  pass


class InvalidDataError(Exception):
  pass


class ActionPostprocessor(network.DistributionNetwork,
                          weights_initializer.ModelWeightsInitializer):
  """Creates action outputs from network outputs and observations."""

  def __init__(self, brain_spec, hparams):
    """Create a new action postprocessor.

    Args:
      brain_spec: A tfa_specs.BrainSpec.
      hparams: A dictionary of hyperparameters.
    """
    self._brain_spec = brain_spec
    self._hparams = hparams

    def _create_projection_layer(tf_spec, proto_spec):
      if isinstance(proto_spec, primitives_pb2.NumberType):
        return _normal_projection_net(tf_spec)
      if isinstance(proto_spec, primitives_pb2.CategoryType):
        return _categorical_projection_net(tf_spec)
      elif isinstance(proto_spec, action_pb2.JoystickType):
        return JoystickActionProjection(proto_spec, tf_spec)
      else:
        raise InvalidTypeError(f'Encountered unknown type {type(proto_spec)}')

    self._layer_nest = tf.nest.map_structure(
        _create_projection_layer,
        brain_spec.action_spec.tfa_spec,   # Nest of tensor specs
        brain_spec.action_spec.spec_nest)  # Nest of proto specs

    output_spec = tf.nest.map_structure(lambda proj_net: proj_net.output_spec,
                                        self._layer_nest)

    super().__init__(
        # The superclass wants this argument, but it's not required.
        input_tensor_spec=None,
        state_spec=(),
        output_spec=output_spec,
        name=self.__class__.__name__)

  def call(self, inputs, observations, training=False, network_state=()):
    """Call the action postprocessor to generate action outputs.

    Args:
      inputs: The network outputs from which to generate actions.
      observations: The unprocessed observation inputs.
      training: Whether the network is being trained.
      network_state: The current state of the network.

    Returns:
      A pair of nested tensors actions, network state, where actions satisfies
      the action-spec associated with the provided brain.
    """
    outer_rank = nest_utils.get_outer_rank(
        observations,
        self._brain_spec.observation_spec.tfa_spec)

    def _apply_action_layer(l):
      if isinstance(l, JoystickActionProjection):
        action, _ = l(inputs, observations,
                      outer_rank=outer_rank, training=training)
      else:
        action, _ = l(inputs, outer_rank=outer_rank, training=training)
      return action

    # We apply all layers to the same tensor inputs.
    actions = tf.nest.map_structure(_apply_action_layer, self._layer_nest)
    return actions, network_state
