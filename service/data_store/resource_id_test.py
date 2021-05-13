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

import collections

from absl.testing import absltest
from absl.testing import parameterized
from data_store import resource_id

TestCase = collections.namedtuple(
    'TestCase',
    ['spec', 'attribute_map', 'id_string', 'collection_map'])

# Shared testcases to test translation back and forth between id_string
# and collection map representation. A missing value indicates an expected
# error result.
COMPUTE_FUNCTION_TESTCASES = [
    # Tests without attributes.
    TestCase(
        spec={'A'},
        attribute_map=None,
        id_string='A/0',
        collection_map={'A': '0'}),
    TestCase(
        spec={'A'},
        attribute_map=None,
        id_string='A/0/B/1',
        collection_map=None),
    TestCase(
        spec={'A'},
        attribute_map=None,
        id_string='B/1/A/0',
        collection_map=None),
    TestCase(
        spec={'A'},
        attribute_map=None,
        id_string=None,
        collection_map={'A': '0', 'B': '1'}),
    TestCase(
        spec={'A': {'B'}},
        attribute_map=None,
        id_string='A/0/B/1',
        collection_map={'A': '0', 'B': '1'}),
    TestCase(
        spec={'A': {'B', 'C'}},
        attribute_map=None,
        id_string='A/0/B/1',
        collection_map={'A': '0', 'B': '1'}),
    TestCase(
        spec={'A': {'B', 'C'}},
        attribute_map=None,
        id_string='A/0/C/2',
        collection_map={'A': '0', 'C': '2'}),
    TestCase(
        spec={'A': {'B': {'C'}}},
        attribute_map=None,
        id_string='A/0/B/1/C/2',
        collection_map={'A': '0', 'B': '1', 'C': '2'}),
    TestCase(  # trailing '/'
        spec={'A': {'B': {'C'}}},
        attribute_map=None,
        id_string='A/0/B/1/C/2/',
        collection_map=None),
    TestCase(  # leading '/'
        spec={'A': {'B': {'C'}}},
        attribute_map=None,
        id_string='/A/0/B/1/C/2',
        collection_map=None),
    TestCase(  # Empty element.
        spec={'A': {'B': {'C'}}},
        attribute_map=None,
        id_string='A//B/1/C/2',
        collection_map=None),
    TestCase(  # Empty collection.
        spec={'A': {'B': {'C'}}},
        attribute_map=None,
        id_string='A/0//1/C/2',
        collection_map=None),
    TestCase(  # Missing element.
        spec={'A': {'B': {'C'}}},
        attribute_map=None,
        id_string='/A/B/1/C/2',
        collection_map=None),

    # Tests with attributes.
    TestCase(
        spec={'A'},
        attribute_map={'A': 'b'},
        id_string='A/0/b',
        collection_map={'A': '0', resource_id.ATTRIBUTE: 'b'}),
    TestCase(
        spec={'A'},
        attribute_map=None,
        id_string=None,
        collection_map={'A': '0', resource_id.ATTRIBUTE: 'b'}),
    TestCase(
        spec={'A'},
        attribute_map=None,
        id_string='A/0/b',
        collection_map=None),
    TestCase(
        spec={'A': {'B': {'C'}}},
        attribute_map={'C': 'test_attr'},
        id_string='A/1/B/2/C/3/test_attr',
        collection_map={
            'A': '1', 'B': '2', 'C': '3', resource_id.ATTRIBUTE: 'test_attr'}),
]


class ResourceSpecTest(parameterized.TestCase):

  @parameterized.parameters(
      ({'A': {'B': {'A'}}}, None),
      ({'A': {'B': {'C'}}}, {'C': 'A'}),
      ({'A': {'B': {'C'}}}, {'A': 'C'}),
      ({'A': {'B': {'C'}}}, {'A': 'D', 'B': 'D'}),
  )
  def test_invalid_specs(self, spec, accessor_map):
    with self.assertRaises(resource_id.InvalidSpecError):
      resource_id.ResourceSpec(spec, accessor_map)


class ResourceIdTest(parameterized.TestCase):

  @parameterized.parameters(*COMPUTE_FUNCTION_TESTCASES)
  def test_compute_collection_map(
      self, spec, attribute_map, id_string, collection_map):
    """Test translation of parts into a collection_map using a spec."""
    spec = resource_id.ResourceSpec(spec, attribute_map=attribute_map)
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
  def test_compute_parts(self, spec, attribute_map, id_string, collection_map):
    """Test translation of collection_map into parts using a spec."""
    spec = resource_id.ResourceSpec(spec, attribute_map=attribute_map)
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

  def test_from_string_attribute_not_supported(self):
    spec = resource_id.ResourceSpec(
        {'foo'},
        attribute_map={'foo': 'cherry'})
    resource_id.ResourceId(spec, 'foo/1/cherry')  # cherry is a valid attribute
    with self.assertRaisesRegex(resource_id.InvalidResourceError,
                                '.*"foo".*"banana".*'):
      resource_id.ResourceId(spec, 'foo/1/banana')

  def test_from_map_attribute_not_supported(self):
    spec = resource_id.ResourceSpec(
        {'foo'},
        attribute_map={'foo': 'cherry'})
    resource_id.ResourceId(
        spec,
        foo='1',
        attribute='cherry')
    with self.assertRaisesRegex(resource_id.InvalidResourceError,
                                '.*"foo".*"banana".*'):
      resource_id.ResourceId(
          spec,
          foo='1',
          attribute='banana')

  def test_specless_from_id_string(self):
    """Test that id strings can be translated into resource ids without spec."""
    self.assertEqual(
        resource_id.ResourceId(None, 'A/0/B/1').collection_map,
        resource_id.ResourceSpec({'A': '0', 'B': '1'}))

  def test_specless_from_component_map(self):
    """Test that component map initialization fails if spec is not present."""
    with self.assertRaises(ValueError):
      # Can't translate from dict without spec.
      resource_id.ResourceId(None, A='0', B='1')

  def test_from_parts(self):
    """Test initialization from path components."""
    rid = resource_id.ResourceId(
        resource_id.ResourceSpec({'A': {'B': None}}), ['A', '0', 'B', '1'])
    self.assertEqual(str(rid), 'A/0/B/1')
    self.assertEqual(rid.collection_map, {'A': '0', 'B': '1'})

  @parameterized.parameters(
      'projects/p0/brains/b0/sessions/s0/episodes/e0/chunks/0',
      'projects/p0/brains/b0/sessions/s0/episodes/e0',
      'projects/p0/brains/b0/sessions/s0/episodes/e0/online_evaluation',
      'projects/p0/brains/b0/sessions/s0/assignments/a0',
      'projects/p0/brains/b0/sessions/s0/models/m0',
      'projects/p0/brains/b0/sessions/s0/models/m0/offline_evaluations/0',
      'projects/p0/brains/b0/sessions/s0/models/m0/serialized_model',
      'projects/p0/brains/b0/sessions/s0',
      'projects/p0/brains/b0/snapshots/s0',
      'projects/p0')
  def test_valid_falken_ids(self, rid):
    """Test that all relevant falken ID types are valid."""
    parsed = resource_id.FalkenResourceId(rid)
    self.assertNotEmpty(parsed.parts)
    self.assertNotEmpty(parsed.collection_map)

  def test_kwargs_constructor_with_accessor_names(self):
    rid = resource_id.FalkenResourceId(
        project='p0', brain='b0', session='s0')
    self.assertEqual(rid.collection_map, {
        'projects': 'p0',
        'brains': 'b0',
        'sessions': 's0',
    })

  def test_getattr(self):
    parsed = resource_id.FalkenResourceId(
        'projects/p0/brains/b0/sessions/s0/episodes/e0/chunks/0')
    self.assertEqual(parsed.project, 'p0')
    self.assertEqual(parsed.brain, 'b0')
    self.assertEqual(parsed.session, 's0')
    self.assertEqual(parsed.episode, 'e0')
    self.assertEqual(parsed.chunk, '0')

if __name__ == '__main__':
  absltest.main()
