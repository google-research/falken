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

import contextlib
import datetime
import glob
import os
import os.path
import re
import shutil
import time

import braceexpand
import flufl.lock


class UnableToLockFileError(RuntimeError):
  """Signals that we were unable to lock a file."""
  pass


def _posix_path(path):
  """Replace system with POSIX directory separators.

  Args:
    path: Path to normalize.

  Returns:
    Path with POSIX directory separators.
  """
  return path.replace(os.path.sep, '/')


class FileSystem(object):
  """Encapsulates file system operations so they can be faked in tests."""

  def __init__(self, root_path):
    """Initializes the file system object with a given root path.

    Args:
      root_path: Path where all Falken files will be stored.
    """
    self._root_path = os.path.realpath(root_path)

  def _resolve(self, path):
    absolute_path = os.path.realpath(os.path.join(self._root_path, path))
    assert absolute_path.startswith(self._root_path)
    return absolute_path

  def read_file(self, path):
    """Reads a file.

    Args:
      path: The path of the file to read.
    Returns:
      A bytes-like object containing the contents of the file.
    """
    with open(self._resolve(path), 'rb') as f:
      return f.read()

  def write_file(self, path, data):
    """Writes into a file.

    Args:
      path: The path of the file to write the data to.
      data: A bytes-like object containing the data to write.
    """
    destination_path = self._resolve(path)
    directory = os.path.dirname(destination_path)

    os.makedirs(directory, exist_ok=True)
    source_path = os.path.join(
        directory, '~' + os.path.basename(destination_path))
    with open(source_path, 'wb') as f:
      f.write(data)

    shutil.move(source_path, destination_path)

  def remove_file(self, path):
    """Removes a file.

    Args:
      path: The path of the file to remove.
    """
    os.remove(self._resolve(path))

  def remove_tree(self, path, ignore_errors=False):
    """Removes a directory tree."""
    shutil.rmtree(self._resolve(path), ignore_errors=ignore_errors)

  def get_modification_time(self, path):
    """Gives the modification time of a file.

    Args:
      path: The path of the file.
    Returns:
      An int with the number of milliseconds since epoch.
    """
    return int(1000 * os.path.getmtime(self._resolve(path)))

  def glob(self, pattern):
    """Encapsulates glob.glob.

    Args:
      pattern: Pattern to search for. May contains brace-style options,
        e.g., "a/{b,c}/*".

    Returns:
      List of path strings found. All paths use POSIX directory separators.
    """
    result = []
    for p in braceexpand.braceexpand(pattern):
      for f in glob.glob(self._resolve(p)):
        result.append(_posix_path(os.path.relpath(f, self._root_path)))
    return result

  def exists(self, path):
    """Encapsulates os.path.exists.

    Args:
      path: Path of file or directory to verify the existence of.
    Returns:
      A boolean for whether the file or directory exists.
    """
    return os.path.exists(self._resolve(path))

  def lock_file(self, path, expire_after=60*60):
    """Locks a file.

     Lock is shared with other files in the same directory (excluding
     files contained in subdirectories).

    Args:
      path: Path of file or directory to lock.
      expire_after: How many seconds to wait for the lock to expire.
        Default is one hour.
    Returns:
      A flufl.Lock object that can be unlocked with unlock_file.
    """
    lock_failure_text = f'Could not lock file {path}.'
    path = self._resolve(self._get_lock_path(path))

    os.makedirs(os.path.dirname(path), exist_ok=True)

    lock = flufl.lock.Lock(path)
    lock.lifetime = datetime.timedelta(seconds=expire_after)
    try:
      # Return immediately if we can't get the lock.
      lock.lock(timeout=0)
      if not lock.is_locked:
        raise UnableToLockFileError(lock_failure_text)
    except (flufl.lock.TimeOutError, flufl.lock.AlreadyLockedError):
      raise UnableToLockFileError(lock_failure_text)

    return lock

  def refresh_lock(self, lock, expire_after=60*60):
    """Refreshes a file lock.

    Args:
      lock: A lock object returned by lock_file.
      expire_after: How many seconds to wait for the lock to expire again.
        Default is one hour.
    """
    lock.refresh(expire_after)

  def unlock_file(self, lock):
    """Unlocks a file.

    Args:
      lock: A lock object returned by lock_file.
    """
    if lock.is_locked:
      lock.unlock()

  @contextlib.contextmanager
  def lock_file_context(self, path, expire_after=60*60):
    """Gives a context manager that locks the given file.

     Lock is shared with other files in the same directory (excluding
     files contained in subdirectories).

    Args:
      path: Path of file or directory to lock.
      expire_after: How many seconds to wait for the lock to expire.
        Default is one hour.
    Yields:
      Uses an empty yield only for the purposes of implementing the context
      manager.
    """
    lock = None
    try:
      lock = self.lock_file(path, expire_after)
      yield
    finally:
      if lock:
        self.unlock_file(lock)

  def _get_lock_path(self, path):
    """Gives the path of the lock file corresponding to path.

    Args:
      path: Path of file or directory to find the lock file for.
    Returns:
      The path to the lock file.
    """
    return _posix_path(os.path.join(os.path.dirname(path), '.lock'))

  def get_staleness(self, path):
    """Computes millisecond staleness of file or directory.

    The staleness of a file is the duration in seconds since its last
    modification. The staleness of a directory is the smaller of:
    * The duration in seconds since its last modification, and
    * The staleness of any of its contents, staleness being defined recursively.

    Args:
      path: The directory or file to check for staleness.

    Returns:
      The milliseconds since last modification of the tree at path as an int.
    """
    resolved_path = self._resolve(path)

    max_mtime = 0
    if os.path.isdir(resolved_path):
      for dirpath, dirnames, filenames in os.walk(resolved_path):
        for p in dirnames + filenames:
          p_mtime = os.path.getmtime(os.path.join(dirpath, p))
          max_mtime = max(max_mtime, p_mtime)
    else:
      max_mtime = os.path.getmtime(resolved_path)
    return int((time.time() - max_mtime) * 1000)


class FakeFileSystem(object):
  """In-memory implementation of the FileSystem class."""

  def __init__(self):
    # Stores the proto contained in each path.
    self._path_to_proto = {}

  def read_file(self, path):
    """Reads a file.

    Args:
      path: The path of the file to read.
    Returns:
      A string containing the contents of the file.
    """
    return self._path_to_proto[_posix_path(path)]

  def write_file(self, path, data):
    """Writes into a file.

    Args:
      path: The path of the file to write the data to.
      data: A string containing the data to write.
    """
    self._path_to_proto[_posix_path(path)] = data

  def glob(self, pattern):
    """Encapsulates glob.glob.

    Args:
      pattern: Pattern to search for.
    Returns:
      List of path strings found.
    """
    # The fake file system doesn't support recursive globs.
    assert '**' not in pattern
    pattern = pattern.replace('*', '[^/]*')
    pattern = _posix_path(pattern)
    return [path for path in sorted(self._path_to_proto)
            if re.match(pattern, path)]

  def exists(self, path):
    """Encapsulates os.path.exists.

    Args:
      path: Path of file or directory to verify the existence of.
    Returns:
      A boolean for whether the file or directory exists.
    """
    return _posix_path(path) in self._path_to_proto
