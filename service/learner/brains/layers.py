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
"""Keras layers.

See: https://www.tensorflow.org/tutorials/customization/custom_layers
"""

import collections
import math

from learner.brains import weights_initializer

import tensorflow as tf
from tf_agents.networks import utils
from tf_agents.utils import nest_utils


FeelersLayerParameters = collections.namedtuple(
    'FeelersLayerParameters', ['kernel_size', 'kernel_count', 'pool_size'])


class Identity(tf.keras.layers.Layer,
               weights_initializer.NoWeightsInterface):
  """A layer that passes through the input unchanged."""

  def call(self, inputs):
    return inputs


class OneHot(tf.keras.layers.Layer,
             weights_initializer.NoWeightsInterface):
  """A layer that performs one-hot encoding of the input."""

  def __init__(self, depth):
    super().__init__()
    self.depth = depth

  def call(self, inputs):
    return tf.one_hot(inputs, self.depth, dtype=tf.float32)

  def get_config(self):
    return {'depth': self.depth}

  @classmethod
  def from_config(cls, config):
    return OneHot(config['depth'])


class Pad1D(tf.keras.layers.Layer,
            weights_initializer.NoWeightsInterface):
  """Pads a (batch, size, channels) tensor."""

  def __init__(self, padding, padding_mode, **kwargs):
    """Creates the padding layer.

    Args:
      padding: (pad_left, pad_right) pair. How many elements to add to
        both sides of the second dimension. If this is used for the very first
        layer of the feelers CNN, this can be thought as the number of feeler
        entries to add before the first feeler entry and after the last.
      padding_mode: One of 'zero', 'wrap', or 'repeat'.
        - zero: For padding out with zeroes.
        - wrap: For padding wrapping around the tensor.
        - repeat: For padding with repeated values from the tensor edges.
      **kwargs: Other kwargs that should be sent to the layer superclass.
    """
    self._padding = padding
    self._padding_mode = padding_mode
    super(Pad1D, self).__init__(**kwargs)

  def call(self, inputs):
    """Apply the layer into inputs.

    Args:
      inputs: A tensor with shape (batch, size, channels).

    Returns:
      Output tensor after applying the layer.
    """
    if self._padding_mode == 'zero':
      # tf.pad interprets this as paddings per dimension. We only need to pad
      # the middle dimension which is why the other two values are pairs of 0s.
      paddings = ((0, 0), self._padding, (0, 0))
      outputs = tf.pad(inputs, paddings)
    elif self._padding_mode == 'wrap':
      outputs = tf.concat([
          inputs[:, (-self._padding[0]):, :],
          inputs,
          inputs[:, :self._padding[1], :]
      ], axis=1)
    elif self._padding_mode == 'repeat':
      outputs = tf.concat([
          tf.repeat(inputs[:, :1, :], self._padding[0], axis=1),
          inputs,
          tf.repeat(inputs[:, -1:, :], self._padding[1], axis=1)
      ], axis=1)
    else:
      raise ValueError(f'Padding mode {self._padding_mode} not supported.')
    return outputs


class Feelers(tf.keras.layers.Layer,
              weights_initializer.ModelWeightsInitializer):
  """A Keras Layer that performs a series of 1D convolutions."""

  def get_config(self):
    return {
        'count': self.count,
        'channels': self.channels,
    }

  @classmethod
  def from_config(cls, config):
    return Feelers(config['count'], config['channels'])

  def __init__(self, count, channels):
    """Creates a module with one-dimensional convolutions.

    Args:
      count: int, number of different directions.
      channels: int, number of inputs reported for each direction.
    """
    super().__init__()
    self.count = count
    self.channels = channels
    # Organization of the distance data can be angles first, channels second,
    # or channels first, angles second.
    # E.g., for inputs with a shape of (angles, channels):
    # [ [23.0, 27.0], [1.0, 27.0], [23.0, 27.0] ]
    # would have three angles for rays detecting distances to two types of
    # objects.

    self.layers = []
    layer_width = self.count

    self.layers_parameters = [
        FeelersLayerParameters(kernel_size=5, kernel_count=3, pool_size=2),
        FeelersLayerParameters(kernel_size=5, kernel_count=3, pool_size=2),
        FeelersLayerParameters(kernel_size=5, kernel_count=2, pool_size=2),
        FeelersLayerParameters(kernel_size=5, kernel_count=2, pool_size=2),
    ]

    # Larger kernel sizes are appropriate for 1D convolutions.
    # Small number of filters to keep total parameter count low.
    for param in self.layers_parameters:
      width_after_next_layer = self._width_after_convolution(
          layer_width, param.kernel_size, param.pool_size)
      if width_after_next_layer < param.kernel_size:
        break
      self.layers.append(
          tf.keras.layers.Conv1D(
              filters=param.kernel_count, kernel_size=param.kernel_size))
      self.layers.append(
          tf.keras.layers.MaxPool1D(pool_size=param.pool_size))
      layer_width = width_after_next_layer

  def _width_after_convolution(self, input_width, kernel_size, pool_size):
    return int((input_width - kernel_size + 1) / pool_size)

  def call(self, inputs):
    """Apply convolutions to batched 2D input tensors."""
    squash = utils.BatchSquash(len(inputs.shape) - 2)
    # Reshape into single batch dim.

    net = squash.flatten(inputs)
    for layer in self.layers:
      net = layer(net)

    # Restore squashed batch dimensions.
    net = squash.unflatten(net)

    # Flatten out all non-batch dimensions.
    net = tf.reshape(net, tf.concat([inputs.shape[:-2], [-1]], axis=0))
    return net


class FeelersV2(tf.keras.layers.Layer,
                weights_initializer.WeightInitializationInterface):
  """A Keras Layer that performs a series of 1D convolutions.

  See go/updated-feelers for details.
  """

  def get_config(self):
    return {
        'count': self._count,
        'kernel_size': self._kernel_size,
        'channels': self._channels,
        'padding_mode': self._padding_mode,
    }

  @classmethod
  def from_config(cls, config):
    return FeelersV2(config['count'], config['kernel_size'], config['channels'],
                     config['padding_mode'])

  def __init__(self, count, kernel_size, channels, padding_mode):
    """Creates a module with one-dimensional convolutions.

    Args:
      count: int, number of different directions.
      kernel_size: int, number of kernels in all layers.
      channels: int, number of channels to use in all convo layer outputs.
      padding_mode: One of 'zero', 'wrap', 'repeat', as defined in Pad1D.
    """
    super().__init__()
    self._count = count
    self._kernel_size = kernel_size
    self._channels = channels
    self._padding_mode = padding_mode

    if kernel_size % 2 == 0:
      raise ValueError('Kernel size must be an odd number')

    self._cnn_layers = []

    input_count = count
    self._number_of_layers = 0
    while input_count > 4:
      next_power = self._next_power_of_two(input_count)
      # Padding inputs to the target size 'pad_to' ensures that after applying
      # convolution, the result is another power of two (< next_power).
      pad_to = next_power + kernel_size - 1
      pad_size = (pad_to - input_count) // 2
      # If pad size is odd, pad asymmetrically.
      extra_pad_right = (pad_to - input_count) % 2
      padding = (pad_size, pad_size + extra_pad_right)

      self._cnn_layers.append(Pad1D(padding, padding_mode))
      # Use valid to prevent automatic 0 padding.
      self._cnn_layers.append(
          tf.keras.layers.Conv1D(channels, kernel_size, padding='valid'))
      # The output of the CNN is now an exact power of 2, so pooling reduces
      # to the next smaller power of two.
      self._cnn_layers.append(tf.keras.layers.MaxPool1D(pool_size=2))
      input_count = next_power // 2
      self._number_of_layers += 1

  def _next_power_of_two(self, n):
    """Return the smallest power of two >= n."""
    if n == 0:
      return 1
    return int(2 ** math.ceil(math.log2(n)))

  def initialize_weights(self):
    """Initialize weights in the layer."""
    for layer in self._cnn_layers:
      weights_initializer.WeightsInitializer.initialize_layer_or_model(layer)

  def call(self, inputs):
    """Apply convolutions to batched 2D input tensors."""
    squash = utils.BatchSquash(len(inputs.shape) - 2)

    # Reshape into single batch dim.
    result = squash.flatten(inputs)
    for layer in self._cnn_layers:
      result = layer(result)

    # Restore squashed batch dimensions.
    return squash.unflatten(result)


class CreateNest(tf.keras.layers.Layer,
                 weights_initializer.WeightInitializationInterface):
  """Applies a nest of layers to single input."""

  def __init__(self, layer_nest):
    """Create CreateNest layer from a tf.nest of input layers."""
    self._layer_nest = layer_nest
    super().__init__()

  def initialize_weights(self):
    """Initialize weights in the layer."""
    tf.nest.map_structure(
        weights_initializer.WeightsInitializer.initialize_layer_or_model,
        self._layer_nest)

  def call(self, inputs):
    """Applies the nest of layers to an input tensor.

    This function produces a nested output tensor, where the shape of the
    nest corresponds to the shape of the layer_nest provided at creation.
    Each layer in the layer_nest is applied to the same input tensors.

    Args:
      inputs: A possibly nested input tensor.

    Returns:
      A nest of the same shape as layer_nest (plus whatever nesting is
      introduced by the layers in layer_nest).
    """
    return tf.nest.map_structure(lambda l: l(inputs), self._layer_nest)


class ComputeNumBatchDims(tf.keras.layers.Layer,
                          weights_initializer.NoWeightsInterface):
  """Compute the number of batch dimensions in tensor nest from spec."""

  def __init__(self, input_tensor_spec):
    """Takes a nest of tensor specs."""
    self._input_tensor_spec = input_tensor_spec
    super().__init__()

  def call(self, inputs):
    return nest_utils.get_outer_rank(inputs, self._input_tensor_spec)


class Error(Exception):
  pass


class FlattenAndConcatenate(tf.keras.layers.Layer,
                            weights_initializer.NoWeightsInterface):
  """A layer that flattens tensors and concatenates them.

  This layer removes outputs that are None.
  """

  def call(self, inputs):
    """Call the layer.

    Args:
      inputs: A pair (num_batch_dims, tensor_nest), where num_batch_dims is a
        scalar and tensor_nest is a batch of tensors.

    Returns:
      A tensor with a single non-batch dimension that flattens out the inputs.

    Raises:
      Error: If there are no input signals that are not None.
    """
    num_batch_dims, inputs = inputs  # unpack inputs.
    def _reshape_to_1d(t):
      # Keep batch dimensions and flatten the rest into as single dimension.
      batch_dims = tf.shape(t)[:num_batch_dims]
      dims = tf.concat([batch_dims, [-1]], axis=0)
      # We reshape to BATCH_DIM_1 x ... x BATCH_DIM_k x -1, which will make
      # the last dimension as large as required to accommodate the tensor.
      return tf.reshape(t, dims)
    inputs = [i for i in tf.nest.flatten(inputs) if i is not None]
    flat_tensors = [_reshape_to_1d(t) for t in inputs]
    float_tensors = [tf.cast(t, dtype=tf.float32) for t in flat_tensors]

    if not float_tensors:
      raise Error('No inputs that are not None.')

    return tf.concat(float_tensors, axis=-1)


class BatchNorm(tf.keras.layers.Layer,
                weights_initializer.WeightInitializationInterface):
  """A batchnorm that always processes data as a 2D tensor.

  This version transforms the input tensor into a rank 2 tensor with a inferred
  batch-size (via the spec) before applying the keras BatchNorm. Keras'
  BatchNorm seems to have trouble with different batch dimensions or alternation
  of batched and unbatched calls.
  """

  def __init__(self, spec):
    """Receives a tensor spec used to compute batch size."""
    self._spec = spec
    self._batch = tf.keras.layers.BatchNormalization()
    super().__init__()

  def initialize_weights(self):
    """Initialize weights in the layer."""
    weights_initializer.WeightsInitializer.initialize_layer_or_model(
        self._batch)

  def call(self, inputs, *args, **kwargs):
    """Applies keras batchnorm on a flattened 2D tensor (batch x data)."""
    batch_dims = inputs.shape[:nest_utils.get_outer_rank(inputs, self._spec)]
    num_batch_elems = tf.reduce_prod(batch_dims)
    transformed_inputs = tf.reshape(inputs, (num_batch_elems, -1))
    result = self._batch(transformed_inputs, *args, **kwargs)
    return tf.reshape(result, inputs.shape)
