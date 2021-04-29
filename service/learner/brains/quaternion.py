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

"""Basic quaternion operations for representing 3D rotation."""

import tensorflow as tf


def to_quaternion(q):
  """Convert a 3D vector or quaternion to a quaternion.

  Note: Having a function that accepts both vectors and quaternions and always
  outputs a quaternion makes it easier to implement the Hamilton product which
  has geometric interpretations when either component is a vector or quaternion.

  Args:
    q: A tensor of batched 3D vectors or quaternions of shape B1 x ... x Bn x X,
      where X = 3 or 4.
  Returns:
    A tensor of shape B1 x ... x Bn x 4. If the input was a batch of 3D vectors,
    then the output is a batch of quaternions that have equivalent x, y, z
    components as the input vectors and where the w component is 0.
  """
  if q.shape[-1] == 4:
    return q
  assert q.shape[-1] == 3
  # Set the w component of a vector to zero to treat it as a quaternion.
  return tf.concat([q, tf.zeros_like(q)[..., -1:]], axis=-1)


def normalize(q):
  """Normalize a quaternion.

  Args:
    q: A tensor of batched quaternions of shape B1 x ... x Bn x 4.
  Returns:
    A tensor of shape B1 x ... x Bn x 4, which contains either the input
    quaternion divided by its L2 norm or a zero quaternion (if the norm was 0).
  """
  return tf.math.divide_no_nan(
      q, tf.expand_dims(tf.linalg.norm(q, axis=-1), axis=-1))


def multiply(q, r):
  """Compute the Hamilton product between two quaternions.

  Args:
    q: A tensor of batched 3D vectors or quaternions of shape B1 x ... x Bn x X,
      where X = 3 or 4. If X is 3, the 3D vectors are interpreted as quaternions
      by setting the w component to 0.
    r: Same as q.
  Returns:
    The Hamilton product q x r which has shape B1 x ... x Bn x 4.
  """

  # Taken from https://en.wikipedia.org/wiki/Quaternion#Hamilton_product
  q = to_quaternion(q)
  r = to_quaternion(r)
  b1, c1, d1, a1 = q[..., 0], q[..., 1], q[..., 2], q[..., 3]
  b2, c2, d2, a2 = r[..., 0], r[..., 1], r[..., 2], r[..., 3]

  w = a1*a2 - b1*b2 - c1*c2 - d1*d2
  x = a1*b2 + b1*a2 + c1*d2 - d1*c2
  y = a1*c2 - b1*d2 + c1*a2 + d1*b2
  z = a1*d2 + b1*c2 - c1*b2 + d1*a2

  return tf.stack([x, y, z, w], axis=-1)


def conjugate(q):
  """Return the conjugate of a quaternion tensor.

  Args:
    q: A tensor of batched quaternions of shape B1 x ... x Bn x 4.
  Returns:
    A tensor of batched quaternions of shape B1 x ... x Bn x 4 represnenting
    the conjugate of the input.
  """
  return tf.concat([-q[..., :3], q[..., 3:4]], axis=-1)


def rotate(v, q):
  """Rotate a vector tensor by a quaternion tensor.

  Args:
    v: A tensor of batched 3D vectors of shape B1 x ... x Bn x 3.
    q: A quaternion tensor fo shape B1 x ... x Bn x 4.
  Returns:
    A 3D vector tensor of shape B1 x ... x Bn x 3. If q is a unit quaternion
    (and hence represents a rotation), then the result is a tensor of batched
    3D vectors that represents each input vector multiplied by its corresponding
    quaternion.
  """
  return multiply(multiply(q, v), conjugate(q))[..., :3]


def from_axis_angle(axis, angle, angle_scalar=True):
  """Computes quaternion from an axis-angle representation.

  Args:
    axis: A tensor of batched 3D vectors of shape B1 x ... x Bn x 3.
    angle: A tensor of batched radians of shape B1 x ... x Bn or
      of shape B1 x ... x Bn x 1, depending on whether angle_scalar=True.
    angle_scalar: Whether the angle is supplied as a scalar or as a vector
      of size 1. This helps compatibility with tf_graphics calling conventions.
  Returns:
    The quaternion representing the indicated axis / angle rotation.
  """
  if angle_scalar:
    angle = tf.expand_dims(angle, axis=-1)

  # Normalize axis.
  axis = tf.math.divide_no_nan(
      axis,
      tf.expand_dims(tf.linalg.norm(axis, axis=-1), axis=-1))
  # Set angle to 0 in cases where axis is empty.
  axis_zero = tf.reduce_all(axis == tf.constant([0, 0, 0], axis.dtype), axis=-1)
  angle = tf.where(tf.expand_dims(axis_zero, axis=-1),
                   tf.zeros_like(angle), angle)
  return tf.concat(
      [axis * tf.sin(angle / 2), tf.cos(angle / 2)], axis=-1)


def identity(dtype=tf.float32):
  """Creates an identity quaternion.

  Args:
    dtype: Tensorflow data type.

  Returns:
    A quaternion [0, 0, 0, 1] in the requested dtype.
  """
  return tf.constant([0, 0, 0, 1], dtype)
