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
"""Handles collecting stats for various parts in the learner."""

import contextlib
import socket
import time

from log import falken_logging

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import data_store_pb2 as falken_schema_pb2

# The event where AssignmentProcessor process runs.
FALKEN_PROCESS_EVENT_NAME = 'process'
# The event for the main training loop in assignment processor.
FALKEN_MAIN_TRAINING_LOOP_EVENT_NAME = 'main_training_loop'
# The event where more chunks are fetched from the DB in the main training loop.
FALKEN_FETCH_CHUNK_EVENT_NAME = 'fetch_chunk'
# The event where train() is called on the brain.
FALKEN_TRAIN_BRAIN_EVENT_NAME = 'train_brain'
# The event to record the evaluation in the DB.
FALKEN_RECORD_EVAL_EVENT_NAME = 'record_eval'
# The event to record the model in the DB.
FALKEN_RECORD_MODEL_EVENT_NAME = 'record_model'
# The event to save the model to permanent path.
FALKEN_SAVE_MODEL_EVENT_NAME = 'save_model'
# The event to save the model to temporary path.
FALKEN_SAVE_MODEL_TMP_EVENT_NAME = 'save_model_tmp'
# The event to export the model from TF through policy_saver.PolicySaver.
FALKEN_EXPORT_MODEL_EVENT_NAME = 'export_model'
# The event to export the checkpoint from TF through common.Checkpointer.
FALKEN_EXPORT_CHECKPOINT_EVENT_NAME = 'export_checkpoint'
# The event to convert the model to TF Lite.
FALKEN_CONVERT_TFLITE_EVENT_NAME = 'convert_tflite'
# The event where offline evaluation is computed on the model.
FALKEN_EVAL_EVENT_NAME = 'eval'


FALKEN_LATENCY_EVENTS = [
    FALKEN_EVAL_EVENT_NAME,
    FALKEN_MAIN_TRAINING_LOOP_EVENT_NAME,
    FALKEN_PROCESS_EVENT_NAME, FALKEN_RECORD_EVAL_EVENT_NAME,
    FALKEN_RECORD_MODEL_EVENT_NAME, FALKEN_SAVE_MODEL_EVENT_NAME,
    FALKEN_SAVE_MODEL_TMP_EVENT_NAME,
    FALKEN_EXPORT_MODEL_EVENT_NAME, FALKEN_EXPORT_CHECKPOINT_EVENT_NAME,
    FALKEN_CONVERT_TFLITE_EVENT_NAME
]

FALKEN_REPEATED_LATENCY_EVENTS = [
    FALKEN_FETCH_CHUNK_EVENT_NAME, FALKEN_TRAIN_BRAIN_EVENT_NAME
]


class StatsCollector:
  """Helper class for collecting stats for various parts in the learner.

  Attributes:
    batch_size: Size of batch used to train model. The total number of
      example steps (gradient updates) per brain.train() operation is
      training_steps * batch_size.
    demonstration_frames: Number of demonstration frames used to train the
      model.
    evaluation_frames: Number of demonstration frames used to evaluate the
      model.
    training_steps: Number of training steps per brain.train() operation.
      The total training steps to train a model is training_steps *
      AssignmentStats.brain_train_steps.
  """

  hostname = socket.gethostname()
  # High level description of the machine (e.g CPU, RAM, GPUs etc.)
  machine_taxonomy = 'unknown'

  # See register_event_listener().
  _event_listeners = set()

  def __init__(self, project_id, brain_id, session_id, assignment_id):
    """Initialize the instance.

    Args:
      project_id: String ID of the project being processed.
      brain_id: String ID of the brain being processed.
      session_id: String ID of the session being processed.
      assignment_id: String ID of the assignment being processed in the project.
    """
    self._start_times_for_events = {}
    self._latency_for_events = {}
    self._project_id = project_id
    self._brain_id = brain_id
    self._session_id = session_id
    self._assignment_id = assignment_id
    self.batch_size = 0
    self.demonstration_frames = 0
    self.evaluation_frames = 0
    self.training_steps = 0

  @staticmethod
  def register_event_listener(event_listener):
    """Register a listener for recorded events in all StatsCollector instances.

    Args:
      event_listener: Callable that adheres to the interface
        (project_id, brain_id, session_id, assignment_id, event_id, latency)
        where project_id, brain_id, session_id, assignment_id reference the
        assignment being processed, event_id event_id is a string identifier
        for the event and latency is the latency of the event in seconds.
        processed.
    """
    StatsCollector._event_listeners.add(event_listener)

  @staticmethod
  def _notify_event_listeners(project_id, brain_id, session_id, assignment_id,
                              event, latency):
    """Notify event listeners of a latency event.

    Args:
      project_id: Project the event is associated with.
      brain_id: Brain this event is associated with.
      session_id: Session this event is associated with.
      assignment_id: Assignment this event is associated with.
      event: Name of the event.
      latency: Latency of the event in seconds.
    """
    for listener in StatsCollector._event_listeners:
      listener(project_id, brain_id, session_id, assignment_id, event, latency)

  @contextlib.contextmanager
  def record_event(self, event):
    """Record the starting time for an event.

    Args:
      event: Name of the event, see stats_collector.FALKEN_*_EVENT_NAME for
        valid names.

    Yields:
      A reference to this instance.
    """
    try:
      if event in FALKEN_LATENCY_EVENTS:
        self._start_times_for_events[event] = time.perf_counter()
      elif event in FALKEN_REPEATED_LATENCY_EVENTS:
        if event in self._start_times_for_events:
          self._start_times_for_events[event].append(time.perf_counter())
        else:
          self._start_times_for_events[event] = [time.perf_counter()]

      else:
        raise ValueError(
            'Tried to start timer for an event that does not exist.')
      yield self

    finally:
      latency_for_event = 0
      if event in FALKEN_LATENCY_EVENTS:
        start_time = self._start_times_for_events.get(event, 0)
        if not start_time:
          raise ValueError('No start time recorded for this event.')
        latency_for_event = time.perf_counter() - start_time
        self._latency_for_events[event] = latency_for_event
      elif event in FALKEN_REPEATED_LATENCY_EVENTS:
        start_time = self._start_times_for_events[event][-1]
        latency_for_event = time.perf_counter() - start_time
        if event in self._latency_for_events:
          self._latency_for_events[event].append(latency_for_event)
        else:
          self._latency_for_events[event] = [latency_for_event]
      falken_logging.info(
          f'Latency for event {event}: {latency_for_event}')
      self._notify_event_listeners(self._project_id, self._brain_id,
                                   self._session_id, self._assignment_id, event,
                                   latency_for_event)

  def get_model_latency_proto(self):
    """Returns a proto containing latency from various model-related events."""
    now = time.perf_counter()
    model_latency_stats = falken_schema_pb2.ModelLatencyStats(
        save_model_tmp_latency=self._latency_for_events.pop(
            FALKEN_SAVE_MODEL_TMP_EVENT_NAME, 0),
        export_model_latency=self._latency_for_events.pop(
            FALKEN_EXPORT_MODEL_EVENT_NAME, 0),
        export_checkpoint_latency=self._latency_for_events.pop(
            FALKEN_EXPORT_CHECKPOINT_EVENT_NAME, 0),
        convert_tflite_latency=self._latency_for_events.pop(
            FALKEN_CONVERT_TFLITE_EVENT_NAME, 0),
        save_model_latency=self._latency_for_events.pop(
            FALKEN_SAVE_MODEL_EVENT_NAME, 0),
        record_model_latency=now -
        self._start_times_for_events.get(FALKEN_RECORD_MODEL_EVENT_NAME, now))
    model_latency_stats.fetch_chunk_latencies.extend(
        self._latency_for_events.pop(FALKEN_FETCH_CHUNK_EVENT_NAME, []))
    # Clear the start time list as well for fetch chunk.
    self._start_times_for_events.pop(FALKEN_FETCH_CHUNK_EVENT_NAME, [])
    model_latency_stats.train_brain_latencies.extend(
        self._latency_for_events.pop(FALKEN_TRAIN_BRAIN_EVENT_NAME, []))
    # Clear the start time list as well for train brain.
    self._start_times_for_events.pop(FALKEN_TRAIN_BRAIN_EVENT_NAME, [])
    # Clear the start time list as well for train brain.
    model_latency_stats.machine_info.CopyFrom(falken_schema_pb2.MachineInfo(
        hostname=StatsCollector.hostname,
        taxonomy=StatsCollector.machine_taxonomy))
    model_latency_stats.training_info.CopyFrom(falken_schema_pb2.TrainingInfo(
        training_steps=self.training_steps, batch_size=self.batch_size,
        demonstration_frames=self.demonstration_frames,
        evaluation_frames=self.evaluation_frames))
    falken_logging.info(f'Model latency stats: \n{model_latency_stats}')

    return model_latency_stats

  def get_eval_latency_proto(self):
    """Returns a proto containing latency from various eval-related events."""
    now = time.perf_counter()
    eval_latency_stats = falken_schema_pb2.EvalLatencyStats(
        eval_latency=self._latency_for_events.get(FALKEN_EVAL_EVENT_NAME, 0),
        record_eval_latency=now -
        self._start_times_for_events.get(FALKEN_RECORD_EVAL_EVENT_NAME, now))
    falken_logging.info(f'Eval latency stats: \n{eval_latency_stats}')
    return eval_latency_stats
