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
"""Fetches data in a background thread."""

import queue
import threading
import traceback

from log import falken_logging as logging


class Empty(Exception):  # pylint: disable=g-bad-exception-name
  """Indicates that no data was present."""


class DataFetcher:
  """Fetches data in the background.

  Can be used as a context manager:
    with DataFetcher(fun, 10.0) as d:
      ...
      a = d.Get()
      ...

  Alternatively, requires Start and Stop methods to be called.
  """

  def __init__(self, fetch_generator, fetch_interval_seconds,
               condition=None):
    """Creates a data fetcher.

    Args:
      fetch_generator: A generator or iterable used to produce data.
      fetch_interval_seconds: Interval between fetches in seconds.
      condition: Override the condition object to wait on when
        fetch_generator has no data. This is exposed for testing purposes.
    """
    self._fetch_generator = fetch_generator
    self._fetch_interval_seconds = fetch_interval_seconds
    self._queue = queue.Queue()
    self._running = False
    self._stop = False
    self._fetcher_thread = None
    self._poll_condition = condition if condition else threading.Condition()

  def Start(self):
    """Start fetching data in a background thread."""
    assert not self._running
    self._stop = False
    self._running = True
    self._fetcher_thread = threading.Thread(target=self._Run, daemon=True)
    self._fetcher_thread.start()

  def Stop(self):
    """Stop fetching data in a background thread."""
    self._stop = True
    self._poll_condition.acquire()
    self._poll_condition.notify()
    self._poll_condition.release()
    self._fetcher_thread.join()

  @property
  def running(self):
    """Whether the fetch thread is running."""
    return self._running

  def __enter__(self):
    self.Start()
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    self.Stop()

  def Get(self, block=True, timeout=None):
    """Interface is identical to queue.get. Raises Empty if no data present."""
    try:
      queue_result = self._queue.get(block=block, timeout=timeout)
      if queue_result[0]:
        # Normal result
        _, result = queue_result
      else:
        # Exception on the queue
        _, e, stack_trace = queue_result

        logging.error(
            f'Error in fetcher thread: {e}'
            f'\nFetcher thread stack trace: {stack_trace}')
        raise e
    except queue.Empty:
      raise Empty()

    return result

  def _Run(self):
    """Main loop for fetcher thread."""
    self._running = True
    try:
      for data in self._fetch_generator:
        if self._stop:
          break
        if data is not None:
          self._queue.put((True, data))
          continue

        self._poll_condition.acquire()
        self._poll_condition.wait(timeout=self._fetch_interval_seconds)
        self._poll_condition.release()
        if self._stop:
          break
    except Exception as e:  # pylint: disable=broad-except
      self._queue.put((False, e, traceback.format_exc))
    self._running = False
