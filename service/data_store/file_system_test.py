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

"""Tests for FileSystem."""

import glob
import os.path
import tempfile
import time
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from data_store import file_system


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
    # Glob should return POSIX paths.
    files = ['dirA1/dirB1/p1.pb',
             'dirA1/dirB2/p1.pb',
             'dirA2/dirC1/p1.pb']
    for f in files:
      self._fs.write_file(f, self._text)

    found_files = self._fs.glob(os.path.join('dir*', 'dir*', 'p1.pb'))
    self.assertEqual(set(files), set(found_files))

  def test_exists(self):
    """Tests FileSystem.exists."""
    path = os.path.join('dirA', 'dirB', 'file.pb')
    self._fs.write_file(path, self._text)
    self.assertTrue(self._fs.exists(path))

  def test_remove_file(self):
    """Tests FileSystem.remove_file."""
    path = os.path.join('dirA', 'dirB', 'file.pb')
    self._fs.write_file(path, self._text)
    self.assertTrue(self._fs.exists(path))
    self._fs.remove_file(path)
    self.assertFalse(self._fs.exists(path))

  def test_get_modification_time(self):
    """Tests FileSystem.get_modification_file."""
    paths = [os.path.join('dirA', 'file1.pb'),
             os.path.join('dirA', 'file2.pb')]
    for path in paths:
      self._fs.write_file(path, self._text)
      # Ensure next file is in a different millisecond.
      time.sleep(0.1)
    times = [self._fs.get_modification_time(path) for path in paths]
    self.assertLess(*times)

  def test_lock(self):
    """Tests locking system."""
    path = os.path.join('dir1', 'to_lock.txt')
    with self._fs.lock_file_context(path):
      self.assertTrue(self._fs.exists(self._fs._get_lock_path(path)))
      with self.assertRaises(file_system.UnableToLockFileError):
        with self._fs.lock_file_context(path):
          pass

    self.assertFalse(self._fs.exists(self._fs._get_lock_path(path)))

  def test_lock_with_timeout(self):
    """Try locking a path that is already locked using a timeout."""
    path = os.path.join('dir1', 'to_lock.txt')
    with self._fs.lock_file_context(path):
      current_time = time.time()
      with self.assertRaises(file_system.UnableToLockFileError):
        with self._fs.lock_file_context(path, timeout=1):
          pass
      elapsed_time = time.time() - current_time
      self.assertGreater(elapsed_time, 0.5)

  @mock.patch.object(time, 'time')
  def test_get_staleness(self, time_mock):
    path = os.path.join('dirA', 'dirB', 'file.pb')
    self._fs.write_file(path, self._text)

    # Check that youngest mtime is being found recursively.
    time_mock.return_value = 103
    with mock.patch.object(os.path, 'getmtime') as getmtime_mock:
      def _getmtime_side_effect(path):
        if path.endswith('file.pb'):
          return 102
        else:
          return 101
      getmtime_mock.side_effect = _getmtime_side_effect
      self.assertEqual(
          self._fs.get_staleness('dirA'),
          1000)

  def test_remove_tree(self):
    path = os.path.join('dirA', 'dirB', 'file.pb')
    self._fs.write_file(path, self._text)
    self.assertTrue(self._fs.exists(path))
    self._fs.remove_tree('dirA')
    self.assertFalse(self._fs.exists(path))


if __name__ == '__main__':
  absltest.main()
