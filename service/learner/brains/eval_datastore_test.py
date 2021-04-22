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

"""Tests for eval_datastore."""

from absl import logging
from absl.testing import absltest

from learner import test_data
from learner.brains import eval_datastore


class EvalDatastoreTest(absltest.TestCase):
  """Test EvalDatastore."""

  def test_create(self):
    """Validate an empty evaluation datastore's state."""
    ds = eval_datastore.EvalDatastore()
    self.assertEqual(ds.eval_frames, 0)
    self.assertEqual(ds.versions, [])
    self.assertEqual(list(ds.get_version_deltas()), [])

  def test_add_unbatched_trajectory(self):
    """Ensure an exception is raised if an unbatched trajectory is buffered."""
    ds = eval_datastore.EvalDatastore()
    with self.assertRaises(Exception):
      ds.add_trajectory(test_data.trajectory(health=1))

  def test_versions(self):
    """Test creating a number of evaluation data sets."""
    ds = eval_datastore.EvalDatastore()

    ds.add_trajectory(test_data.trajectory(health=1, add_batch_dimension=True))
    ds.add_trajectory(test_data.trajectory(health=2, add_batch_dimension=True))
    v1 = ds.create_version()
    self.assertEqual(ds.eval_frames, 2)
    self.assertEqual(ds.versions, [v1])

    ds.add_trajectory(test_data.trajectory(health=3, add_batch_dimension=True))
    v2 = ds.create_version()
    self.assertEqual(ds.eval_frames, 3)
    self.assertEqual(ds.versions, [v1, v2])

    v1_data = ds.get_version(v1)
    v2_data = ds.get_version(v2)

    logging.debug('v1_data is %s', v1_data)
    logging.debug('v2_data is %s', v2_data)

    self.assertEqual(list(v1_data[1]['player']['health']), [1.0, 2.0])
    self.assertEqual(list(v2_data[1]['player']['health']), [1.0, 2.0, 3.0])

    versions, dsizes, ddata = zip(*ds.get_version_deltas())
    self.assertEqual(versions, (v1, v2))
    self.assertEqual(dsizes, (2, 1))
    self.assertEqual(list(ddata[0][1]['player']['health']), [1.0, 2.0])
    self.assertEqual(list(ddata[1][1]['player']['health']), [3])

  def test_empty_and_prev_version(self):
    """Verify create_version does not create a new eval set when empty."""
    ds = eval_datastore.EvalDatastore()
    self.assertIsNone(ds.create_version())
    for i in range(8):
      ds.add_trajectory(test_data.trajectory(health=i,
                                             add_batch_dimension=True))
    v1 = ds.create_version()
    v2 = ds.create_version()
    self.assertEqual(v1, v2)

  def test_clear(self):
    """Test clearing a populated datastore."""
    ds = eval_datastore.EvalDatastore()
    for i in range(8):
      ds.add_trajectory(test_data.trajectory(health=i,
                                             add_batch_dimension=True))
    ds.clear()
    self.assertEmpty(ds.versions)
    self.assertEqual(ds.eval_frames, 0)
    self.assertEmpty(list(ds.get_version_deltas()))


if __name__ == '__main__':
  absltest.main()
