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

"""Tests for resource_id."""

from absl.testing import absltest
from absl.testing import parameterized
from data_store import resource_id

# Shared testcases to test translation back and forth between id_string
# and collection map representation. A missing value indicates an expected
# error result.
COMPUTE_FUNCTION_TESTCASES = [
    ({'A'}, 'A/0', {'A': '0'}),
    ({'A'}, 'A/0/B/1', None),
    ({'A'}, 'B/1/A/0', None),
    ({'A'}, None, {'A': '0', 'B': '1'}),
    ({'A': {'B'}}, 'A/0/B/1', {'A': '0', 'B': '1'}),
    ({'A': {'B', 'C'}}, 'A/0/B/1', {'A': '0', 'B': '1'}),
    ({'A': {'B', 'C'}}, 'A/0/C/2', {'A': '0', 'C': '2'}),
    ({'A': {'B': {'C'}}}, 'A/0/B/1/C/2', {'A': '0', 'B': '1', 'C': '2'}),
    ({'A': {'B': {'C'}}}, 'A/0/B/1/C/2/', None),  # trailing '/'
    ({'A': {'B': {'C'}}}, '/A/0/B/1/C/2', None),  # leading '/'
    ({'A': {'B': {'C'}}}, 'A//B/1/C/2', None),  # Empty element.
    ({'A': {'B': {'C'}}}, 'A/0//1/C/2', None),  # Empty collection.
    ({'A': {'B': {'C'}}}, '/A/B/1/C/2', None)  # Missing element.
]


class ResourceIdTest(parameterized.TestCase):

  @parameterized.parameters(*COMPUTE_FUNCTION_TESTCASES)
  def test_compute_collection_map(self, spec, id_string, collection_map):
    """Test translation of parts into a collection_map using a spec."""
    if id_string:  # Pick out relevant shared testcases.
      parts = id_string.split('/') if id_string else None
      if collection_map:
        self.assertEqual(
            resource_id.ResourceId._compute_collection_map(spec, parts),
            collection_map)
      else:
        with self.assertRaises(resource_id.InvalidResourceError):
          resource_id.ResourceId._compute_collection_map(spec, parts)

  @parameterized.parameters(*COMPUTE_FUNCTION_TESTCASES)
  def test_compute_parts(self, spec, id_string, collection_map):
    """Test translation of collection_map into parts using a spec."""
    if collection_map:  # Pick out relevant shared testcases.
      if id_string:
        parts = id_string.split('/') if id_string else None
        self.assertEqual(
            resource_id.ResourceId._compute_parts(
                spec, collection_map),
            parts)
      else:
        with self.assertRaises(resource_id.InvalidResourceError):
          resource_id.ResourceId._compute_parts(spec, collection_map)

  def test_specless_from_id_string(self):
    """Test that id strings can be translated into resource ids without spec."""
    self.assertEqual(
        resource_id.ResourceId(None, 'A/0/B/1').collection_map,
        {'A': '0', 'B': '1'})

  def test_specless_from_component_map(self):
    """Test that component map initialization fails if spec is not present."""
    with self.assertRaises(ValueError):
      # Can't translate from dict without spec.
      resource_id.ResourceId(None, A='0', B='1')

  def test_from_parts(self):
    """Test initialization from path components."""
    rid = resource_id.ResourceId({'A': {'B': None}}, ['A', '0', 'B', '1'])
    self.assertEqual(str(rid), 'A/0/B/1')
    self.assertEqual(rid.collection_map, {'A': '0', 'B': '1'})

  @parameterized.parameters(
      'projects/p0/brains/b0/sessions/s0/episodes/e0/chunks/0',
      'projects/p0/brains/b0/sessions/s0/episodes/e0',
      'projects/p0/brains/b0/sessions/s0/online_evaluations/e0',
      'projects/p0/brains/b0/sessions/s0/offline_evaluations/e0',
      'projects/p0/brains/b0/sessions/s0/assignments/a0',
      'projects/p0/brains/b0/sessions/s0/models/m0',
      'projects/p0/brains/b0/sessions/s0',
      'projects/p0/brains/b0/snapshots/s0',
      'projects/p0')
  def test_valid_falken_ids(self, rid):
    """Test that all relevant falken ID types are valid."""
    parsed = resource_id.FalkenResourceId(rid)
    self.assertNotEmpty(parsed.parts)
    self.assertNotEmpty(parsed.collection_map)


if __name__ == '__main__':
  absltest.main()
