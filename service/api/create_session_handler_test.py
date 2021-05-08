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
"""Tests for create_session_handler."""
import copy
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from api import create_session_handler
from api import proto_conversion
from api import resource_id

import common.generate_protos  # pylint: disable=unused-import
import data_store_pb2
import falken_service_pb2
from google.protobuf import timestamp_pb2
from google.rpc import code_pb2
import session_pb2


class CreateSessionHandlerTest(parameterized.TestCase):

  def setUp(self):
    """Create a file system object that uses a temporary directory."""
    super().setUp()
    self._ds = mock.Mock()

  @parameterized.named_parameters(
      ('InteractiveTraining', session_pb2.INTERACTIVE_TRAINING, ''),
      ('EvaluationWithSnapshot', session_pb2.EVALUATION, 'test_snapshot_id'),
      ('EvaluationWithoutSnapshot', session_pb2.EVALUATION, ''),
      ('InferenceWithSnapshot', session_pb2.INFERENCE, 'test_snapshot_id'),
      ('InferenceWithoutSnapshot', session_pb2.INFERENCE, ''))
  @mock.patch.object(proto_conversion.ProtoConverter,
                     'convert_proto')
  @mock.patch.object(resource_id, 'generate_resource_id')
  @mock.patch.object(create_session_handler, '_validate_session')
  def test_create_session(
      self, session_type, snapshot_id, validate_session, generate_resource_id,
      convert_proto):
    generate_resource_id.return_value = 'test_session_id'
    request = falken_service_pb2.CreateSessionRequest(
        project_id='test_project',
        spec=session_pb2.SessionSpec(
            project_id='test_project',
            brain_id='test_brain_id',
            session_type=session_type,
            snapshot_id=snapshot_id))

    context = mock.Mock()
    context.invocation_metadata.return_value = [
        ('user-agent', 'grpc-c/16.0.0 (linux; chttp2)')
    ]

    write_session = data_store_pb2.Session(
        project_id=request.project_id,
        brain_id=request.spec.brain_id,
        session_id=generate_resource_id.return_value,
        starting_snapshot_ids=['test_snapshot_id'],
        session_type=request.spec.session_type,
        user_agent='grpc-c/16.0.0 (linux; chttp2)'
    )

    data_store_session = copy.copy(write_session)
    data_store_session.created_micros = 1619726720852543
    previous_session = copy.copy(data_store_session)
    previous_session.session_id = 'test_prev_session_id'
    previous_session.session_type = session_pb2.INTERACTIVE_TRAINING

    expected_session = session_pb2.Session(
        project_id=request.spec.project_id,
        brain_id=request.spec.brain_id,
        name=write_session.session_id,
        session_type=request.spec.session_type,
        starting_snapshot_ids=[],
        create_time=timestamp_pb2.Timestamp(seconds=1619726720))
    self._ds.read_session.side_effect = [previous_session, data_store_session]
    self._ds.read_snapshot.return_value = data_store_pb2.Snapshot(
        project_id=request.spec.snapshot_id,
        brain_id=request.spec.brain_id,
        snapshot_id='test_snapshot_id',
        session_id=previous_session.session_id)
    convert_proto.return_value = expected_session
    self._ds.get_most_recent_snapshot.return_value = data_store_pb2.Snapshot(
        project_id=request.spec.snapshot_id,
        brain_id=request.spec.brain_id,
        snapshot_id='test_snapshot_id',
        session_id=previous_session.session_id)

    self.assertEqual(
        create_session_handler.create_session(request, context, self._ds),
        expected_session)

    validate_session.assert_called_once_with(
        request.spec, context, 'test_snapshot_id', previous_session)
    generate_resource_id.assert_called_once_with()
    context.invocation_metadata.assert_called_once_with()
    if snapshot_id:
      self._ds.read_snapshot.assert_called_once_with(
          'test_project', 'test_brain_id', 'test_snapshot_id')
    else:
      self._ds.get_most_recent_snapshot.assert_called_once_with(
          request.spec.project_id, request.spec.brain_id)

    self._ds.write_session.assert_called_once_with(write_session)
    self._ds.read_session.assert_has_calls([
        mock.call(
            request.spec.project_id, request.spec.brain_id,
            previous_session.session_id),
        mock.call(
            request.spec.project_id, request.spec.brain_id,
            data_store_session.session_id)])
    convert_proto.called_once_with(data_store_session)

  def test_get_snapshot_id_and_previous_session_id(self):
    mock_data_store = mock.Mock()
    mock_data_store.read_snapshot.return_value = data_store_pb2.Snapshot(
        project_id='test_project_id', brain_id='test_brain_id',
        snapshot_id='test_snapshot_id', session_id='test_prev_session_id')
    mock_session_spec = mock.Mock(
        project_id='test_project_id', brain_id='test_brain_id',
        snapshot_id='test_snapshot_id')
    expected_snapshot_id = 'test_snapshot_id'
    expected_prev_session_id = 'test_prev_session_id'
    self.assertEqual(
        create_session_handler._get_snapshot_id_and_previous_session_id(
            mock_session_spec,
            mock_data_store),
        (expected_snapshot_id, expected_prev_session_id)
    )
    mock_data_store.read_snapshot.assert_called_once_with(
        'test_project_id', 'test_brain_id', 'test_snapshot_id')

  def test_get_snapshot_id_and_previous_session_id_not_specified(self):
    mock_data_store = mock.Mock()
    mock_data_store.get_most_recent_snapshot.return_value = (
        data_store_pb2.Snapshot(
            project_id='test_project_id',
            brain_id='test_brain_id',
            snapshot_id='test_snapshot_id',
            session_id='test_prev_session_id'))
    mock_session_spec = mock.Mock(
        project_id='test_project_id', brain_id='test_brain_id',
        snapshot_id='')

    expected_snapshot_id = 'test_snapshot_id'
    expected_prev_session_id = 'test_prev_session_id'
    self.assertEqual(
        create_session_handler._get_snapshot_id_and_previous_session_id(
            mock_session_spec,
            mock_data_store),
        (expected_snapshot_id, expected_prev_session_id)
    )
    mock_data_store.get_most_recent_snapshot.assert_called_once_with(
        'test_project_id', 'test_brain_id')

  def test_get_snapshot_id_and_previous_session_id_no_snapshot_found(self):
    mock_data_store = mock.Mock()
    mock_data_store.get_most_recent_snapshot.return_value = None
    mock_session_spec = mock.Mock(
        project_id='test_project_id', brain_id='test_brain_id',
        snapshot_id='')
    self.assertEqual(
        create_session_handler._get_snapshot_id_and_previous_session_id(
            mock_session_spec,
            mock_data_store),
        ('', '')
    )
    mock_data_store.get_most_recent_snapshot.assert_called_once_with(
        'test_project_id', 'test_brain_id')

  def test_validate_session_no_session_type(self):
    mock_session = mock.Mock(session_type=None)
    mock_context = mock.Mock()
    mock_context.abort.side_effect = Exception()
    with self.assertRaises(Exception):
      create_session_handler._validate_session(mock_session, mock_context)
    mock_context.abort.assert_called_once_with(
        code_pb2.INVALID_ARGUMENT,
        'Session type not set in the request. Please specify session type.')

  @parameterized.parameters(session_pb2.INFERENCE, session_pb2.EVALUATION)
  def test_validate_session_no_starting_snapshot(self, session_type):
    mock_session_spec = mock.Mock(session_type=session_type,
                                  brain_id='test_brain_id')
    mock_context = mock.Mock()
    mock_context.abort.side_effect = Exception()
    with self.assertRaises(Exception):
      create_session_handler._validate_session(mock_session_spec, mock_context)
    mock_context.abort.assert_called_once_with(
        code_pb2.INVALID_ARGUMENT,
        f'Session type {session_type} requires a starting snapshot for brain '
        'test_brain_id.')

  def test_validate_session_eval_on_top_of_training(self):
    mock_session_spec = mock.Mock(session_type=session_pb2.EVALUATION,
                                  brain_id='test_brain_id')
    mock_context = mock.Mock()
    mock_context.abort.side_effect = Exception()
    mock_previous_session = mock.Mock(session_type=session_pb2.EVALUATION)
    with self.assertRaises(Exception):
      create_session_handler._validate_session(
          mock_session_spec, mock_context, 'test_snapshot_id',
          mock_previous_session)
    mock_context.abort.assert_called_once_with(
        code_pb2.INVALID_ARGUMENT,
        'Evaluation sessions must have a starting snapshot produced from an '
        'interactive training session for brain test_brain_id.')

if __name__ == '__main__':
  absltest.main()
