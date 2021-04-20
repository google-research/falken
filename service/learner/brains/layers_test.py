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
"""Tests for the layers module."""

import math
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized

from learner.brains import layers
from learner.brains import weights_initializer

import tensorflow as tf


class LayersTest(parameterized.TestCase):

  def test_onehot(self):
    l = layers.OneHot(3)
    self.assertEqual(list(l(0)), [1, 0, 0])
    self.assertEqual(list(l(1)), [0, 1, 0])
    self.assertEqual(list(l(2)), [0, 0, 1])

  def test_identity(self):
    l = layers.Identity(3)
    self.assertEqual(l(2), 2)
    self.assertEqual(l([2, 3, 4]), [2, 3, 4])

  @parameterized.parameters('zero', 'wrap', 'repeat')
  def test_pad1d(self, padding_mode):
    input_tensor = tf.constant([
        [(0, 0, 0), (1, 1, 1), (2, 2, 2), (3, 3, 3), (4, 4, 4)],
        [(0, 1, 2), (2, 3, 4), (4, 5, 6), (6, 7, 8), (8, 9, 10)]])

    result = layers.Pad1D([1, 2], padding_mode)(input_tensor)

    if padding_mode == 'zero':
      expected = [[[0, 0, 0],
                   [0, 0, 0],
                   [1, 1, 1],
                   [2, 2, 2],
                   [3, 3, 3],
                   [4, 4, 4],
                   [0, 0, 0],
                   [0, 0, 0]],
                  [[0, 0, 0],
                   [0, 1, 2],
                   [2, 3, 4],
                   [4, 5, 6],
                   [6, 7, 8],
                   [8, 9, 10],
                   [0, 0, 0],
                   [0, 0, 0]]]
    elif padding_mode == 'wrap':
      expected = [[[4, 4, 4],
                   [0, 0, 0],
                   [1, 1, 1],
                   [2, 2, 2],
                   [3, 3, 3],
                   [4, 4, 4],
                   [0, 0, 0],
                   [1, 1, 1]],
                  [[8, 9, 10],
                   [0, 1, 2],
                   [2, 3, 4],
                   [4, 5, 6],
                   [6, 7, 8],
                   [8, 9, 10],
                   [0, 1, 2],
                   [2, 3, 4]]]
    else:
      expected = [[[0, 0, 0],
                   [0, 0, 0],
                   [1, 1, 1],
                   [2, 2, 2],
                   [3, 3, 3],
                   [4, 4, 4],
                   [4, 4, 4],
                   [4, 4, 4]],
                  [[0, 1, 2],
                   [0, 1, 2],
                   [2, 3, 4],
                   [4, 5, 6],
                   [6, 7, 8],
                   [8, 9, 10],
                   [8, 9, 10],
                   [8, 9, 10]]]

    self.assertEqual(result.numpy().tolist(), expected)

  @parameterized.parameters(
      ([],),
      ([1,],),
      ([10, 1],),
      ([20, 10, 1],))
  def test_feelers(self, batch_dims):
    count = 100
    channels = 6
    data = tf.random.normal(batch_dims + [count, channels])
    l = layers.Feelers(count, channels)
    # Intermediate convolution widths: 48, 22, 9
    # 9 outputs over two channels, so expect 18 outputs.
    self.assertEqual(l(data).shape[-1], 18)
    self.assertEqual(l(data).shape[:-1], batch_dims)

  @parameterized.parameters(['zero', 'wrap', 'repeat'])
  def test_new_feelers_architecture(self, padding_mode):
    batch_size = 2
    input_channels = 2
    output_channels = 3
    kernel_size = 5

    for input_count in range(300):
      input_shape = (batch_size, input_count, input_channels)
      input_tensor = tf.zeros(input_shape)
      layer = layers.FeelersV2(
          input_count, kernel_size, output_channels, padding_mode)

      # Verify number of layers grows logarithmically.
      self.assertEqual(layer._number_of_layers,
                       0 if input_count == 0
                       else max(0, math.ceil(math.log2(input_count)) - 2))

      outputs = layer(input_tensor)
      # Instead of making output_channels depend on input_count
      # we could add a single fully connected layer when input_count <= 4.
      expected_shape = (batch_size,
                        input_count if input_count <= 4 else 4,
                        input_channels if input_count <= 4 else output_channels)
      self.assertEqual(outputs.shape, expected_shape)

  @parameterized.parameters(
      ([],),
      ([1,],),
      ([10, 1],),
      ([20, 10, 1],))
  def test_new_feelers_batch_dims(self, batch_dims):
    count = 100
    input_channels = 6
    output_channels = 3
    data = tf.random.normal(batch_dims + [count, input_channels])
    layer = layers.FeelersV2(
        count, kernel_size=5, channels=output_channels, padding_mode='wrap')
    output = layer(data)

    # For any count >= 4, the feelers will produce exactly 4 outputs.
    output_count = 4
    self.assertEqual(output.shape, batch_dims + [output_count, output_channels])

  @mock.patch.object(weights_initializer.WeightsInitializer,
                     'initialize_layer_or_model')
  def test_new_feelers_initialize_weights(self, mock_initialize_layer_or_model):
    """Initialize feelers v2 layers weights."""
    feelers = layers.FeelersV2(100, kernel_size=5, channels=3,
                               padding_mode='wrap')
    feelers.initialize_weights()
    mock_initialize_layer_or_model.assert_has_calls(
        [mock.call(layer) for layer in feelers._cnn_layers])

  def test_flatten_and_concatenate(self):
    tensors = [
        tf.reshape(tf.range(0, 100), (4, 5, 5)),
        tf.reshape(tf.range(100, 140), (4, 5, 2)),
        tf.reshape(tf.range(140, 160), (4, 5, 1)),
    ]
    l = layers.FlattenAndConcatenate()

    f1 = l((1, tensors))
    f2 = l((2, tensors))

    self.assertEqual(f1.shape, (4, 40))
    self.assertEqual(f2.shape, (4, 5, 8))

    flat_f1 = f1.numpy().reshape(160,).tolist()
    flat_f2 = f2.numpy().reshape(160,).tolist()
    want = [float(i) for i in range(160)]

    self.assertEqual(sorted(flat_f1), want)
    self.assertEqual(sorted(flat_f2), want)

  def test_create_nest(self):
    l1 = tf.keras.layers.Lambda(lambda x: x * 3)
    l2 = tf.keras.layers.Lambda(lambda x: x * 2)
    l = layers.CreateNest((l1, l2))
    out = l(tf.constant([1, 2]))

    def _assert_tensor_nest_equal(got, want):
      tf.nest.map_structure(
          lambda x, y: self.assertEqual(x.numpy().tolist(), y.numpy().tolist()),
          got, want)

    _assert_tensor_nest_equal(
        out,
        (tf.constant([3, 6]), tf.constant([2, 4])))

  @mock.patch.object(weights_initializer.WeightsInitializer,
                     'initialize_layer_or_model')
  def test_nest_initialize_weights(self, mock_initialize_layer_or_model):
    """Initialize Nest layer weights."""
    layer1 = tf.keras.layers.Lambda(lambda x: x)
    layer2 = tf.keras.layers.Lambda(lambda x: x)
    nest_layer = layers.CreateNest({'player': {'one': layer1, 'two': layer2}})
    nest_layer.initialize_weights()
    mock_initialize_layer_or_model.assert_has_calls([mock.call(layer1),
                                                     mock.call(layer2)])

  def test_create_num_batch_dims(self):
    spec = (tf.TensorSpec((3, 2), dtype=tf.float32),
            tf.TensorSpec((), dtype=tf.float32))
    l = layers.ComputeNumBatchDims(spec)
    self.assertEqual(
        l((tf.ones((3, 2)), tf.ones(()))),
        0)
    self.assertEqual(
        l((tf.ones((10, 3, 2)), tf.ones((10,)))),
        1)
    self.assertEqual(
        l((tf.ones((5, 10, 3, 2)), tf.ones((5, 10,)))),
        2)

  @parameterized.parameters(
      [(), ()],
      [(5,), (5,)],
      [(5, 10), (5,)],
      [(5,), (5, 10)],
      [(20, 10, 5), ()],
      [(20, 10, 5), (20, 10, 5)])
  def test_batch_norm(self, batch_size, shape):
    tensor = tf.ones(batch_size + shape, dtype=tf.float32)
    batch_norm = layers.BatchNorm(tf.TensorSpec(shape, dtype=tf.float32))
    output = batch_norm(tensor)
    self.assertEqual(output.shape, batch_size + shape)

  @mock.patch.object(weights_initializer.WeightsInitializer,
                     'initialize_layer_or_model')
  def test_batch_norm_initialize_weights(self, mock_initialize_layer_or_model):
    """Initialize BatchNorm weights."""
    batch_norm = layers.BatchNorm(tf.TensorSpec((5, 10), dtype=tf.float32))
    batch_norm.initialize_weights()
    mock_initialize_layer_or_model.assert_called_once_with(batch_norm._batch)

if __name__ == '__main__':
  absltest.main()
