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
"""Tests WeightsInitializer."""

from unittest import mock
from absl.testing import absltest
from absl.testing import parameterized
from learner.brains import weights_initializer
import tensorflow as tf
from tf_agents.keras_layers import bias_layer
from tf_agents.networks import categorical_projection_network
from tf_agents.networks import nest_map
from tf_agents.networks import network
from tf_agents.networks import normal_projection_network
from tf_agents.networks import sequential
from tf_agents.specs import tensor_spec


class _ValidNoWeightsLayer(tf.keras.layers.Layer,
                           weights_initializer.NoWeightsInterface):
  """Layer with no weights."""
  pass


class _InvalidNoWeightsLayer(tf.keras.layers.Dense,
                             weights_initializer.NoWeightsInterface):
  """Layer incorrectly implements NoWeightsInterface as it has weights."""
  pass


class _TFAgentsUnknownTrainableNetwork(network.Network):
  """Unknown trainable TF Agents network (layer/model)."""

  def __init__(self, **kwargs):
    """Initialize the instance with a dense layer.

    Args:
      **kwargs: Passed to the super class.
    """
    self._dense = tf.keras.layers.Dense(16)
    super().__init__(**kwargs)

  def call(self, inputs, **kwargs):
    """Process the input tensor.

    Args:
      inputs: Tensor to process.
      **kwargs: Passed to the super class.

    Returns:
      (result, state) tuple where result is a tensor of the result
      and state is the network state.
    """
    return self._dense(inputs), kwargs.get('network_state', ())


class _CustomSequential(tf.keras.Sequential,
                        weights_initializer.ModelWeightsInitializer):
  """Sequential layer that implements ModelWeightsInitializer."""
  pass


class WeightsInitializerTest(parameterized.TestCase):
  """Test WeightsInitializer."""

  def test_initialize_weights(self):
    """Initialize a tensor with an initializer."""
    weights = tf.Variable([1, 2, 3], dtype=tf.float32)
    expected_minval = 10.0
    expected_maxval = 20.0

    weights_initializer.WeightsInitializer.initialize(
        weights,
        tf.keras.initializers.RandomUniform(minval=expected_minval,
                                            maxval=expected_maxval))
    for weight in weights.numpy():
      self.assertGreaterEqual(weight, expected_minval)
      self.assertLessEqual(weight, expected_maxval)

  @parameterized.named_parameters(
      ('Lambda', tf.keras.layers.Lambda(lambda _: None)),
      ('MaxPool1D', tf.keras.layers.MaxPool1D()),
      ('NoWeightsInterface', _ValidNoWeightsLayer()))
  def test_initialize_layer_with_no_weights(self, layer):
    """Ignore layers with no weights."""
    weights_initializer.WeightsInitializer.initialize_layer_or_model(layer)

  def test_initialize_invalid_layer_with_no_weights(self):
    """A layer with weights that implements NoWeightsInterface should raise."""
    layer = _InvalidNoWeightsLayer(16)
    _ = layer(tf.constant([[0.1, 0.2, 0.3]]))
    with self.assertRaises(AssertionError):
      weights_initializer.WeightsInitializer.initialize_layer_or_model(layer)

  @staticmethod
  def _fill_tensor(tensor, value):
    """Fill all elements of a tensor in-place.

    Args:
      tensor: Tensor to fill with a value.
      value: Value to set all elements of the tensor to.
    """
    tensor.assign(tf.fill(tensor.shape, value))

  @staticmethod
  def _fill_tensors(tensors, value):
    """Fill all elements of a set of tensors in-place.

    Args:
      tensors: Tensor instances to fill with a value.
      value: Value to set all elements of the tensor to.
    """
    for tensor in tensors:
      WeightsInitializerTest._fill_tensor(tensor, value)

  def _assert_all_elements_of_tensor_not_equal(self, tensor, value):
    """Assert that all elements of the specified tensor do not equal a value.

    Args:
      tensor: Tensor to check.
      value: Value that should not be in the tensor.
    """
    for element in tensor.numpy().flatten():
      self.assertNotAlmostEqual(element, value)

  def _assert_all_elements_of_tensors_not_equal(self, tensors, value):
    """Assert that all elements of the specified tensors do not equal a value.

    Args:
      tensors: Tensor instances to check.
      value: Value that should not be in the tensor.
    """
    for tensor in tensors:
      self._assert_all_elements_of_tensor_not_equal(tensor, value)

  @parameterized.named_parameters(
      ('Model', tf.keras.Sequential),
      ('TFAgentsNetwork', sequential.Sequential),
      ('UsingModelWeightsInitializer', _CustomSequential))
  def test_initialize_model_weights(self, sequential_class):
    """Initialize weights of layers within a model."""
    model = sequential_class(layers=[tf.keras.layers.Dense(16),
                                     tf.keras.layers.Dense(16)])
    _ = model(tf.constant([[1, 2, 3]]))  # Instance the model.
    weights_tensors = [layer.bias for layer in model.layers]
    self._fill_tensors(weights_tensors, 20.0)

    weights_initializer.WeightsInitializer.initialize_layer_or_model(model)
    self._assert_all_elements_of_tensors_not_equal(weights_tensors, 20.0)

  def test_initialize_layer_with_weight_reset(self):
    """Test initializing a mock layer with an initialize_weights method."""
    layer = mock.Mock(weights_initializer.WeightInitializationInterface)

    weights_initializer.WeightsInitializer.initialize_layer_or_model(
        layer)
    layer.initialize_weights.called_once()

  def test_initialize_unknown_layer_or_model(self):
    """Try initializing weights in an unsupported class."""
    with self.assertRaises(AssertionError):
      weights_initializer.WeightsInitializer.initialize_layer_or_model(list())

  def test_initialize_bias_weights(self):
    """Initialize a layer with bias weights."""
    layer = bias_layer.BiasLayer()
    _ = layer(tf.constant([1.0, 2.0, 3.0]))  # Instance the layer.
    self._fill_tensor(layer.bias, 24.0)

    weights_initializer.WeightsInitializer.initialize_layer_or_model(
        layer)
    self._assert_all_elements_of_tensor_not_equal(layer.bias, 24.0)

  @parameterized.named_parameters(
      ('Dense', (tf.keras.layers.Dense(32),
                 tf.constant([[0.0, 0.0, 0.0]]))),
      ('Conv1D', (tf.keras.layers.Conv1D(2, 2),
                  tf.constant([[[0.0, 0.0, 0.0]]]))))
  def test_initialize_kernel_and_bias_weights(self, layer_and_input):
    """Initialize a layer with kernel and bias weights."""
    layer, input_tensor = layer_and_input
    _ = layer(input_tensor)  # Instance the layer.
    self._fill_tensors([layer.kernel, layer.bias], 42.0)

    weights_initializer.WeightsInitializer.initialize_layer_or_model(
        layer)
    self._assert_all_elements_of_tensors_not_equal([layer.kernel, layer.bias],
                                                   42.0)

  def test_initialize_batch_normalization_layer(self):
    """Initialize a tf.keras.layers.BatchNormalization layer."""
    layer = tf.keras.layers.BatchNormalization()
    _ = layer(tf.constant([1.0, 2.0]))  # Instance the layer.
    weights_tensors = [layer.gamma, layer.beta, layer.moving_mean,
                       layer.moving_variance]
    self._fill_tensors(weights_tensors, 543.0)

    weights_initializer.WeightsInitializer.initialize_layer_or_model(
        layer)
    self._assert_all_elements_of_tensors_not_equal(weights_tensors, 543.0)

  def test_initialize_unknown_tfa_network_with_weights(self):
    """Raise an error if an unknown network is trainable."""
    input_tensor_spec = tensor_spec.TensorSpec((1, 3), tf.float32)
    layer = _TFAgentsUnknownTrainableNetwork(
        input_tensor_spec=input_tensor_spec)
    # Instance the layer.
    _ = layer.create_variables(input_tensor_spec=input_tensor_spec,
                               training=False)
    with self.assertRaises(AssertionError):
      weights_initializer.WeightsInitializer.initialize_layer_or_model(
          layer)

  def test_initialize_tfa_nest_map(self):
    """Initialize nested layers in a TF Agents NestMap."""
    nested_layers = {
        'player': {
            'one': tf.keras.layers.Dense(16),
            'two': tf.keras.layers.Dense(16)
        }
    }
    player_one_layer = nested_layers['player']['one']
    player_two_layer = nested_layers['player']['two']
    nested_tensor_specs = {
        'player': {
            'one': tensor_spec.TensorSpec((1, 3), tf.float32),
            'two': tensor_spec.TensorSpec((1, 6), tf.float32)
        }
    }
    layer = nest_map.NestMap(nested_layers=nested_layers,
                             input_spec=nested_tensor_specs)
    # Instance the layer.
    layer({
        'player': {
            'one': tf.constant([[2.0, 4.0, 6.0]]),
            'two': tf.constant([[5.0, 4.0, 6.0, 3.0, 7.0, 2.0]])
        }
    })
    weights_tensors = [player_one_layer.kernel,
                       player_one_layer.bias,
                       player_two_layer.kernel,
                       player_two_layer.bias]
    self._fill_tensors(weights_tensors, 246.0)

    weights_initializer.WeightsInitializer.initialize_layer_or_model(
        layer)
    self._assert_all_elements_of_tensors_not_equal(weights_tensors, 246.0)

  def test_initialize_tfa_categorical_projection_network(self):
    """Initialize weights in a TF Agents CategoricalProjectionNetwork."""
    layer = categorical_projection_network.CategoricalProjectionNetwork(
        tensor_spec.BoundedTensorSpec([1], tf.int32, 1, 5))
    _ = layer(tf.constant([[4]]), 1)  # Instance the layer.
    weights_tensors = [layer._projection_layer.kernel,
                       layer._projection_layer.bias]
    self._fill_tensors(weights_tensors, 42.0)

    weights_initializer.WeightsInitializer.initialize_layer_or_model(
        layer)
    self._assert_all_elements_of_tensors_not_equal(weights_tensors, 42.0)

  def test_initialize_normal_projection_net_no_state_dependent_stddev(self):
    """Initialize weights in a TF Agents NormalProjectionNetwork."""
    layer = normal_projection_network.NormalProjectionNetwork(
        tensor_spec.BoundedTensorSpec([1], tf.float32, 5.0, 10.0),
        state_dependent_std=False)
    _ = layer(tf.constant([[7.0]]), 1)  # Instance the layer.
    weights_tensors = [layer._means_projection_layer.kernel,
                       layer._means_projection_layer.bias,
                       layer._bias.bias]
    self._fill_tensors(weights_tensors, 42.0)

    weights_initializer.WeightsInitializer.initialize_layer_or_model(
        layer)
    self._assert_all_elements_of_tensors_not_equal(weights_tensors, 42.0)

  def test_initialize_tfa_normal_projection_net_state_dependent_stddev(self):
    """Initialize weights in a TF Agents NormalProjectionNetwork."""
    layer = normal_projection_network.NormalProjectionNetwork(
        tensor_spec.BoundedTensorSpec([1], tf.float32, 5.0, 10.0),
        state_dependent_std=True)
    _ = layer(tf.constant([[9.0]]), 1)  # Instance the layer.
    weights_tensors = [layer._means_projection_layer.kernel,
                       layer._means_projection_layer.bias,
                       layer._stddev_projection_layer.kernel,
                       layer._stddev_projection_layer.bias]
    self._fill_tensors(weights_tensors, 13.0)

    weights_initializer.WeightsInitializer.initialize_layer_or_model(
        layer)
    self._assert_all_elements_of_tensors_not_equal(weights_tensors, 13.0)


if __name__ == '__main__':
  absltest.main()
