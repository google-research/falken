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
"""Tests for google3.research.kernel.falken.service.learner.data_fetcher."""

import threading
import time

from unittest import mock

from absl.testing import absltest
from learner import data_fetcher


class DataFetcherTest(absltest.TestCase):
  """Test DataFetcher."""

  _FETCH_INTERVAL_SECONDS = 0.05

  def test_data_fetcher(self):
    """Retrieve and ensure the fetch does not wait for available data."""
    mock_condition = mock.Mock(spec=threading.Condition)()

    def _fetch_data():
      """Generator that returns 3 data items."""
      # Only wait on the condition variable when data isn't available.
      self.assertEqual(0, mock_condition.wait.call_count)
      for i in (1, 2, 3):
        yield i
        self.assertEqual(0, mock_condition.wait.call_count)
      # Return none and then make sure that the fetcher tried to wait.
      yield None
      mock_condition.wait.assert_called_once_with(
          timeout=DataFetcherTest._FETCH_INTERVAL_SECONDS)

    with data_fetcher.DataFetcher(
        _fetch_data(), DataFetcherTest._FETCH_INTERVAL_SECONDS,
        condition=mock_condition) as fetcher:
      self.assertEqual(fetcher.get(), 1)
      self.assertEqual(fetcher.get(), 2)
      self.assertEqual(fetcher.get(), 3)
      with self.assertRaises(data_fetcher.Empty):
        fetcher.get(timeout=0.01)

  def test_error_propagation(self):
    """Ensure get() raises the exception returned by the generator."""

    class _TestError(Exception):
      pass

    def _fetch_data():
      """Generator that returns 2 data items followed by an exception."""
      yield 1
      yield 2
      raise _TestError()

    mock_condition = mock.Mock(spec=threading.Condition)()
    with data_fetcher.DataFetcher(
        _fetch_data(), DataFetcherTest._FETCH_INTERVAL_SECONDS,
        condition=mock_condition) as fetcher:
      fetcher.get()
      fetcher.get()
      with self.assertRaises(_TestError):
        fetcher.get()
    self.assertEqual(0, mock_condition.wait.call_count)

  def test_stop_stops_thread(self):
    """Stop the fetcher thread."""
    yield_count = 0
    def _fetch_data():
      nonlocal yield_count
      while True:
        yield 'Yes!'
        yield_count += 1

    with data_fetcher.DataFetcher(
        _fetch_data(), DataFetcherTest._FETCH_INTERVAL_SECONDS) as fetcher:
      self.assertTrue(fetcher.running)
      fetcher.get()
      fetcher.get()
    self.assertFalse(fetcher.running)
    # Make sure the thread isn't still calling the generator.
    stopped_yield_count = yield_count
    time.sleep(DataFetcherTest._FETCH_INTERVAL_SECONDS * 2)
    self.assertEqual(yield_count, stopped_yield_count)


if __name__ == '__main__':
  absltest.main()
