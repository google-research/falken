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
"""Handles interactions with the file system."""

import os
import pathlib
import re
import shutil
import tempfile
from log import falken_logging


class FileSystemPrimitives:
  """Wrapper for python-supported file functionality."""

  def delete_recursively(self, path):
    shutil.rmtree(path)

  def make_dirs(self, path, exist_ok=True):
    pathlib.Path(path).mkdir(parents=True, exist_ok=exist_ok)

  def copy(self, src, dst):
    shutil.copy(src, dst)

  def is_directory(self, path):
    return pathlib.Path(path).is_dir()

  def walk(self, path):
    yield from os.walk(path)


class FileSystem:
  """Helper class for handling interactions with the file system."""

  def __init__(self, tmp_models_directory, models_directory,
               checkpoints_directory, summaries_directory):
    self._tmp_models_directory = tmp_models_directory
    self._models_directory = models_directory
    self._checkpoints_directory = checkpoints_directory
    self._summaries_directory = summaries_directory
    self._fs = FileSystemPrimitives()

  def is_directory(self, path):
    return self._fs.is_directory(path)

  def _get_sanitized_string(self, unsafe):
    """Returns a valid path, replacing non-alphanumerics with an underscore."""
    return re.sub('[^a-zA-Z0-9]+', '_', unsafe)

  def _checkpoints_path(self, assignment):
    return os.path.join(self._checkpoints_directory, assignment.project_id,
                        assignment.brain_id, assignment.session_id,
                        self._get_sanitized_string(assignment.assignment_id))

  def create_checkpoints_path(self, assignment):
    """Create and return the directory for checkpoints."""
    path = self._checkpoints_path(assignment)
    falken_logging.info('Creating checkpoint directory.',
                        checkpoint_directory_path=path)
    # Fetch full assignment info.
    self._fs.make_dirs(path)
    return path

  def wipe_checkpoints(self, assignment):
    """Delete all checkpoints."""
    path = self._checkpoints_path(assignment)
    if self._fs.is_directory(path):
      falken_logging.info(
          'Removing checkpoints directory.', checkpoint_directory_path=path)
      self._fs.delete_recursively(path)

  def create_summary_path(self, assignment):
    """Create and return the directory for summaries."""
    path = os.path.join(self._summaries_directory, assignment.project_id,
                        assignment.brain_id, assignment.session_id,
                        self._get_sanitized_string(assignment.assignment_id))
    falken_logging.info(
        'Creating summary directory.', summary_directory_path=path)
    self._fs.make_dirs(path)
    return path

  def create_tmp_checkpoint_path(self, assignment, model_id):
    """Create and return the temporary checkpoints export directory."""
    # TODO(hmoraldo): Escape assignment ID to ensure valid path.
    full_tmp_path = os.path.join(self._tmp_models_directory,
                                 assignment.project_id, assignment.brain_id,
                                 assignment.session_id, model_id, 'checkpoint')
    falken_logging.info(
        'Creating tmp checkpoint directory.', model_path=full_tmp_path)
    self._fs.make_dirs(full_tmp_path)
    return full_tmp_path

  def extract_tmp_model_path_from_checkpoint_path(self, checkpoint_path):
    """Create a tmp model path from tmp checkpoint path.

    Args:
      checkpoint_path: Str, something like
        $BORG_ALLOC_DIR/ramdisk/falken_models/test_project_id/test_brain_id/
        test_session_id/test_model_id/checkpoint/.

    Returns:
      model_path: Str, something like
        $BORG_ALLOC_DIR/ramdisk/falken_models/test_project_id/test_brain_id/
        test_session_id/test_model_id/saved_model/.
    """
    dir_name = os.path.dirname(checkpoint_path)
    assert dir_name.startswith(self._tmp_models_directory)
    assert os.path.basename(checkpoint_path) == 'checkpoint'
    return os.path.join(dir_name, 'saved_model')

  @staticmethod
  def _get_relative_path(base, path):
    if not path.startswith(base):
      raise ValueError(f'{path} is not inside {base}')
    rel_path = path[len(base):]
    if rel_path and rel_path[0] in (os.path.sep, os.path.altsep):
      rel_path = rel_path[1:]
    return rel_path

  def _copy_file(self, src_dir, full_path, dst_dir):
    rel_path = FileSystem._get_relative_path(src_dir, full_path)
    target = os.path.join(dst_dir, rel_path)
    self._fs.make_dirs(os.path.dirname(target))
    self._fs.copy(full_path, target)

  def _copy_directory(self, src, dst):
    files = []
    for (dirname, _, fnames) in self._fs.walk(src):
      files.extend(os.path.join(dirname, fname) for fname in fnames)
    for f in files:
      self._copy_file(src, f, dst)

  def copy_to_model_directory(self, full_tmp_path):
    """Copy files in the temp model dir to permanent model dir."""
    rel_path = FileSystem._get_relative_path(
        self._tmp_models_directory, full_tmp_path)
    model_path = os.path.join(self._models_directory, rel_path)
    self._copy_directory(full_tmp_path, model_path)
    falken_logging.info(
        'Completed copying model to permanent storage.', model_path=model_path)
    return model_path

  def compress_model_directory(self, full_tmp_path):
    """Compresses all files in full_tmp_path, saving to permanent storage."""
    rel_path = FileSystem._get_relative_path(
        self._tmp_models_directory, full_tmp_path)
    model_path = os.path.join(self._models_directory, rel_path) + '.zip'
    self._fs.make_dirs(os.path.split(model_path)[0])

    # Compress in a temporary directory and then move to destination.
    with tempfile.TemporaryDirectory(dir=self._tmp_models_directory) as tmp_dir:
      tmp_file = os.path.join(tmp_dir, 'tmp_zip')
      shutil.make_archive(tmp_file, 'zip', full_tmp_path)
      tmp_file += '.zip'
      self._fs.copy(tmp_file, model_path)

    return model_path

  def wipe_tmp_model_directory(self, full_tmp_path):
    falken_logging.info(
        'Removing tmp model directory.', policy_path=full_tmp_path)
    self._fs.delete_recursively(full_tmp_path)

