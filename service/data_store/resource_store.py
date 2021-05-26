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
"""Reads resources from and writes resources to storage."""

import abc
import os
import os.path
import time
from typing import List, Optional, Union, Tuple, Type

from data_store import file_system
from data_store import resource_id
from google.protobuf import message


class NotFoundError(Exception):
  """Raised when datastore cannot find a requested object."""
  pass


class InternalError(Exception):
  """Raised when filesystem is not in the expected state."""
  pass


class ResourceEncoder(abc.ABC):
  """Base class for resource encoders."""

  @abc.abstractmethod
  def encode_resource(self, res_id: resource_id.ResourceId,
                      resource: message.Message) -> str:
    """Typecheck and encode a resource into a bytes-like string.

    Args:
      res_id: The resource id of resource.
      resource: A proto representing the resource data.

    Returns:
      A bytes-like object that can be written to a file.
    """
    raise NotImplementedError()

  @abc.abstractmethod
  def decode_resource(self, res_id: resource_id.ResourceId,
                      data: Union[str, bytes]) -> message.Message:
    """Decode a resource from bytes to proto based on its resource ID.

    Args:
      res_id: The resource id of the resource.
      data: A bytes-like object representing the resource data
    Returns:
      A proto representation of the resource.
    """
    raise NotImplementedError()


class ResourceResolver(abc.ABC):
  """Base class for resource resolvers."""

  @abc.abstractmethod
  def resolve_attribute_name(self, attribute_type: Type[message.Message]) -> (
      Optional[str]):
    """Returns the attribute name of the proto type if any or returns None."""
    raise NotImplementedError()

  @abc.abstractmethod
  def encode_proto_field(self, field_name: str, value: str) -> (
      Tuple[str, str]):
    """Encodes a proto field into a resource accessor and element id.

    Args:
      field_name: The name of the proto field, e.g., 'project_id'.
      value: The value of the proto field.
    Returns:
      A pair (accessor_id, element_id) for a ResourceId that corresponds
      to the input proto field.
    """
    raise NotImplementedError()

  @abc.abstractmethod
  def get_timestamp_micros(self, resource: message.Message) -> int:
    """Determine timestamp in microseconds from resource object."""
    raise NotImplementedError()

  @abc.abstractmethod
  def set_timestamp_micros(self, resource: message.Message,
                           timestamp_micros: int):
    """Set timestamp to given value in resource object (not in storage)."""
    raise NotImplementedError()

  @abc.abstractmethod
  def to_resource_id(self, resource: message.Message) -> resource_id.ResourceId:
    """Determine resource id from the resource data object."""
    raise NotImplementedError()


class ResourceStore:
  """Stores resources with ResourceIDs in a filesystem."""

  _RESOURCE_PREFIX = 'resource.'

  def __init__(self, fs: file_system.FileSystem,
               resource_encoder: ResourceEncoder,
               resource_resolver: ResourceResolver,
               resource_id_type: Type[resource_id.ResourceId]):
    self._fs = fs
    self._encoder = resource_encoder
    self._resolver = resource_resolver
    self._resource_id_type = resource_id_type

  def _get_filename(self, timestamp_micros: int) -> str:
    """Returns file name from microsecond timestamp."""
    # 16 leading zeros should have us covered until year 3.16e8.
    return f'{self._RESOURCE_PREFIX}{timestamp_micros:016d}'

  def _get_path(self, res_id: resource_id.ResourceId,
                timestamp_micros: int) -> str:
    """Returns path from a resource ID and a microsecond timestamp."""
    return os.path.join(str(res_id), self._get_filename(timestamp_micros))

  @staticmethod
  def get_timestamp_in_microseconds() -> int:
    """Get the number of microseconds since the epoch."""
    return int(time.time() * 1_000_000)

  def write(self, resource: message.Message) -> resource_id.ResourceId:
    """Writes the resource to an appropriately chosen path."""
    res_id = self._resolver.to_resource_id(resource)
    timestamp_micros = self._resolver.get_timestamp_micros(resource)
    read_timestamp = None
    if not timestamp_micros:
      try:
        # Try to read the timestamp from the filesystem.
        read_timestamp = self.read_timestamp_micros(res_id)
      except NotFoundError:
        pass

    if not timestamp_micros:
      # Caller did not provide an explicit timestamp.
      if read_timestamp:
        # If this is an existing object in the filesystem, use its timestamp.
        timestamp_micros = read_timestamp
      else:
        # Create a new timestamp
        timestamp_micros = self.get_timestamp_in_microseconds()
      self._resolver.set_timestamp_micros(resource, timestamp_micros)
    else:
      # If the user-provided timestamp and timestamp read from the file system
      # disagree, raise an error.
      if read_timestamp and read_timestamp != timestamp_micros:
        raise ValueError(
            'Resource already exists with a different timestamp: \n'
            f'resource: {resource}\nexisting timestamp: {read_timestamp}')

    data = self._encoder.encode_resource(res_id, resource)
    self._fs.write_file(self._get_path(res_id, timestamp_micros), data)
    return res_id

  def read_timestamp_micros(self, res_id: resource_id.ResourceId) -> int:
    """Read the timestamp of a resource from the filesystem."""
    files = self._fs.glob(os.path.join(str(res_id),
                                       f'{self._RESOURCE_PREFIX}*'))
    if not files:
      raise NotFoundError(f'Could not find resource "{res_id}"')
    if len(files) > 1:
      raise InternalError(
          f'Found more than one file for resource id "{res_id}"')
    (file,) = files
    try:
      return int(os.path.basename(file)[len(self._RESOURCE_PREFIX):])
    except ValueError:
      raise InternalError(
          f'Could not translate filename to microsecond timestamp: "{file}"')

  def read(self, res_id: resource_id.ResourceId) -> message.Message:
    """Reads a resource by resource id and returns it.

    Args:
      res_id: The id of the resource to read.
    Returns:
      A datastore proto representing the resource.
    Raises:
      NotFoundError: If the resource does not exist.
    """
    timestamp_micros = self.read_timestamp_micros(res_id)
    try:
      data = self._fs.read_file(self._get_path(res_id, timestamp_micros))
    except FileNotFoundError:
      raise NotFoundError(f'Could not find resource "{res_id}"')
    return self._encoder.decode_resource(res_id, data)

  def _decode_token(self, token):
    """Decodes a pagination token.

    Args:
      token: A string with the form "timestamp:resource_id", or None.

    Returns:
      A pair (timestamp, resource_id), where timestamp is an integer, and
      resource_id a string.
    """
    if token is None:
      return -1, ''

    pair = token.split(':')
    if len(pair) != 2:
      raise ValueError(f'Invalid token {token}.')
    return int(pair[0]), pair[1]

  def _encode_token(self, timestamp_micros: int,
                    res_id: resource_id.ResourceId) -> str:
    """Encodes a pagination token.

    Args:
      timestamp_micros: The microsecond timestamp of the most recently read
          token for the page.
      res_id: The resource id of the last token on the page.

    Returns:
      The encoded string with the form "timestamp:resource_id".
    """
    return f'{timestamp_micros}:{res_id}'

  def list(self,
           res_id_glob: resource_id.ResourceId,
           min_timestamp_micros: int = 0,
           page_token: Optional[str] = None,
           page_size: Optional[int] = None,
           time_descending: Optional[bool] = False) -> (
               Tuple[List[resource_id.ResourceId], str]):
    """Lists all resource_ids that match the provided pattern.

    Args:
      res_id_glob: A resource ID glob, containing '*' and brace components of
        the form '{a,b,c}' that are resolved in a shell-style fashion.
      min_timestamp_micros: Only return res_ids at least as recent as this
        timestamp.
      page_token: The token for the previous page if any.
      page_size: The size of the page or None to return all IDs.
      time_descending: If True, list items in descending create time.

    Returns:
      A tuple of a list of resource IDs and pagination token.
    """
    glob_path = os.path.join(str(res_id_glob), f'{self._RESOURCE_PREFIX}*')
    files = self._fs.glob(glob_path)
    paths = [os.path.dirname(f) for f in files]
    timestamps = [
        int(os.path.basename(f)[len(self._RESOURCE_PREFIX):]) for f in files]
    by_timestamp = sorted(zip(timestamps, paths), reverse=time_descending)

    page_token_res_id = None
    page_token_timestamp = None
    if page_token:
      page_token_timestamp, page_token_res_id = self._decode_token(page_token)
    # Return True if the first item goes before the second item in a list in
    # ascending or descending order.
    check_is_before = (
        lambda x, y: x > y) if time_descending else (lambda x, y: x < y)

    page = []
    last_timestamp_micros = 0
    last_read_index = -1
    for last_read_index, (timestamp_micros, res_id_string) in enumerate(
        by_timestamp):
      if timestamp_micros < min_timestamp_micros:
        # Skip if created before provided min timestamp.
        continue
      if page_token and check_is_before(
          timestamp_micros, page_token_timestamp):
        # Skip if created before the token based on time_descending.
        continue
      if page_token and timestamp_micros == page_token_timestamp and (
          # Skip if item is the token.
          res_id_string == page_token_res_id or
          # Skip if item is before the token based on time_descending.
          check_is_before(res_id_string, page_token_res_id)):
        continue

      page.append(self._resource_id_type(res_id_string))
      last_timestamp_micros = timestamp_micros
      if page_size and len(page) == page_size:
        break

    if last_read_index == len(by_timestamp) - 1:
      return page, ''
    else:
      token = self._encode_token(last_timestamp_micros, page[-1])
    return page, token

  def read_by_proto_ids(
      self,
      attribute_type: Optional[Type[message.Message]] = None,
      **kwargs) -> message.Message:
    """Read a resource using its proto ID fields.

    Args:
      attribute_type: By default, this function will return a resource ID for
          the primary resource associated with key. If an attribute of the
          primary resource is required, then the type of the attribute can be
          specified here.
      **kwargs: A string-valued dictionary that maps proto ID fields to
          proto field values, e.g.:
              ds.read_by_proto_ids(project_id='p0', brain_id='b0')
    Returns:
      The resource proto corresponding to the provided key fields.
    """
    res_id = self.resource_id_from_proto_ids(
        attribute_type=attribute_type, **kwargs)
    return self.read(res_id)

  def list_by_proto_ids(
      self,
      attribute_type: Optional[Type[message.Message]] = None,
      min_timestamp_micros: int = 0,
      page_token: Optional[str] = None,
      page_size: Optional[int] = None,
      time_descending: Optional[bool] = False,
      **kwargs) -> Tuple[List[resource_id.ResourceId], str]:
    """List resource ids their ID fields.

    Args:
      attribute_type: By default, this function will return resource IDs for the
          primary resource associated with key. If an attribute of the primary
          resource is required, then the type of the attribute can be specified
          here.
      min_timestamp_micros: Only return res_ids at least as recent as this
        timestamp.
      page_token: The token for the previous page if any.
      page_size: The size of the page or None to return all IDs.
      time_descending: If True, list items in descending create time.
      **kwargs: A string-valued dictionary that maps proto ID fields to
          proto field values, e.g.:
              ds.read_by_proto_ids(project_id='p0', brain_id='b0')
          Glob and brace expansion expressions can be used, but note that
          when globbing the 'assignment_id' field, only '*' is supported and
          every other string is interpreted as plain text.
    Returns:
      A tuple of a list of resource IDs and a pagination token.
    """
    res_id = self.resource_id_from_proto_ids(
        attribute_type=attribute_type, **kwargs)
    return self.list(
        res_id,
        min_timestamp_micros=min_timestamp_micros,
        page_token=page_token,
        page_size=page_size,
        time_descending=time_descending)

  def resource_id_from_proto_ids(
      self,
      attribute_type: Optional[Type[message.Message]] = None,
      **kwargs) -> resource_id.ResourceId:
    """Construct a resource id from proto ID fields.

    Args:
      attribute_type: By default, this function will return a resource ID for
          the primary resource associated with key. If an attribute of the
          primary resource is required, then the type of the attribute can be
          specified here.
      **kwargs: A string-valued dictionary that maps proto ID fields to
          proto field values, e.g.:
              ds.read_by_proto_ids(project_id='p0', brain_id='b0')
    Returns:
      A resource ID that encodes the proto key fields.
    """
    if attribute_type:
      attribute_name = self._resolver.resolve_attribute_name(attribute_type)
    else:
      attribute_name = None
    accessor_map = {}
    for proto_field, field_value in kwargs.items():
      accessor_id, elem_id = self._resolver.encode_proto_field(proto_field,
                                                               field_value)
      accessor_map[accessor_id] = elem_id

    assert resource_id.ATTRIBUTE not in accessor_map
    if attribute_name:
      accessor_map[resource_id.ATTRIBUTE] = attribute_name
    return self._resource_id_type(**accessor_map)

  def to_resource_id(self, resource: message.Message) -> resource_id.ResourceId:
    return self._resolver.to_resource_id(resource)

  def get_most_recent(self, res_id_glob: Union[str, resource_id.ResourceId]):
    """Returns the most recent ID matching the glob or None if not found."""
    resource_ids, _ = self.list(res_id_glob, page_size=None)
    return resource_ids[-1] if resource_ids else None
