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
"""Reads and writes data from storage."""

import hashlib
import os
import os.path
import re
import time

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import data_store_pb2


_PROJECT_FILE_PATTERN = 'project_*.pb'
_BRAIN_FILE_PATTERN = 'brain_*.pb'
_SNAPSHOT_FILE_PATTERN = 'snapshot_*.pb'
_SESSION_FILE_PATTERN = 'session_*.pb'
_CHUNK_FILE_PATTERN = 'episode-chunk_*.pb'
_ONLINE_EVALUATION_FILE_PATTERN = 'online-evaluation_*.pb'
_ASSIGNMENT_FILE_PATTERN = 'assignment_*.pb'
_MODEL_FILE_PATTERN = 'model_*.pb'
_SERIALIZED_MODEL_FILE_PATTERN = 'serialized-model_*.pb'
_OFFLINE_EVALUATION_FILE_PATTERN = 'offline-evaluation_*.pb'


# Allow retrieving file patterns by the corresponding file type.
_FILE_PATTERN_BY_RESOURCE_TYPE = {
    'brain': _BRAIN_FILE_PATTERN,
    'session': _SESSION_FILE_PATTERN,
    'episode_chunk': _CHUNK_FILE_PATTERN,
    'online_evaluation': _ONLINE_EVALUATION_FILE_PATTERN,
    'model': _MODEL_FILE_PATTERN,
    'snapshot': _SNAPSHOT_FILE_PATTERN
}


# Allow retrieving the parent directory in which a resource of a given
# resource type is stored.
_DIRECTORY_BY_RESOURCE_TYPE = {
    'project': 'projects',
    'brain': 'brains',
    'snapshot': 'snapshots',
    'session': 'sessions',
    'episode': 'episodes',
    'episode_chunk': 'chunks',
    'online_evaluation': 'episodes',
    'assignment': 'assignments',
    'model': 'models',
    'offline_evaluation': 'offline_evaluations'
}


class NotFoundError(Exception):
  """Raised when datastore cannot find a requested object."""
  pass


class ListOptions(object):
  """List options for methods like DataStore.list_brains."""

  def __init__(self, page_token=None, minimum_timestamp=None):
    """Initializes the list options.

    Only one of page_token or minimum_timestamp arguments should be specified.

    Args:
      page_token: A string token indicating where to start pagination, or None.
      minimum_timestamp: An integer indicating which timestamp to start listing
        from; or None.
    """
    if page_token and minimum_timestamp is not None:
      raise ValueError(
          'At least one of page_token and from_timestamp should be None.')

    self.page_token = page_token
    self.minimum_timestamp = minimum_timestamp

  def __eq__(self, obj):
    """Overrides equality method."""
    return (obj.page_token == self.page_token and
            obj.minimum_timestamp == self.minimum_timestamp)


class DataStore(object):
  """Reads and writes data from storage."""

  _FILENAME_METADATA_RE = re.compile(
      r'^(?P<name>[^_]+)_(?P<timestamp>[0-9]+)\..*')

  def __init__(self, file_system):
    """Initializes the data store with a given root path.

    Args:
      file_system: A FileSystem or MockFileSystem object.
    """
    self._fs = file_system
    self._callbacks = {}

  def __del__(self):
    self.remove_all_assignment_callbacks()

  def read_project(self, project_id):
    """Retrieves a project proto from storage.

    Args:
      project_id: The project id string for the object to retrieve.
    Returns:
      A Project proto.
    """
    return self._read_proto(
        os.path.join(self._get_project_glob(project_id), _PROJECT_FILE_PATTERN),
        data_store_pb2.Project)

  def write_project(self, project):
    """Writes a project proto to storage.

    Args:
      project: The Project proto to write.
    """
    self._check_type(project, data_store_pb2.Project)
    self._write_proto(
        os.path.join(
            self._get_project_glob(project.project_id), _PROJECT_FILE_PATTERN),
        project)

  def read_brain(self, project_id, brain_id):
    """Retrieves a brain proto from storage.

    Args:
      project_id: The project id string for the object to retrieve.
      brain_id: The brain id string for the object to retrieve.
    Returns:
      A Brain proto.
    """
    return self._read_proto(
        os.path.join(self._get_brain_glob(project_id, brain_id),
                     _BRAIN_FILE_PATTERN), data_store_pb2.Brain)

  def write_brain(self, brain):
    """Writes a brain proto to storage.

    Args:
      brain: The Brain proto to write.
    """
    self._check_type(brain, data_store_pb2.Brain)
    self._write_proto(
        os.path.join(
            self._get_brain_glob(brain.project_id, brain.brain_id),
            _BRAIN_FILE_PATTERN),
        brain)

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
        os.path.join(
            self._get_snapshot_glob(project_id, brain_id, snapshot_id),
            _SNAPSHOT_FILE_PATTERN),
        data_store_pb2.Snapshot)

  def write_snapshot(self, snapshot):
    """Writes a snapshot proto to storage.

    Args:
      snapshot: The Snapshot proto to write.
    """
    self._check_type(snapshot, data_store_pb2.Snapshot)
    self._write_proto(
        os.path.join(
            self._get_snapshot_glob(snapshot.project_id, snapshot.brain_id,
                                    snapshot.snapshot_id),
            _SNAPSHOT_FILE_PATTERN),
        snapshot)

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
        os.path.join(
            self._get_session_glob(project_id, brain_id, session_id),
            _SESSION_FILE_PATTERN),
        data_store_pb2.Session)

  def write_session(self, session):
    """Writes a session proto to storage.

    Args:
      session: The Session proto to write.
    """
    self._check_type(session, data_store_pb2.Session)
    self._write_proto(
        os.path.join(
            self._get_session_glob(session.project_id, session.brain_id,
                                   session.session_id), _SESSION_FILE_PATTERN),
        session)

  def read_episode_chunk(self, project_id, brain_id, session_id, episode_id,
                         chunk_id):
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
        os.path.join(
            self._get_chunk_glob(project_id, brain_id, session_id, episode_id,
                                 chunk_id),
            _CHUNK_FILE_PATTERN),
        data_store_pb2.EpisodeChunk)

  def write_episode_chunk(self, chunk):
    """Writes an episode chunk proto to storage.

    Args:
      chunk: The EpisodeChunk proto to write.
    """
    self._check_type(chunk, data_store_pb2.EpisodeChunk)
    self._write_proto(
        os.path.join(
            self._get_chunk_glob(chunk.project_id, chunk.brain_id,
                                 chunk.session_id, chunk.episode_id,
                                 chunk.chunk_id),
            _CHUNK_FILE_PATTERN),
        chunk)

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
        os.path.join(
            self._get_episode_glob(project_id, brain_id, session_id,
                                   episode_id),
            _ONLINE_EVALUATION_FILE_PATTERN),
        data_store_pb2.OnlineEvaluation)

  def write_online_evaluation(self, online_evaluation):
    """Writes an online evaluation proto to storage.

    Args:
      online_evaluation: The OnlineEvaluation proto to write.
    """
    self._check_type(online_evaluation, data_store_pb2.OnlineEvaluation)
    self._write_proto(
        os.path.join(
            self._get_episode_glob(
                online_evaluation.project_id, online_evaluation.brain_id,
                online_evaluation.session_id, online_evaluation.episode_id),
            _ONLINE_EVALUATION_FILE_PATTERN),
        online_evaluation)

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
        os.path.join(
            self._get_assignment_glob(
                project_id, brain_id, session_id, assignment_id),
            _ASSIGNMENT_FILE_PATTERN),
        data_store_pb2.Assignment)

  def write_assignment(self, assignment):
    """Writes an assignment proto to storage.

    Args:
      assignment: The Assignment proto to write.
    """
    self._check_type(assignment, data_store_pb2.Assignment)
    self._write_proto(
        os.path.join(
            self._get_assignment_glob(assignment.project_id,
                                      assignment.brain_id,
                                      assignment.session_id,
                                      assignment.assignment_id),
            _ASSIGNMENT_FILE_PATTERN), assignment)

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
        os.path.join(
            self._get_model_glob(project_id, brain_id, session_id, model_id),
            _MODEL_FILE_PATTERN), data_store_pb2.Model)

  def write_model(self, model):
    """Writes a model proto to storage.

    Args:
      model: The Model proto to write.
    """
    self._check_type(model, data_store_pb2.Model)
    self._write_proto(
        os.path.join(
            self._get_model_glob(model.project_id, model.brain_id,
                                 model.session_id, model.model_id),
            _MODEL_FILE_PATTERN), model)

  def read_serialized_model(self, project_id, brain_id, session_id, model_id):
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
        os.path.join(
            self._get_model_glob(project_id, brain_id, session_id, model_id),
            _SERIALIZED_MODEL_FILE_PATTERN),
        data_store_pb2.SerializedModel)

  def write_serialized_model(self, serialized_model):
    """Writes a serialized model proto to storage.

    Args:
      serialized_model: The SerializedModel proto to write.
    """
    self._check_type(serialized_model, data_store_pb2.SerializedModel)
    self._write_proto(
        os.path.join(
            self._get_model_glob(
                serialized_model.project_id, serialized_model.brain_id,
                serialized_model.session_id, serialized_model.model_id),
            _SERIALIZED_MODEL_FILE_PATTERN),
        serialized_model)

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
        os.path.join(
            self._get_offline_evaluation_glob(project_id, brain_id, session_id,
                                              model_id, str(evaluation_set_id)),
            _OFFLINE_EVALUATION_FILE_PATTERN), data_store_pb2.OfflineEvaluation)

  def write_offline_evaluation(self, offline_evaluation):
    """Writes an offline evaluation proto to storage.

    Args:
      offline_evaluation: The OfflineEvaluation proto to write.
    """
    self._check_type(offline_evaluation, data_store_pb2.OfflineEvaluation)
    self._write_proto(
        os.path.join(
            self._get_offline_evaluation_glob(
                offline_evaluation.project_id, offline_evaluation.brain_id,
                offline_evaluation.session_id, offline_evaluation.model_id,
                str(offline_evaluation.evaluation_set_id)),
            _OFFLINE_EVALUATION_FILE_PATTERN),
        offline_evaluation)

  def _check_type(self, data, expected_type):
    """Verifies data has type expected_type.

    Args:
      data: Data to check the type for.
      expected_type: Expected type for data.
    Raises:
      ValueError: if data doesn't have the expected type.
    """
    if not isinstance(data, expected_type):
      raise ValueError(
          f'Value has type {type(data)}, but it should have type '
          f'{expected_type}.')

  def _read_proto(self, pattern, data_type):
    """Finds matching file path, and reads its binary proto data.

    Args:
      pattern: The path pattern of the file where the proto is stored, including
        a single * to allow for unknown parts of the name to be filled in.
        No more than one file is allowed to match with the pattern path.
      data_type: The class of the proto to read.
    Returns:
      The proto that was read from storage.
    Raises:
      NotFoundError: If the requested file does not exist.
    """
    assert pattern.count('*') == 1
    paths = self._fs.glob(pattern)
    if not paths:
      raise NotFoundError(f'File with pattern "{pattern}" does not exist.')
    if len(paths) > 1:
      raise ValueError(
          f'More than one file was found matching pattern "{pattern}".')

    return data_type.FromString(self._fs.read_file(paths[0]))

  def _write_proto(self, pattern, data):
    """Writes proto data into the given file, with a timestamp in its name.

    Args:
      pattern: The path of the file where the proto is stored, with a * that
        will be replaced by the timestamp.
      data: A proto to store in that location. If data.created_micros is set,
        it will use its value as timestamp and update an existing file,
        otherwise it will use the current time.
    Raises:
      NotFoundError: If the requested file does not exist.
    """
    assert pattern.count('*') == 1

    if data.created_micros:
      # When create_micros is set, reflect it in the file path timestamp.
      path = pattern.replace('*', str(data.created_micros))
      if not self._fs.exists(path):
        raise NotFoundError(
            f'Could not update file {path} as it doesn\'t exist.')
    else:
      existing_files = self._fs.glob(pattern)
      if existing_files:
        raise ValueError(
            'There was an attempt to create a file from a new timestamp at '
            f'\'{pattern}\', but the following list of files with timestamps '
            f'was found: {existing_files}.')

      data.created_micros = int(time.time() * 1_000_000)
      path = pattern.replace('*', str(data.created_micros))

    self._fs.write_file(path, data.SerializeToString())

  def _decode_token(self, token):
    """Decodes a pagination token.

    Args:
      token: A string with the form "timestamp:resource_id", or None.
    Returns:
      A pair (timestamp, resource_id), where timestamp is an integer, and
      resource_id a string.
    """
    if token is None:
      return -1, ''

    pair = token.split(':')
    if len(pair) != 2:
      raise ValueError(f'Invalid token {token}.')
    return int(pair[0]), pair[1]

  def _encode_token(self, timestamp, resource_id):
    """Encodes a pagination token.

    Args:
      timestamp: An integer with a number of milliseconds since epoch.
      resource_id: A string containing a resource id.
    Returns:
      The encoded string with the form "timestamp:resource_id".
    """
    return f'{timestamp}:{resource_id}'

  def list_brains(self, project_id, page_size, list_options=None):
    """Lists brains for a given project.

    Args:
      project_id: The project id string to use for finding the brains.
      page_size: An int describing the max amount of brains to return, or
        None to return all of them.
      list_options: A ListOptions object specifying what to list, or None.
    Returns:
      A pair (brain_ids, next_token), where brain_ids is a list of
      brain id strings, and next_token is the token for the next page,
      or None if there is no next page.
    """
    return self._list_resources(
        self._get_resource_list_glob('brain', [project_id]),
        page_size, list_options)

  def list_sessions(self, project_id, brain_id, page_size, list_options=None):
    """Lists sessions for a given brain.

    Args:
      project_id: The project id string to use for finding the sessions.
      brain_id: The brain id string to use for finding the sessions.
      page_size: An int describing the max amount of sessions to return, or
        None to return all of them.
      list_options: A ListOptions object specifying what to list, or None.
    Returns:
      A pair (session_ids, next_token), where session_ids is a list of
      session id strings, and next_token is the token for the next page,
      or None if there is no next page.
    """
    return self._list_resources(
        self._get_resource_list_glob('session', [project_id, brain_id]),
        page_size, list_options)

  def list_episode_chunks(
      self, project_id, brain_id, session_id, episode_id, page_size,
      list_options=None):
    """Lists chunks for a given episode.

    Args:
      project_id: The project id string to use for finding the chunks.
      brain_id: The brain id string to use for finding the chunks.
      session_id: The session id string to use for finding the chunks.
      episode_id: The episode id string to use for finding the chunks.
      page_size: An int describing the max amount of brains to return, or
        None to return all of them.
      list_options: A ListOptions object specifying what to list, or None.
    Returns:
      A pair (chunk_ids, next_token), where chunk_ids is a list of
      episode chunk id ints, and next_token is the token for the next page,
      or None if there is no next page.
    """
    chunk_ids, next_token = self._list_resources(
        self._get_resource_list_glob(
            'episode_chunk', [project_id, brain_id, session_id, episode_id]),
        page_size, list_options)
    chunk_ids = [int(s) for s in chunk_ids]
    return chunk_ids, next_token

  def list_online_evaluations(
      self, project_id, brain_id, session_id, page_size, list_options=None):
    """Lists online evaluations for a given session.

    Args:
      project_id: The project id string to use for finding
        the online evaluations.
      brain_id: The brain id string to use for finding the online evaluations.
      session_id: The session id string to use for finding
        the online evaluations.
      page_size: An int describing the max amount of evaluations to return, or
        None to return all of them.
      list_options: A ListOptions object specifying what to list, or None.
    Returns:
      A pair (eval_ids, next_token), where eval_ids is a list of
      online evaluation id strings, and next_token is the token for the next
      page, or None if there is no next page.
    """
    return self._list_resources(
        self._get_resource_list_glob(
            'online_evaluation', [project_id, brain_id, session_id]),
        page_size, list_options)

  def get_most_recent_model(self, project_id, brain_id, session_id):
    """Gives the most recent model.

    Args:
      project_id: The project id string to use for finding the model.
      brain_id: The brain id string to use for finding the model.
      session_id: The session id string for finding the model.
    Returns:
      The string for the most recent model id, or None if no model is found.
    """
    resource_ids, _ = self._list_resources(self._get_resource_list_glob(
        'model', [project_id, brain_id, session_id]), page_size=None)
    return resource_ids[-1] if resource_ids else None

  def get_most_recent_snapshot(self, project_id, brain_id):
    """Gives the most recent snapshot.

    Args:
      project_id: The project id string to use for finding the snapshot.
      brain_id: The brain id string to use for finding the snapshot.
    Returns:
      The string for the most recent model id, or None if no snapshot is found.
    """
    resource_ids, _ = self._list_resources(self._get_resource_list_glob(
        'snapshot', [project_id, brain_id]), page_size=None)
    return resource_ids[-1] if resource_ids else None

  def _get_resource_list_glob(self, resource_type, resource_ids):
    """Gives the glob pattern to use for listing resources of a given type.

    Args:
      resource_type: Type of resource to build the path for.
      resource_ids: List of arguments to use to call self._get_*_path.
    Returns:
      A string with the path to use for listing.
    """
    path_callable_by_resource_type = {
        'brain': self._get_project_glob,
        'session': self._get_brain_glob,
        'episode_chunk': self._get_episode_glob,
        'online_evaluation': self._get_session_glob,
        'model': self._get_session_glob,
        'snapshot': self._get_brain_glob
    }
    return os.path.join(
        path_callable_by_resource_type[resource_type](*resource_ids),
        _DIRECTORY_BY_RESOURCE_TYPE[resource_type], '*',
        _FILE_PATTERN_BY_RESOURCE_TYPE[resource_type])

  def _list_resources(
      self, glob_path, page_size, list_options=None):
    """Lists resources for a given glob, from oldest to newest.

    Args:
      glob_path: Path to use for glob. Last two components of the path must be:
       * for glob (which matches the resource id), and a file name pattern.
      page_size: An int describing the max amount of resources to return, or
        None to return all of them.
      list_options: A ListOptions object specifying what to list, or None.
    Returns:
      A pair (resource_ids, next_token), where resource_ids is a list of
      resource id strings, and next_token is the token for the next page,
      or None if there is no next page.
    """
    page_token = list_options.page_token if list_options else None
    minimum_timestamp = list_options.minimum_timestamp if list_options else None

    if page_size == 0:
      return [], None

    # decoded_token is (starting timestamp, starting resource id)
    if minimum_timestamp is not None:
      decoded_token = (minimum_timestamp, '')
    else:
      decoded_token = self._decode_token(page_token)

    files = self._fs.glob(glob_path)
    id_to_token = {
        self._get_resource_id(f):
        (DataStore._get_timestamp(f), self._get_resource_id(f))
        for f in files
    }
    resource_ids = sorted(
        [r for r in id_to_token.keys() if id_to_token[r] >= decoded_token],
        key=lambda r: id_to_token[r])

    # If page_size is None, this gives the full list.
    next_page = resource_ids[:page_size]
    # If resource_ids has the same size as next_page, there are no more pages.
    next_token = (self._encode_token(*id_to_token[resource_ids[page_size]])
                  if len(resource_ids) > len(next_page) else None)

    return next_page, next_token

  def _get_resource_id(self, path):
    """Returns the resource id for a file.

    Args:
      path: Path of the file to get the resource id for. The last component
        of the path must be a filename, and the previous to last must be the
        resource id.
    Returns:
      The id for the resource in the given path.
    """
    return os.path.basename(os.path.dirname(path))

  @staticmethod
  def _get_timestamp(path):
    """Returns the timestamp for a file.

    Args:
      path: Path of the file to get the timestamp for. The file component of
        the path must have the timestamp after an underscore and before the
        extension (for example, in brain_1234.pb).
    Returns:
      An int with the amount of milliseconds since epoch.
    """
    match = re.match(DataStore._FILENAME_METADATA_RE, os.path.basename(path))
    if not match:
      raise ValueError(f'Path {path} does not contain a timestamp.')
    return int(match.group('timestamp'))

  @staticmethod
  def _as_glob_string(argument):
    """Interprets an argument to a path function as a glob string.

    Args:
      argument: An argument that is type string, None, int or list of string.
    Returns:
      A glob pattern representing the argument, including '*' and curly brace
      expressions.
    """
    if argument is None:
      return '*'
    if isinstance(argument, str):
      return argument
    if isinstance(argument, int):
      return str(argument)
    try:
      return '{' + ','.join(str(a) for a in argument) + '}'
    except TypeError:
      raise ValueError(
          f'Could not interpret argument "{argument}" as a path component. ' +
          'Arguments are expected to be None, type str/int or an iterable of '
          'strings/ints.')

  def _get_project_glob(self, project_id):
    """Gives the glob pattern for a project.

    Arguments may be None (indicating any), lists or int/string literals.

    Args:
      project_id: The project id string to use for building the path.
    Returns:
      A string describing the project directory path.
    """
    return os.path.join(_DIRECTORY_BY_RESOURCE_TYPE['project'],
                        self._as_glob_string(project_id))

  def _get_brain_glob(self, project_id, brain_id):
    """Gives the glob pattern for a brain.

    Arguments may be None (indicating any), lists or int/string literals.

    Args:
      project_id: The project id string to use for building the path.
      brain_id: The brain id string to use for building the path.
    Returns:
      A string describing the brain directory path.
    """
    return os.path.join(self._get_project_glob(project_id),
                        _DIRECTORY_BY_RESOURCE_TYPE['brain'],
                        self._as_glob_string(brain_id))

  def _get_snapshot_glob(self, project_id, brain_id, snapshot_id):
    """Gives the glob pattern for a snapshot.

    Arguments may be None (indicating any), lists or int/string literals.

    Args:
      project_id: The project id string to use for building the path.
      brain_id: The brain id string to use for building the path.
      snapshot_id: The snapshot id string for building the path.
    Returns:
      A string describing the snapshot directory path.
    """
    return os.path.join(
        self._get_brain_glob(project_id, brain_id),
        _DIRECTORY_BY_RESOURCE_TYPE['snapshot'],
        self._as_glob_string(snapshot_id))

  def _get_session_glob(self, project_id, brain_id, session_id):
    """Gives the glob pattern for a session.

    Arguments may be None (indicating any), lists or int/string literals.

    Args:
      project_id: The project id string to use for building the path.
      brain_id: The brain id string to use for building the path.
      session_id: The session id string for building the path.
    Returns:
      A string describing the session directory path.
    """
    return os.path.join(
        self._get_brain_glob(project_id, brain_id),
        _DIRECTORY_BY_RESOURCE_TYPE['session'],
        self._as_glob_string(session_id))

  def _get_episode_glob(self, project_id, brain_id, session_id, episode_id):
    """Gives the glob pattern for an episode.

    Arguments may be None (indicating any), lists or int/string literals.

    Args:
      project_id: The project id string to use for building the path.
      brain_id: The brain id string to use for building the path.
      session_id: The session id string for building the path.
      episode_id: The episode id string for building the path.
    Returns:
      A string describing the episode directory path.
    """
    return os.path.join(
        self._get_session_glob(project_id, brain_id, session_id),
        _DIRECTORY_BY_RESOURCE_TYPE['episode'],
        self._as_glob_string(episode_id))

  def _get_chunk_glob(
      self, project_id, brain_id, session_id, episode_id, chunk_id):
    """Gives the glob pattern for an episode chunk.

    Arguments may be None (indicating any), lists or int/string literals.

    Args:
      project_id: The project id string to use for building the path.
      brain_id: The brain id string to use for building the path.
      session_id: The session id string for building the path.
      episode_id: The episode id string for building the path.
      chunk_id: An int describing the episode chunk id for building the path.
    Returns:
      A string describing the episode chunk directory path.
    """
    return os.path.join(
        self._get_episode_glob(project_id, brain_id, session_id, episode_id),
        _DIRECTORY_BY_RESOURCE_TYPE['episode_chunk'],
        self._as_glob_string(chunk_id))

  def _get_assignment_glob(
      self, project_id, brain_id, session_id, assignment_id):
    """Gives the glob pattern for an assignment.

    Arguments may be None (indicating any), lists or int/string literals.

    Args:
      project_id: The project id string to use for building the path.
      brain_id: The brain id string to use for building the path.
      session_id: The session id string for building the path.
      assignment_id: The assignment id string for building the path.
    Returns:
      A string describing the assignment directory path.
    """
    def _encode(id_string):
      """Encode an assignment ID into a file path."""
      return hashlib.sha256(id_string.encode('utf-8')).hexdigest()

    if isinstance(assignment_id, str):
      assignment_id = _encode(assignment_id)
    elif assignment_id is not None:
      try:
        assignment_id = [_encode(id_string) for id_string in assignment_id]
      except TypeError:
        raise ValueError(
            f'assignment_id has unexpected type {type(assignment_id)}, '
            'must be str, iterable of strings or None')

    return os.path.join(
        self._get_session_glob(project_id, brain_id, session_id),
        _DIRECTORY_BY_RESOURCE_TYPE['assignment'],
        self._as_glob_string(assignment_id))

  def _get_model_glob(
      self, project_id, brain_id, session_id, model_id):
    """Gives the glob pattern for a model.

    Arguments may be None (indicating any), lists or int/string literals.

    Args:
      project_id: The project id string to use for building the path.
      brain_id: The brain id string to use for building the path.
      session_id: The session id string for building the path.
      model_id: The model id string for building the path.
    Returns:
      A string describing the model directory path.
    """
    return os.path.join(
        self._get_session_glob(project_id, brain_id, session_id),
        _DIRECTORY_BY_RESOURCE_TYPE['model'],
        self._as_glob_string(model_id))

  def _get_offline_evaluation_glob(
      self, project_id, brain_id, session_id, model_id, evaluation_set_id):
    """Gives the glob pattern for an offline evaluation.

    Arguments may be None (indicating any), lists or int/string literals.

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
    return os.path.join(
        self._get_model_glob(project_id, brain_id, session_id, model_id),
        _DIRECTORY_BY_RESOURCE_TYPE['offline_evaluation'],
        self._as_glob_string(evaluation_set_id))

  def add_assignment_callback(self, callback):
    """Adds a callback function for newly created assignments.

    Args:
      callback: A function that will be called with a single argument,
        an assignment id.
    """
    def file_callback(file_name):
      # TODO(b/185940506): check file matches assignment, read file,
      # and return the parsed id.
      callback(file_name)

    if callback in self._callbacks:
      raise ValueError('Added assignment callback twice.')

    self._callbacks[callback] = file_callback
    self._fs.add_file_callback(file_callback)

  def remove_assignment_callback(self, callback):
    """Removes a function from the assignment callbacks.

    Args:
      callback: The callback function to remove.
    """
    self._fs.remove_file_callback(self._callbacks.pop(callback))

  def remove_all_assignment_callbacks(self):
    """Removes all assignment callbacks."""
    while self._callbacks:
      self.remove_assignment_callback(next(iter(self._callbacks)))
