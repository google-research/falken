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
"""Converts data_store protos to API consumable protos."""

import common.generate_protos  # pylint: disable=g-bad-import-order,unused-import
import brain_pb2
import data_store_pb2
from google.protobuf import timestamp_pb2
import session_pb2


class ProtoConverter:
  """Module to convert data_store protos to API consumable protos."""

  # Lazily initialized by convert_data_store_proto().
  _PROTO_MAP = {}
  _PROTO_FIELD_NAME_MAP = {}
  _PROTO_FIELD_CONVERTER_MAP = {}

  @staticmethod
  def _convert_micros_to_timestamp(proto, field_name):
    """Converts proto's uint64 micros field to google.protobuf.Timestamp.

    Args:
      proto: The proto which contains the uint64 micros field.
      field_name: Field name which contains the uint64 micros.

    Returns:
      google.protobuf.Timestamp representation of the uint64 time in the
        provided proto.
    """
    micros = getattr(proto, field_name)
    return timestamp_pb2.Timestamp(seconds=micros // 1000000)

  @staticmethod
  def _convert_timestamp_to_micros(proto, field_name):
    """Converts proto's google.protobuf.Timestamp field to uint64.

    Args:
      proto: The proto which contains the google.protobuf.Timestamp field.
      field_name: Field name which contains the google.protobuf.Timestamp.

    Returns:
      uint64 micros representation of the google.protobuf.Timestamp.
    """
    timestamp = getattr(proto, field_name)
    return timestamp.seconds * 1000000

  @staticmethod
  def _set_field(target_proto, field_name, value):
    """Sets field of the target_proto with the value provided.

    Args:
      target_proto: Proto which contains the field_name.
      field_name: Field name to set.
      value: Value to set the field to.
    """
    field_descriptor = target_proto.DESCRIPTOR.fields_by_name[field_name]
    if field_descriptor.type == field_descriptor.TYPE_MESSAGE:
      getattr(target_proto, field_name).CopyFrom(value)
    elif field_descriptor.label == field_descriptor.LABEL_REPEATED:
      getattr(target_proto, field_name).extend(value)
    else:
      setattr(target_proto, field_name, value)

  @staticmethod
  def _get_target_proto(source_proto_type):
    """Gets the target common proto type from a source proto type.

    Args:
      source_proto_type: Proto type defined in  the source proto.

    Returns:
      target proto type defining the type of the proto message that
        corresponds to the source proto.

    Raises:
      ValueError: If the source proto type does not map to any proto.
    """
    if not ProtoConverter._PROTO_MAP:
      ProtoConverter._PROTO_MAP = {
          data_store_pb2.Brain: brain_pb2.Brain,
          data_store_pb2.Session: session_pb2.Session
      }
    target_proto_type = ProtoConverter._PROTO_MAP.get(source_proto_type)
    if not target_proto_type:
      raise ValueError(
          f'Proto {type(source_proto_type)} could not be mapped to any '
          'proto.')
    return target_proto_type

  @staticmethod
  def _get_target_field_name(field_name, source_proto_type, target_proto_type):
    """Get the target field name from a source proto field name.

    Args:
      field_name: Name of the field in the source proto.
      source_proto_type: Proto type defined in source proto.
      target_proto_type: Common proto type counterpart of source_proto_type.

    Returns:
      Target field_name that can be set, or None if there is no field to be
        set in the target.
    """
    if not ProtoConverter._PROTO_FIELD_NAME_MAP:
      ProtoConverter._PROTO_FIELD_NAME_MAP = {
          data_store_pb2.Brain: {
              'name': 'display_name',
          },
          data_store_pb2.Session: {
              'session_id': 'name',
          },
          None: {
              'created_micros': 'create_time',
              'create_time': 'created_micros'
          }
      }

    target_field_name = None
    if (source_proto_type in ProtoConverter._PROTO_FIELD_NAME_MAP and
        field_name in ProtoConverter._PROTO_FIELD_NAME_MAP[source_proto_type]):
      target_field_name = ProtoConverter._PROTO_FIELD_NAME_MAP[
          source_proto_type][field_name]
    elif field_name in ProtoConverter._PROTO_FIELD_NAME_MAP.get(None, {}):
      target_field_name = ProtoConverter._PROTO_FIELD_NAME_MAP[None][field_name]
    elif field_name in target_proto_type.DESCRIPTOR.fields_by_name:
      target_field_name = field_name

    # Check that the target_field_name can be found in the target_proto fields.
    if target_field_name in target_proto_type.DESCRIPTOR.fields_by_name:
      return target_field_name
    return None

  @staticmethod
  def _convert_field(source_field, source_proto, target_field):
    """Converts the data_store_proto's field to a common proto's field.

    Args:
      source_field: google.protobuf.FieldDescriptor for the field to be
        converted in the source_proto.
      source_proto: Proto messaged defined in source proto.
      target_field: google.protobuf.FieldDescriptor for the field to be set from
        the source_field.

    Returns:
      converted field which went through the function defined in
        _PROTO_FIELD_CONVERTER_MAP.

    Raises:
      ValueError when the field could not be converted.
    """
    field_name = source_field.name
    if not ProtoConverter._PROTO_FIELD_CONVERTER_MAP:
      ProtoConverter._PROTO_FIELD_CONVERTER_MAP = {
          None: {
              'created_micros': ProtoConverter._convert_micros_to_timestamp,
              'create_time': ProtoConverter._convert_timestamp_to_micros,
          }
      }
    source_proto_type = type(source_proto)
    if (source_proto_type in ProtoConverter._PROTO_FIELD_CONVERTER_MAP and
        field_name
        in ProtoConverter._PROTO_FIELD_CONVERTER_MAP[source_proto_type]):
      converter = ProtoConverter._PROTO_FIELD_CONVERTER_MAP[source_proto_type][
          field_name]
      return converter(source_proto, field_name)
    elif field_name in ProtoConverter._PROTO_FIELD_CONVERTER_MAP.get(None, {}):
      converter = ProtoConverter._PROTO_FIELD_CONVERTER_MAP[None][field_name]
      return converter(source_proto, field_name)
    elif target_field.type == source_field.type:
      return getattr(source_proto, field_name)
    else:
      raise ValueError(
          f'Proto field {field_name} in {source_proto_type} could not be '
          f'converted to {target_field.name}.')

  @staticmethod
  def convert_proto(data_store_proto):
    """Converts a data_store proto to a falken.common.proto.

    Args:
      data_store_proto: Proto object, an instance of a proto type defined in
        data_store.proto

    Returns:
      proto conversion of the data_store_proto in falken.common.proto.

    Raises:
      ValueError: If the provided data_store_proto could not be converted.
    """
    data_store_proto_type = type(data_store_proto)
    target_proto_type = ProtoConverter._get_target_proto(data_store_proto_type)
    converted_proto = target_proto_type()

    for field_name in data_store_proto.DESCRIPTOR.fields_by_name:
      target_field_name = ProtoConverter._get_target_field_name(
          field_name, data_store_proto_type, target_proto_type)
      if target_field_name:
        target_field = converted_proto.DESCRIPTOR.fields_by_name[
            target_field_name]
        source_field = data_store_proto.DESCRIPTOR.fields_by_name[field_name]
        ProtoConverter._set_field(
            converted_proto, target_field_name,
            ProtoConverter._convert_field(source_field, data_store_proto,
                                          target_field))
    return converted_proto
