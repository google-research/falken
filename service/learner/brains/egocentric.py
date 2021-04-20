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

"""Transform 3D signals between egocentric, world-centric and camera-centric.

Falken policies are trained to operate on ego-centric observations and
ego-centric outputs which helps with quick generalization of behaviors. This
file contains the necessary transformation function to translate world-centric
observations inputs into ego-centric observation signals, and to translate
egocentric observation outputs into camera-centric control signals for
camera-relative controls.
"""

import collections

import tensorflow as tf
from tensorflow_graphics.geometry.transformation import quaternion
from tensorflow_graphics.math import vector


def vec_to_angle_magnitude(vec2d):
  """Translate a 2D direction to angle and magnitude.

  Considers (0,1) to be the forward direction with an angle of 0.

  Args:
    vec2d: A float tensor of size B1 x ... x Bn x 2.

  Returns:
    A pair (radians, magnitude) of batched scalar tensors B1 x ... x Bn.
  """
  # Note that we consider (0, 1) forward, so we swap x and y in the atan call.
  radians = tf.atan2(vec2d[..., 0], vec2d[..., 1])
  magnitude = tf.norm(vec2d, axis=-1)
  # We use unity conventions, so we need to negate radians to get the
  # clockwise angle.
  return -radians, magnitude


def angle_magnitude_to_vec(radians, magnitude):
  """Translate an angle and a magnitude to a vector.

  Translates an angle of zero to a scaled vector (0, 1).

  Args:
    radians: A batched scalar tensor B1 x ... x Bn representing the angle.
    magnitude: A batched scalar tensor B1 x ... x Bn representing magnitude.

  Returns:
    A float tensor of size B1 x ... x Bn x 2 representing a 2D vector.
  """
  radians = tf.expand_dims(radians, axis=-1)
  magnitude = tf.expand_dims(magnitude, axis=-1)
  # We use unity conventions, so we need to negate radians to get the
  # clockwise angle.
  return tf.concat(
      [tf.sin(-radians) * magnitude, tf.cos(-radians) * magnitude], axis=-1)


def normalize_and_fix_quaternion(quat):
  """Normalize quaternions and replace all-zero quats with identity.

  Args:
    quat: A (possibly batched) quaternion tensor of shape (A1,...,An, 4).
  Returns:
    A tensor of normalized quaternions of the same shape as the input.
  """
  identity_quat = tf.constant([0.0, 0.0, 0.0, 1.0], dtype=quat.dtype)
  is_zero = tf.expand_dims(
      tf.cast(tf.norm(quat, axis=-1) == 0.0, dtype=quat.dtype),
      axis=-1)
  fixed_quats = is_zero * identity_quat + (1 - is_zero) * quat
  return quaternion.normalize(fixed_quats)


def normalize_vector_no_nan(vec):
  """Normalize vectors, leaving zero-vectors as zero-vectors.

  Args:
    vec: A (possibly batched) vector tensor of shape (A1,...,An, 4).
  Returns:
    A tensor of normalized vectors of the same shape as the input.
  """
  return tf.math.divide_no_nan(
      vec, tf.expand_dims(tf.norm(vec, axis=-1), axis=-1))


def sign_no_zero(tensor):
  """Computes the sign function, but replaces 0s by 1s.

  Args:
    tensor: The input tensor.
  Returns:
    A tensor of the same shape as the input, containing only ones and zeros.
  """
  s = tf.sign(tensor)
  return tf.where(tf.equal(s, 0.0), tf.ones_like(s), s)


def up(orientation):
  """Return the positive-y direction relative to a reference frame.

  Args:
    orientation: A (possibly-batched) tensor of shape (A1,...,An, 4)
      representing orientations specified as quaternions.
  Returns:
    A tensor of shape (A1,...,An, 3) representing the requested direction in the
    input frames of reference.
  """
  return quaternion.rotate(
      tf.constant([0.0, 1.0, 0.0], orientation.dtype),
      orientation)


def down(orientation):
  """Return the negative-y direction relative to a reference frame.

  Args:
    orientation: A (possibly-batched) tensor of shape (A1,...,An, 4)
      representing orientations specified as quaternions.
  Returns:
    A tensor of shape (A1,...,An, 3) representing the requested direction in the
    input frames of reference.
  """
  return quaternion.rotate(
      tf.constant([0.0, -1.0, 0.0], orientation.dtype),
      orientation)


def right(orientation):
  """Return the positive-x direction relative to a reference frame.

  Args:
    orientation: A (possibly-batched) tensor of shape (A1,...,An, 4)
      representing orientations specified as quaternions.
  Returns:
    A tensor of shape (A1,...,An, 3) representing the requested direction in the
    input frames of reference.
  """
  return quaternion.rotate(
      tf.constant([1.0, 0.0, 0.0], orientation.dtype),
      orientation)


def left(orientation):
  """Return the negative-x direction relative to a reference frame.

  Args:
    orientation: A (possibly-batched) tensor of shape (A1,...,An, 4)
      representing orientations specified as quaternions.
  Returns:
    A tensor of shape (A1,...,An, 3) representing the requested direction in the
    input frames of reference.
  """
  return quaternion.rotate(
      tf.constant([-1.0, 0.0, 0.0], orientation.dtype),
      orientation)


def forward(orientation):
  """Return the positive-z direction relative to a reference frame.

  Args:
    orientation: A (possibly-batched) tensor of shape (A1,...,An, 4)
      representing orientations specified as quaternions.
  Returns:
    A tensor of shape (A1,...,An, 3) representing the requested direction in the
    input frames of reference.
  """
  return quaternion.rotate(
      tf.constant([0.0, 0.0, 1.0], orientation.dtype),
      orientation)


def back(orientation):
  """Return the negative-z direction relative to a reference frame.

  Args:
    orientation: A (possibly-batched) tensor of shape (A1,...,An, 4)
      representing orientations specified as quaternions.
  Returns:
    A tensor of shape (A1,...,An, 3) representing the requested direction in the
    input frames of reference.
  """
  return quaternion.rotate(
      tf.constant([0.0, 0.0, -1.0], orientation.dtype),
      orientation)


EgocentricSignal = collections.namedtuple(
    'EgocentricSignal', [
        # Tensor of size [A1,...,An, 3] indicating the direction to the goal
        # projected onto the local reference frame XZ plane.
        'xz_direction',
        # Tensor of size [A1,...,An, 3] indicating the direction to the goal
        # projected onto the local reference frame YZ plane.
        'yz_direction',
        # Tensor of size [A1,...,An] indicating the distance to the goal.
        'distance'])


def egocentric_signal(orientation,
                      position,
                      goal_position):
  """Computes ego-centric steering signals for a controlled object.

  Returns ego-centric direction to goal in the XZ and the YZ plane of the
  controlled object.

  Args:
    orientation: A (possibly batched) tensor of shape [A1, ..., An, 4]
      representing the orientation of controlled objects as quaternions.
    position: A (possibly batched) tensor of shape [A1, ..., An, 3] representing
      the position of controlled objects as vectors in world-space.
    goal_position: A (possibly batched) tensor of shape [A1, ..., An, 3]
      representing the position of a target object (e.g., another entity) for
      each batch entry as a vector in world-space.

  Returns:
    An EgocentricSignal with same batch sizes as the inputs.
  """
  orientation = normalize_and_fix_quaternion(orientation)
  direction_to_goal = goal_position - position
  distances = tf.norm(direction_to_goal, axis=-1)

  def _project_onto(target_vector, *vs):
    """Project target_vector onto remaining vectors."""
    return [vector.dot(v, target_vector, axis=-1) for v in vs]

  def _to_local_frame(orientation, direction):
    """Project a target vector into a local reference frame."""
    return _project_onto(
        direction,
        right(orientation),
        up(orientation),
        forward(orientation))

  x_local, y_local, z_local = _to_local_frame(orientation, direction_to_goal)

  def _construct_2d_direction(x, y):
    """Construct 2D unit vectors from batched x and y components."""
    return normalize_vector_no_nan(
        tf.concat([x, y], axis=-1))

  xz_rel_dir = _construct_2d_direction(x_local, z_local)
  yz_rel_dir = _construct_2d_direction(y_local, z_local)

  return EgocentricSignal(xz_rel_dir, yz_rel_dir, distances)


def egocentric_signal_to_target_frame(
    orientation,
    camera_orientation,
    egocentric_direction):
  """Translates an ego-centric signal to a camera-relative control frame.

  This takes a 2D directional control signal indicating a direction on the XZ
  axis of the controlled entity and translates it into the camera frame.
  Informally, the output will be (0, 1) if the control signal points away from
  or up relative-to the camera, and it will be (1, 0) if it points right
  relative to the camera.

  The signal is computed as follows: First, the camera-relative (0, 1) signal is
  projected onto the XZ plane of the controlled object by finding the
  intersection of the camera YZ plane with the controlled object's XZ plane.
  We then determine the angle alpha between this projected vector and the
  egocentric control signal. To obtain the camera-relative output signal,
  we rotate (0, 1) by the same angle alpha.

  For example, assume a top down camera, a controlled entity that is yawed by
  90 degrees (i.e., facing east) and a control signal of (1, 0), indicating a
  desired direction of "go right relative to current eastward facing" which is
  equivalent to "go south". Then the intersection of the camera YZ plane and
  the player XZ plane yields the vector (0, 0, 1), i.e., pushing forward should
  make the player move north. Since the egocentric control signal indicates a
  movement direction of 'south' the angle is 180 degrees. So, to obtain the
  camera-relative output signal, we rotate (0, 1) by 180 degrees and obtain
  (0, -1).

  Note that the magnitude of the output signal is the same as that of the
  input signal.

  Args:
    orientation: A (possibly batched) tensor of shape [A1, ..., An, 4]
      representing the orientation of controlled entities as quaternions.
      Orientations are relative to world-space.
    camera_orientation: A (possibly batched) tensor of shape [A1, ..., An, 4]
      representing the orientation of cameras that serve as frames of reference
      for controlling the entities.
      Orientations are relative to world-space.
    egocentric_direction: A (possibly batched) tensor of shape [A1, ..., An, 2]
      representing 2D control vectors that indicate a desired direction in the
      XZ plane of the controlled entities, relative to orientation.

  Returns:
    A (possibly batched) tensor of shape [A1, ..., An, 2] indicating a direction
    signal relative to the camera.
  """
  orientation = normalize_and_fix_quaternion(orientation)
  camera_orientation = normalize_and_fix_quaternion(camera_orientation)

  # Compute intersection of camera YZ plane and entity XZ plane.
  control_fwd = normalize_vector_no_nan(
      vector.cross(up(orientation),
                   left(camera_orientation), axis=-1))

  control_right = vector.cross(control_fwd, up(orientation))

  # If the camera is upside down, it's possible that the vectors point the
  # wrong way, so we check for that and possibly fix it.
  is_fwd = sign_no_zero(
      vector.dot(control_fwd, forward(camera_orientation)))
  is_right = sign_no_zero(
      vector.dot(control_right, right(camera_orientation)))

  control_fwd *= is_fwd
  control_right *= is_right

  # Turn the 2D control signal into a 3D signal.
  egocentric_direction_3d = tf.concat(
      [egocentric_direction[..., 0:1],                 # [X] component
       tf.zeros_like(egocentric_direction[..., 0:1]),  # [0]
       egocentric_direction[..., 1:2]], axis=-1)       # [Z] component

  # Compute the intended control direction in world-space.
  world_space_direction = quaternion.rotate(egocentric_direction_3d,
                                            orientation)

  # Project the desired world-space directions into a camera-relative control
  # frame.
  camera_control_vector_x = vector.dot(control_right, world_space_direction)
  camera_control_vector_y = vector.dot(control_fwd, world_space_direction)

  camera_control_vector = tf.concat([camera_control_vector_x,
                                     camera_control_vector_y], axis=-1)

  return camera_control_vector
