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

"""Tests for DataStore."""

import glob
import os.path
import tempfile
import threading

from absl.testing import absltest
from absl.testing import parameterized
from data_store import data_store
from data_store import file_system

import common.generate_protos  # pylint: disable=g-bad-import-order,unused-import

import data_store_pb2


class FileSystemTest(parameterized.TestCase):

  def setUp(self):
    """Create a file system object that uses a temporary directory."""
    super().setUp()
    self._temporary_directory = tempfile.TemporaryDirectory()
    self._fs = file_system.FileSystem(self._temporary_directory.name)
    self._text = 'Hello Falken'.encode('utf-8')

  def tearDown(self):
    """Clean up the temporary directory and file system."""
    super().tearDown()
    self._temporary_directory.cleanup()
    self._fs = None
    self._text = None

  def test_read_write_file(self):
    """Tests files read and writing files, and verify writing location."""
    path = 'some-project.pb'
    self._fs.write_file(path, self._text)

    files = glob.glob(os.path.join(self._temporary_directory.name, path))
    self.assertLen(files, 1)

    self.assertEqual(self._text, self._fs.read_file(path))

  def test_glob(self):
    """Tests FileSystem.glob."""
    files = ['dirA1/dirB1/p1.pb', 'dirA1/dirB2/p1.pb', 'dirA2/dirC1/p1.pb']
    for f in files:
      self._fs.write_file(f, self._text)

    found_files = self._fs.glob('dir*/dir*/p1.pb')
    self.assertEqual(set(files), set(found_files))

  def test_exists(self):
    """Tests FileSystem.exists."""
    path = 'dirA/dirB/file.pb'
    self._fs.write_file(path, self._text)
    self.assertTrue(self._fs.exists(path))

  def test_list_by_globbing(self):
    ds = data_store.DataStore(self._fs)
    s0 = data_store_pb2.Session(
        project_id='p0',
        brain_id='b0',
        session_id='s0')
    s1 = data_store_pb2.Session(
        project_id='p0',
        brain_id='b0',
        session_id='s1')
    s2 = data_store_pb2.Session(
        project_id='p1',
        brain_id='b1',
        session_id='s2')
    s3 = data_store_pb2.Session(
        project_id='p2',
        brain_id='b2',
        session_id='s3')
    ds.write_session(s0)
    ds.write_session(s1)
    ds.write_session(s2)
    ds.write_session(s3)
    ids, _ = ds.list_sessions(['p0', 'p2'], None, 10)
    self.assertEqual(ids, ['s0', 's1', 's3'])

  def test_callback(self):
    """Tests callback system."""
    callback_called = threading.Event()
    found_files = []

    def callback(file):
      nonlocal found_files
      found_files.append(file)
      callback_called.set()

    self._fs.add_file_callback(callback)
    self._fs.write_file('dir1/trigger.txt', self._text)
    self.assertTrue(callback_called.wait(timeout=3))

    self.assertEqual(['dir1/trigger.txt'], found_files)
    self._fs.remove_all_file_callbacks()

  def test_lock(self):
    """Tests locking system."""
    path = 'dir1/to_lock.txt'
    with self._fs.lock_file(path):
      self.assertTrue(self._fs.exists(self._fs._get_lock_path(path)))
      with self.assertRaises(file_system.UnableToLockFileError):
        with self._fs.lock_file(path):
          pass

    self.assertFalse(self._fs.exists(self._fs._get_lock_path(path)))


if __name__ == '__main__':
  absltest.main()
