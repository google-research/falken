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
# pylint: disable=g-bad-import-order, unused-import
"""Create a new brain. The returned brains can be trained in sessions."""

import common.generate_protos
import brain_pb2
import data_store_pb2
import traceback

from absl import logging
from api import data_cache
from api import proto_conversion
from api import resource_id
from learner.brains import specs
from google.protobuf import any_pb2
from google.protobuf import timestamp_pb2
from google.rpc import code_pb2
from google.rpc import status_pb2
from google.rpc import error_details_pb2


def create_brain(request, context, data_store):
  """Creates a new brain.

  Stores the brain in data_store and converts the data_store to the API-accepted
  proto and returns it.

  Args:
    request: falken_service_pb2.CreateBrainRequest containing information about
      the brain requested to be created.
    context: grpc.ServicerContext containing context about the RPC.
    data_store: Falken data_store.DataStore object to write the brain.

  Returns:
    brain: brain_pb2.Brain proto object of the brain that was just created.

  Raises:
    Exception: The gRPC context is aborted when the brain spec is invalid,
    which raises an exception to terminate the RPC with a no-OK status.
  """
  logging.debug(
      'CreateBrain called for project %s and brain_spec %s for brain '
      'name %s.', request.project_id, request.brain_spec, request.display_name)
  try:
    _ = specs.ProtobufNode.from_spec(request.brain_spec)

  except specs.InvalidSpecError as e:
    context.abort(
        code_pb2.INVALID_ARGUMENT,
        'Unable to create Brain. BrainSpec spec invalid. Error: ' + repr(e))
    return

  write_data_store_brain = data_store_pb2.Brain(
      project_id=request.project_id,
      brain_id=resource_id.generate_resource_id(),
      name=request.display_name,
      brain_spec=request.brain_spec)
  data_store.write(write_data_store_brain)
  return proto_conversion.ProtoConverter.convert_proto(
      data_cache.get_brain(data_store, write_data_store_brain.project_id,
                           write_data_store_brain.brain_id))
