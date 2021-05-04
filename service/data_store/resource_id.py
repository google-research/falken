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

"""Parsing of resource IDs."""


class InvalidResourceError(Exception):
  """Raised when a resource does not match the spec."""
  pass


class ResourceId:
  """A class to represent and validate resource ids.

  A resource ID is a path-like string of the following form:
    "/collection_1/elem_id_1/.../collection_k/elem_id_k"

  For example: "/authors/RWilson/books/Illuminatus", where
  "authors" and "books" are collections, and "RWilson" and "Illuminatus" are,
  respectively, IDs of the corresponding elements in those collections.

  Construction of a ResourceID from a dictionary requires a resource spec in the
  form of a nested dictionary that represents the hierarchy of collections.
  Consider the example spec below:

    {'countries': {'celebrities': None, 'dishes': {'ingredients'}}}

  This would admit the following resource IDs:
    /countries/austria
    /countries/austria/celebrities/sigmund_freud
    /countries/austria/dishes/wienerschnitzel
    /countries/austria/dishes/wienerschnitzel/ingredients/eggs

  Attributes:
    id_string: A string representation of the resource id, e.g.,
      'authors/RWilson/books/Illuminatus'.
    parts: A list of path parts, e.g.,
      ['authors', 'RWilson', 'books', 'Illuminatus']
    collection_map: A map from collection name to element ID, e.g.,
      {'authors': 'RWilson', 'books': 'Illuminatus'},
  """

  def __init__(self, resource_spec, id_or_parts=None, **kwargs):
    """Create a new resource ID matching the provided spec.

    Args:
      resource_spec: A nested dictionary (with leaves of type None, or of
          iterable type), specifiying the hierarchical relationships between
          collections. See class-level comment.
      id_or_parts: A string representing the resource id or a list of strings
          representing individual resource id components.
      **kwargs: Direct assignments of strings to collections.

    Raises:
      InvalidResourceError: If a specified resource is invalid (e.g., does not
          match spec).
    """
    self._resource_spec = resource_spec

    if bool(id_or_parts) + bool(kwargs) != 1:
      raise ValueError(
          'Resource id must be specified using exactly one of the following: '
          '"id_string", "parts" or individual key-value assignments via '
          '"kw_args"')

    self.id_string = None
    self.parts = None
    self.collection_map = None

    if id_or_parts:
      if isinstance(id_or_parts, str):
        self.id_string = id_or_parts
        # Initialize from id_string.
        self.parts = self.id_string.split('/')
      else:
        # Initialize from parts list.
        try:
          self.parts = list(id_or_parts)
        except TypeError:
          raise ValueError('Expected string or iterable for "id_or_parts", got '
                           + type(id_or_parts))
        self.id_string = '/'.join(self.parts)
      if len(self.parts) % 2 != 0:
        raise InvalidResourceError(
            'Resource is expected to have an even number of parts.')
      self.collection_map = self._compute_collection_map(
          self._resource_spec, self.parts)
    else:
      # Initialize from kw_args.
      self.collection_map = dict(**kwargs)
      self.parts = self._compute_parts(
          self._resource_spec, self.collection_map)
      self.id_string = '/'.join(self.parts)

  def __str__(self) -> str:
    """Path-style string representation of the resource ID."""
    return self.id_string

  def __hash__(self) -> int:
    return self.id_string.__hash__()

  @staticmethod
  def _compute_collection_map(resource_spec, parts):
    """Computes the collection map from the parts and spec.

    Args:
      resource_spec: The resource spec as a dictionary. See class-level comment.
      parts: A list of strings.
    Returns:
      A dictionary mapping collection names to collection element IDs.
    Raises:
      InvalidResourceError: If parts do not match spec.
    """
    current_spec_node = resource_spec
    collection_map = {}

    if len(parts) % 2 != 0:
      raise InvalidResourceError(
          'Spec must have an even number of components')

    for i in range(0, len(parts), 2):
      collection, elem_id = parts[i], parts[i+1]
      if resource_spec and (current_spec_node is None or
                            collection not in current_spec_node):
        raise InvalidResourceError(f'Not a valid collection: {collection}')
      if not collection or not elem_id:
        raise InvalidResourceError('Components and IDs may not be empty.')
      collection_map[collection] = elem_id
      try:
        # Try to go deeper into the spec, which is allowed to fail if we've
        # reached the leaves.
        if resource_spec:
          current_spec_node = current_spec_node[collection]
      except TypeError:
        current_spec_node = None

    return collection_map

  @staticmethod
  def _compute_parts(resource_spec, collection_map):
    """Compute the parts from a collection_map and spec.

    Args:
      resource_spec: The resource spec as a dictionary. See class-level comment.
      collection_map: A mapping from collection names to element ids.
    Returns:
      A list of strings respresenting the path components of the resource id.
    Raises:
      InvalidResourceError: If parts do not match spec.
    """
    keys_to_process = set(collection_map)
    parts = []
    if not resource_spec:
      raise ValueError(
          'Resource spec must be provided in order to initialize from kwargs.')
    current_spec_node = resource_spec
    while keys_to_process and current_spec_node:
      handled = False
      for key in current_spec_node:
        if key in keys_to_process:
          parts.append(key)
          parts.append(collection_map[key])
          if not key or not collection_map[key]:
            raise InvalidResourceError('Components and IDs may not be empty.')
          keys_to_process.remove(key)
          try:
            current_spec_node = current_spec_node[key]
          except TypeError:
            # This is allowed when we hit the leaves of the spec.
            current_spec_node = None
          handled = True
          break
      if not handled:
        break
    if keys_to_process:
      raise InvalidResourceError(
          'Could not match the following keys to spec: '
          + str(keys_to_process))
    return parts


class FalkenResourceId(ResourceId):
  """A ResourceId with a fixed spec representing Falken resources."""

  FALKEN_RESOURCE_SPEC = {
      'projects': {
          'brains': {
              'sessions': {
                  'episodes': {
                      'chunks',
                  },
                  'online_evaluations': None,
                  'offline_evaluations': None,
                  'assignments': None,
                  'models': None,
              },
              'snapshots': None,
          }
      }
  }

  def __init__(self, *args, **kwargs):
    super().__init__(
        FalkenResourceId.FALKEN_RESOURCE_SPEC,
        *args, **kwargs)
