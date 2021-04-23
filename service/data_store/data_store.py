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

import hashlib
import os
import os.path

import common.generate_protos  # pylint: disable=g-bad-import-order,unused-import

import data_store_pb2


_PROJECT_FILE_NAME = 'project.pb'
_BRAIN_FILE_NAME = 'brain.pb'
_SNAPSHOT_FILE_NAME = 'snapshot.pb'
_SESSION_FILE_NAME = 'session.pb'
_CHUNK_FILE_NAME = 'episode_chunk.pb'
_ONLINE_EVALUATION_FILE_NAME = 'online_evaluation.pb'
_ASSIGNMENT_FILE_NAME = 'assignment.pb'
_MODEL_FILE_NAME = 'model.pb'
_SERIALIZED_MODEL_FILE_NAME = 'serialized_model.pb'
_OFFLINE_EVALUATION_FILE_NAME = 'offline_evaluation.pb'


class DataStore(object):
  """Reads and writes data from storage."""

  def __init__(self, root_path):
    """Initializes the data store with a given root path.

    Args:
      root_path: Path where all Falken files will be stored.
    """
    self._root_path = root_path

  def read_project(self, project_id):
    """Retrieves a project proto from storage.

    Args:
      project_id: The project id string for the object to retrieve.
    Returns:
      A Project proto.
    """
    return self._read_proto(self._get_project_path(project_id),
                            _PROJECT_FILE_NAME, data_store_pb2.Project)

  def write_project(self, project):
    """Writes a project proto to storage.

    Args:
      project: The Project proto to write.
    """
    self._write_proto(
        self._get_project_path(project.project_id), _PROJECT_FILE_NAME, project)

  def read_brain(self, project_id, brain_id):
    """Retrieves a brain proto from storage.

    Args:
      project_id: The project id string for the object to retrieve.
      brain_id: The brain id string for the object to retrieve.
    Returns:
      A Brain proto.
    """
    return self._read_proto(self._get_brain_path(project_id, brain_id),
                            _BRAIN_FILE_NAME, data_store_pb2.Brain)

  def write_brain(self, brain):
    """Writes a brain proto to storage.

    Args:
      brain: The Brain proto to write.
    """
    self._write_proto(
        self._get_brain_path(brain.project_id, brain.brain_id),
        _BRAIN_FILE_NAME, brain)

  def read_snapshot(self, project_id, brain_id, snapshot_id):
    """Retrieves a snapshot proto from storage.

    Args:
      project_id: The project id string for the object to retrieve.
      brain_id: The brain id string for the object to retrieve.
      snapshot_id: The snapshot id string for the object to retrieve.
    Returns:
      A Snapshot proto.
    """
    return self._read_proto(
        self._get_snapshot_path(project_id, brain_id, snapshot_id),
        _SNAPSHOT_FILE_NAME, data_store_pb2.Snapshot)

  def write_snapshot(self, snapshot):
    """Writes a snapshot proto to storage.

    Args:
      snapshot: The Snapshot proto to write.
    """
    self._write_proto(
        self._get_snapshot_path(
            snapshot.project_id, snapshot.brain_id, snapshot.snapshot_id),
        _SNAPSHOT_FILE_NAME, snapshot)

  def read_session(self, project_id, brain_id, session_id):
    """Retrieves a session proto from storage.

    Args:
      project_id: The project id string for the object to retrieve.
      brain_id: The brain id string for the object to retrieve.
      session_id: The session id string for the object to retrieve.
    Returns:
      A Session proto.
    """
    return self._read_proto(
        self._get_session_path(project_id, brain_id, session_id),
        _SESSION_FILE_NAME, data_store_pb2.Session)

  def write_session(self, session):
    """Writes a session proto to storage.

    Args:
      session: The Session proto to write.
    """
    self._write_proto(
        self._get_session_path(
            session.project_id, session.brain_id, session.session_id),
        _SESSION_FILE_NAME, session)

  def read_episode_chunk(
      self, project_id, brain_id, session_id, episode_id, chunk_id):
    """Retrieves an episode chunk proto from storage.

    Args:
      project_id: The project id string for the object to retrieve.
      brain_id: The brain id string for the object to retrieve.
      session_id: The session id string for the object to retrieve.
      episode_id: The episode id string for the object to retrieve.
      chunk_id: The int describing the chunk id for the object to retrieve.
    Returns:
      An EpisodeChunk proto.
    """
    return self._read_proto(
        self._get_chunk_path(
            project_id, brain_id, session_id, episode_id, chunk_id),
        _CHUNK_FILE_NAME, data_store_pb2.EpisodeChunk)

  def write_episode_chunk(self, chunk):
    """Writes an episode chunk proto to storage.

    Args:
      chunk: The EpisodeChunk proto to write.
    """
    self._write_proto(
        self._get_chunk_path(
            chunk.project_id, chunk.brain_id, chunk.session_id,
            chunk.episode_id, chunk.chunk_id),
        _CHUNK_FILE_NAME, chunk)

  def read_online_evaluation(
      self, project_id, brain_id, session_id, episode_id):
    """Retrieves an online evaluation proto from storage.

    Args:
      project_id: The project id string for the object to retrieve.
      brain_id: The brain id string for the object to retrieve.
      session_id: The session id string for the object to retrieve.
      episode_id: The episode id string for the object to retrieve.
    Returns:
      An OnlineEvaluation proto.
    """
    return self._read_proto(
        self._get_episode_path(project_id, brain_id, session_id, episode_id),
        _ONLINE_EVALUATION_FILE_NAME, data_store_pb2.OnlineEvaluation)

  def write_online_evaluation(self, online_evaluation):
    """Writes an online evaluation proto to storage.

    Args:
      online_evaluation: The OnlineEvaluation proto to write.
    """
    self._write_proto(
        self._get_episode_path(
            online_evaluation.project_id, online_evaluation.brain_id,
            online_evaluation.session_id, online_evaluation.episode_id),
        _ONLINE_EVALUATION_FILE_NAME, online_evaluation)

  def read_assignment(self, project_id, brain_id, session_id, assignment_id):
    """Retrieves an assignment proto from storage.

    Args:
      project_id: The project id string for the object to retrieve.
      brain_id: The brain id string for the object to retrieve.
      session_id: The session id string for the object to retrieve.
      assignment_id: The assignment id string for the object to retrieve.
    Returns:
      An Assignment proto.
    """
    return self._read_proto(
        self._get_assignment_path(project_id, brain_id, session_id,
                                  assignment_id),
        _ASSIGNMENT_FILE_NAME, data_store_pb2.Assignment)

  def write_assignment(self, assignment):
    """Writes an assignment proto to storage.

    Args:
      assignment: The Assignment proto to write.
    """
    self._write_proto(
        self._get_assignment_path(
            assignment.project_id, assignment.brain_id, assignment.session_id,
            assignment.assignment_id),
        _ASSIGNMENT_FILE_NAME, assignment)

  def read_model(self, project_id, brain_id, session_id, model_id):
    """Retrieves a model proto from storage.

    Args:
      project_id: The project id string for the object to retrieve.
      brain_id: The brain id string for the object to retrieve.
      session_id: The session id string for the object to retrieve.
      model_id: The model id string for the object to retrieve.
    Returns:
      A Model proto.
    """
    return self._read_proto(
        self._get_model_path(project_id, brain_id, session_id, model_id),
        _MODEL_FILE_NAME, data_store_pb2.Model)

  def write_model(self, model):
    """Writes a model proto to storage.

    Args:
      model: The Model proto to write.
    """
    self._write_proto(
        self._get_model_path(
            model.project_id, model.brain_id, model.session_id, model.model_id),
        _MODEL_FILE_NAME, model)

  def read_serialized_model(
      self, project_id, brain_id, session_id, model_id):
    """Retrieves a serialized model proto from storage.

    Args:
      project_id: The project id string for the object to retrieve.
      brain_id: The brain id string for the object to retrieve.
      session_id: The session id string for the object to retrieve.
      model_id: The model id string for the object to retrieve.
    Returns:
      An SerializedModel proto.
    """
    return self._read_proto(
        self._get_model_path(project_id, brain_id, session_id, model_id),
        _SERIALIZED_MODEL_FILE_NAME, data_store_pb2.SerializedModel)

  def write_serialized_model(self, serialized_model):
    """Writes a serialized model proto to storage.

    Args:
      serialized_model: The SerializedModel proto to write.
    """
    self._write_proto(
        self._get_model_path(
            serialized_model.project_id, serialized_model.brain_id,
            serialized_model.session_id, serialized_model.model_id),
        _SERIALIZED_MODEL_FILE_NAME, serialized_model)

  def read_offline_evaluation(
      self, project_id, brain_id, session_id, model_id, evaluation_set_id):
    """Retrieves an offline evaluation proto from storage.

    Args:
      project_id: The project id string for the object to retrieve.
      brain_id: The brain id string for the object to retrieve.
      session_id: The session id string for the object to retrieve.
      model_id: The model id string for the object to retrieve.
      evaluation_set_id: The int describing the evaluation set id for the object
        to retrieve.
    Returns:
      An OfflineEvaluation proto.
    """
    return self._read_proto(
        self._get_offline_evaluation_path(
            project_id, brain_id, session_id, model_id, str(evaluation_set_id)),
        _OFFLINE_EVALUATION_FILE_NAME, data_store_pb2.OfflineEvaluation)

  def write_offline_evaluation(self, offline_evaluation):
    """Writes an offline evaluation proto to storage.

    Args:
      offline_evaluation: The OfflineEvaluation proto to write.
    """
    self._write_proto(
        self._get_offline_evaluation_path(
            offline_evaluation.project_id, offline_evaluation.brain_id,
            offline_evaluation.session_id, offline_evaluation.model_id,
            str(offline_evaluation.evaluation_set_id)),
        _OFFLINE_EVALUATION_FILE_NAME, offline_evaluation)

  def _read_proto(self, path, file, data_type):
    """Reads binary proto data from the given file.

    Args:
      path: The path of the directory where the proto is stored.
      file: The proto file name.
      data_type: The class of the proto to read.
    Returns:
      The proto that was read from storage.
    """
    with open(os.path.join(path, file), 'rb') as f:
      return data_type.FromString(f.read())

  def _write_proto(self, path, file, data):
    """Writes proto data into the given file.

    Args:
      path: The path of the directory where the proto is stored.
      file: The proto file name.
      data: A proto to store in that location.
    """
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, file), 'wb') as f:
      f.write(data.SerializeToString())

  def _get_project_path(self, project_id):
    """Gives the path for a project.

    Args:
      project_id: The project id string to use for building the path.
    Returns:
      A string describing the project directory path.
    """
    assert project_id
    return os.path.join(self._root_path, 'projects', project_id)

  def _get_brain_path(self, project_id, brain_id):
    """Gives the path for a brain.

    Args:
      project_id: The project id string to use for building the path.
      brain_id: The brain id string to use for building the path.
    Returns:
      A string describing the brain directory path.
    """
    assert brain_id
    return os.path.join(self._get_project_path(project_id), 'brains', brain_id)

  def _get_snapshot_path(self, project_id, brain_id, snapshot_id):
    """Gives the path for a snapshot.

    Args:
      project_id: The project id string to use for building the path.
      brain_id: The brain id string to use for building the path.
      snapshot_id: The snapshot id string for building the path.
    Returns:
      A string describing the snapshot directory path.
    """
    assert snapshot_id
    return os.path.join(
        self._get_brain_path(project_id, brain_id), 'snapshots', snapshot_id)

  def _get_session_path(self, project_id, brain_id, session_id):
    """Gives the path for a session.

    Args:
      project_id: The project id string to use for building the path.
      brain_id: The brain id string to use for building the path.
      session_id: The session id string for building the path.
    Returns:
      A string describing the session directory path.
    """
    assert session_id
    return os.path.join(
        self._get_brain_path(project_id, brain_id), 'sessions', session_id)

  def _get_episode_path(self, project_id, brain_id, session_id, episode_id):
    """Gives the path for an episode.

    Args:
      project_id: The project id string to use for building the path.
      brain_id: The brain id string to use for building the path.
      session_id: The session id string for building the path.
      episode_id: The episode id string for building the path.
    Returns:
      A string describing the episode directory path.
    """
    assert episode_id
    return os.path.join(
        self._get_session_path(project_id, brain_id, session_id), 'episodes',
        episode_id)

  def _get_chunk_path(
      self, project_id, brain_id, session_id, episode_id, chunk_id):
    """Gives the path for an episode chunk.

    Args:
      project_id: The project id string to use for building the path.
      brain_id: The brain id string to use for building the path.
      session_id: The session id string for building the path.
      episode_id: The episode id string for building the path.
      chunk_id: An int describing the episode chunk id for building the path.
    Returns:
      A string describing the episode chunk directory path.
    """
    assert chunk_id
    return os.path.join(
        self._get_episode_path(project_id, brain_id, session_id, episode_id),
        'chunks', str(chunk_id))

  def _get_assignment_path(
      self, project_id, brain_id, session_id, assignment_id):
    """Gives the path for an assignment.

    Args:
      project_id: The project id string to use for building the path.
      brain_id: The brain id string to use for building the path.
      session_id: The session id string for building the path.
      assignment_id: The assignment id string for building the path.
    Returns:
      A string describing the assignment directory path.
    """
    assert assignment_id
    return os.path.join(
        self._get_session_path(project_id, brain_id, session_id),
        'assignments',
        hashlib.sha256(assignment_id.encode('utf-8')).hexdigest())

  def _get_model_path(
      self, project_id, brain_id, session_id, model_id):
    """Gives the path for a model.

    Args:
      project_id: The project id string to use for building the path.
      brain_id: The brain id string to use for building the path.
      session_id: The session id string for building the path.
      model_id: The model id string for building the path.
    Returns:
      A string describing the model directory path.
    """
    assert model_id
    return os.path.join(
        self._get_session_path(project_id, brain_id, session_id),
        'models', model_id)

  def _get_offline_evaluation_path(
      self, project_id, brain_id, session_id, model_id, evaluation_set_id):
    """Gives the path for an offline evaluation.

    Args:
      project_id: The project id string to use for building the path.
      brain_id: The brain id string to use for building the path.
      session_id: The session id string for building the path.
      model_id: The model id string for building the path.
      evaluation_set_id: The int describing the evaluation set id, used
        for building the path.
    Returns:
      A string describing the offline evaluation directory path.
    """
    assert evaluation_set_id
    return os.path.join(
        self._get_model_path(project_id, brain_id, session_id, model_id),
        'offline_evaluations', evaluation_set_id)
