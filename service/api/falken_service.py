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

import common.generate_protos  # pylint: disable=unused-import
import falken_service_pb2_grpc
import grpc

FLAGS = flags.FLAGS

flags.DEFINE_integer('port', None,
                     'Port for the Falken service to accept RPCs.')
flags.DEFINE_string('ssl_dir', '', 'Path containing the SSL cert and key.')
flags.DEFINE_integer(
    'max_workers', 10,
    'The max number of threads to use in the pool to start the grpc server.')


class FalkenService(falken_service_pb2_grpc.FalkenService):
  """The Python implementation of the GRPC falken_service.FalkenService."""

  def CreateBrain(self, request, context):
    """Creates a new brain from a BrainSpec."""
    raise NotImplementedError('Method not implemented!')

  def GetBrain(self, request, context):
    """Retrieves an existing Brain."""
    raise NotImplementedError('Method not implemented!')

  def ListBrains(self, request, context):
    """Returns a list of Brains in the project."""
    raise NotImplementedError('Method not implemented!')

  def CreateSession(self, request, context):
    """Creates a Session to begin training using the given Brain."""
    raise NotImplementedError('Method not implemented!')

  def GetSessionCount(self, request, context):
    """Retrieves session count for a given brain."""
    raise NotImplementedError('Method not implemented!')

  def GetSession(self, request, context):
    """Retrieves a Session by ID."""
    raise NotImplementedError('Method not implemented!')

  def GetSessionByIndex(self, request, context):
    """Retrieves a Session by index."""
    raise NotImplementedError('Method not implemented!')

  def ListSessions(self, request, context):
    """Returns a list of Sessions for a given Brain."""
    raise NotImplementedError('Method not implemented!')

  def StopSession(self, request, context):
    """Stops an active Session."""
    raise NotImplementedError('Method not implemented!')

  def ListEpisodeChunks(self, request, context):
    """Returns all Steps in all Episodes for the Session."""
    raise NotImplementedError('Method not implemented!')

  def SubmitEpisodeChunks(self, request, context):
    """Submits EpisodeChunks."""
    raise NotImplementedError('Method not implemented!')

  def GetModel(self, request, context):
    """Returns a serialized model."""
    raise NotImplementedError('Method not implemented!')


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
