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
"""Retrieve an existing Falken object from data_store."""

from absl import logging
from api import proto_conversion
from data_store import resource_id

import common.generate_protos  # pylint: disable=unused-import,g-bad-import-order
from google.rpc import code_pb2


class GetHandler:
  """Handles retrieving of a Falken proto instance for a given request.

  This is a base class extended by implementation handlers for each type of
  request.
  """

  def __init__(self, request, context, data_store, request_args,
               glob_pattern):
    """Initialize GetHandler.

    Args:
      request: falken_service_pb2.Get*Request containing fields that are used
        to query the Falken object.
      context: grpc.ServicerContext containing context about the RPC.
      data_store: Falken data_store.DataStore object to read the Falken object
        from.
      request_args: list of field names of the request, ordered in
        FALKEN_RESOURCE_SPEC in data_store/resource_id.py
      glob_pattern: String used in combination with request_args to generate the
        resource_id.FalkenResourceId to query the data_store.
    """
    self._request = request
    self._context = context
    self._request_type = type(request)
    self._data_store = data_store
    self._glob_pattern = glob_pattern
    self._request_args = request_args

  def get(self):
    """Retrieves the instance requested from data store.

    Returns:
      session: Falken proto that was requested.

    Raises:
      Exception: The gRPC context is aborted when the required fields are not
        specified in the request, which raises an exception to terminate the RPC
        with a no-OK status.
    """
    logging.debug('Get called with request %s', str(self._request))

    args = []
    for arg in self._request_args:
      if not getattr(self._request, arg):
        self._context.abort(
            code_pb2.INVALID_ARGUMENT,
            f'Could not find {arg} in {self._request_type}.')
      args.append(getattr(self._request, arg))

    return self._read_and_convert_proto(
        resource_id.FalkenResourceId(self._glob_pattern.format(*args)))

  def _read_and_convert_proto(self, res_id):
    return proto_conversion.ProtoConverter.convert_proto(
        self._data_store.read(res_id))


class GetBrainHandler(GetHandler):
  """Handles retrieving an existing brain."""

  def __init__(self, request, context, data_store):
    super().__init__(request, context, data_store, ['project_id', 'brain_id'],
                     'projects/{0}/brains/{1}')


class GetSessionHandler(GetHandler):
  """Handles retrieving an existing session."""

  def __init__(self, request, context, data_store):
    super().__init__(
        request, context, data_store, ['project_id', 'brain_id', 'session_id'],
        'projects/{0}/brains/{1}/sessions/{2}')


class GetSessionByIndexHandler(GetHandler):
  """Handles retrieving an existing session by index."""

  def __init__(self, request, context, data_store):
    super().__init__(request, context, data_store, ['project_id', 'brain_id'],
                     'projects/{0}/brains/{1}/sessions/*')

  def get(self):
    logging.debug(
        'GetSessionByIndex called for project_id %s with brain_id %s and index '
        '%d.', self._request.project_id, self._request.brain_id,
        self._request.session_index)
    if not (self._request.project_id and self._request.brain_id and
            self._request.session_index):
      self._context.abort(
          code_pb2.INVALID_ARGUMENT,
          'Project ID, brain ID, and session index must be specified in '
          'GetSessionByIndexRequest.')

    session_ids, _ = self._data_store.list(
        resource_id.FalkenResourceId(
            self._glob_pattern.format(
                self._request.project_id, self._request.brain_id)),
        page_size=self._request.session_index + 1)
    if len(session_ids) < self._request.session_index:
      self._context.abort(
          code_pb2.INVALID_ARGUMENT,
          f'Session at index {self._request.session_index} was not found.')

    return self._read_and_convert_proto(
        session_ids[self._request.session_index])


class GetModelHandler(GetHandler):
  """Handles retrieving an existing model."""

  def __init__(self, request, context, data_store):
    super().__init__(request, context, data_store,
                     ['project_id', 'brain_id', 'session_id', 'model_id'],
                     'projects/{0}/brains/{1}/sessions/{2}/models/{3}')

    if request.snapshot_id and request.model_id:
      context.abort(
          code_pb2.INVALID_ARGUMENT,
          'Either model ID or snapshot ID should be specified, not both. '
          f'Found snapshot_id {request.snapshot_id} and model_id '
          f'{request.model_id}.')

    if request.snapshot_id:
      self._request_args = [
          'project_id', 'brain_id', 'session_id', 'snapshot_id']
      self._glob_pattern = 'projects/{0}/brains/{1}/sessions/{2}/snapshots/{3}'

