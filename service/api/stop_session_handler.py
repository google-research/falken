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
"""Handles stopping of an active session."""

from absl import logging
from api import unique_id

import common.generate_protos  # pylint: disable=unused-import
from data_store import data_store as data_store_module
from data_store import resource_id
import data_store_pb2
import falken_service_pb2
from google.rpc import code_pb2
import session_pb2


def stop_session(request, context, data_store):
  """Stops an active session.

  Args:
    request: falken_service_pb2.StopSessionRequest containing information
      about the session requested to be stopped.
    context: grpc.ServicerContext containing context about the RPC.
    data_store: Falken data_store.DataStore object to update the session.

  Returns:
    falken_service_pb2.StopSessionResponse containing the snapshot_id for the
      session.

  Raises:
    Exception: The gRPC context is aborted when the session is not found in
      data_store, or other issues occur in the handling.
  """
  logging.debug('StopSession called for project_id %s with session %s.',
                request.project_id, request.session.name)
  session = None
  session_resource_id = resource_id.FalkenResourceId(
      project=request.session.project_id,
      brain=request.session.brain_id,
      session=request.session.name)
  try:
    session = data_store.read(session_resource_id)
  except FileNotFoundError as e:
    context.abort(
        code_pb2.NOT_FOUND,
        f'Failed to find session {session_resource_id.session} in data_store. '
        f'{e}')

  model_resource_id = _get_final_model_from_model_selector()

  snapshot_id = _get_snapshot_id(
      session_resource_id, session, model_resource_id, data_store, context)

  # Update session to be ended with snapshot ID.
  _update_session_end()

  return falken_service_pb2.StopSessionResponse(snapshot_id=snapshot_id)


def _get_final_model_from_model_selector():
  raise NotImplementedError('Model selector code is still in progress.')


def _get_snapshot_id(
    session_resource_id, session, model_resource_id, data_store, context):
  """Get snapshot ID for the session differentiated by session type.

  Creates a new snapshot if appropriate.

  Args:
    session_resource_id: resource_id.FalkenResourceID for the session being
      stopped.
    session: data_store_pb2.Session instance.
    model_resource_id: resource_id.FalkenResourceID for the model that was
      selected by model_selector for this session.
    data_store: data_store.DataStore instance to read and write the new
      snapshot into.
    context: grpc.ServicerContext containing context to abort when issues occur.

  Returns:
    Snapshot ID string.

  Raises:
    The gRPC context is aborted when issues occur with reading/writing the
      snapshot.
  """

  # If training happened (training or evaluation), create new snapshot,
  # otherwise return initial snapshot.
  if session.session_type == session_pb2.INFERENCE:
    # End of an inference session, return the initial snapshot.
    try:
      return _single_starting_snapshot(
          session_resource_id, session.starting_snapshots)
    except ValueError as e:
      context.abort(code_pb2.INVALID_ARGUMENT, e)
  elif session.session_type == session_pb2.INTERACTIVE_TRAINING:
    try:
      return _create_or_use_existing_snapshot(
          session_resource_id, session.starting_snapshots, model_resource_id,
          data_store, expect_starting_snapshot=False)
    except (FileNotFoundError, data_store_module.InternalError,
            ValueError) as e:
      context.abort(
          code_pb2.NOT_FOUND, 'Failed to create snapshot for training session '
          f'{session_resource_id.session}. {e}')
  elif session.session_type == session_pb2.EVALUATION:
    try:
      return _create_or_use_existing_snapshot(
          session_resource_id, session.starting_snapshots, model_resource_id,
          data_store, expect_starting_snapshot=True)
    except (FileNotFoundError, data_store_module.InternalError,
            ValueError) as e:
      context.abort(
          code_pb2.NOT_FOUND, 'Failed to create snapshot for evaluation session'
          f' {session_resource_id.session}. {e}')
  else:
    context.abort(
        code_pb2.INVALID_ARGUMENT,
        f'Unsupported session_type: {session.session_type} found in '
        f'{session.session_id}.')


def _single_starting_snapshot(session_resource_id, starting_snapshots):
  """Returns the single starting snapshot from a list of snapshot IDs.

  Args:
    session_resource_id: resource_id.FalkenResourceId for the session with the
      starting snapshots.
    starting_snapshots: List of snapshot IDs specified as starting snapshots
      for the session.

  Returns:
    Starting snapshot ID string.

  Raises:
    ValueError if the length of starting snapshots is not 1.
  """
  if len(starting_snapshots) != 1:
    raise ValueError(
        'Unexpected number of starting_snapshots, wanted exactly 1, got '
        f'{len(starting_snapshots)} for session {session_resource_id.session}.')
  return starting_snapshots[0]


def _create_or_use_existing_snapshot(
    session_resource_id, starting_snapshots, model_resource_id,
    data_store, expect_starting_snapshot):
  """Return snapshot ID for a new snapshot or existing snapshot.

  If a final model was selected by model_selector and passed onto the
  model_resource_id, creates a snapshot for this model and return the snapshot
  ID. Otherwise, returns the starting snapshot ID.

  Args:
    session_resource_id: resource_id.FalkenResourceID for the session being
      stopped.
    starting_snapshots: Starting snapshot IDs of the session being stopped.
    model_resource_id: resource_id.FalkenResourceID for the model that was
      selected by model_selector for this session.
    data_store: data_store.DataStore instance to read and write the new
      snapshot into.
    expect_starting_snapshot: bool, whether we are expecting a starting
      snapshot. If False and no model ID is found, we return an empty string.

  Returns:
    Snapshot ID string for the created snapshot or the starting snapshot.

  Raises:
    FileNotFoundError, InternalError for issues while writing the snapshot.
    ValueError for issues while getting starting snapshot IDs.
  """
  if model_resource_id:
    # Use model ID for new snapshot.
    model = data_store.read(model_resource_id)
    return _create_snapshot(session_resource_id, starting_snapshots,
                            model_resource_id, model.model_path, data_store)
  else:
    # Return existing snapshot. Callers with expect_starting_snapshot True will
    # raise ValueError if the len(starting_shots) != 1.
    if len(starting_snapshots) == 1 or expect_starting_snapshot:
      return _single_starting_snapshot(
          session_resource_id, starting_snapshots)
    return ''


def _create_snapshot(session_resource_id, starting_snapshots,
                     model_resource_id, model_path, data_store):
  """Creates a new snapshot in data_store.

  Args:
    session_resource_id: resource_id.FalkenResourceID for the session to create
      the new snapshot for.
    starting_snapshots: Starting snapshot IDs of the session to create the
      new snapshot for.
    model_resource_id: resource_id.FalkenResourceID for the model that was
      selected by model_selector to create the snapshot for.
    model_path: Path for the model to write the snapshot for.
    data_store: data_store.DataStore instance to read and write the new
      snapshot into.

  Returns:
    Snapshot ID string for the created snapshot.

  Raises:
    FileNotFoundError if any starting snapshots cannot be found on data_store.
    InternalError if something goes wrong with writing the snapshot on
      data_store.
  """
  snapshot_resource_id = resource_id.FalkenResourceId(
      project=session_resource_id.project, brain=session_resource_id.brain,
      snapshot=unique_id.generate_unique_id())
  write_snapshot = data_store_pb2.Snapshot(
      project_id=snapshot_resource_id.project,
      brain_id=snapshot_resource_id.brain,
      snapshot_id=snapshot_resource_id.snapshot)
  write_snapshot.model = model_resource_id.model
  write_snapshot.model_path = model_path

  for starting_snapshot_id in starting_snapshots:
    starting_snapshot_resource_id = resource_id.FalkenResourceId(
        str(snapshot_resource_id))
    starting_snapshot_resource_id.snapshot = starting_snapshot_id
    starting_snapshot = data_store.read(starting_snapshot_resource_id)

    # Add parent snapshot to the graph and copy the ancestors.
    parent = data_store_pb2.SnapshotParents(
        snapshot=snapshot_resource_id.snapshot)
    parent.parent_snapshots.append(starting_snapshot_id)
    write_snapshot.ancestor_snapshots.append(parent)
    for ancestor in starting_snapshot.ancestor_snapshots:
      write_snapshot.ancestor_snapshots.append(ancestor)

  data_store.write(write_snapshot)
  return snapshot_resource_id.snapshot


def _update_session_end():
  raise NotImplementedError()

