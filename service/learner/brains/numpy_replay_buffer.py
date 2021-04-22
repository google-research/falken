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
"""A simple replay buffer backed by numpy arrays with fast inserts."""

from learner.brains import tensor_nest

import numpy as np
import tensorflow as tf


class Error(Exception):
  pass


class NumpyReplayBuffer:
  """A simple replay buffer backed by numpy arrays.

  Elements are replaced in FIFO order. Note that after elements are added,
  a new dataset must be created.
  """

  def __init__(self, spec, capacity):
    """Create a new replay buffer.

    Args:
      spec: A nest of TensorSpec or BoundedTensorSpec objects.
      capacity: Maximum elements to store in the buffer.
    """
    def _CreateBuffer(spec):
      """Create a buffer tensor from a single tensorspec."""
      shape = (capacity,) + spec.shape
      return np.zeros(shape, dtype=spec.dtype.as_numpy_dtype())
    self._buffer = tf.nest.map_structure(_CreateBuffer, spec)
    self._size = 0  # Elements in buffer.
    self._rr_ptr = 0  # Fifo-pointer to the next element to overwrite.
    self._spec = spec  # Spec nest
    self._capacity = capacity  # Size of the backing numpy arrays.

  def Clear(self):
    """Clear the replay buffer."""
    def _Clear(buf):
      """Reset the specified numpy array to zeros.

      Args:
        buf: Numpy array to clear to zeros.
      """
      buf.fill(0)
    tf.nest.map_structure(_Clear, self._buffer)
    self._size = 0
    self._rr_ptr = 0

  def Add(self, nested_tensor):
    """Add an input of arbitrary length to the buffer.

    Args:
      nested_tensor: A tensor nest where the first dimension corresponds to
        the length of the input. (Must be at least one)
    """
    size = tensor_nest.batch_size(nested_tensor)
    def _Update(buf, t):
      """Update buffer buf from tensor t."""
      buf_start = self._rr_ptr  # Pointer to the buffer start.
      t_start = 0  # Pointer to the input_tensor
      todo = size  # Number of elements to copy
      while todo > 0:  # Repeatedly copy until end of buffer.
        buf_end = min(self._capacity, buf_start + todo)
        buf_len = (buf_end - buf_start)
        t_end = t_start + buf_len
        buf[buf_start:buf_end] = t[t_start:t_end]

        buf_start = (buf_start + buf_len) % self._capacity
        t_start += buf_len
        todo -= buf_len
    tf.nest.map_structure(_Update, self._buffer, nested_tensor)
    # Update size of the buffer.
    self._size = min(self._capacity, self._size + size)
    # Update round robin pointer.
    self._rr_ptr = (self._rr_ptr + size) % self._capacity

  @property
  def size(self):
    return self._size

  def Gather(self):
    """Return contents as a single nested tensor."""
    if not self._size:
      raise Error('Cannot gather empty buffer.')
    def _Shorten(buffer_tensor):  # Cut off empty parts of the buffer.
      return buffer_tensor[:self._size]
    return tf.nest.map_structure(_Shorten, self._buffer)

  def AsDataset(self):
    """Return contents as a single-shot dataset.

    Note: If elements are added to the replay buffer a new dataset needs to be
    created.

    Returns:
      A tf.data.Dataset representing the contents of the buffer.
    """
    return tf.data.Dataset.from_tensor_slices(self.Gather())
