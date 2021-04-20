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

"""Reads and writes data from storage."""

import os.path


class DataStore(object):
  """Reads and writes data from storage."""

  def __init__(self, root_path):
    """Initializes the data store with a given root path.

    Args:
      root_path: Path where all Falken files will be stored.
    """
    self._root_path = root_path

  def _get_project_path(self, project_id):
    """Gives the path for a project."""
    assert project_id
    return os.path.join(self._root_path, 'projects', project_id)

  def _get_brain_path(self, project_id, brain_id):
    """Gives the path for a brain."""
    assert brain_id
    return os.path.join(self._get_project_path(project_id), 'brains', brain_id)

  def _get_snapshot_path(self, project_id, brain_id, snapshot_id):
    """Gives the path for a snapshot."""
    assert snapshot_id
    return os.path.join(
        self._get_brain_path(project_id, brain_id), 'snapshots', snapshot_id)

  def _get_session_path(self, project_id, brain_id, session_id):
    """Gives the path for a session."""
    assert session_id
    return os.path.join(
        self._get_brain_path(project_id, brain_id), 'sessions', session_id)

  def _get_episode_path(self, project_id, brain_id, session_id, episode_id):
    """Gives the path for an episode."""
    assert episode_id
    return os.path.join(
        self._get_session_path(project_id, brain_id, session_id), 'episodes',
        episode_id)

  def _get_chunk_path(
      self, project_id, brain_id, session_id, episode_id, chunk_id):
    """Gives the path for an episode chunk."""
    assert chunk_id
    return os.path.join(
        self._get_episode_path(project_id, brain_id, session_id, episode_id),
        'chunks', chunk_id)

  def _get_assignment_path(
      self, project_id, brain_id, session_id, assignment_id):
    """Gives the path for an assignment."""
    assert assignment_id
    return os.path.join(
        self._get_session_path(project_id, brain_id, session_id),
        'assignments', assignment_id)

  def _get_model_path(
      self, project_id, brain_id, session_id, model_id):
    """Gives the path for a model."""
    assert model_id
    return os.path.join(
        self._get_session_path(project_id, brain_id, session_id),
        'models', model_id)

  def _get_offline_evaluation_path(
      self, project_id, brain_id, session_id, model_id, evaluation_set_id):
    """Gives the path for an offline evaluation."""
    assert evaluation_set_id
    return os.path.join(
        self._get_model_path(project_id, brain_id, session_id, model_id),
        'offline_evaluations', evaluation_set_id)
