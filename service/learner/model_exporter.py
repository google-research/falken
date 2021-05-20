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
"""Exports models to be consumed by the Falken API in a background thread."""

import copy
import os
import queue
import threading
import traceback
from typing import NamedTuple, List, Tuple, Dict

from learner import file_system
from learner import model_manager as model_man
from learner import stats_collector
from learner import storage as storage_module
from learner.brains import continuous_imitation_brain
from log import falken_logging

# pylint: disable=unused-import, g-bad-import-order
import common.generate_protos
import data_store_pb2


class Error(Exception):
  """Base class for exceptions."""


class InactiveExporterError(Error):
  """Raised when exporter thread is inactive but is called on."""


class _ModelExportTask(NamedTuple):
  """Task class containing information needed for exporting model."""
  checkpoint_path: str
  eval_list: List[Tuple[int, float]]
  stats: stats_collector.StatsCollector
  model_id: str
  episode_id: str
  episode_chunk_id: int
  training_examples_completed: int
  max_training_examples: int
  most_recent_demo_time_micros: int


class ModelExporter:
  """Exports models in the background.

  Call EvaluateAndSavePolicy to export models in the background, and Stop to
  stop the background thread.
  """

  def __init__(self,
               assignment: data_store_pb2.Assignment,
               storage: storage_module.Storage,
               file: file_system.FileSystem,
               model_manager: model_man.ModelManager,
               hparams: Dict[str, str]):
    """Creates a new ModelExporter."""
    self._assignment = assignment
    self._storage = storage
    self._file = file
    self._model_manager = model_manager
    self._brain_spec = self._storage.get_brain_spec(self._assignment.project_id,
                                                    self._assignment.brain_id)
    self._queue = queue.Queue()
    self._error_queue = queue.Queue()
    self._export_model_thread = threading.Thread(
        target=self._run, daemon=True)
    self._hparams = hparams
    self._synchronous = hparams.get('synchronous_export', False)

  def __enter__(self):
    self.start()
    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    self.stop()

  def export_model(
      self,
      checkpoint_path: str,
      eval_list: List[Tuple[int, int]],
      stats: stats_collector.StatsCollector,
      model_id: str,
      episode_id: str,
      episode_chunk_id: int,
      training_examples_completed: int,
      max_training_examples: int,
      most_recent_demo_time_micros: int):
    """Export model in a background thread.

    Args:
      checkpoint_path: Str, path to where the checkpoint for the model is
        stored.
      eval_list: List, results of brain.compute_full_evaluation() in a list.
      stats: stats_collector.StatsCollector, contains stats recorded so far for
        the model.
      model_id: The ID of the model that is being exported.
      episode_id: The ID of the episode associated with this model.
      episode_chunk_id: The ID of the episode chunk associated with this model.
      training_examples_completed: Amount of steps * batches completed at
        the time of saving.
      max_training_examples: Maximum step * batch count allowed for training
        this model.
      most_recent_demo_time_micros: Time for the most recent human demonstration
        used to train this model (the most recent chunk that contains human
        data).

    Raises:
      ValueError: When the checkpoint path is not provided.
      InactiveExporterError: When the exporter thread is not active.
    """
    if not checkpoint_path:
      raise ValueError('Checkpoint path is empty when calling ExportModel.')
    if not self._export_model_thread.is_alive():
      raise InactiveExporterError('Exporter thread is not active.')

    model_export_task = _ModelExportTask(
        checkpoint_path, copy.deepcopy(eval_list), copy.deepcopy(stats),
        model_id, episode_id, episode_chunk_id, training_examples_completed,
        max_training_examples, most_recent_demo_time_micros)
    if self._synchronous:
      self._export_model(model_export_task)
    else:
      self._queue.put(model_export_task)

    self._reraise_error()

  def _run(self):
    """Loop that is exporting models."""
    while True:
      try:
        export_info = self._queue.get(block=True)
        if not export_info:
          break
        self._export_model(export_info)

      except queue.Empty:
        continue

      except Exception as e:  # pylint: disable=broad-except
        self._error_queue.put((e, traceback.format_exc()))

  def _export_model(self, export_task: _ModelExportTask):
    """Exports model.

    Converts the saved policy to TFLite, records it on permanent storage, and
    records evaluation results.

    Args:
      export_task: _ModelExportTask object containing info needed for export
        operations.
    """
    checkpoint_path = export_task.checkpoint_path
    eval_list = export_task.eval_list
    stats = export_task.stats
    model_id = export_task.model_id
    episode_id = export_task.episode_id
    episode_chunk_id = export_task.episode_chunk_id
    training_examples_completed = export_task.training_examples_completed
    max_training_examples = export_task.max_training_examples
    most_recent_demo_time_micros = export_task.most_recent_demo_time_micros

    falken_logging.info('Exporting model.',
                        checkpoint_directory_path=checkpoint_path,
                        eval_list=eval_list)

    if not self._file.is_directory(checkpoint_path):
      raise ValueError(f'No checkpoint at {checkpoint_path}')

    tmp_model_path = self._file.extract_tmp_model_path_from_checkpoint_path(
        checkpoint_path)
    # TODO(b/162866696): Instead of initializing here, initialize when class
    # is created (could be tricky to implement since brain has fixed checkpoints
    # dir).
    export_brain = continuous_imitation_brain.ContinuousImitationBrain(
        brain_id=self._assignment.brain_id,
        spec_pb=self._brain_spec,
        checkpoint_path=checkpoint_path,
        hparams=self._hparams,
        compile_graph=False)

    with stats.record_event(stats_collector.FALKEN_EXPORT_MODEL_EVENT_NAME):
      export_brain.export_saved_model(tmp_model_path)

    with stats.record_event(stats_collector.FALKEN_CONVERT_TFLITE_EVENT_NAME):
      tf_lite_path = os.path.join(tmp_model_path, 'tflite')
      export_brain.convert_model_to_tflite(tmp_model_path, tf_lite_path)

    tmp_parent_path = os.path.dirname(tmp_model_path)
    with stats.record_event(stats_collector.FALKEN_SAVE_MODEL_EVENT_NAME):
      publish_path = self._file.copy_to_model_directory(tmp_parent_path)
      publish_zip_path = self._file.compress_model_directory(tmp_parent_path)
      self._file.wipe_tmp_model_directory(tmp_parent_path)

    with stats.record_event(stats_collector.FALKEN_RECORD_MODEL_EVENT_NAME):
      self._storage.record_new_model(
          self._assignment, episode_id, episode_chunk_id,
          training_examples_completed, max_training_examples,
          most_recent_demo_time_micros, publish_path, publish_zip_path,
          model_id, stats.get_model_latency_proto())

    with stats.record_event(stats_collector.FALKEN_RECORD_EVAL_EVENT_NAME):
      self._storage.record_evaluations(self._assignment, model_id, eval_list,
                                       stats.get_eval_latency_proto())

    falken_logging.info('Saved evaluation and recorded in db.',
                        model_id=model_id,
                        model_path=publish_path)

  def start(self):
    self._export_model_thread.start()

  def stop(self):
    """Blocks the caller until we finish exporting models in the queue."""
    self._queue.put(None)
    self._export_model_thread.join()
    self._reraise_error()

  def _reraise_error(self):
    try:
      error_result = self._error_queue.get(block=False, timeout=None)
      e, stack_trace = error_result
      falken_logging.error('Error in model exporter thread.',
                           error=e, stack_trace=stack_trace)
      raise e
    except queue.Empty:
      return None
