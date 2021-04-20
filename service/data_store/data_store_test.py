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

from absl.testing import absltest
from data_store import data_store


class DataStoreTest(absltest.TestCase):

  def test_get_project_path(self):
    self.assertEqual(
        '/base/projects/p1',
        data_store.DataStore('/base')._get_project_path('p1'))

  def test_get_brain_path(self):
    self.assertEqual(
        '/base/projects/p1/brains/b1',
        data_store.DataStore('/base')._get_brain_path('p1', 'b1'))

  def test_get_snapshot_path(self):
    self.assertEqual(
        '/base/projects/p1/brains/b1/snapshots/s1',
        data_store.DataStore('/base')._get_snapshot_path('p1', 'b1', 's1'))

  def test_get_session_path(self):
    self.assertEqual(
        '/base/projects/p1/brains/b1/sessions/s1',
        data_store.DataStore('/base')._get_session_path('p1', 'b1', 's1'))

  def test_get_episode_path(self):
    self.assertEqual(
        '/base/projects/p1/brains/b1/sessions/s1/episodes/e1',
        data_store.DataStore('/base')._get_episode_path(
            'p1', 'b1', 's1', 'e1'))

  def test_get_chunk_path(self):
    self.assertEqual(
        '/base/projects/p1/brains/b1/sessions/s1/episodes/e1/chunks/c1',
        data_store.DataStore('/base')._get_chunk_path(
            'p1', 'b1', 's1', 'e1', 'c1'))

  def test_get_assignment_path(self):
    self.assertEqual(
        '/base/projects/p1/brains/b1/sessions/s1/assignments/a1',
        data_store.DataStore('/base')._get_assignment_path(
            'p1', 'b1', 's1', 'a1'))

  def test_get_model_path(self):
    self.assertEqual(
        '/base/projects/p1/brains/b1/sessions/s1/models/m1',
        data_store.DataStore('/base')._get_model_path('p1', 'b1', 's1', 'm1'))

  def test_get_offline_evaluation_path(self):
    self.assertEqual(
        '/base/projects/p1/brains/b1/sessions/s1/models/m1/'
        'offline_evaluations/o1',
        data_store.DataStore('/base')._get_offline_evaluation_path(
            'p1', 'b1', 's1', 'm1', 'o1'))


if __name__ == '__main__':
  absltest.main()
