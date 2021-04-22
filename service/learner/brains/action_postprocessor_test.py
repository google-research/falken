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

"""Tests for action_postprocessor."""


from absl.testing import absltest
from google.protobuf import text_format
from learner import test_data
from learner.brains import action_postprocessor
from learner.brains import specs
import tensorflow as tf
from tf_agents.specs import tensor_spec

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import action_pb2


class ActionPostprocessorTest(absltest.TestCase):

  def test_action_postprocessor(self):
    """Test basic operation of the action postprocessor."""
    brain_spec = specs.BrainSpec(test_data.brain_spec())
    hparams = dict()

    processor = action_postprocessor.ActionPostprocessor(brain_spec, hparams)
    observations = tf.nest.map_structure(
        tf.constant,
        brain_spec.observation_spec.tfa_value(
            test_data.observation_data(50, [0.0, 0.0, 0.0])))

    # Fictitious network output.
    net = tf.constant([1.0, 2.0, 3.0], tf.float32)
    output, _ = processor(net, observations=observations)
    action_spec = brain_spec.action_spec.tfa_spec

    def _check_equal_shape(t_spec, distribution):
      print(t_spec, distribution)
      self.assertEqual(t_spec.shape, distribution.sample().shape)

    tf.nest.map_structure(_check_equal_shape, action_spec, output)

  def test_joystick_action_projection(self):
    spec = action_pb2.JoystickType()
    text_format.Parse(
        """
        axes_mode: DIRECTION_XZ
        controlled_entity: "player"
        control_frame: "camera"
        """,
        spec)
    tf_spec = tensor_spec.BoundedTensorSpec(
        shape=(1, 2),
        dtype=tf.float32,
        minimum=-1.0,
        maximum=1.0)

    proj = action_postprocessor.JoystickActionProjection(
        spec, tf_spec)

    observations = {
        'player': {
            'position': tf.constant([0.0, 0.0, 0.0], tf.float32),
            'rotation': tf.constant([0.0, 0.0, 0.0, 1.0], tf.float32),
        },
        'camera': {
            'position': tf.constant([0.0, 0.0, 0.0], tf.float32),
            'rotation': tf.constant([0.3, 0.7, -0.3, 0.7], tf.float32),
        }
    }
    forward = tf.constant([0, 1.0], tf.float32)

    output, _ = proj(tf.zeros((1,), tf.float32), observations, 0,
                     lambda x: forward)

    got = [round(v, 2) for v in output.mean().numpy().tolist()[0]]
    self.assertEqual(got, [-1.0, 0.0])


if __name__ == '__main__':
  absltest.main()
