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
"""The Python implementation of the GRPC falken_service.FalkenService."""
from concurrent import futures
import os

from absl import app
from absl import flags
from absl import logging
from api import create_brain_handler
from api import create_session_handler
from api import get_handler
from api import get_session_count_handler
from api import list_handler
from api import request_metadata
from api import submit_episode_chunks_handler
from api import unique_id

import common.generate_protos  # pylint: disable=unused-import
from data_store import data_store
from data_store import file_system
import data_store_pb2
import falken_service_pb2_grpc
from google.rpc import code_pb2
import grpc

FLAGS = flags.FLAGS

flags.DEFINE_integer('port', None,
                     'Port for the Falken service to accept RPCs.')
flags.DEFINE_string('ssl_dir', '', 'Path containing the SSL cert and key.')
flags.DEFINE_integer(
    'max_workers', 10,
    'The max number of threads to use in the pool to start the grpc server.')
flags.DEFINE_string('root_dir', '',
                    'Directory where the Falken service will store data.')
flags.DEFINE_multi_string(
    'project_ids', [],
    'Project IDs to create API keys for and use with Falken.')

# Clients must specify the API key value using this metadata key.
_API_METADATA_KEY = 'x-goog-api-key'


class FalkenService(falken_service_pb2_grpc.FalkenService):
  """The Python implementation of the GRPC falken_service.FalkenService."""

  def __init__(self):
    """Initializes datastore and sets up API keys."""
    self.data_store = data_store.DataStore(
        file_system.FileSystem(FLAGS.root_dir))
    self._create_api_keys(FLAGS.project_ids)

  def _create_api_keys(self, project_ids):
    """Creates API keys in storage, and logs the generated keys for use.

    Args:
      project_ids: Project IDs to generate the API keys for. API keys will work
        only when used in combination with their respective project IDs.
    """
    for project_id in project_ids:
      api_key = unique_id.generate_base64_id()
      project = data_store_pb2.Project(
          project_id=project_id, name=project_id, api_key=api_key)
      self.data_store.write(project)
      logging.info('Generated key for %s: %s', project_id, api_key)

  def _validate_project_and_api_key(self, request, context):
    """Validate the project and API key.

    Aborts the RPC when the validation fails.

    Args:
      request: RPC request which must contain the project_id field.
      context: RPC context which must contain the api_key in its metadata.
    """
    if not request.project_id:
      context.abort(code_pb2.UNAUTHENTICATED,
                    'No project ID set in the request.')
    api_key = request_metadata.extract_metadata_value(
        context, _API_METADATA_KEY)
    if not api_key:
      context.abort(code_pb2.UNAUTHENTICATED,
                    'No API key found in the metadata.')
    project_id = request.project_id
    api_key_for_project = self.data_store.read_by_proto_ids(
        project_id=project_id).api_key
    if api_key_for_project != api_key:
      context.abort(
          code_pb2.UNAUTHENTICATED,
          f'Project ID {project_id} and API key {api_key} does not match.')

  def CreateBrain(self, request, context):
    """Creates a new brain from a BrainSpec."""
    self._validate_project_and_api_key(request, context)
    return create_brain_handler.create_brain(request, context, self.data_store)

  def GetBrain(self, request, context):
    """Retrieves an existing Brain."""
    self._validate_project_and_api_key(request, context)
    return create_session_handler.GetBrainHandler(
        request, context, self.data_store).get()

  def ListBrains(self, request, context):
    """Returns a list of Brains in the project."""
    self._validate_project_and_api_key(request, context)
    return list_handler.ListBrainsHandler(
        request, context, self.data_store).list()

  def CreateSession(self, request, context):
    """Creates a Session to begin training using the given Brain."""
    self._validate_project_and_api_key(request, context)
    return create_session_handler.create_session(
        request, context, self.data_store)

  def GetSessionCount(self, request, context):
    """Retrieves session count for a given brain."""
    self._validate_project_and_api_key(request, context)
    return get_session_count_handler.get_session_count(
        request, context, self.data_store)

  def GetSession(self, request, context):
    """Retrieves a Session by ID."""
    self._validate_project_and_api_key(request, context)
    return get_handler.GetSessionHandler(
        request, context, self.data_store).get()

  def GetSessionByIndex(self, request, context):
    """Retrieves a Session by index."""
    self._validate_project_and_api_key(request, context)
    return create_session_handler.GetSessionByIndexHandler(
        request, context, self.data_store).get()

  def ListSessions(self, request, context):
    """Returns a list of Sessions for a given Brain."""
    self._validate_project_and_api_key(request, context)
    return list_handler.ListSessionsHandler(
        request, context, self.data_store).list()

  def StopSession(self, request, context):
    """Stops an active Session."""
    self._validate_project_and_api_key(request, context)
    raise NotImplementedError('Method not implemented!')

  def ListEpisodeChunks(self, request, context):
    """Returns all Steps in all Episodes for the Session."""
    self._validate_project_and_api_key(request, context)
    return list_handler.ListEpisodeChunksHandler(
        request, context, self.data_store).list()

  def SubmitEpisodeChunks(self, request, context):
    """Submits EpisodeChunks."""
    self._validate_project_and_api_key(request, context)
    return submit_episode_chunks_handler.submit_episode_chunks(
        request, context, self.data_store)

  def GetModel(self, request, context):
    """Returns a serialized model."""
    self._validate_project_and_api_key(request, context)
    return get_handler.GetModelHandler(
        request, context, self.data_store).get()


def read_server_credentials():
  """Reads server credentials from local directory specified in ssl_dir.

  Returns:
    A ServerCredentials object.
  """
  with open(os.path.join(FLAGS.ssl_dir, 'key.pem'), 'rb') as f:
    private_key = f.read()
  with open(os.path.join(FLAGS.ssl_dir, 'cert.pem'), 'rb') as f:
    certificate_chain = f.read()
  return grpc.ssl_server_credentials(((private_key, certificate_chain),))


def log_service_handlers(server):
  """Log all service handlers for a server.

  Args:
    server: Server to query.
  """
  # pylint: disable=protected-access
  for service in server._state.generic_handlers:
    logging.debug('Service: %s', service.service_name())
    # pylint: disable=protected-access
    for method in service._method_handlers:
      logging.debug('- %s', method)


def _configure_server(server, port, credentials):
  """Configure the server to use the specified credentials and port.

  Args:
    server: grpc.server instance.
    port: Port number to serve on localhost.
    credentials: gRPC credentials instance.
  """
  server.add_secure_port(f'[::]:{port}', credentials)


def serve():
  """Start API server.

  Returns:
    Reference to the server object.
  """
  server = grpc.server(
      futures.ThreadPoolExecutor(max_workers=FLAGS.max_workers))
  falken_service_pb2_grpc.add_FalkenServiceServicer_to_server(
      FalkenService(), server)
  _configure_server(server, FLAGS.port, read_server_credentials())
  log_service_handlers(server)
  server.start()
  return server


def main(argv):
  if len(argv) > 1:
    logging.error('Non-flag parameters are not allowed: %s', argv)
  logging.debug('Starting the API service...')
  server = serve()
  server.wait_for_termination()


if __name__ == '__main__':
  flags.mark_flag_as_required('port')
  app.run(main)
