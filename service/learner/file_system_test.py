## Copyright 2021 Google LLC
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
"""Tests for google3.research.kernel.falken.service.learner.file_system."""

import glob
import os
import zipfile

from absl.testing import absltest
from absl.testing import parameterized
import common.generate_protos  # pylint: disable=unused-import
import data_store_pb2

from learner import file_system


class FileSystemTest(parameterized.TestCase):

  def setUp(self):
    super(FileSystemTest, self).setUp()

    temp_path = self.create_tempdir()
    self.checkpoints_path = os.path.join(temp_path, 'checkpoints')
    self.summaries_path = os.path.join(temp_path, 'summaries')
    self.tmp_models_path = os.path.join(temp_path, 'tmp_models')
    self.models_path = os.path.join(temp_path, 'models')

    self.file_system = file_system.FileSystem(self.tmp_models_path,
                                              self.models_path,
                                              self.checkpoints_path,
                                              self.summaries_path)
    self.assignment = data_store_pb2.Assignment(
        project_id='test_project_id',
        brain_id='test_brain_id',
        session_id='test_session_id',
        assignment_id='ass1gnm3nt_id')

  def test_create_checkpoints_path(self):
    self.assertEqual(
        self.file_system.create_checkpoints_path(self.assignment),
        os.path.join(self.checkpoints_path, 'test_project_id',
                     'test_brain_id', 'test_session_id', 'ass1gnm3nt_id'))

  def test_wipe_checkpoints(self):
    path = self.file_system.create_checkpoints_path(self.assignment)
    with open(os.path.join(path, 'test.txt'), 'w') as f:
      f.write('test')
    files = glob.glob(os.path.join(path, '*'))
    self.assertNotEmpty(files)
    self.file_system.wipe_checkpoints(self.assignment)
    files = glob.glob(os.path.join(path, '*'))
    self.assertEmpty(files)

  def test_create_summary_path(self):
    self.assertEqual(
        self.file_system.create_summary_path(self.assignment),
        os.path.join(self.summaries_path, 'test_project_id',
                     'test_brain_id', 'test_session_id', 'ass1gnm3nt_id'))

  def test_create_tmp_checkpoint_path(self):
    self.assertEqual(
        self.file_system.create_tmp_checkpoint_path(self.assignment,
                                                    'test_model_id'),
        os.path.join(self.tmp_models_path, 'test_project_id',
                     'test_brain_id', 'test_session_id', 'test_model_id',
                     'checkpoint'))

  def test_extract_tmp_model_path_from_checkpoint_path(self):
    self.assertEqual(
        self.file_system.extract_tmp_model_path_from_checkpoint_path(
            os.path.join(self.tmp_models_path, 'test_project_id',
                         'test_brain_id', 'test_session_id', 'test_model_id',
                         'checkpoint')),
        os.path.join(self.tmp_models_path, 'test_project_id',
                     'test_brain_id', 'test_session_id', 'test_model_id',
                     'saved_model'))

  def test_extract_tmp_model_path_from_checkpoint_path_invalid_path(self):
    with self.assertRaises(Exception):
      self.file_system.extract_tmp_model_path_from_checkpoint_path(
          os.path.join('blah', 'blah', 'checkpoint'))

  def test_extract_tmp_model_path_from_checkpoint_path_invalid_base_name(self):
    invalid_base_name = os.path.join(
        self.tmp_models_path, 'test_project_id',
        'test_brain_id', 'test_session_id', 'test_model_id', 'blah')
    with self.assertRaises(Exception):
      self.file_system.extract_tmp_model_path_from_checkpoint_path(
          invalid_base_name)

  def test_copy_to_model_directory(self):
    file_names = ['test_model.pb', os.path.join('variables', 'test.index')]
    model_path = os.path.dirname(
        self.file_system.create_tmp_checkpoint_path(self.assignment,
                                                    'test_model_id'))
    os.mkdir(os.path.join(model_path, 'variables'))

    for file_name in file_names:
      file_path = os.path.join(model_path, file_name)
      with open(file_path, 'w') as f:
        f.write('some data')

    self.file_system.copy_to_model_directory(model_path)

    permanent_model_path = os.path.join(
        self.models_path, 'test_project_id', 'test_brain_id',
        'test_session_id', 'test_model_id')
    for file_name in file_names:
      with open(os.path.join(permanent_model_path, file_name), 'r') as f:
        self.assertEqual('some data', f.read())

  def test_compress_model_directory(self):
    file_names = ['test_model.pb', os.path.join('variables', 'test.index')]
    model_path = os.path.dirname(
        self.file_system.create_tmp_checkpoint_path(self.assignment,
                                                    'test_model_id'))
    os.mkdir(os.path.join(model_path, 'variables'))

    for file_name in file_names:
      file = os.path.join(model_path, file_name)
      with open(file, 'w') as f:
        f.write('some data')

    permanent_model_path = self.file_system.compress_model_directory(model_path)

    self.assertEqual(
        permanent_model_path,
        os.path.join(self.models_path, 'test_project_id', 'test_brain_id',
                     'test_session_id', 'test_model_id.zip'))

    with open(permanent_model_path, 'rb') as f:
      with zipfile.ZipFile(f) as z:
        self.assertEqual(  # pylint: disable=g-generic-assert
            sorted(z.namelist()), [
                'checkpoint/', 'test_model.pb', 'variables/',
                'variables/test.index'
            ])

  def test_wipe_tmp_model_directory(self):
    path = os.path.dirname(
        self.file_system.create_checkpoints_path(self.assignment))
    with open(os.path.join(path, 'test.txt'), 'w') as f:
      f.write('test')
    files = glob.glob(os.path.join(path, '*'))
    self.assertNotEmpty(files)
    self.file_system.wipe_tmp_model_directory(path)
    files = glob.glob(os.path.join(path, '*'))
    self.assertEmpty(files)


if __name__ == '__main__':
  absltest.main()
