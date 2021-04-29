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

"""Tests for quaternion."""

import math

from absl.testing import absltest
from absl.testing import parameterized
from learner.brains import quaternion

import tensorflow as tf


class QuaternionTest(parameterized.TestCase):

  def assert_tensors_almost_equal(self, t1, t2, places=3):
    """Check that tensors are almost equal pointwise."""
    diff = t2 - t1
    min_val, max_val = tf.reduce_min(diff), tf.reduce_max(diff)
    self.assertAlmostEqual(min_val.numpy(), 0.0, places)
    self.assertAlmostEqual(max_val.numpy(), 0.0, places)

  @parameterized.parameters(0, 1, 2, 3)
  def test_quaternion_to_quaternion(self, batch_dims):
    """Check that to_quaternion is identity map for quaternions."""
    shape = [2] * batch_dims + [4]
    quaternions = tf.random.normal(shape)
    result = quaternion.to_quaternion(quaternions)
    self.assert_tensors_almost_equal(quaternions, result)

  @parameterized.parameters(0, 1, 2, 3)
  def test_vector_to_quaternion(self, batch_dims):
    """Check that to_quaternion preserves input vector components."""
    shape = [2] * batch_dims
    vectors = tf.random.normal(shape + [3])
    result = quaternion.to_quaternion(vectors)
    self.assertEqual(result.shape, shape + [4])
    vector_component = result[..., 0:3]
    w_component = result[..., 3]
    self.assert_tensors_almost_equal(vector_component, vectors)
    self.assert_tensors_almost_equal(w_component, tf.zeros_like(w_component))

  @parameterized.parameters(0, 1, 2, 3)
  def test_normalize(self, batch_dims):
    """Check that normalization works for non-zero values."""
    shape = [2] * batch_dims + [4]
    q = tf.random.normal(shape)
    result = quaternion.normalize(q)

    self.assertEqual(result.shape, shape)
    norms = tf.linalg.norm(result, axis=-1)
    self.assert_tensors_almost_equal(norms, tf.constant(1.0))

  @parameterized.parameters(0, 1, 2, 3)
  def test_normalize_zeros(self, batch_dims):
    """Check that normalization works for zero values."""
    shape = [2] * batch_dims + [4]
    q = tf.zeros(shape, tf.float32)
    result = quaternion.normalize(q)
    self.assertEqual(result.shape, shape)
    norms = tf.linalg.norm(result, axis=-1)
    self.assert_tensors_almost_equal(norms, 0.0)

  def test_identity(self):
    """Test that the identity quaternion is [0, 0, 0, 1]."""
    want = tf.constant([0.0, 0.0, 0.0, 1.0], tf.float32)
    self.assert_tensors_almost_equal(quaternion.identity(), want)

  @parameterized.parameters(0, 1, 2, 3)
  def test_conjugate(self, batch_dims):
    """Test that a quaternion multiplied with its conjugate yields identity."""
    shape = [2] * batch_dims + [4]
    q = quaternion.normalize(tf.random.normal(shape))
    qc = quaternion.conjugate(q)
    r1 = quaternion.multiply(q, qc)
    r2 = quaternion.multiply(qc, q)
    identity = quaternion.identity(tf.float32)
    self.assert_tensors_almost_equal(r1, identity)
    self.assert_tensors_almost_equal(r2, identity)

  def test_multiply(self):
    """Spot-check quaternion multiplication."""
    q1 = tf.constant([[1, 2, 3, 4],
                      [-0.25, 0.5, 0.75, 0.3]], dtype=tf.float32)
    q2 = tf.constant([[0.1, 0.1, 0.1, 0.9],
                      [-0.4, 0.25, -1, 0]], dtype=tf.float32)
    want = tf.constant(
        [[1.2, 2.4, 3, 3], [-0.8075, -0.475, -0.1625, 0.525]],
        dtype=tf.float32)
    result = quaternion.multiply(q1, q2)
    self.assert_tensors_almost_equal(result, want)

  def test_axis_angle_rotate(self):
    """Spot-check rotations via axis-angle specified quaternions."""
    pi = math.pi

    angle = tf.constant([
        pi / 2,
        -pi / 4,
        pi / 3], dtype=tf.float32)
    axis = tf.constant([
        [1, 0, 0],
        [0, 0, -1],
        [0, 0, 0]], dtype=tf.float32)  # Special case where axis is all zero.
    vector = tf.constant([
        [0, 0, 2],
        [1, 0, 0],
        [1, 0, 0]], dtype=tf.float32)

    result = quaternion.rotate(
        vector,
        quaternion.from_axis_angle(axis, angle))

    want = tf.constant([
        [0, -2, 0],
        [0.707, 0.707, 0],
        [1, 0, 0]], dtype=tf.float32)

    self.assert_tensors_almost_equal(result, want)

  @parameterized.parameters(0, 1, 2, 3)
  def test_axis_angle_rotate_batch(self, batch_dims):
    """Test that rotation and axis_angle work with batches."""
    shape = [2] * batch_dims
    angle = tf.random.normal(shape, dtype=tf.float32)
    axis = tf.random.normal(shape + [3], dtype=tf.float32)

    vector = tf.random.normal(shape + [3], dtype=tf.float32)
    vector /= tf.linalg.norm(vector)

    quaternions = quaternion.from_axis_angle(axis, angle)
    conjugates = quaternion.conjugate(quaternions)

    # Rotate by quaternion followed by conjugate gives identity rotation.
    result = quaternion.rotate(
        quaternion.rotate(vector, quaternions),
        conjugates)

    self.assert_tensors_almost_equal(result, vector)


if __name__ == '__main__':
  absltest.main()
