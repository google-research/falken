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

"""Tests for stats_collector."""

import time
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from learner import stats_collector

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import data_store_pb2 as falken_schema_pb2


class StatsCollectorTest(parameterized.TestCase):

  def setUp(self):
    super(StatsCollectorTest, self).setUp()
    self.stats_collector = stats_collector.StatsCollector(
        'test_project_id', 'test_brain_id', 'test_session_id',
        'test_assignment_id')

  def test_record_bad_event(self):
    with self.assertRaises(ValueError):
      with self.stats_collector.record_event('BLAH'):
        yield

  @parameterized.parameters(sorted(stats_collector.FALKEN_LATENCY_EVENTS))
  def test_record_good_event(self, event_name):
    with self.stats_collector.record_event(event_name):
      yield

  @parameterized.parameters(
      sorted(stats_collector.FALKEN_REPEATED_LATENCY_EVENTS))
  def test_record_good_repeated_event(self, event_name):
    with self.stats_collector.record_event(event_name):
      yield

  @staticmethod
  def _reset_mock_perf_counter(perf_counter, start_time, interval,
                               default_time=-1):
    """Reset a mock time.perf_counter with a set of times.

    Args:
      perf_counter: Mock of time.perf_counter.
      start_time: First time to return from time.perf_counter().
      interval: Interval until the second time to return.
      default_time: Default time to return the scheduled interval has elapsed.
    """
    counter_times = [start_time, start_time + interval]

    def get_next_time_or_default():
      """Get the next time from counter_times or return default_time."""
      try:
        return counter_times.pop(0)
      except IndexError:
        return default_time

    perf_counter.side_effect = get_next_time_or_default

  @mock.patch.object(time, 'perf_counter')
  def test_get_model_latency_proto(self, mock_perf_counter):
    self.stats_collector.training_steps = 1000
    self.stats_collector.batch_size = 500
    self.stats_collector.demonstration_frames = 18000
    self.stats_collector.evaluation_frames = 2000
    expected_latency_proto = falken_schema_pb2.ModelLatencyStats(
        fetch_chunk_latencies=(2, 0.5),
        train_brain_latencies=(1.5, 1.2),
        save_model_tmp_latency=0.4,
        save_model_latency=0.3,
        record_model_latency=5)
    expected_latency_proto.training_info.training_steps = 1000
    expected_latency_proto.training_info.batch_size = 500
    expected_latency_proto.training_info.demonstration_frames = 18000
    expected_latency_proto.training_info.evaluation_frames = 2000
    expected_latency_proto.machine_info.hostname = (
        stats_collector.StatsCollector.hostname)
    expected_latency_proto.machine_info.taxonomy = (
        stats_collector.StatsCollector.machine_taxonomy)

    self._reset_mock_perf_counter(mock_perf_counter, 1, 2)
    with self.stats_collector.record_event(
        stats_collector.FALKEN_FETCH_CHUNK_EVENT_NAME):
      pass

    self._reset_mock_perf_counter(mock_perf_counter, 4, 0.5)
    with self.stats_collector.record_event(
        stats_collector.FALKEN_FETCH_CHUNK_EVENT_NAME):
      pass

    self._reset_mock_perf_counter(mock_perf_counter, 6, 1.5)
    with self.stats_collector.record_event(
        stats_collector.FALKEN_TRAIN_BRAIN_EVENT_NAME):
      pass

    self._reset_mock_perf_counter(mock_perf_counter, 8.8, 1.2)
    with self.stats_collector.record_event(
        stats_collector.FALKEN_TRAIN_BRAIN_EVENT_NAME):
      pass

    self._reset_mock_perf_counter(mock_perf_counter, 10, 0.4)
    with self.stats_collector.record_event(
        stats_collector.FALKEN_SAVE_MODEL_TMP_EVENT_NAME):
      pass

    self._reset_mock_perf_counter(mock_perf_counter, 11, 0.3)
    with self.stats_collector.record_event(
        stats_collector.FALKEN_SAVE_MODEL_EVENT_NAME):
      pass

    self._reset_mock_perf_counter(mock_perf_counter, 30, 5)
    with self.stats_collector.record_event(
        stats_collector.FALKEN_RECORD_MODEL_EVENT_NAME):
      model_latency_proto = self.stats_collector.get_model_latency_proto()
      self.assertEqual(model_latency_proto, expected_latency_proto)
      self.assertEqual(model_latency_proto.training_info.training_steps, 1000)
      self.assertEqual(model_latency_proto.training_info.batch_size, 500)
      self.assertEqual(model_latency_proto.training_info.demonstration_frames,
                       18000)
      self.assertEqual(model_latency_proto.training_info.evaluation_frames,
                       2000)

  @mock.patch.object(time, 'perf_counter')
  def test_get_eval_latency_proto(self, mock_perf_counter):
    expected_latency_proto = falken_schema_pb2.EvalLatencyStats(
        eval_latency=1, record_eval_latency=0.5)
    self._reset_mock_perf_counter(mock_perf_counter, 42, 1)
    with self.stats_collector.record_event(
        stats_collector.FALKEN_EVAL_EVENT_NAME):
      pass

    self._reset_mock_perf_counter(mock_perf_counter, 43, 0.5)
    with self.stats_collector.record_event(
        stats_collector.FALKEN_RECORD_EVAL_EVENT_NAME):
      eval_latency_proto = self.stats_collector.get_eval_latency_proto()
      self.assertEqual(eval_latency_proto, expected_latency_proto)

  @mock.patch.object(time, 'perf_counter')
  @mock.patch.object(stats_collector.StatsCollector, '_notify_event_listeners')
  def test_notify_event_listener_on_record_event(
      self, mock_notify_event_listeners, mock_perf_counter):
    """Notify an event listener when an event is recorded."""
    self._reset_mock_perf_counter(mock_perf_counter, 4, 2)
    with self.stats_collector.record_event(
        stats_collector.FALKEN_FETCH_CHUNK_EVENT_NAME):
      pass

    mock_notify_event_listeners.assert_called_with(
        'test_project_id', 'test_brain_id', 'test_session_id',
        'test_assignment_id', stats_collector.FALKEN_FETCH_CHUNK_EVENT_NAME, 2)

  def test_register_and_notify_event_listeners(self):
    """Test event listener registration and notification."""
    mock_listeners = [mock.Mock(), mock.Mock()]
    try:
      stats_collector.StatsCollector.register_event_listener(mock_listeners[0])
      stats_collector.StatsCollector.register_event_listener(mock_listeners[1])

      event = ('project', 'brain', 'session', 'assignment', 'event', 21)
      stats_collector.StatsCollector._notify_event_listeners(*event)
      mock_listeners[0].assert_called_with(*event)
      mock_listeners[1].assert_called_with(*event)
    finally:
      stats_collector.StatsCollector._event_listeners.clear()


if __name__ == '__main__':
  absltest.main()
