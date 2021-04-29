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

"""Tests for google3.research.kernel.falken.service.learner.brains.egocentric."""

from absl.testing import absltest
from absl.testing import parameterized

from learner.brains import egocentric
from learner.brains import quaternion

import numpy as np
import tensorflow as tf


def tensor_to_list(t):
  if isinstance(t, list):
    return t
  return t.numpy().tolist()


def quat_from_string(quat_str):
  """Translate a string with rotation instructions to a quaternion.

  Args:
    quat_str: A rotation description executed left to right using 'y', 'p', 'r'
      to denote yaw pitch and roll.
      E.g.: y90/r10/p45.
  Returns:
    A quaternion executing the desired rotation in an ego-centric way, left to
    right. E.g., Yaw 90 degrees, then roll 10 degrees, then pitch 45.
  """
  q = tf.constant([0, 0, 0, 1], dtype=tf.float32)
  for q_str in quat_str.split('/'):
    if not q_str:
      continue
    if q_str[0] == 'y':  # yaw
      rel_axis = [0, 1, 0]
    elif q_str[0] == 'p':  # pitch
      rel_axis = [1, 0, 0]
    elif q_str[0] == 'r':  # roll
      rel_axis = [0, 0, 1]
    else:
      assert False

    angle = float(q_str[1:])
    # Find axis for ego-centric rotation.
    axis = quaternion.rotate(tf.constant(rel_axis, dtype=tf.float32), q)

    q = quaternion.multiply(
        quaternion.from_axis_angle(
            axis, np.radians(angle, dtype=np.float32)),
        q)
  return q


class EgocentricTest(parameterized.TestCase):

  def assertFloatTensorEqual(self, t1, t2):
    """Compares that two floating-point tensors are approximately equal.

    Note that floating point numbers should not be compared by equality when
    comparing results of arithmetic operations, but instead by near equality
    due to the imprecision of rounding.

    This comparison uses two decimal points of precision, which is sufficient
    for the purposes of this test which uses two decimal points of precision
    in floating point literals.

    Args:
      t1: A numeric tensor.
      t2: Another numeric tensor.
    """
    it1 = tf.math.round(t1 * 100)
    it2 = tf.math.round(t2 * 100)
    t1 = tf.cast(it1, t1.dtype) / 100
    t2 = tf.cast(it2, t1.dtype) / 100
    self.assertEqual(tensor_to_list(t1), tensor_to_list(t2))

  @parameterized.parameters(
      # Zero quaternion becomes identity.
      ([0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]),
      # Same as above but multiple batch dimensions.
      ([[[0.0, 0.0, 0.0, 0.0]]], [[[0.0, 0.0, 0.0, 1.0]]]),
      # Multiple batch dimensions with two elements.
      ([[[1.0, 1.0, 1.0, 1.0],
         [0.0, 0.0, 0.0, 0.0]]],
       [[[0.5, 0.5, 0.5, 0.5],
         [0.0, 0.0, 0.0, 1.0]]]),
      # Check for idempotency on normalized quaternions.
      ([0.0, 1.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0])
  )
  def test_normalize_quaternion(self, quat, expected):
    quat = tf.constant(quat, dtype=tf.float32)
    expected = tf.constant(expected, dtype=tf.float32)
    got = egocentric.normalize_and_fix_quaternion(quat)
    self.assertFloatTensorEqual(got, expected)

  @parameterized.parameters(
      # Idempotent on normalized vectors.
      ([0, 0, 1], [0, 0, 1]),
      # Preserves zero vectors.
      ([0, 0, 0], [0, 0, 0]),
      # Multiple elements, multiple batch-dimensions.
      ([[[[0, 0, 0]]]], [[[[0, 0, 0]]]]),
      ([4, 4, 2], [2/3, 2/3, 1/3])
  )
  def test_normalize_vector_non_nan(self, vec, expected):
    vec = tf.constant(vec, dtype=tf.float32)
    got = egocentric.normalize_vector_no_nan(vec)
    self.assertFloatTensorEqual(got, tf.constant(expected, dtype=tf.float32))

  @parameterized.parameters(
      # Multiple elements, multiple batch dimensions.
      ([[[0.3, -1], [0, 1]]], [[[1.0, -1], [1, 1]]]),
      # Multiple elements, single batch dimensions.
      ([0.0, -12, -0.0, 0], [1, -1, 1, 1])
  )
  def test_sign_no_zero(self, t, expected):
    t = tf.constant(t, dtype=tf.float32)
    got = egocentric.sign_no_zero(t)
    self.assertFloatTensorEqual(got, tf.constant(expected, dtype=tf.float32))

  def test_directions_orthogonal(self):
    random_quats = np.random.random((100, 4))
    random_quats = egocentric.normalize_and_fix_quaternion(random_quats)

    right_vecs = egocentric.right(random_quats)
    left_vecs = egocentric.left(random_quats)
    up_vecs = egocentric.up(random_quats)
    down_vecs = egocentric.down(random_quats)
    forward_vecs = egocentric.forward(random_quats)
    back_vecs = egocentric.back(random_quats)

    # Check that sides mirror each other.
    self.assertFloatTensorEqual(right_vecs, -left_vecs)
    self.assertFloatTensorEqual(up_vecs, -down_vecs)
    self.assertFloatTensorEqual(forward_vecs, -back_vecs)

    right_norm = tf.norm(right_vecs, axis=-1)
    up_norm = tf.norm(up_vecs, axis=-1)
    forward_norm = tf.norm(forward_vecs, axis=-1)

    # Check that lengths are all ones.
    self.assertFloatTensorEqual(right_norm, np.ones_like(right_norm))
    self.assertFloatTensorEqual(up_norm, np.ones_like(up_norm))
    self.assertFloatTensorEqual(forward_norm, np.ones_like(forward_norm))

    # Check orthogonality
    right_up = egocentric.vector_dot(right_vecs, up_vecs, False)
    forward_up = egocentric.vector_dot(forward_vecs, up_vecs, False)
    right_forward = egocentric.vector_dot(right_vecs, forward_vecs, False)

    self.assertFloatTensorEqual(right_up, np.zeros_like(right_up))
    self.assertFloatTensorEqual(forward_up, np.zeros_like(forward_up))
    self.assertFloatTensorEqual(right_forward, np.zeros_like(right_forward))

  @parameterized.named_parameters(
      ('Neutral', '', [0, 1], [0, 1]),
      ('Behind', 'y180', [0, -1], [0, -1]),
      ('Upside-down', 'r180', [0, 1], [0, 1]),
      ('Upside-down, facing back', 'p180', [0, -1], [0, -1]),
      ('Pitched down', 'p90', [0, 0], [1, 0]),
      ('Pitched up', 'p-90', [0, 0], [-1, 0]),
      ('Facing right', 'y90', [-1, 0], [0, 0]),
      ('Facing left', 'y-90', [1, 0], [0, 0]),
      ('Facing left, pitched up', 'y-90/p-90', [1, 0], [0, 0]),
      ('45 right', 'y45', [-0.707, 0.707], [0, 1]),
      ('45 up', 'p-45', [0, 1.0], [-0.707, 0.707]),
      ('upside down, 45 right', 'r180/y45', [-0.707, 0.707], [0, 1]),
      ('roll left, 45 right, roll right',
       'r90/y45/r-90', [0, 1], [-0.707, 0.707]),
  )
  def test_yaw_pitch_signal(self, quat_str, want_xz, want_yz):
    q = quat_from_string(quat_str)
    xz, yz, dist = egocentric.egocentric_signal(
        q,
        tf.constant([1, 1, 1], dtype=tf.float32),
        tf.constant([1, 1, 3], dtype=tf.float32))
    self.assertFloatTensorEqual(xz, tf.constant(want_xz, dtype=tf.float32))
    self.assertFloatTensorEqual(yz, tf.constant(want_yz, dtype=tf.float32))
    self.assertFloatTensorEqual(dist, 2 * tf.ones_like(dist))

  def test_yaw_pitch_signal_at_goal(self):
    xz, yz, dist = egocentric.egocentric_signal(
        quat_from_string(''),
        tf.constant([4, 12, 13], dtype=tf.float32),
        tf.constant([4, 12, 13], dtype=tf.float32))
    self.assertFloatTensorEqual(xz, tf.constant([0, 0], dtype=tf.float32))
    self.assertFloatTensorEqual(yz, tf.constant([0, 0], dtype=tf.float32))
    self.assertFloatTensorEqual(dist, tf.zeros_like(dist))

  def test_yaw_pitch_signal_batch(self):
    xz, yz, dist = egocentric.egocentric_signal(
        tf.stack([quat_from_string(''), quat_from_string('y90')]),
        tf.constant([[[4, 12, 13], [0, 0, 0]]], dtype=tf.float32),
        tf.constant([[[4, 12, 13], [0, 0, 2]]], dtype=tf.float32))
    self.assertFloatTensorEqual(
        xz, tf.constant([[[0, 0], [-1, 0]]], dtype=tf.float32))
    self.assertFloatTensorEqual(
        yz, tf.constant([[[0, 0], [0, 0]]], dtype=tf.float32))
    self.assertFloatTensorEqual(
        dist, tf.constant([[0, 2]], dtype=tf.float32))

  def test_camera_frame_transform_neutral(self):
    control_signal = tf.constant(
        [[0, 0],
         [0, 1],
         [-1, 1],
         [0.5, 0.5]],
        dtype=tf.float32)
    identity_quat = tf.constant(
        [[0, 0, 0, 1]] * len(control_signal), dtype=tf.float32)

    # Leave the control unchanged
    self.assertFloatTensorEqual(
        egocentric.egocentric_signal_to_target_frame(
            identity_quat, identity_quat, control_signal),
        control_signal)

  def test_camera_frame_transform_upside_down(self):
    control_signal = tf.constant(
        [[0, 0],
         [0, 1],
         [-1, 1],
         [0.5, 0.5]],
        dtype=tf.float32)

    # Being upside down reverses the x direction.
    want = tf.concat(
        [-control_signal[..., 0:1],
         control_signal[..., 1:2]],
        axis=-1)

    upside_down = tf.constant(
        [quat_from_string('r180').numpy().tolist()] * len(control_signal),
        dtype=tf.float32)
    identity = tf.constant(
        [quat_from_string('').numpy().tolist()] * len(control_signal),
        dtype=tf.float32)

    # Controlled entity upside down
    self.assertFloatTensorEqual(
        egocentric.egocentric_signal_to_target_frame(
            upside_down, identity, control_signal), want)

    # Camera upside down
    self.assertFloatTensorEqual(
        egocentric.egocentric_signal_to_target_frame(
            identity, upside_down, control_signal), want)

  @parameterized.parameters(
      ((4,), (2,), (2,)),
      ((10, 4,), (10, 2,), (10, 2,)),
      ((1, 4,), (1, 2,), (1, 2,)),
      ((10, 1, 4,), (10, 1, 2,), (10, 1, 2,)),
      ((50, 3, 4,), (50, 3, 2,), (50, 3, 2,)))
  def test_camera_frame_transform_batch(
      self, orientation_shape, direction_shape, want_shape):
    """Test different input shapes."""
    orientation = tf.ones(orientation_shape, dtype=tf.float32)
    direction = tf.ones(direction_shape, dtype=tf.float32)
    result = egocentric.egocentric_signal_to_target_frame(
        orientation, orientation, direction)
    self.assertEqual(tf.shape(result).numpy().tolist(), list(want_shape))

  @parameterized.named_parameters(
      ('player yawed east goes north',
       quat_from_string('y90'), quat_from_string('p45'), [0, 1], [1, 0]),
      ('player yawed east goes left',
       quat_from_string('y90'), quat_from_string('p45'), [-1, 0], [0, 1]),
      ('player yawed east, camera facing south, goes back',
       quat_from_string('y-90'), quat_from_string('y180/p45'),
       [0, -1], [-1, 0]),
      ('player upside down, yawed east, camera facing west, goes right',
       quat_from_string('y90/r180'), quat_from_string('y-90/p45'),
       [1, 0], [1, 0]),
      ('player neutral, camera pitched backwards, goes forward',
       quat_from_string(''), quat_from_string('p100'),
       [0, 1], [0, -1]),
      ('player upside down, camera pitched backwards, goes left',
       quat_from_string('r180'), quat_from_string('p100'),
       [-1, 0], [1, 0]),
      ('player lying down on their right side, camera neutral, goes left',
       quat_from_string('r-90'), quat_from_string(''),
       [-1, 0], [0, 0]),  # (0, 0) since player XZ and camera YZ are parallel.
  )
  def test_camera_frame_transform(
      self, orientation, camera_orientation, direction, want):
    direction = tf.constant(direction, dtype=tf.float32)
    want = tf.constant(want, dtype=tf.float32)
    output = egocentric.egocentric_signal_to_target_frame(
        orientation, camera_orientation, direction)
    self.assertFloatTensorEqual(output, want)

  @parameterized.parameters(
      ([0.0, 1.0], 0.0, 1.0),
      ([[[0.0, 1.0]]], [[0.0]], [[1.0]]),
      ([[0.5, 0.0], [-3.0, 0.0]], [-np.pi/2, np.pi/2], [0.5, 3.0]),
      (
          [  # vec: 2x2x2
              [
                  [0.5, 0.0],
                  [-3.0, 0.0]
              ],
              [
                  [0.0, 1.0],
                  [1, 1]
              ]
          ],
          [  # angle: 2x2
              [-np.pi/2, np.pi/2],
              [-0.0, -np.pi/4]
          ],
          [  # magnitude: 2x2
              [0.5, 3.0],
              [1.0, 1.41]
          ]
      ))
  def test_vec_angle_magnitude_translation(self, vec, angle, magnitude):
    vec = tf.constant(vec, tf.float32)
    angle = tf.constant(angle, tf.float32)
    magnitude = tf.constant(magnitude, tf.float32)

    # Direction vec -> (angle, magnitude)
    got_angle, got_magnitude = egocentric.vec_to_angle_magnitude(vec)
    self.assertFloatTensorEqual(got_angle, angle)
    self.assertFloatTensorEqual(got_magnitude, magnitude)

    # Direction (angle, magnitude) -> vec
    got_vec = egocentric.angle_magnitude_to_vec(angle, magnitude)
    self.assertFloatTensorEqual(got_vec, vec)


if __name__ == '__main__':
  absltest.main()
