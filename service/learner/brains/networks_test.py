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

"""Tests for networks."""

from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from google.protobuf import text_format
from learner import test_data
from learner.brains import networks
from learner.brains import specs
from learner.brains import weights_initializer
import tensorflow as tf

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import brain_pb2
import observation_pb2


class NetworksTest(parameterized.TestCase):

  _DEFAULT_HPARAMS = {
      'fc_layers': [32, 16],
      'dropout': 0.1,
      'activation_fn': 'swish',
      'feelers_version': 'v1',
      'feelers_v2_output_channels': 3,
      'feelers_v2_kernel_size': 5,
  }

  @parameterized.parameters(([],), ([1],), ([5],), ([5, 10],))
  def test_falken_network(self, batch_dims):
    brain_spec = specs.BrainSpec(test_data.brain_spec())
    net = networks.FalkenNetwork(brain_spec, dict(self._DEFAULT_HPARAMS))

    obs = test_data.observation_data(10, [0, 0, 0])
    scalar_nest = brain_spec.observation_spec.tfa_value(obs)

    def _size(dims):
      size = 1
      for d in dims:
        size *= d
      return size

    def _safe_concat(l, t):
      """Concat that works for empty lists."""
      if not l:
        return t
      return tf.concat([l, t], axis=0)

    def _clone_to_batch(tensor, batch_dims):
      t = tf.stack([tensor] * _size(batch_dims))
      new_dims = _safe_concat(batch_dims, tensor.shape)
      return tf.reshape(t, new_dims)

    batch_nest = tf.nest.map_structure(lambda t: _clone_to_batch(t, batch_dims),
                                       scalar_nest)

    distribution_nest, _ = net(batch_nest)

    sampled = tf.nest.map_structure(lambda s: s.sample(), distribution_nest)
    def _has_shape(d1, s):
      batch_shape = d1.shape
      spec_shape = _safe_concat(batch_dims, s.shape)
      self.assertEqual(batch_shape, spec_shape)
    tf.nest.map_structure(
        _has_shape, sampled, brain_spec.action_spec.tfa_spec)

  def test_minimal_joystick_action(self):
    """Test if a single joystick action is handled correctly."""
    brain_spec = brain_pb2.BrainSpec()
    text_format.Parse("""
        observation_spec {
          player {
            position {
            }
            rotation {
            }
          }
          global_entities {
            position {
            }
            rotation {
            }
          }
        }
        action_spec {
          actions {
            name: "joyAction"
            joystick {
              axes_mode: DELTA_PITCH_YAW
              controlled_entity: "player"
            }
          }
        }
        """, brain_spec)
    py_spec = specs.BrainSpec(brain_spec)
    net = networks.FalkenNetwork(
        py_spec,
        dict(fc_layers=[32, 16], dropout=0.1, activation_fn='swish'))
    data = observation_pb2.ObservationData()
    text_format.Parse("""
      player {
        position {}
        rotation {}
      }
      global_entities {
        position {}
        rotation {}
      }
      """, data)
    tf_data = py_spec.observation_spec.tfa_value(data)

    distributions, _ = net(tf_data)

    distributions = tf.nest.flatten(distributions)
    # The network weights are randomly initialized so the output value is
    # indeterminate at test time.
    self.assertLen(distributions, 1)
    self.assertEqual(distributions[0].sample().numpy().shape, (2,))

  @parameterized.named_parameters(
      ('FeelersV1', 'v1'),
      ('FeelersV2', 'v2'))
  @mock.patch.object(weights_initializer.WeightsInitializer,
                     'initialize_layer_or_model')
  def test_initialize_falken_network_weights(self, feelers_version,
                                             mock_initialize_layer_or_model):
    """Test initialization of layers owned by the network."""
    hparams = dict(self._DEFAULT_HPARAMS)
    hparams['feelers_version'] = feelers_version
    network = networks.FalkenNetwork(
        specs.BrainSpec(test_data.brain_spec()), hparams)
    network.initialize_weights()
    mock_initialize_layer_or_model.has_calls(
        mock.call(network._preprocessor),
        mock.call(network._mlp),
        mock.call(network._postprocessor))


class HelperFunctionTests(parameterized.TestCase):

  def test_get_dropout(self):
    hparams = dict(fc_layers=[128, 128])
    hparams['dropout'] = 0.1
    self.assertEqual(
        networks._get_dropout(hparams), [0.1, 0.1])
    hparams['dropout'] = [0.1, 0.2]
    self.assertEqual(
        networks._get_dropout(hparams), [0.1, 0.2])
    hparams['dropout'] = None
    self.assertEqual(networks._get_dropout(hparams), [None, None])

  def test_get_activation_fn(self):
    hparams = dict(activation_fn='tanh')
    self.assertEqual(
        networks._get_activation_fn(hparams),
        tf.keras.activations.tanh)

if __name__ == '__main__':
  absltest.main()
