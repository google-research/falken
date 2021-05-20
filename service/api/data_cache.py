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
"""Handles caching for falken data_store objects."""

import functools

_MAX_CACHE = 512


def get_brain_spec(data_store, project_id, brain_id):
  """Get cached brain's brain_spec.

  Args:
    data_store: data_store.DataStore to read from if the brain is not cached.
    project_id: Project ID associated with the requested brain spec.
    brain_id: Brain ID associated with the requested brain spec.

  Returns:
    brain_pb2.BrainSpec instance.
  """
  return get_brain(data_store, project_id, brain_id).brain_spec


@functools.lru_cache(maxsize=_MAX_CACHE)
def get_brain(data_store, project_id, brain_id):
  """Get cached brain or read brain from data_store.

  Args:
    data_store: data_store.DataStore to read from if the brain is not cached.
    project_id: Project ID associated with the requested brain.
    brain_id: Brain ID associated with the requested brain.

  Returns:
    data_store_pb2.Brain instance.
  """
  return data_store.read_by_proto_ids(project_id=project_id, brain_id=brain_id)


@functools.lru_cache(maxsize=_MAX_CACHE)
def get_session_type(data_store, project_id, brain_id, session_id):
  """Get the cached session type (immutable) of a session.

  Args:
    data_store: data_store.DataStore to read from if the session is not cached.
    project_id: Project ID associated with the requested session.
    brain_id: Brain ID associated with the requested session.
    session_id: Session ID associated with the requested session.

  Returns:
    session_pb2.SessionType enum.
  """
  return data_store.read_by_proto_ids(
      project_id=project_id, brain_id=brain_id,
      session_id=session_id).session_type


@functools.lru_cache(maxsize=_MAX_CACHE)
def get_starting_snapshot(data_store, project_id, brain_id, session_id):
  """Returns a data_store_pb2.Snapshot of the starting snapshot for a session.

  Args:
    data_store: data_store.DataStore to read from if the snapshot is not cached.
    project_id: Project ID associated with the requested session.
    brain_id: Brain ID associated with the requested session.
    session_id: Session ID associated with the requested session.

  Returns:
    data_store_pb2.Snapshot instance.

  Raises:
    ValueError if session doesn't have exactly one starting_snapshots.
  """
  session = data_store.read_by_proto_ids(
      project_id=project_id, brain_id=brain_id,
      session_id=session_id)
  if len(session.starting_snapshots) != 1:
    raise ValueError(
        f'Require exactly 1 starting snapshot, got '
        f'{len(session.starting_snapshots)} for session {session.session_id}.')
  return data_store.read_by_proto_ids(
      project_id=project_id, brain_id=brain_id,
      session_id=session_id, snapshot_id=session.starting_snapshots[0])
