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

"""Methods that operator on nests of Tensor instances.

A tensor nest is a dictionary tree where the leaves are Tensor instances.

For example:

n = {'a': {'b': tf.constant([1, 2, 3]), 'c': tf.constant([3, 4])}}

is a nest where n['a']['b'] references tensor [1, 2, 3] and n['a']['b']
references tensor [3, 4].

See https://www.tensorflow.org/api_docs/python/tf/nest
"""

import tensorflow as tf


class MismatchedBatchSizeError(Exception):
  """Raised if tensors in a nest contain inconsistent batch sizes."""
  pass


def batch_size(tensor_nest):
  """Return outermost dimension of tensors in tensor nest.

  Args:
    tensor_nest: Nest (dictionary tree) of tensors to query. All tensors in the
      provided nest must have the same outermost dimension size.

  Returns:
    Nest (dictionary tree) of outer most dimensions (batch sizes) of each tensor
    in the nest. If the provided nest is empty, this method returns None.

    For example, given

    {
      'foo': {
        'bar': tf.constant([[1, 2, 3], [4, 5, 6]]),
        'baz': tf.constant([[7, 8], [9, 0]]),
      }
    }

    this returns 2 as the outer most dimension of all tensors in the nest is 2.

  Raises:
    MismatchedBatchSizeError: If tensors in the nest contain inconsistent batch
      sizes.
  """
  # Get the batch size of each tensor.
  batch_sizes_nest = tf.nest.map_structure(len, tensor_nest)

  # Validate that all batch sizes are the same.
  previous_size = None
  size = None
  for size in tf.nest.flatten(batch_sizes_nest):
    if previous_size and size != previous_size:
      raise MismatchedBatchSizeError(
          'Tensors found in nest with mismatched batch sizes: ' +
          str(batch_sizes_nest))
    previous_size = size

  return size


def concatenate_batched(tensor_nest_list):
  """Concatenate tensors along the batch dimension in the set of nests.

  Args:
    tensor_nest_list: List of tensor nests.

  Returns:
    A tensor nest that is the combination of the supplied tensor nests.

    For example, given:
    [{'a': {'b': Tensor([[1.0, 2.0], [3.0, 4.0]])}}
     {'a': {'b': Tensor([[4.0, 5.0]])}}]

    This method will return:
    {'a': {'b': Tensor([[1.0, 2.0], [3.0, 4.0], [4.0, 5.0]])}}
  """
  return tf.nest.map_structure(lambda *tensors: tf.concat(tensors, axis=0),
                               *tensor_nest_list)
