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
"""Tests for NumpyReplayBuffer."""

from absl.testing import absltest
from learner.brains import numpy_replay_buffer

import numpy as np
import tensorflow as tf


def test_spec():
  return {'a': tf.TensorSpec([], tf.int32),
          'b': tf.TensorSpec([2], tf.float32)}


def test_rb(capacity=10):
  spec = test_spec()
  return numpy_replay_buffer.NumpyReplayBuffer(spec=spec, capacity=capacity)


def test_data(value, size=1):
  spec = test_spec()
  def _array_from_spec(s):
    return np.ones((size,) + tuple(s.shape),
                   dtype=s.dtype.as_numpy_dtype()) * value
  return tf.nest.map_structure(_array_from_spec, spec)


class NumpyReplayBufferTest(absltest.TestCase):

  def test_replay_buffer_empty_raises(self):
    rb = test_rb()
    with self.assertRaises(numpy_replay_buffer.Error):
      rb.Gather()
    with self.assertRaises(numpy_replay_buffer.Error):
      rb.AsDataset()

  def test_add_data(self):
    rb = test_rb(10)
    self.assertEqual(rb.size, 0)
    rb.Add(test_data(1, 1))
    self.assertEqual(rb.size, 1)
    rb.Add(test_data(1, 3))
    self.assertEqual(rb.size, 4)
    rb.Add(test_data(1, 10))  # hit capacity
    self.assertEqual(rb.size, 10)

  def test_gather(self):
    rb = test_rb(10)
    rb.Add(test_data(1, 1))
    rb.Add(test_data(2, 2))
    want = {
        'a': np.array([1, 2, 2], dtype=np.int32),
        'b': np.array([[1, 1], [2, 2], [2, 2]], dtype=np.float32),
    }
    self.assertEqual(
        tf.nest.map_structure(lambda x: x.tolist(), want),
        tf.nest.map_structure(lambda x: x.tolist(), rb.Gather()))

  def test_round_robin(self):
    """Ensure fifo overwriting works."""
    rb = test_rb(10)
    rb.Add(test_data(1, 5))
    rb.Add(test_data(2, 20))
    rb.Add(test_data(3, 1))
    a_value = list(rb.Gather()['a'])
    self.assertEqual(
        a_value,
        [2, 2, 2, 2, 2, 3, 2, 2, 2, 2])

  def test_as_dataset(self):
    rb = test_rb(10)
    rb.Add(test_data(11, 1))
    rb.Add(test_data(13, 1))
    ds = list(rb.AsDataset())
    # With extra time dimension.
    self.assertEqual(ds[0]['a'], 11)
    self.assertEqual(ds[1]['a'], 13)

  def test_clear(self):
    """Test clearing a populated buffer."""
    rb = test_rb(5)
    rb.Add(test_data(2, 1))
    rb.Add(test_data(3, 1))
    rb.Clear()
    self.assertEqual(rb.size, 0)
    with self.assertRaises(numpy_replay_buffer.Error):
      rb.Gather()
    with self.assertRaises(numpy_replay_buffer.Error):
      rb.AsDataset()


if __name__ == '__main__':
  absltest.main()
