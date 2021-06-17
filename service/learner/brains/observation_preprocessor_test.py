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
"""Tests for observation_preprocessor."""

import math

from absl.testing import absltest
from absl.testing import parameterized
from google.protobuf import text_format
from learner import test_data
from learner.brains import observation_preprocessor
from learner.brains import tfa_specs
import numpy as np
import tensorflow as tf

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import brain_pb2
import observation_pb2


def get_hparams(feelers_version):
  return dict(
      always_compute_egocentric=True, feelers_version=feelers_version,
      feelers_v2_output_channels=3, feelers_v2_kernel_size=5)


class ObservationPreprocessorTest(parameterized.TestCase):

  @parameterized.parameters([
      ('v1', 'default'), ('v2', 'default'), ('v2', 'wrap')])
  def test_preproc(self, feelers_version, yaw_range):
    spec_proto = test_data.brain_spec()
    if yaw_range == 'wrap':
      # Force yaw_angles to loop around 360 degrees.
      for field in spec_proto.observation_spec.player.entity_fields:
        if field.HasField('feeler'):
          for i, yaw in enumerate(
              np.linspace(0, math.pi, len(field.feeler.yaw_angles))):
            field.feeler.yaw_angles[i] = yaw

    spec = tfa_specs.BrainSpec(spec_proto)

    obs_preproc = observation_preprocessor.ObservationPreprocessor(
        spec, get_hparams(feelers_version))
    data = test_data.observation_data(50, [0.0, 0.0, 0.0])

    # Set camera position / rotation.
    data.camera.position.x = data.player.position.x
    data.camera.position.y = data.player.position.y
    data.camera.position.z = data.player.position.z
    data.camera.rotation.x = 0
    data.camera.rotation.y = 0
    data.camera.rotation.z = 1  # 180 degrees rotated around z
    data.camera.rotation.w = 0

    tfa_val = spec.observation_spec.tfa_value(data)

    # Apply preprocessing layers to tf_val
    preprocessed, _ = obs_preproc(tfa_val)  # Ignore state component.
    preprocessed = preprocessed.numpy().tolist()

    def _dist(d):
      """Preprocess distances to match observation preprocessor."""
      return np.log(d + 1)

    want = [
        0.0,                 # global_entities/0/drink - one-hot, category 0
        0.0,                 # global_entities/0/drink - one-hot, category 1
        1.0,                 # global_entities/0/drink - one-hot, category 2
        2 * (66 / 100) - 1,  # global_entities/0/evilness
        1,                   # player/feeler
        1.1,                 # player/feeler
        2,                   # player/feeler
        2.1,                 # player/feeler
        3,                   # player/feeler
        3.1,                 # player/feeler
        2 * (50 / 100) - 1,  # player/health
        0.0,                 # XZ-angle camera to entity1
        0.0,                 # YZ-angle camera to entity1
        _dist(1.0),          # distance camera to entity1
        0.0,                 # XZ-angle camera to entity2
        -math.pi/2,          # YZ-angle camera to entity2
        _dist(1.0),          # distance camera to entity2
        math.pi/2,           # XZ-angle camera to entity3
        0.0,                 # YZ-angle camera to entity3
        _dist(2.0),          # distance camera to entity3
        0.0,                 # XZ-angle player to entity1
        0.0,                 # YZ-angle player to entity1
        _dist(1.0),          # distance player to entity1
        0.0,                 # XZ-angle player to entity2
        math.pi/2,           # YZ-angle player to entity2
        _dist(1.0),          # distance player to entity2
        -math.pi/2,          # XZ-angle player to entity3
        0.0,                 # YZ-angle player to entity3
        _dist(2.0)           # distance player to entity3
    ]
    # We're rounding aggressively because batch norm adds noise.
    self.assertSequenceAlmostEqual(preprocessed, want, delta=0.05)

  @parameterized.parameters(['v1', 'v2'])
  def test_preproc_batch(self, feelers_version):
    spec = tfa_specs.BrainSpec(test_data.brain_spec())

    obs_preproc = observation_preprocessor.ObservationPreprocessor(
        spec, get_hparams(feelers_version))
    tfa_val = spec.observation_spec.tfa_value(
        test_data.observation_data(50, [0.0, 0.0, 0.0]))

    # Create batch of nested observations of size 5
    tfa_val = tf.nest.map_structure(
        lambda x: tf.stack([x, x, x, x, x]),
        tfa_val)

    # Apply preprocessing layers to tf_val
    preprocessed, _ = obs_preproc(tfa_val)  # Ignore state component.

    self.assertEqual(preprocessed.shape, (5, 29))

  @parameterized.parameters(['v1', 'v2'])
  def test_preproc_missing_player(self, feelers_version):
    proto_obs_spec = test_data.observation_spec()
    proto_obs_spec.ClearField('player')  # Delete player pos from spec.
    proto_act_spec = test_data.action_spec()  # Delete player references.

    # Remove joystick actions since they reference the player and camera.
    # The last 3 actions in the example model are joystick actions, so we
    # remove them from the list.
    del proto_act_spec.actions[-3:]

    brain_spec = test_data.brain_spec()
    brain_spec.observation_spec.CopyFrom(proto_obs_spec)
    brain_spec.action_spec.CopyFrom(proto_act_spec)

    spec = tfa_specs.BrainSpec(brain_spec)

    obs_preproc = observation_preprocessor.ObservationPreprocessor(
        spec, get_hparams(feelers_version))

    proto_data = test_data.observation_data(50, [0.0, 0.0, 0.0])
    proto_data.ClearField('player')  # Delete player from data.
    tfa_val = spec.observation_spec.tfa_value(proto_data)

    # Apply preprocessing layers to tf_val
    preprocessed, _ = obs_preproc(tfa_val)  # Ignore state component.
    preprocessed = preprocessed.numpy().tolist()

    want = [
        0.0,   # global_entities/0/drink - one-hot, categpry 0
        0.0,   # global_entities/0/drink - one-hot, category 1
        1.0,   # global_entities/0/drink - one-hot, category 2
        2 * (66.0 / 100.0) - 1,    # global_entities/0/evilness
    ]
    self.assertSequenceAlmostEqual(preprocessed, want, delta=0.05)

  @parameterized.product(dir_mode=['angle', 'unit_circle'],
                         dist_mode=['linear', 'log_plus_one'],
                         num_batch_dims=[0, 1, 2])
  def test_egocentric_modes(self, dir_mode, dist_mode, num_batch_dims):
    brain_spec = brain_pb2.BrainSpec()
    text_format.Parse(
        """
        observation_spec {
          player {
            position {}
            rotation {}
          }
          global_entities {
            position {}
            rotation {}
          }
        }
        action_spec {
          actions {
            name: "joy_pitch_yaw"
              joystick {
                axes_mode: DELTA_PITCH_YAW
                controlled_entity: "player"
              }
          }
        }
        """, brain_spec)
    hparams = {
        'egocentric_direction_mode': dir_mode,
        'egocentric_distance_mode': dist_mode,
    }

    spec = tfa_specs.BrainSpec(brain_spec)
    obs_preproc = observation_preprocessor.ObservationPreprocessor(
        spec, hparams)

    observation_data = observation_pb2.ObservationData()
    text_format.Parse(
        """
        player {
          position {}
          rotation {}
        }
        global_entities {
          position {
            x: 1
            y: -1
            z: 1
          }
          rotation {}
        }
        """, observation_data)
    tfa_val = spec.observation_spec.tfa_value(observation_data)

    # Stack into a batch of the requested size.
    for _ in range(num_batch_dims):
      tfa_val = tf.nest.map_structure(
          lambda x: tf.stack([x, x]), tfa_val)

    preprocessed, _ = obs_preproc(tfa_val)  # Ignore state component.
    preprocessed = preprocessed.numpy()

    # Unpack result of first batch.
    for _ in range(num_batch_dims):
      preprocessed = preprocessed[0]

    if dir_mode == 'angle':
      want = [-math.pi/4, math.pi/4]  # -45, 45 degree in radians.
      self.assertSequenceAlmostEqual(preprocessed[:len(want)], want, delta=0.05)
      preprocessed = preprocessed[len(want):]
    else:
      assert dir_mode == 'unit_circle'
      v = 1 / math.sqrt(2)  # X and Y component of 45 degree 2D unit vec.
      want = [v, v, -v, v]
      self.assertSequenceAlmostEqual(preprocessed[:len(want)], want, delta=0.05)
      preprocessed = preprocessed[len(want):]

    if dist_mode == 'linear':
      want = [math.sqrt(3)]  # diagonal of the unit cube.
      self.assertSequenceAlmostEqual(want, preprocessed, delta=0.05)
    else:
      assert dist_mode == 'log_plus_one'
      want = [math.log(math.sqrt(3) + 1)]
      self.assertSequenceAlmostEqual(want, preprocessed, delta=0.05)


if __name__ == '__main__':
  absltest.main()
