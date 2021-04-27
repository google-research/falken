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
"""Converts Tensorflow to TF-Lite models preserving top level tensor names."""

import typing

import flatbuffers
import tensorflow as tf

# pylint: disable=g-bad-import-order
import common.generate_flatbuffers  # pylint: disable=unused-import
from tflite import Model
from tflite import SubGraph


# Encoding for strings in FlatBuffers.
_FLATBUFFERS_TEXT_ENCODING = 'utf-8'
# File identifier for TF Lite FlatBuffers.
_TFLITE_FILE_IDENTIFIER = 'TFL3'
# Prefix used in structured_input_signature for nested TensorSpecs which is
# stripped when converting to a concrete function argument.
_TF_FUNCTION_ARG_PREFIX = '0/'


def convert(saved_model_path: str,
            signature_keys: typing.List[str]) -> bytearray:
  """Convert a SavedModel proto to a TFLite model FlatBuffer.

  TFLiteConverter destructively changes tensor names when converting from
  a SavedModel proto. This class converts a SavedModel proto using
  TFLiteConverter and then patches the resultant TensorFlow Lite FlatBuffer
  with TensorSpec names from the original SavedModel proto.

  Args:
    saved_model_path: Directory containing the saved_model.pb file to
      convert.
    signature_keys: A list containing a *single* key that references the
      graph to convert.

  Returns:
    Binary array containing the TFLite FlatBuffer.
  """
  assert len(signature_keys) == 1
  model = tf.saved_model.load(saved_model_path)
  # Get the signature of the main function from the original model.
  main_graph = model.signatures[signature_keys[0]]

  converter = tf.lite.TFLiteConverter.from_concrete_functions([main_graph])
  converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS]
  converter.allow_custom_ops = True
  # Patch the TensorFlow Lite model with the original graph's signature.
  return _patch_tflite_model(converter.convert(), main_graph)


def _patch_tflite_model(tflite_flatbuffer: bytearray, main_graph) -> bytearray:
  """Create a patched TF Lite model with the specified function signature.

  Input parameters and output parameters in the specified TF Lite model are
  renamed to those matching the signature of the specified function / graph.

  Args:
    tflite_flatbuffer: TF Lite model FlatBuffer converted from a SavedModel
      proto.
    main_graph: tf.function.ConcreteFunction loaded from the same
      SavedModel proto used to create tflite_flatbuffer.

  Returns:
    A new TF Lite model FlatBuffer with input and output Tensor names specified
    by main_graph_signature.
  """
  inputs_map, outputs_map = _create_tflite_to_tf_tensor_name_map(main_graph)

  lite_model = Model.ModelT.InitFromObj(
      Model.Model.GetRootAsModel(tflite_flatbuffer, 0))

  # Per the schema //third_party/tensorflow/lite/schema/schema.fbs the 0th
  # graph is the main model.
  main_subgraph = lite_model.subgraphs[0]

  # Rename inputs and outputs.
  _rename_tflite_tensors(main_subgraph.tensors, main_subgraph.inputs,
                         inputs_map)
  _rename_tflite_tensors(main_subgraph.tensors, main_subgraph.outputs,
                         outputs_map)

  # Pack the updated FlatBuffer.
  builder = flatbuffers.Builder(0)
  builder.Finish(lite_model.Pack(builder),
                 file_identifier=_TFLITE_FILE_IDENTIFIER.encode(
                     _FLATBUFFERS_TEXT_ENCODING))
  return builder.Output()


def _rename_tflite_tensors(
    tensors: typing.List[SubGraph.SubGraphT],
    tensor_indices: typing.List[int],
    tflite_to_tf_names: typing.Dict[str, str]):
  """Patch Tensors in a TF Lite FlatBuffer with new names.

  Args:
    tensors: List of Tensors to patch in-place.
    tensor_indices: List of indexes that select the instances in the tensors
      list to patch.
    tflite_to_tf_names: Dictionary mapping old to new tensor names.
  """
  for index in tensor_indices:
    tensor = tensors[index]
    current_tensor_name = tensor.name.decode(_FLATBUFFERS_TEXT_ENCODING)
    assert current_tensor_name in tflite_to_tf_names, (
        f'Tensor name {current_tensor_name} not found in map '
        f'{tflite_to_tf_names}')
    replacement_tensor_name = tflite_to_tf_names[current_tensor_name]
    tensor.name = replacement_tensor_name.encode(_FLATBUFFERS_TEXT_ENCODING)


def _tf_tensor_name_to_tflite_name(tensor_tf_name: str) -> str:
  """Convert a TF tensor name to the format used by TFLiteConverter.

  Args:
    tensor_tf_name: Tensor name to convert.

  Returns:
    Converted tensor name.
  """
  # See get_tensor_name() in //third_party/tensorflow/lite/python/util.py
  return tensor_tf_name.split(':')[0]


def _tf_tensor_spec_name_to_tensor_name(tensor_spec_name: str) -> str:
  """Convert a TF TensorSpec name to the format used by Tensor arguments.

  Args:
    tensor_spec_name: TensorSpec name to convert.

  Returns:
    Converted tensor spec name.
  """
  if tensor_spec_name.startswith(_TF_FUNCTION_ARG_PREFIX):
    tensor_spec_name = tensor_spec_name[len(_TF_FUNCTION_ARG_PREFIX):]
  return tensor_spec_name.replace('/', '_').lower()


def _create_tflite_to_tf_tensor_name_map(graph) -> typing.Tuple[
    typing.Dict[str, str], typing.Dict[str, str]]:
  """Create a map of TF Lite tensor names to the original TF tensor spec names.

  Args:
    graph: tf.function.ConcreteFunction loaded from a SavedModel proto.

  Returns:
    Tuple of (inputs_tflite_name_to_tf_map, outputs_tflite_name_to_tf_map)
    where each entry of the tuple is a dictionary of TF TensorSpec names
    indexed by TF Lite tensor names for inputs and outputs respectively.
  """
  # Create a mapping of input TensorSpec names to Tensor / argument names.
  arg_name_to_structured_input_name = {}
  args, kwargs = graph.structured_input_signature
  for input_tensor_spec in list(args) + list(kwargs.values()):
    # Add :0 to the name as all inputs are not positional.
    arg_name_to_structured_input_name[
        _tf_tensor_spec_name_to_tensor_name(input_tensor_spec.name) + ':0'] = (
            input_tensor_spec.name)

  # Map each TFLite input name to the original TensorSpec name.
  inputs_tflite_name_to_tf_map = {}
  for input_tensor in graph.inputs:
    # Ignore all unknown / unnamed arguments.
    if input_tensor.name.startswith('unknown'):
      continue
    assert input_tensor.name in arg_name_to_structured_input_name, (
        f'Tensor named {input_tensor.name} not found in converted '
        f'structured input names {arg_name_to_structured_input_name}.')
    inputs_tflite_name_to_tf_map[
        _tf_tensor_name_to_tflite_name(input_tensor.name)] = (
            arg_name_to_structured_input_name[input_tensor.name])

  # This follows the same logic in
  # tf.function.ConcreteFunction._build_call_outputs() to order
  # output_signatures in the same order as the generated output tensors
  # making it possible to map from each output Tensor to the associated
  # TensorSpec that generated it.
  outputs_tflite_name_to_tf_map = {}
  for output_tensor, output_tensor_spec in zip(
      graph.outputs, tf.nest.flatten(graph.structured_outputs,
                                     expand_composites=True)):
    outputs_tflite_name_to_tf_map[_tf_tensor_name_to_tflite_name(
        output_tensor.name)] = output_tensor_spec.name
  return (inputs_tflite_name_to_tf_map, outputs_tflite_name_to_tf_map)
