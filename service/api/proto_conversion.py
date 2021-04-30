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


class ProtoConverter:
  """Module to convert data_store protos to API consumable protos."""

  # Allow mapping from common proto fields to data_store proto fields.
  _PROTO_FIELD_NAME_MAP = {'display_name': 'name'}

  # Lazily initialized by convert_data_store_proto().
  _DATA_STORE_PROTO_TO_COMMON_PROTO = {}
  _DATA_STORE_FIELD_TO_CONVERTER = {}

  @staticmethod
  def _convert_create_time(proto):
    """Converts proto's created_micros field to google.protobuf.Timestamp.

    Args:
      proto: The proto which contains the created_micros field.

    Returns:
      google.protobuf.Timestamp representation of the uint64 time in the
        provided proto.
    """
    return timestamp_pb2.Timestamp(seconds=proto.created_micros // 1000000)

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
    else:
      setattr(target_proto, field_name, value)

  @staticmethod
  def convert_data_store_proto(data_store_proto):
    """Converts a data_store proto to a falken.common.proto.

    Args:
      data_store_proto: Proto object, an instance of a proto type defined in
        data_store.proto

    Returns:
      proto conversion of the data_store_proto in falken.common.proto.

    Raises:
      ValueError: If the provided data_store_proto could not be converted.
    """
    if not ProtoConverter._DATA_STORE_PROTO_TO_COMMON_PROTO:
      ProtoConverter._DATA_STORE_PROTO_TO_COMMON_PROTO = {
          data_store_pb2.Brain: brain_pb2.Brain
      }
    if not ProtoConverter._DATA_STORE_FIELD_TO_CONVERTER:
      ProtoConverter._DATA_STORE_FIELD_TO_CONVERTER = {
          'create_time': ProtoConverter._convert_create_time
      }
    target_proto_type = ProtoConverter._DATA_STORE_PROTO_TO_COMMON_PROTO.get(
        type(data_store_proto))
    if not target_proto_type:
      raise ValueError(
          f'Proto {type(data_store_proto)} could not be mapped to any common '
          'proto.')
    converted_proto = target_proto_type()
    for field_name in converted_proto.DESCRIPTOR.fields_by_name:
      if field_name in data_store_proto.DESCRIPTOR.fields_by_name:
        ProtoConverter._set_field(converted_proto, field_name,
                                  getattr(data_store_proto, field_name))
      elif field_name in ProtoConverter._PROTO_FIELD_NAME_MAP:
        ProtoConverter._set_field(
            converted_proto, field_name,
            getattr(data_store_proto,
                    ProtoConverter._PROTO_FIELD_NAME_MAP[field_name]))
      elif field_name in ProtoConverter._DATA_STORE_FIELD_TO_CONVERTER:
        ProtoConverter._set_field(
            converted_proto, field_name,
            ProtoConverter._DATA_STORE_FIELD_TO_CONVERTER[field_name](
                data_store_proto))
      else:
        raise ValueError(
            f'Proto {type(data_store_proto)}\'s field {field_name} could not '
            'be mapped.')
    return converted_proto
