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
"""Tests for stop_session_handler."""

from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from api import stop_session_handler
from api import unique_id

import common.generate_protos  # pylint: disable=unused-import
from data_store import resource_id
import data_store_pb2
import falken_service_pb2
from google.rpc import code_pb2
import session_pb2


class StopSessionHandlerTest(parameterized.TestCase):

  def test_stop_session_not_found(self):
    mock_ds = mock.Mock()
    mock_ds.read.side_effect = FileNotFoundError('Session not found.')
    mock_context = mock.Mock()
    mock_context.abort.side_effect = Exception()
    request = falken_service_pb2.StopSessionRequest(
        project_id='p0',
        session=session_pb2.Session(project_id='p0', brain_id='b0', name='s0'))

    with self.assertRaises(Exception):
      stop_session_handler.stop_session(request, mock_context, mock_ds)

    mock_context.abort.assert_called_once_with(
        code_pb2.NOT_FOUND,
        'Failed to find session s0 in data_store. Session not found.')
    mock_ds.read.called_once_with(
        resource_id.FalkenResourceId(
            project=request.session.project_id, brain=request.session.brain_id,
            session=request.session.name))

  @mock.patch.object(
      stop_session_handler, '_get_final_model_from_model_selector')
  @mock.patch.object(stop_session_handler, '_get_snapshot_id')
  def test_stop_session(self, get_snapshot_id, get_final_model):
    get_snapshot_id.return_value = 'test_snapshot_id'
    request = falken_service_pb2.StopSessionRequest(
        project_id='p0',
        session=session_pb2.Session(project_id='p0', brain_id='b0', name='s0'))
    read_session = data_store_pb2.Session(project_id='p0', brain_id='b0',
                                          session_id='s0')
    mock_ds = mock.Mock()
    mock_ds.read.return_value = read_session
    mock_context = mock.Mock()

    self.assertEqual(
        stop_session_handler.stop_session(request, mock_context, mock_ds),
        falken_service_pb2.StopSessionResponse(
            snapshot_id=get_snapshot_id.return_value))

    expected_session_resource_id = resource_id.FalkenResourceId(
        project=request.session.project_id, brain=request.session.brain_id,
        session=request.session.name)
    read_session_with_snapshot_updated = data_store_pb2.Session(
        project_id='p0', brain_id='b0', session_id='s0',
        snapshot=get_snapshot_id.return_value)
    mock_ds.write_stopped_session.assert_called_once_with(
        read_session_with_snapshot_updated)
    mock_ds.read.assert_called_once_with(expected_session_resource_id)
    get_snapshot_id.assert_called_once_with(
        expected_session_resource_id, mock_ds.read.return_value,
        get_final_model.return_value, mock_ds, mock_context)
    get_final_model.assert_called_once()

  @mock.patch.object(stop_session_handler, '_single_starting_snapshot')
  def test_get_snapshot_id_inference(self, single_starting_snapshot):
    single_starting_snapshot.return_value = 'test_snapshot_id'
    session_resource_id = resource_id.FalkenResourceId(
        'projects/p0/brains/b0/sessions/s0')
    session = data_store_pb2.Session(session_type=session_pb2.INFERENCE)

    self.assertEqual(
        stop_session_handler._get_snapshot_id(
            session_resource_id, session, None, mock.Mock(), mock.Mock()),
        'test_snapshot_id')

    single_starting_snapshot.assert_called_once_with(session_resource_id, [])

  @mock.patch.object(stop_session_handler, '_single_starting_snapshot')
  def test_get_snapshot_id_inference_failure(self, single_starting_snapshot):
    single_starting_snapshot.side_effect = ValueError(
        'Unexpected number of starting_snapshot_ids, wanted exactly 1, '
        'got 5 for session s0.')
    session_resource_id = resource_id.FalkenResourceId(
        'projects/p0/brains/b0/sessions/s0')
    session = data_store_pb2.Session(
        session_type=session_pb2.INFERENCE, starting_snapshots=[])
    mock_context = mock.Mock()
    mock_context.abort.side_effect = Exception()

    with self.assertRaises(Exception):
      stop_session_handler._get_snapshot_id(
          session_resource_id, session, None, mock.Mock(), mock_context)

    mock_context.abort.assert_called_once_with(
        code_pb2.INVALID_ARGUMENT, single_starting_snapshot.side_effect)
    single_starting_snapshot.assert_called_once_with(session_resource_id, [])

  @parameterized.named_parameters(
      ('interactive_training', session_pb2.INTERACTIVE_TRAINING, False),
      ('evaluation', session_pb2.EVALUATION, True))
  @mock.patch.object(stop_session_handler, '_create_or_use_existing_snapshot')
  def test_get_snapshot_id(
      self, session_type, expect_starting_snapshot,
      create_or_use_existing_snapshot):
    create_or_use_existing_snapshot.return_value = 'test_snapshot_id'
    session_resource_id = resource_id.FalkenResourceId(
        'projects/p0/brains/b0/sessions/s0')
    session = data_store_pb2.Session(session_type=session_type)
    mock_model_resource_id = mock.Mock()

    self.assertEqual(
        stop_session_handler._get_snapshot_id(
            session_resource_id, session, mock_model_resource_id, mock.Mock(),
            mock.Mock()),
        'test_snapshot_id')

    create_or_use_existing_snapshot.assert_called_once_with(
        session_resource_id, session.starting_snapshots,
        mock_model_resource_id, mock.ANY,
        expect_starting_snapshot=expect_starting_snapshot)

  @parameterized.named_parameters(
      ('interactive_training', session_pb2.INTERACTIVE_TRAINING, False,
       'training'),
      ('evaluation', session_pb2.EVALUATION, True, 'evaluation'))
  @mock.patch.object(stop_session_handler, '_create_or_use_existing_snapshot')
  def test_get_snapshot_id_failure(
      self, session_type, expect_starting_snapshot, log_session_type_name,
      create_or_use_existing_snapshot):
    create_or_use_existing_snapshot.side_effect = FileNotFoundError(
        'Not found.')
    session_resource_id = resource_id.FalkenResourceId(
        'projects/p0/brains/b0/sessions/s0')
    session = data_store_pb2.Session(session_type=session_type)
    mock_model_resource_id = mock.Mock()
    mock_context = mock.Mock()
    mock_context.abort.side_effect = Exception()

    with self.assertRaises(Exception):
      stop_session_handler._get_snapshot_id(
          session_resource_id, session, mock_model_resource_id, mock.Mock(),
          mock_context)

    create_or_use_existing_snapshot.assert_called_once_with(
        session_resource_id, session.starting_snapshots,
        mock_model_resource_id, mock.ANY,
        expect_starting_snapshot=expect_starting_snapshot)
    mock_context.abort.assert_called_once_with(
        code_pb2.NOT_FOUND,
        f'Failed to create snapshot for {log_session_type_name} session s0. '
        f'{create_or_use_existing_snapshot.side_effect}')

  def test_get_snapshot_id_invalid_session_type(self):
    session_resource_id = resource_id.FalkenResourceId(
        'projects/p0/brains/b0/sessions/s0')
    session = data_store_pb2.Session(session_id='s0', session_type=20)
    mock_model_resource_id = mock.Mock()
    mock_context = mock.Mock()
    mock_context.abort.side_effect = Exception()

    with self.assertRaises(Exception):
      stop_session_handler._get_snapshot_id(
          session_resource_id, session, mock_model_resource_id, mock.Mock(),
          mock_context)

    mock_context.abort.assert_called_once_with(
        code_pb2.INVALID_ARGUMENT, 'Unsupported session_type: 20 found in s0.')

  def test_single_starting_snapshot(self):
    self.assertEqual(
        stop_session_handler._single_starting_snapshot(mock.Mock(), ['ss0']),
        'ss0')

  def test_single_starting_snapshot_wrong_len(self):
    with self.assertRaisesWithLiteralMatch(
        ValueError, 'Unexpected number of starting_snapshots, wanted exactly 1,'
        ' got 2 for session s0.'):
      stop_session_handler._single_starting_snapshot(
          resource_id.FalkenResourceId('projects/p0/brains/b0/sessions/s0'),
          ['ss0', 'ss1'])

  @parameterized.named_parameters(
      ('model_id_exists',
       resource_id.FalkenResourceId(
           'projects/p0/brains/b0/sessions/s0/models/m0'),
       True, True, ['ss0']),
      ('model_id_does_not_exist', None, False, True, ['ss0']),
      ('do_not_expect_starting_snapshot_but_have_snapshot', None, False, False,
       ['ss0']),
      ('wrong_starting_snapshot_length', None, False, False, []))
  @mock.patch.object(stop_session_handler, '_create_snapshot')
  @mock.patch.object(stop_session_handler, '_single_starting_snapshot')
  def test_create_or_use_existing_snapshot(
      self, model_resource_id, model_exists, expect_starting_snapshot,
      starting_snapshot_ids, single_starting_snapshot, create_snapshot):
    result_snapshot_id = 'ss1'
    create_snapshot.return_value = result_snapshot_id
    single_starting_snapshot.return_value = result_snapshot_id
    if len(starting_snapshot_ids) != 1:
      result_snapshot_id = ''
    mock_ds = mock.Mock()
    mock_ds.read.return_value = data_store_pb2.Model(model_path='model_path')
    session_resource_id = mock.Mock()

    self.assertEqual(
        stop_session_handler._create_or_use_existing_snapshot(
            session_resource_id, starting_snapshot_ids, model_resource_id,
            mock_ds, expect_starting_snapshot),
        result_snapshot_id)

    if model_exists:
      mock_ds.read.assert_called_once_with(model_resource_id)
      create_snapshot.assert_called_once_with(
          session_resource_id, starting_snapshot_ids, model_resource_id,
          mock_ds.read.return_value.model_path, mock_ds)
    elif starting_snapshot_ids:
      single_starting_snapshot.assert_called_once_with(
          session_resource_id, starting_snapshot_ids)

  @mock.patch.object(unique_id, 'generate_unique_id')
  def test_create_snapshot(self, uid):
    uid.return_value = 'ss2'
    session_resource_id = resource_id.FalkenResourceId(
        'projects/p0/brains/b0/sessions/s0')
    model_resource_id = resource_id.FalkenResourceId(
        'projects/p0/brains/b0/sessions/s0/models/m0')
    mock_ds = mock.Mock()
    mock_ds.read.return_value = data_store_pb2.Snapshot(
        project_id='p0',
        brain_id='b0',
        snapshot_id='ss1',
        ancestor_snapshots=[
            data_store_pb2.SnapshotParents(
                snapshot='ss0', parent_snapshots=['ss-1', 'ss-2'])
        ])

    self.assertEqual(
        stop_session_handler._create_snapshot(
            session_resource_id, ['ss1'], model_resource_id, 'test_model_path',
            mock_ds),
        'ss2')

    mock_ds.write.called_once_with(
        data_store_pb2.Snapshot(
            project_id='p0', brain_id='b0', snapshot_id='ss2', model='m0',
            model_path='test_model_path',
            ancestor_snapshots=[
                data_store_pb2.SnapshotParents(
                    snapshot='ss1', parent_snapshots=['ss0']),
                data_store_pb2.SnapshotParents(
                    snapshot='ss0', parent_snapshots=['ss-1', 'ss-2'])
            ]))


if __name__ == '__main__':
  absltest.main()
