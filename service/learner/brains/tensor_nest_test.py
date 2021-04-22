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

from absl.testing import absltest
from learner.brains import tensor_nest

import tensorflow as tf


class TensorNestTest(absltest.TestCase):
  """Tests for the tensor_nest module."""

  def test_batch_size_valid_nest(self):
    """Get the batch size of a nest of tensors with the same batch size."""
    nest = {
        'a': {
            'b': tf.constant([[1, 2, 3], [4, 5, 6]]),
            'c': tf.constant([[7, 8, 9, 10], [11, 12, 13, 14]])
        },
    }
    self.assertEqual(2, tensor_nest.batch_size(nest))

  def test_batch_size_invalid_nest(self):
    """Get the batch size of a nest of tensors with different batch sizes."""
    nest = {
        'a': {
            'b': tf.constant([[1, 2, 3], [4, 5, 6], [7, 8, 9]]),
            'c': tf.constant([[7, 8, 9, 10], [11, 12, 13, 14]])
        },
    }
    self.assertRaisesRegex(
        tensor_nest.MismatchedBatchSizeError,
        'Tensors found in nest with mismatched batch sizes: {\'a\'.*}',
        tensor_nest.batch_size, nest)

  def test_batch_size_empty_nest(self):
    """Get the batch size of an empty tensor nest."""
    self.assertIsNone(tensor_nest.batch_size({}))

  def test_concatenate_batched(self):
    """Test the concatenation of a set of batched tensor nests."""
    nests = [
        {
            'a': {
                'b': tf.constant([[1, 2], [3, 4]]),
                'c': tf.constant([[9, 8, 7], [6, 5, 4]]),
            },
        },
        {
            'a': {
                'b': tf.constant([[5, 6]]),
                'c': tf.constant([[3, 2, 1]]),
            },
        },
    ]
    expected = {
        'a': {
            'b': tf.constant([[1, 2], [3, 4], [5, 6]]),
            'c': tf.constant([[9, 8, 7], [6, 5, 4], [3, 2, 1]]),
        },
    }
    tf.nest.assert_same_structure(tensor_nest.concatenate_batched(nests),
                                  expected, expand_composites=True)


if __name__ == '__main__':
  absltest.main()
