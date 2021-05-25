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
"""Business logic to access Falken objects in the data store."""

import hashlib
from typing import Optional, Union, Tuple, Type

from data_store import file_system
from data_store import resource_id
from data_store import resource_store
from log import falken_logging

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import data_store_pb2

DatastoreProto = Union[
    data_store_pb2.Assignment,
    data_store_pb2.Brain,
    data_store_pb2.EpisodeChunk,
    data_store_pb2.Model,
    data_store_pb2.OfflineEvaluation,
    data_store_pb2.OnlineEvaluation,
    data_store_pb2.Project,
    data_store_pb2.Session,
    data_store_pb2.SerializedModel,
    data_store_pb2.Snapshot,
]


# Map resource collection IDs to proto type of the resource.
_PROTO_BY_COLLECTION_ID = {
    'projects': data_store_pb2.Project,
    'brains': data_store_pb2.Brain,
    'snapshots': data_store_pb2.Snapshot,
    'sessions': data_store_pb2.Session,
    'chunks': data_store_pb2.EpisodeChunk,
    'assignments': data_store_pb2.Assignment,
    'models': data_store_pb2.Model,
    'offline_evaluations': data_store_pb2.OfflineEvaluation,
}

_PROTO_BY_ATTRIBUTE_ID = {
    'serialized_model': data_store_pb2.SerializedModel,
    'online_evaluation': data_store_pb2.OnlineEvaluation,
}


class _ResourceEncoder(resource_store.ResourceEncoder):
  """Encodes/decodes protos to/from bytes based on resource id."""

  def _get_proto_type(self, res_id: resource_id.FalkenResourceId) -> (
      Type[DatastoreProto]):
    """Determines the protobuf type from a resource id."""
    assert len(res_id.parts) >= 2  # Valid resource ids have at least 2 parts.
    if res_id.attribute:
      try:
        return _PROTO_BY_ATTRIBUTE_ID[res_id.attribute]
      except KeyError:
        raise ValueError(
            f'Error determining proto type for "{res_id}". '
            f'Not a supported attribute: {res_id.attribute}')

    collection_id = res_id.parts[-2]
    try:
      return _PROTO_BY_COLLECTION_ID[collection_id]
    except KeyError:
      raise ValueError(
          f'Error determining proto type for "{res_id}". '
          f'Not a supported collection: {collection_id}')

  def encode_resource(self,
                      res_id: resource_id.ResourceId,
                      resource: DatastoreProto) -> str:
    """Typecheck and encode a resource into a bytes-like string.

    Args:
      res_id: The resource id of resource.
      resource: A proto representing the resource data.

    Returns:
      A bytes-like object that can be written to a file.
    """
    expected_type = self._get_proto_type(res_id)

    if not isinstance(resource, expected_type):
      raise ValueError(
          f'Resource has type {type(resource)}, but it should have type '
          f'{expected_type}.')

    return resource.SerializeToString()

  def decode_resource(self,
                      res_id: resource_id.ResourceId,
                      data: Union[str, bytes]) -> DatastoreProto:
    """Decode a resource from bytes to proto based on its resource ID.

    Args:
      res_id: The resource id of the resource.
      data: A bytes-like object representing the resource data
    Returns:
      A proto representation of the resource.
    """
    proto_type = self._get_proto_type(res_id)
    return proto_type.FromString(data)


class _ResourceResolver(resource_store.ResourceResolver):
  """Handles and parses the underlying resource type for ResourceID usage."""

  # Map key_field_name -> collection name mapping
  _KEY_FIELDS = [
      'assignment_id',
      'brain_id',
      'chunk_id',
      'episode_id',
      'model_id',
      'offline_evaluation_id',
      'project_id',
      'session_id',
      'snapshot_id',
  ]

  # Maps proto types to their attributes.
  _ATTRIBUTE_MAP = {
      data_store_pb2.OnlineEvaluation: 'online_evaluation',
      data_store_pb2.SerializedModel: 'serialized_model',
  }

  def resolve_attribute_name(
      self, attribute_type: Type[DatastoreProto]) -> Optional[str]:
    """Returns the attribute name of the proto type if any or returns None."""
    return _ResourceResolver._ATTRIBUTE_MAP.get(attribute_type)

  def encode_proto_field(self, field_name: str, value: str) -> Tuple[str, str]:
    """Encodes a proto field assignment into a resource accessor and element id.

    Args:
      field_name: The name of the proto field, e.g., 'project_id'.
      value: The value of the proto field.
    Returns:
      A pair (accessor_id, element_id) for a FalkenResourceId that corresponds
      to the input proto field assignment.
    """
    if field_name == 'assignment_id':
      if value != '*':  # Assignments only support '*' globs.
        # We hash assignment_ids since they can get pretty long.
        value = hashlib.sha256(value.encode('utf-8')).hexdigest()
    if not field_name.endswith('_id'):
      raise ValueError(f'Unsupported proto field: {field_name}')
    return field_name[:-len('_id')], value

  def get_timestamp_micros(self, resource: DatastoreProto) -> int:
    """Determine timestamp in microseconds from resource object."""
    return resource.created_micros or None  # return 0s as Nones

  def set_timestamp_micros(self, resource: DatastoreProto,
                           timestamp_micros: int):
    """Set timestamp to given value in resource object (not in storage)."""
    resource.created_micros = timestamp_micros

  def to_resource_id(self, resource: DatastoreProto) -> (
      resource_id.ResourceId):
    """Determine resource id from the resource data object."""
    accessor_map = {}

    for key in _ResourceResolver._KEY_FIELDS:
      try:
        proto_value = getattr(resource, key)
      except AttributeError:
        # Key is not present in this proto.
        continue
      if proto_value is None:
        raise ValueError(
            f'Object: \n===\n{resource}\n===\n' +
            f'of type {type(resource)} does not set ' +
            f'the required key field "{key}".')
      accessor_name, element_id = self.encode_proto_field(key, proto_value)
      accessor_map[accessor_name] = element_id

    # Check if the proto represents an attribute.
    attribute_name = _ResourceResolver._ATTRIBUTE_MAP.get(
        type(resource))
    if attribute_name:
      accessor_map[resource_id.ATTRIBUTE] = attribute_name
    if not accessor_map:
      raise ValueError(
          'Could not determine resource id of resource of type ' +
          f'{type(resource)}:\n===\n{resource}\n===')
    return resource_id.FalkenResourceId(**accessor_map)


class SnapshotDataStoreMixin:
  """"Mix-in that performs operations on DataStore Snapshot protos."""

  def get_most_recent_snapshot(self, project_id: str, brain_id: str) -> (
      Optional[resource_id.ResourceId]):
    """Get the most recent snapshot of a brain.

    Args:
      project_id: ID of the project to query.
      brain_id: ID of the brain to query.

    Returns:
      ResourceId of the snapshot.
    """
    return self.get_most_recent(self.resource_id_from_proto_ids(
        project_id=project_id, brain_id=brain_id, snapshot_id='*'))


class SessionDataStoreMixin:
  """Mix-in that performs operations on DataStore Session protos."""

  def write_stopped_session(self, session: data_store_pb2.Session) -> (
      resource_id.ResourceId):
    """Write the specified session to the data store marking it as stopped.

    Args:
      session: Session to stop.

    Returns:
      ResourceId of the session.
    """
    session.ended_micros = self.get_timestamp_in_microseconds()
    resource = self.write(session)
    falken_logging.info(f'Stopped session {resource}.')
    return resource

  def update_session_data_timestamps(
      self,
      session_resource_id: resource_id.FalkenResourceId,
      timestamp_micros: int,
      has_demo_data: bool):
    """Updates data received timestamps in a session.

    Sessions have two timestamp fields that record the timestmap of the last
    chunk of data received and the timestamp of the last chunk of data received
    that contained demo data. This function updates one or both of those fields
    to the indicated value.

    Args:
      session_resource_id: Resource ID of the session to update.
      timestamp_micros: A microsecond timestamp.
      has_demo_data: Whether the last_demo_data_received_micros timestamp should
          be updated.
    """
    session = self.read(session_resource_id)
    session.last_data_received_micros = (
        max(timestamp_micros, session.last_data_received_micros))

    if has_demo_data:
      session.last_demo_data_received_micros = (
          max(timestamp_micros, session.last_demo_data_received_micros))
    write_resource_id = self.write(session)
    assert session_resource_id == write_resource_id


class DataStore(resource_store.ResourceStore,
                SnapshotDataStoreMixin,
                SessionDataStoreMixin):
  """Reads and writes data from storage."""

  def __init__(self, fs: file_system.FileSystem):
    """Initializes the data store with a given root path.

    Args:
      fs: A FileSystem or MockFileSystem object.
    """
    super().__init__(fs, _ResourceEncoder(), _ResourceResolver(),
                     resource_id.FalkenResourceId)
