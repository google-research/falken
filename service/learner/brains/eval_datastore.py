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

"""Storage for incrementing versioned sets of eval data."""

from learner.brains import tensor_nest


class EvalDatastore:
  """Stores versioned sets of eval data in chunks.

  This class stores an incrementally growing evaluation dataset containing
  tf_agents Trajectories. Newly added data is first stored in a temporary
  buffer. Once the 'create_version' function is called, a new version label
  is returned that can be used to retrieve all submitted data up to this
  point.

  Usage:
    e = EvalDatastore()
    e.add_trajectory(t1)
    e.add_trajectory(t2)
    v1 = e.create_version()
    e.add_trajectory(t3)
    v2 = e.create_version()

    b1 = e.get_version(v1)  // contains t1, t2
    b2 = e.get_version(v2)  // contains t1, t2, t3
  """

  def __init__(self):
    """Initialize an empty datastore."""
    self._versions = []
    self._eval_frames = 0

    self._buffer = []
    self._buffer_eval_frames = 0
    self._chunks = []
    self._chunk_ids = {}

  def _version_id(self, chunk_index):
    """Get the version of the specified chunk.

    Args:
      chunk_index: Chunk to query.

    Returns:
      Version ID.
    """
    return chunk_index

  def _chunk_index(self, version_id):
    """Get the index of the chunk associated with the specified version.

    Args:
      version_id: ID of the version.

    Returns:
      Chunk index.
    """
    return version_id

  @property
  def versions(self):
    """Get a list of IDs (integers) for each version in the datastore."""
    return self._versions[:]

  @property
  def eval_frames(self):
    """Get the number of versioned evaluation frames."""
    return self._eval_frames

  def add_trajectory(self, trajectory):
    """Add a new batched trajectory.

    Args:
      trajectory: TF Agents Trajectory instance to add to the datastore.
    """
    self._buffer_eval_frames += tensor_nest.batch_size(trajectory)
    self._buffer.append(trajectory)

  def _clear_buffer(self):
    """Clear the buffer used to aggregate trajectories for the next version."""
    self._buffer.clear()
    self._buffer_eval_frames = 0

  def clear(self):
    """Clear the contents of the buffer."""
    self._versions.clear()
    self._eval_frames = 0

    self._clear_buffer()
    self._chunks.clear()
    self._chunk_ids.clear()

  def create_version(self):
    """Create a new eval set version from buffer contents and return its id.

    Returns:
      A new version ID if data was added. The previous version ID if no data
      was added since the last version. None if the datastore is empty.
    """
    if not self._buffer:
      return self._versions[-1] if self._versions else None
    chunk = tensor_nest.concatenate_batched(self._buffer)
    self._eval_frames += self._buffer_eval_frames
    self._clear_buffer()

    self._chunks.append(chunk)
    version_id = self._version_id(len(self._chunks) - 1)
    self._versions.append(version_id)
    return version_id

  def get_version_deltas(self):
    """Return delta chunks of data that make up successive versions.

    Returns:
      An iterable with entries (version_id, delta_size, delta_data).
    """
    sizes = map(tensor_nest.batch_size, self._chunks)
    return zip(self._versions, sizes, self._chunks)

  def get_version(self, version):
    """Retrieve the eval data associated with the indicated version.

    Args:
      version: The version to retrieve the set in.

    Returns:
      Nest of TF Agents Trajectory instances that contains a batch of eval-set
      data for the requested version.
    """
    chunk_index = self._chunk_index(version)
    chunks = self._chunks[:chunk_index + 1]
    return tensor_nest.concatenate_batched(chunks)
