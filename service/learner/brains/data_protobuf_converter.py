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

import numpy as np


import common.generate_protos  # pylint: disable=unused-import
import action_pb2
import observation_pb2
import primitives_pb2


class ConversionError(Exception):
  """Raised when data can't be converted."""


class DataProtobufConverter:
  """Converts a data proto to a tensor."""

  # Lazily initialized by to_tensor().
  _DATA_PROTO_CLASS_TO_CONVERTER = None

  @staticmethod
  def _category_to_tensor(data):
    """Convert a Category proto to a tensor.

    Args:
      data: Category proto.

    Returns:
      1 element numpy array.
    """
    return np.array([data.value], dtype=np.int32)

  @staticmethod
  def _number_to_tensor(data):
    """Convert a Number proto to a tensor.

    Args:
      data: Number proto.

    Returns:
      1 element numpy array.
    """
    return np.array([data.value], dtype=np.float32)

  @staticmethod
  def _position_to_tensor(data):
    """Convert a Position proto to a tensor.

    Args:
      data: Position proto.

    Returns:
      3 element numpy array.
    """
    return np.array([data.x, data.y, data.z], dtype=np.float32)

  @staticmethod
  def _rotation_to_tensor(data):
    """Convert a Rotation proto to a tensor.

    Args:
      data: Rotation proto.

    Returns:
      4 element numpy array.
    """
    return np.array([data.x, data.y, data.z, data.w], dtype=np.float32)

  @staticmethod
  def _feeler_to_tensor(data):
    """Convert a Feeler proto to a tensor.

    Args:
      data: Feeler proto.

    Returns:
      Numpy tensor.
    """
    measurements = data.measurements
    count = len(measurements)
    experimental_data_count = (
        len(measurements[0].experimental_data) if count else 0)
    values = np.empty([count, 1 + experimental_data_count], dtype=np.float32)
    # NOTE: Accessing repeated fields by index is ~10% faster than enumerating
    # which results in a temporary tuple being allocated then unpacked into two
    # variables per iteration.
    for i in range(count):
      measurement = measurements[i]
      values[i, 0] = measurement.distance.value
      experimental_data = measurement.experimental_data
      for j in range(experimental_data_count):
        values[i, j + 1] = experimental_data[j].value
    return values

  @staticmethod
  def _joystick_to_tensor(data):
    """Convert a Joystick proto to a tensor.

    Args:
      data: Joystick proto.

    Returns:
      2 element numpy array.
    """
    return np.array([data.x_axis, data.y_axis], dtype=np.float32)

  @staticmethod
  def leaf_to_tensor(data, name):
    """Convert the specified data proto to a tensor.

    Args:
      data: Data protobuf. This should be validated against a spec using
        ProtobufValidator before conversion.
      name: Name to report if conversion fails.

    Returns:
      Numpy array / tensor.

    Raises:
      ConversionError: If the data can't be converted.
    """
    if not DataProtobufConverter._DATA_PROTO_CLASS_TO_CONVERTER:
      DataProtobufConverter._DATA_PROTO_CLASS_TO_CONVERTER = {
          primitives_pb2.Category: DataProtobufConverter._category_to_tensor,
          primitives_pb2.Number: DataProtobufConverter._number_to_tensor,
          primitives_pb2.Position: DataProtobufConverter._position_to_tensor,
          primitives_pb2.Rotation: DataProtobufConverter._rotation_to_tensor,
          observation_pb2.Feeler: DataProtobufConverter._feeler_to_tensor,
          action_pb2.Joystick: DataProtobufConverter._joystick_to_tensor,
      }
    converter = DataProtobufConverter._DATA_PROTO_CLASS_TO_CONVERTER.get(
        type(data))
    if not converter:
      raise ConversionError(f'Failed to convert {name} ({data}) to a tensor.')
    return converter(data)
