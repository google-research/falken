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
"""Test conversion from TensorFlow SavedModel to TFLite model."""

import collections
import tempfile
import typing

from absl.testing import absltest
from learner import test_data
from learner.brains import networks
from learner.brains import saved_model_to_tflite_model
from learner.brains import specs
import tensorflow as tf
from tf_agents.agents.behavioral_cloning import behavioral_cloning_agent
from tf_agents.policies import policy_saver
from tf_agents.trajectories import time_step as ts

# pylint: disable=g-bad-import-order
import common.generate_flatbuffers  # pylint: disable=unused-import
from generated_flatbuffers.tflite import Model
from generated_flatbuffers.tflite import Tensor
from generated_flatbuffers.tflite import TensorType


class MockTensor(tf.Tensor):

  def __init__(self, name):
    self._name = name

  @property
  def name(self):
    return self._name

MockTensorSpec = collections.namedtuple('MockTensorSpec', ['name'])
MockFunction = collections.namedtuple(
    'MockFunction', ['inputs', 'structured_input_signature',
                     'outputs', 'structured_outputs'])


class SavedModelToTFLiteModelTest(absltest.TestCase):
  """Test saved_model_to_tflite_model."""

  def save_model(self) -> str:
    """Create and save a model.

    Returns:
      Path to the directory containing the saved model.
    """
    saved_model_path = tempfile.TemporaryDirectory().name
    brain_spec = specs.BrainSpec(test_data.brain_spec())
    agent = behavioral_cloning_agent.BehavioralCloningAgent(
        ts.time_step_spec(brain_spec.observation_spec.tfa_spec),
        brain_spec.action_spec.tfa_spec,
        cloning_network=networks.FalkenNetwork(
            brain_spec, {
                'dropout': None,
                'fc_layers': [32],
                'feelers_version': 'v1'
            }),
        optimizer=None,
        loss_fn=lambda *unused_args: None)
    agent.initialize()
    _ = agent.policy.variables()
    policy_saver.PolicySaver(agent.policy, batch_size=1).save(saved_model_path)
    return saved_model_path

  def test_rename_tflite_tensors(self):
    """Test patching TF Lite FlatBuffer Tensors with a new names."""
    tensor0 = Tensor.TensorT()
    tensor0.name = 'foo_bar_0'.encode(
        saved_model_to_tflite_model._FLATBUFFERS_TEXT_ENCODING)
    tensor1 = Tensor.TensorT()
    tensor1.name = 'bar_0_baz'.encode(
        saved_model_to_tflite_model._FLATBUFFERS_TEXT_ENCODING)
    tensor2 = Tensor.TensorT()
    tensor2.name = 'bar_1_baz'.encode(
        saved_model_to_tflite_model._FLATBUFFERS_TEXT_ENCODING)

    saved_model_to_tflite_model._rename_tflite_tensors(
        [tensor0, tensor1, tensor2], [0, 2],
        {'foo_bar_0': '0/foo/bar/0',
         'bar_1_baz': '0/bar/1/baz'})
    self.assertEqual(tensor0.name.decode(
        saved_model_to_tflite_model._FLATBUFFERS_TEXT_ENCODING), '0/foo/bar/0')
    self.assertEqual(tensor1.name.decode(
        saved_model_to_tflite_model._FLATBUFFERS_TEXT_ENCODING), 'bar_0_baz')
    self.assertEqual(tensor2.name.decode(
        saved_model_to_tflite_model._FLATBUFFERS_TEXT_ENCODING), '0/bar/1/baz')

  def test_tf_tensor_name_to_tflite_name(self):
    """Test converting TF tensor names to TF lite tensor names."""
    self.assertEqual(
        saved_model_to_tflite_model._tf_tensor_name_to_tflite_name('foo_bar:0'),
        'foo_bar')
    self.assertEqual(
        saved_model_to_tflite_model._tf_tensor_name_to_tflite_name('bar_baz:1'),
        'bar_baz')
    self.assertEqual(
        saved_model_to_tflite_model._tf_tensor_name_to_tflite_name('a_tensor'),
        'a_tensor')

  def test_tf_tensor_spec_name_to_tensor_name(self):
    """Test converting TF tensor spec names to tensor argument names."""
    self.assertEqual(
        saved_model_to_tflite_model._tf_tensor_spec_name_to_tensor_name(
            '0/foo/Bar/1/bazNumber'), 'foo_bar_1_baznumber')
    self.assertEqual(
        saved_model_to_tflite_model._tf_tensor_spec_name_to_tensor_name(
            'magic/Stuff'), 'magic_stuff')

  def test_create_tflite_to_tf_tensor_name_map(self):
    """Test creating a map of TF Lite to TF tensor spec name."""
    input_map, output_map = (
        saved_model_to_tflite_model._create_tflite_to_tf_tensor_name_map(
            MockFunction(
                inputs=[MockTensor('foo_0_bar:0'),
                        MockTensor('bish_0_bosh:0')],
                structured_input_signature=(
                    [MockTensorSpec('0/foo/0/bar')],
                    {'0/bish/0/bosh': MockTensorSpec('0/bish/0/bosh')}
                ),
                outputs=[MockTensor('identity_0:0'),
                         MockTensor('random_1:0')],
                structured_outputs={
                    'action': {'turn_key': MockTensor('action/turn_key'),
                               'open_door': MockTensor('action/open_door')}})))
    self.assertEqual(input_map, {'foo_0_bar': '0/foo/0/bar',
                                 'bish_0_bosh': '0/bish/0/bosh'})
    self.assertEqual(output_map, {'identity_0': 'action/open_door',
                                  'random_1': 'action/turn_key'})

  def test_create_tflite_to_tf_tensor_name_map_broken_function(self):
    """Fail with mismatched tensor spec to tensor name."""
    with self.assertRaises(AssertionError):
      saved_model_to_tflite_model._create_tflite_to_tf_tensor_name_map(
          MockFunction(
              inputs=[MockTensor('foo_0_bar'),
                      MockTensor('bish_0_bosh:0')],
              structured_input_signature=(
                  [MockTensorSpec('0/foo/0/bar')],
                  {'0/bish/0/bosh': MockTensorSpec('0/bish/0/bosh')}
              ),
              outputs=[], structured_outputs=[]))

  def test_convert_saved_model(self):
    """Convert a saved model to TF Lite model."""
    # Convert to a TFLite FlatBuffer.
    tflite_flatbuffer = saved_model_to_tflite_model.convert(
        self.save_model(), ['action'])
    model = Model.ModelT.InitFromObj(
        Model.Model.GetRootAsModel(tflite_flatbuffer, 0))
    self.assertLen(model.subgraphs, 1)
    subgraph = model.subgraphs[0]
    inputs_and_outputs = []
    for i in list(subgraph.inputs) + list(subgraph.outputs):
      tensor = subgraph.tensors[i]
      shape = tensor.shapeSignature if tensor.shapeSignature else tensor.shape
      inputs_and_outputs.append((
          tensor.name.decode(
              saved_model_to_tflite_model._FLATBUFFERS_TEXT_ENCODING),
          tensor.type, repr([d for d in shape])))

    self.assertCountEqual(
        inputs_and_outputs,
        [('0/discount',
          TensorType.TensorType.FLOAT32, '[1]'),
         ('0/observation/global_entities/0/position',
          TensorType.TensorType.FLOAT32, '[1, 3]'),
         ('0/observation/global_entities/0/rotation',
          TensorType.TensorType.FLOAT32, '[1, 4]'),
         ('0/observation/global_entities/1/position',
          TensorType.TensorType.FLOAT32, '[1, 3]'),
         ('0/observation/global_entities/1/rotation',
          TensorType.TensorType.FLOAT32, '[1, 4]'),
         ('0/observation/global_entities/2/drink',
          TensorType.TensorType.INT32, '[1, 1]'),
         ('0/observation/global_entities/2/evilness',
          TensorType.TensorType.FLOAT32, '[1, 1]'),
         ('0/observation/global_entities/2/position',
          TensorType.TensorType.FLOAT32, '[1, 3]'),
         ('0/observation/global_entities/2/rotation',
          TensorType.TensorType.FLOAT32, '[1, 4]'),
         ('0/observation/player/health',
          TensorType.TensorType.FLOAT32, '[1, 1]'),
         ('0/observation/player/position',
          TensorType.TensorType.FLOAT32, '[1, 3]'),
         ('0/observation/player/rotation',
          TensorType.TensorType.FLOAT32, '[1, 4]'),
         ('0/observation/player/feeler',
          TensorType.TensorType.FLOAT32, '[1, 3, 2]'),
         ('0/observation/camera/position',
          TensorType.TensorType.FLOAT32, '[1, 3]'),
         ('0/observation/camera/rotation',
          TensorType.TensorType.FLOAT32, '[1, 4]'),
         ('0/reward',
          TensorType.TensorType.FLOAT32, '[1]'),
         ('0/step_type',
          TensorType.TensorType.INT32, '[1]'),
         ('action/switch_weapon',
          TensorType.TensorType.INT32, '[1, 1]'),
         ('action/throttle',
          TensorType.TensorType.FLOAT32, '[1, 1]'),
         ('action/joy_pitch_yaw',
          TensorType.TensorType.FLOAT32, '[1, 2]'),
         ('action/joy_xz',
          TensorType.TensorType.FLOAT32, '[1, 2]'),
         ('action/joy_xz_world',
          TensorType.TensorType.FLOAT32, '[1, 2]'),
         ])

  def test_verify_function_output_order(self):
    """Verify the outputs of a tf.function.ConcreteFunction are sorted."""
    # Outputs of tf_agents policies are dictionaries with each key indicating
    # the name of the output (action) spec for the agent.
    # http://cs/piper///depot/google3/third_party/py/tf_agents/policies/\
    #   policy_saver.py;l=603;rcl=314434347
    # This dictionary (which is unsorted) is flattened and sorted when
    # serialized by tf.function.ConcreteFunction._build_call_outputs().

    # Expected input mapping from TFLite to TF inputs of the Lout module.
    expected_input_map = {'player_drink_booze': 'player/drink/booze',
                          'player_drink_bubbles': 'player/drink/bubbles',
                          'player_drink_water': 'player/drink/water'}
    # Test with all 2^N combinations of the following outputs.
    outputs = ['action/player/chestpuff', 'action/player/bowl',
               'action/player/stride', 'action/player/bluff',
               'action/player/swing']
    combinations = 2 ** len(outputs)
    for combination in range(1, combinations):
      selected = set()
      offset = 0
      bits = combination
      while bits:
        if bits & 1:
          selected.add(outputs[offset])
        offset += 1
        bits >>= 1

      class Lout(tf.Module):
        """Test module that provides a signature to serialize."""

        def __init__(self, output_names: typing.Iterable[str], **kwargs):
          """Initialize the module to generate the specified set of outputs.

          Args:
            output_names: Set of outputs to generate.
            **kwargs: Passed to tf.Module's initializer.
          """
          self._output_names = tf.constant(list(output_names))
          super(Lout, self).__init__(**kwargs)

        @tf.function(input_signature=[
            tf.TensorSpec((1,), dtype=tf.float32, name='player/drink/booze'),
            tf.TensorSpec((1,), dtype=tf.float32, name='player/drink/water'),
            tf.TensorSpec((1,), dtype=tf.int32, name='player/drink/bubbles'),
        ])
        def __call__(self, ethanol, h2o,
                     carbonation) -> typing.Iterable[tf.Tensor]:
          """Generate a set of outputs.

          The values of the outputs are _not_ used by the test case.

          Args:
            ethanol: Increases value of outputs.
            h2o: Dilutes value of outputs.
            carbonation: Modulates value of outputs.

          Returns:
            Dictionary of outputs whose names match _output_names.
          """
          output_tensors = {}
          for index, output in enumerate(self._output_names.numpy()):
            output_tensors[output.decode()] = tf.identity(
                (ethanol - h2o) * float(index % carbonation), name=output)
          return output_tensors

      # Call the function at least once to instance.
      lout = Lout(selected, name=f'Lout{combination}')
      _ = lout(tf.constant([0.2]), tf.constant([0.5]), tf.constant([5]))
      with tempfile.TemporaryDirectory() as temp_name:
        # Save and load the model to retrieve the graph signature.
        tf.saved_model.save(lout, temp_name)
        tf.keras.backend.clear_session()
        model = tf.saved_model.load(temp_name)
        graph = model.signatures['serving_default']
        input_map, output_map = (
            saved_model_to_tflite_model._create_tflite_to_tf_tensor_name_map(
                graph))

        # Output tensors should be sorted by tensor name.
        expected_output_map = {}
        for index, output in enumerate(sorted(selected)):
          expected_output_map[f'Identity_{index}'
                              if index > 0 else 'Identity'] = output

        self.assertCountEqual(input_map, expected_input_map)
        self.assertCountEqual(output_map, expected_output_map)


if __name__ == '__main__':
  absltest.main()
