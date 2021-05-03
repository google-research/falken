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

import glob
import os
import os.path
import re
import shutil

import braceexpand
import watchdog.events
import watchdog.observers


class FileMovedEventHandler(watchdog.events.FileSystemEventHandler):
  """Event handler for file moves."""

  def __init__(self, root_path, callback):
    """Initializes the event handler.

    Args:
      root_path: Path where all Falken files will be stored.
      callback: Function that takes a single argument for the destination path
        of the file that was moved.
    """
    self._root_path = root_path
    self._callback = callback

  def on_moved(self, event):
    """Method called every time a file move is detected.

    Args:
      event: A watchdog.events.FileMovedEvent object.
    """
    self._callback(os.path.relpath(event.dest_path, self._root_path))


class FileSystem(object):
  """Encapsulates file system operations so they can be faked in tests."""

  def __init__(self, root_path):
    """Initializes the file system object with a given root path.

    Args:
      root_path: Path where all Falken files will be stored.
    """
    self._root_path = root_path
    self._observers = {}

  def __del__(self):
    self.remove_all_file_callbacks()

  def add_file_callback(self, callback):
    """Sets up a callback function.

    The callback function will be called every time a file is created with
    write_file(..., trigger_callback=True).

    Args:
      callback: Function that takes a single argument for the destination path
        of the file that was moved.
    """
    event_handler = FileMovedEventHandler(self._root_path, callback)

    observer = watchdog.observers.Observer()
    observer.schedule(event_handler, self._root_path, recursive=True)
    observer.start()

    if callback in self._observers:
      raise ValueError('Added callback twice.')

    self._observers[callback] = observer

  def remove_file_callback(self, callback):
    """Removes all file callbacks."""
    observer = self._observers.pop(callback)
    observer.stop()
    observer.join()

  def remove_all_file_callbacks(self):
    """Removes all file callbacks."""
    for callback in list(self._observers):
      self.remove_file_callback(callback)

  def read_file(self, path):
    """Reads a file.

    Args:
      path: The path of the file to read.
    Returns:
      A bytes-like object containing the contents of the file.
    """
    with open(os.path.join(self._root_path, path), 'rb') as f:
      return f.read()

  def write_file(self, path, data):
    """Writes into a file.

    Args:
      path: The path of the file to write the data to.
      data: A bytes-like object containing the data to write.
    """
    destination_path = os.path.join(self._root_path, path)
    directory = os.path.dirname(destination_path)

    os.makedirs(directory, exist_ok=True)
    source_path = os.path.join(
        directory, '~' + os.path.basename(destination_path))
    with open(source_path, 'wb') as f:
      f.write(data)

    shutil.move(source_path, destination_path)

  def glob(self, pattern):
    """Encapsulates glob.glob.

    Args:
      pattern: Pattern to search for. May contains brace-style options,
        e.g., "a/{b,c}/*".
    Returns:
      List of path strings found.
    """
    result = []
    for p in braceexpand.braceexpand(pattern):
      for f in glob.glob(os.path.join(self._root_path, p)):
        result.append(os.path.relpath(f, self._root_path))
    return result

  def exists(self, path):
    """Encapsulates os.path.exists.

    Args:
      path: Path of file or directory to verify the existence of.
    Returns:
      A boolean for whether the file or directory exists.
    """
    return os.path.exists(os.path.join(self._root_path, path))


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
    return self._path_to_proto[path]

  def write_file(self, path, data):
    """Writes into a file.

    Args:
      path: The path of the file to write the data to.
      data: A string containing the data to write.
    """
    self._path_to_proto[path] = data

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
    return [path for path in sorted(self._path_to_proto)
            if re.match(pattern, path)]

  def exists(self, path):
    """Encapsulates os.path.exists.

    Args:
      path: Path of file or directory to verify the existence of.
    Returns:
      A boolean for whether the file or directory exists.
    """
    return path in self._path_to_proto
