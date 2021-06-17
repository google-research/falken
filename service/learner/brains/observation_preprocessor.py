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
"""Used to translate semantic observations into network structures."""

import math

from learner.brains import egocentric
from learner.brains import layers
import tensorflow as tf
from tf_agents.networks import nest_map
from tf_agents.networks import network
from tf_agents.networks import sequential

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import action_pb2
import observation_pb2
import primitives_pb2


class ObservationPreprocessor(sequential.Sequential):
  """A network that preprocess observations and produces a flat output layer."""

  def __init__(self, brain_spec, hparams):
    self._hparams = hparams
    processing_layers = layers.CreateNest(
        (ObservationNestPreprocess(brain_spec.observation_spec, hparams),
         EgocentricDirectionToEntity(brain_spec, hparams)))

    seq_layers = [
        # Flatten and concatenate takes a pair (batch_size, input_nest),
        # we create this pair with a CreateNest layer, so that we can structure
        # the whole network as a sequential.Sequential network.
        layers.CreateNest(
            (layers.ComputeNumBatchDims(brain_spec.observation_spec.tfa_spec),
             processing_layers)),
        layers.FlattenAndConcatenate()]
    super().__init__(seq_layers, brain_spec.observation_spec.tfa_spec)


class ObservationNestPreprocess(nest_map.NestMap):
  """A network that processes individual observations in a nest."""

  def __init__(self, observation_spec, hparams):
    def _create_sublayer(proto_spec, tfa_spec):
      if isinstance(proto_spec, primitives_pb2.CategoryType):
        return layers.OneHot(len(proto_spec.enum_values))
      elif isinstance(proto_spec, observation_pb2.FeelerType):
        if hparams['feelers_version'] == 'v1':
          feelers = layers.Feelers(
              proto_spec.count,
              len(proto_spec.experimental_data) + 1)
        elif hparams['feelers_version'] == 'v2':
          if (math.isclose(proto_spec.yaw_angles[0], 0) and
              math.isclose(proto_spec.yaw_angles[-1], 2 * math.pi)):
            padding_mode = 'wrap'
          else:
            padding_mode = 'repeat'

          feelers = layers.FeelersV2(
              proto_spec.count,
              hparams['feelers_v2_kernel_size'],
              hparams['feelers_v2_output_channels'],
              padding_mode)
        else:
          raise ValueError('feelers_version hparam contains an invalid value:'
                           f'{hparams["feelers_version"]}.')

        return sequential.Sequential([layers.BatchNorm(tfa_spec), feelers])
      elif isinstance(proto_spec, primitives_pb2.NumberType):
        return sequential.Sequential([
            layers.NormalizeRange(proto_spec.minimum, proto_spec.maximum),
            layers.BatchNorm(tfa_spec)])
      else:
        return tf.keras.layers.Lambda(lambda x: None)

    super().__init__(tf.nest.map_structure(
        _create_sublayer,
        observation_spec.spec_nest,
        observation_spec.tfa_spec))


def _get_from_nest(nest, path):
  """Return element from a dictionary-only nest using path specified as list.

  Args:
    nest: A nested dictionary.
    path: A list of strings specifying a nested element.
  Returns:
    An leaf or subnest of the input nest.
  """
  if not path or not nest:
    return nest
  return _get_from_nest(nest.get(path[0], None), path[1:])


def _check_position(spec_nest, path):
  """Check that the provided path in the spec nest names a PositionType."""
  spec = _get_from_nest(spec_nest, path)
  if spec is not None and not isinstance(spec, primitives_pb2.PositionType):
    raise InvalidSpecError(
        f'{"/".join(path)} was expected to be of type Position, but is instead '
        f'{type(spec)}')


def _check_rotation(spec_nest, path):
  """Check that the provided path in the spec nest names a RotationType."""
  spec = _get_from_nest(spec_nest, path)
  if spec is not None and not isinstance(spec, primitives_pb2.RotationType):
    raise InvalidSpecError(
        f'{"/".join(path)} was expected to be of type Rotation, but is instead '
        f'{type(spec)}')


def _get_global_entities(nest):
  """Returns list of string indices representing each global entity.

  For example, if 'global_entities/0' and 'global_entities/1' exist in the
  input nest, this function will return the list ['0', '1'].

  Args:
    nest: A tensor or spec nest generated from a falken observation spec.
  Returns:
    A list of strings, representing the indices / IDs of each global entity.
  """
  entities = nest.get('global_entities', None)
  if not entities:
    return []
  return list(entities.keys())


class InvalidSpecError(Exception):
  """Raised when spec is invalid."""
  pass


class EgocentricDirectionToEntity(network.Network):
  """A network that produces egocentric signals from player to entities."""

  _DEFAULT_HPARAMS = {
      # How to process direction input signals:
      #  'unit_circle': Provide direction as a point on the unit circle.
      #  'angle': Compute angle in radians in [-pi, pi],
      'egocentric_direction_mode': 'angle',
      # How to process:
      #   'linear': Simply provide Euclidean distance.
      #   'log_plus_one: Compute log(distance + 1).
      'egocentric_distance_mode': 'log_plus_one',
  }

  def __init__(self, brain_spec, hparams):
    """Create a new egocentric signal preprocessor.

    Args:
      brain_spec: A tfa_specs.BrainSpec.
      hparams: A dictionary of hyperparameters.
    """
    self._brain_spec = brain_spec
    self._validate_spec()
    self._hparams = hparams
    super().__init__(input_tensor_spec=brain_spec.observation_spec.tfa_spec)

  def _get_hparam(self, name):
    return self._hparams.get(name, self._DEFAULT_HPARAMS.get(name, None))

  def _validate_spec(self):
    proto_spec = self._brain_spec.observation_spec.spec_nest
    _check_position(proto_spec, ['player', 'position'])
    _check_rotation(proto_spec, ['player', 'rotation'])
    if 'camera' in proto_spec:
      _check_position(proto_spec, ['camera', 'position'])
      _check_rotation(proto_spec, ['camera', 'rotation'])
    indices = _get_global_entities(proto_spec)
    for i in indices:
      _check_position(proto_spec, ['global_entities', i, 'position'])

  def _get_controlled_entities(self):
    """Return names of entities controlled by joystick actions."""
    def _get_controlled_entity(x):
      if isinstance(x, action_pb2.JoystickType):
        return x.controlled_entity
      return None

    # Map each Joystick action to its controlled_entity (or None, if not a
    # Joystick action).
    controlled_entities = tf.nest.flatten(tf.nest.map_structure(
        _get_controlled_entity,
        self._brain_spec.action_spec.spec_nest))

    # Filter out None values.
    controlled_entities = [c for c in controlled_entities if c]
    return sorted(set(controlled_entities))

  @staticmethod
  def _process_egocentric_distance(mode, dist):
    """Process distance tensors into a list of tensor nests based on mode.

    Args:
      mode: A valid hparam valuue for "egocentric_distance_mode", see
        _DEFAULT_HPARAMS for their meaning.
      dist: A possibly batched scalar tensor representing a distance.

    Returns:
      A list of tensors nests, shape and meaning determined by 'mode', that
      encode the egocentric distance signal.
    """
    if mode == 'linear':
      # Mode "linear" simply passes through the raw distance signal.
      return [dist]
    assert mode == 'log_plus_one'
    # Mode "log_plus_one" computes a log of the distance + 1.
    return [tf.math.log(dist + 1)]

  @staticmethod
  def _process_egocentric_direction(mode, xz_dir, yz_dir):
    """Process direction tensors into a list of tensor nests based on mode.

    Args:
      mode: A valid hparam value for "egocentric_direction_mode", see
        _DEFAULT_HPARAMS for their meaning.
      xz_dir: A possibly batched tensor of shape (B1,...,BN, 2) representing
        a direction in the XZ plane.
      yz_dir: A possibly batched tensor of shape (B1,...,BN, 2) representing
        a direction in the YZ plane.

    Returns:
      A list of tensors nests, shape and meaning determined by 'mode', that
      encode the egocentric direction signals.
    """
    if mode == 'unit_circle':
      # In mode "unit_circle" we pass through the direction tensors unmodified
      # as an output.
      return [xz_dir, yz_dir]
    xz_angle, _ = egocentric.vec_to_angle_magnitude(xz_dir)
    yz_angle, _ = egocentric.vec_to_angle_magnitude(yz_dir)

    assert mode == 'angle'
    # In mode angle we return two tensors representing angles.
    return [xz_angle, yz_angle]

  def _process_egocentric(self, signal: egocentric.EgocentricSignal):
    """Process an egocentric signal into a nest of derived tensors.

    Args:
      signal: The egocentric input signal.

    Returns:
      A nested tensor that represents the processed signal. Shape and meaning
      depend on hyperparameter settings.
    """
    output_signals = []
    output_signals += self._process_egocentric_direction(
        self._get_hparam('egocentric_direction_mode'),
        signal.xz_direction,
        signal.yz_direction)
    output_signals += self._process_egocentric_distance(
        self._get_hparam('egocentric_distance_mode'),
        signal.distance)
    return output_signals

  def call(self, inputs, training=False, network_state=()):
    """Create egocentric input signals for each player / entity pair.

    Args:
      inputs: An input tensor test.
      training: Whether the network is being trained.
      network_state: Current state of the network.

    Returns:
      A pair of tensor nests state, network_state.
    Raises:
      InvalidSpecError: If input spec has unsupported entity references.
    """
    controlled_entitities = self._get_controlled_entities()
    raw_signals = []

    entity_positions = []

    for e in controlled_entitities:
      if e not in ('player', 'camera'):
        raise InvalidSpecError(f'Unsupported entity: {e}')
      position = _get_from_nest(inputs, [e, 'position'])
      rotation = _get_from_nest(inputs, [e, 'rotation'])

      if position is None or rotation is None:
        continue

      entity_positions = []
      for i in _get_global_entities(inputs):
        entity_position = _get_from_nest(inputs,
                                         ['global_entities', i, 'position'])
        if entity_position is not None:
          entity_positions.append(entity_position)

      raw_signals += [
          egocentric.egocentric_signal(
              rotation, position, entity_position)
          for entity_position in entity_positions]

    result = [self._process_egocentric(signal) for signal in raw_signals]

    return result, network_state
