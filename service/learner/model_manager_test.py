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
"""Tests for model_manager."""

from absl.testing import absltest
from learner import model_manager


class ModelManagerTest(absltest.TestCase):

  def test_model_manager_update_no_eval(self):
    man = model_manager.ModelManager()
    man.record_new_model('m1', [])
    man.record_new_model('m2', [])
    man.record_new_model('m3', [])
    self.assertEqual(man.best_model_id, 'm3')

  def test_model_manager_update(self):
    man = model_manager.ModelManager()
    man.record_new_model('m1', [])
    self.assertEqual(man.best_model_id, 'm1')
    man.record_new_model('m2', [(1, 2)])
    self.assertEqual(man.best_model_id, 'm2')
    man.record_new_model('m3', [(1, 0)])
    self.assertEqual(man.best_model_id, 'm3')
    man.record_new_model('m4', [(1, 1)])
    self.assertEqual(man.best_model_id, 'm3')
    man.record_new_model('m5', [(2, 4)])
    self.assertEqual(man.best_model_id, 'm5')
    with self.assertRaises(AssertionError):
      man.record_new_model('m6', [(1, -10)])

  def test_model_manager_improvement_epsilon(self):
    man = model_manager.ModelManager()
    epsilon = model_manager._IMPROVEMENT_EPSILON / 2
    n_models = model_manager._NO_IMPROVEMENT_MODEL_LIMIT
    for i in range(n_models + 2):
      man.record_new_model(f'm{i}', [(1, 1 - i * epsilon)])
    self.assertEqual(man._models_without_improvement, n_models + 1)
    self.assertTrue(man.should_stop())


if __name__ == '__main__':
  absltest.main()
