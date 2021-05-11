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


class InvalidSpecError(Exception):
  """Raised when a resource spec is invalid."""
  pass


class ResourceSpec(dict):
  """A syntax specification for a class of valid resource IDs.

  A resource ID is a path-like string of one of the following forms:
    "/collection_1/elem_id_1/.../collection_k/elem_id_k"
  or
    "/collection_1/elem_id_1/.../collection_k/elem_id_k/attribute"

  For example: "/authors/RWilson/books/Illuminatus/date_published", where
  "authors" and "books" are collections, and "RWilson" and "Illuminatus" are,
  respectively, IDs of the corresponding elements in those collections and
  'date_published' is an attribute of books.

  A resource spec represents the hierarchy of collections for the purpose of
  ResourceID validation, a specification valid attributes for each collection
  type and friendly names for the accessor functions.

  Consider the example spec below:

  ResourceSpec(
    {'countries': {'celebrities': None, 'dishes': {'ingredients'}}},
    accessor_map={
        'countries': 'country',
        'celebrities': 'celebrity',
        'dishes': 'dish',
        'ingredients': 'ingredient'},
    attributes={
      'dishes': ['inventor']
    })

  This would admit the following resource IDs:
    /countries/austria
    /countries/austria/celebrities/sigmund_freud
    /countries/austria/dishes/wienerschnitzel
    /countries/austria/dishes/wienerschnitzel/inventor
    /countries/austria/dishes/wienerschnitzel/ingredients/eggs

  Furthermore, the optional accessor_map argument enables aliasing for
  collection ids for convenience as follows:

    rid = ResourceId(country='austria', 'celebrity'='sigmund_freud')
    assert rid.country == 'austria'
    assert str(rid) == 'countries/austria/celebrities/sigmund_freud'
  """

  def _initialize(self, spec_node, seen, accessor_map):
    """Recursively initialize data structures and validate spec.

    Args:
      spec_node: An node in the nested spec dictionary, dictionary or iterable.
      seen: A set of collection_ids that have been visited already.
      accessor_map: A mapping from collection ids to accessor names.
    Raises:
      InvalidSpecError: If errors in the spec are found.
    """
    if not spec_node:
      return
    for collection_id in spec_node:
      if collection_id in seen:
        raise InvalidSpecError(
            f'Encountered collection_id twice: {collection_id}')
      seen.add(collection_id)
      if collection_id in accessor_map:
        name = accessor_map[collection_id]
      else:
        name = collection_id

      if name in self.accessor_name_to_collection_id:
        raise InvalidSpecError(
            f'Accessor name "{name}" is used for both "{collection_id}" and '
            f'"{self.accessor_name_to_collection_id[name]}."')
      self.accessor_name_to_collection_id[name] = collection_id
      self.collection_id_to_accessor_name[collection_id] = name
      if collection_id == ATTRIBUTE or name == ATTRIBUTE:
        raise InvalidSpecError(
            f'Reserved name "{ATTRIBUTE}" may not be used for accessor names '
            'or collection IDs.')

    try:
      subnodes = spec_node.values()
    except AttributeError:
      subnodes = []
    for subnode in subnodes:
      self._initialize(subnode, seen, accessor_map)

  def __init__(self, spec_nest, accessor_map=None, attribute_map=None):
    """Create a new spec from a spec dictionary and an optional accessor map.

    Args:
      spec_nest: A nest of stirngs representing the spec.
          See class-level comment.
      accessor_map: A map from collection_ids to friendly names used to access
          this collection in ResourceID instances.
      attribute_map: A map from collection_ids to attributes supported by
          elements of that collection.
    Raises:
      InvalidSpecError: If there are problems with the spec or accessor_map.
    """
    if not isinstance(spec_nest, dict):
      spec_nest = {key: None for key in spec_nest}
    super().__init__(spec_nest)
    self.attribute_map = attribute_map or dict()
    accessor_map = accessor_map or dict()
    self.collection_id_to_accessor_name = dict()
    self.accessor_name_to_collection_id = dict()
    seen = set()
    self._initialize(self, seen, accessor_map)
    for collection_id in accessor_map:
      if collection_id not in self.collection_id_to_accessor_name:
        raise InvalidSpecError(
            f'Accessor for collection_id {collection_id} does not match a '
            f'collection_id in the spec.')


# Used as a special key in ResourceId constructor dictionaries.
# We use a friendly name, so that it can also be used in kwargs.
ATTRIBUTE = 'attribute'


class ResourceId:
  """A class to represent and validate resource ids.

  A resource ID is a path-like string
    "/collection_1/elem_id_1/.../collection_k/elem_id_k"
  or
    "/collection_1/elem_id_1/.../collection_k/elem_id_k/attribute_name"

  See ResourceSpec class comments for examples.

  Attributes:
    id_string: A string representation of the resource id, e.g.,
      'authors/RWilson/books/Illuminatus/date_published'.
    parts: A list of path parts, e.g.,
      ['authors', 'RWilson', 'books', 'Illuminatus', 'date_published']
    collection_map: A map from collection names and the special key
      ATTRIBUTE to element IDs and attribute names, e.g.,
          {'authors': 'RWilson', 'books': 'Illuminatus',
           ATTRIBUTE: 'date_published'},
  """

  def __init__(self, resource_spec, id_or_parts=None, **kwargs):
    """Create a new resource ID matching the provided spec.

    Args:
      resource_spec: A ResourceSpec object describing the hierarchy of
          collections and supported attributes.
      id_or_parts: A string representing the resource id or a list of strings
          representing individual resource id components.
      **kwargs: Direct assignments of strings to collections. Addressing a
          collection must be done via its accessor name (if provided in the
          spec), otherwise it uses the collection_id.

    Raises:
      InvalidResourceError: If a specified resource is invalid (e.g., does not
          match spec).
    """
    if resource_spec and not isinstance(resource_spec, ResourceSpec):
      raise ValueError('resource_spec must be of type ResourceSpec.')
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
          self.parts = [str(s) for s in id_or_parts]
        except TypeError:
          raise ValueError('Expected string or iterable for "id_or_parts", got '
                           + type(id_or_parts))
        self.id_string = '/'.join(self.parts)
      self.collection_map = self._compute_collection_map(
          self._resource_spec, self.parts)
    else:
      # Initialize from kw_args.
      if not resource_spec:
        raise ValueError(
            'ResourceSpec must be provided when initializing from kwargs.')
      self.collection_map = dict()
      for accessor_name, elem_id in kwargs.items():
        try:
          collection_id = (
              resource_spec.accessor_name_to_collection_id[accessor_name])
          self.collection_map[collection_id] = str(elem_id)
        except KeyError:
          if accessor_name != ATTRIBUTE:
            raise InvalidResourceError('Unknown collection: ' + accessor_name)
          self.collection_map[ATTRIBUTE] = str(elem_id)

      self.parts = self._compute_parts(
          self._resource_spec, self.collection_map)
      self.id_string = '/'.join(self.parts)

  def __str__(self) -> str:
    """Path-style string representation of the resource ID."""
    return self.id_string

  def __hash__(self) -> int:
    return self.id_string.__hash__()

  def __getattr__(self, attr_name):
    """Allows access to collection_map values using accessor names.

    E.g.:
      spec = ResourceSpec({'countries': {'dishes'}},
                          {'countries': 'country', 'dishes': 'dish'})
      rid = ResourceId(spec, 'countries/mexico/dishes/pozole'
      print(rid.country)  # prints 'mexico'
      print(rid.dish)     # prints 'pozole'

    Args:
      attr_name: The accessor name of a collection or its collection_id if no
        name was provided.
    Returns:
      The element name in the corresponding collection.
    """
    try:
      if self._resource_spec:
        collection_id = (
            self._resource_spec.accessor_name_to_collection_id[attr_name])
      else:
        collection_id = attr_name
    except KeyError:
      return super().__getattr__(attr_name)
    return self.collection_map[collection_id]

  def get_accessor_name(self, collection_id):
    if not self._resource_spec:
      return collection_id
    return self._resource_spec.collection_id_to_accessor_name[collection_id]

  @staticmethod
  def _compute_collection_map(resource_spec, parts):
    """Computes the collection map from the parts and spec.

    Args:
      resource_spec: The resource spec as a dictionary. See class-level comment.
      parts: A list of strings representing an alternation of collection_id
        and element_id, possible with a final attribute.
    Returns:
      A dictionary mapping collection names to collection element IDs and
      the special string ATTRIBUTE to the attribute name.
    Raises:
      InvalidResourceError: If parts do not match spec.
    """
    current_spec_node = resource_spec
    collection_map = {}

    if len(parts) % 2 == 0:
      attribute = None
    else:
      attribute = None
      parts, attribute = parts[:-1], parts[-1]

    assert len(parts) % 2 == 0
    if not parts:
      raise InvalidResourceError(
          'Spec must have an even, non-zero number of components')

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

    if attribute is not None:
      last_collection_id = parts[-2]
      if attribute not in resource_spec.attribute_map.get(
          last_collection_id, []):
        raise InvalidResourceError(
            f'Collection "{last_collection_id}" does not support attribute '
            f'"{attribute}"')
      collection_map[ATTRIBUTE] = attribute
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
    collection_ids_to_process = set(collection_map)
    try:
      collection_ids_to_process.remove(ATTRIBUTE)
    except KeyError:
      pass

    parts = []
    current_spec_node = resource_spec

    while collection_ids_to_process and current_spec_node:
      handled = False
      for key in current_spec_node:
        if not key:
          raise InvalidResourceError('Collection IDs in spec may not be empty.')

        if key in collection_ids_to_process:
          parts.append(key)
          parts.append(collection_map[key])
          if not parts[-1]:
            raise InvalidResourceError('Element IDs may not be empty.')
          collection_ids_to_process.remove(key)
          try:
            current_spec_node = current_spec_node[key]
          except TypeError:
            # This is allowed when we hit the leaves of the spec.
            current_spec_node = None
          handled = True
          break
      if not handled:
        break

    if collection_ids_to_process:
      raise InvalidResourceError(
          'Could not match the following collection ids to spec: '
          + str(collection_ids_to_process))
    if not parts:
      raise InvalidResourceError(
          'Resource does not specify an element within a collection: '
          + str(collection_map))

    last_collection_id = parts[-2]
    attribute = collection_map.get(ATTRIBUTE, None)
    if attribute:
      if attribute not in resource_spec.attribute_map.get(
          last_collection_id, []):
        raise InvalidResourceError(
            f'Collection "{last_collection_id}" does not support attribute '
            f'"{attribute}"')
      parts.append(attribute)
    return parts

  def __eq__(self, o):
    return str(self) == str(o)


class FalkenResourceId(ResourceId):
  """A ResourceId with a fixed spec representing Falken resources."""

  FALKEN_RESOURCE_SPEC = ResourceSpec(
      {
          'projects': {
              'brains': {
                  'sessions': {
                      'episodes': {
                          'chunks',
                      },
                      'online_evaluations': None,
                      'assignments': None,
                      'models': {'offline_evaluations'},
                      'serialized_models': None,
                  },
                  'snapshots': None,
              }
          }
      },
      accessor_map={
          'projects': 'project',
          'brains': 'brain',
          'sessions': 'session',
          'episodes': 'episode',
          'chunks': 'chunk',
          'online_evaluations': 'online_evaluation',
          'assignments': 'assignment',
          'models': 'model',
          'serialized_models': 'serialized_model',
          'snapshots': 'snapshot',
          'offline_evaluations': 'offline_evaluation',
      })

  def __init__(self, *args, **kwargs):
    super().__init__(
        FalkenResourceId.FALKEN_RESOURCE_SPEC,
        *args, **kwargs)
