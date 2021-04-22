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
"""Imports and executes all tests."""

import importlib
import inspect
import os
import subprocess
import sys
from common import pip_installer  # pylint: disable=unused-import

# Add search paths for all modules.
_SERVICE_MODULE_PATHS = ['data_store', 'log', 'learner', 'learner/brains']
sys.path.extend(
    [os.path.join(os.path.dirname(__file__), p) for p in _SERVICE_MODULE_PATHS]
)

_SUBPROCESS_TESTS = [
    'common/generate_protos_test.py',
    'common/pip_installer_test.py',
]

_TEST_MODULES = [
    'data_store.data_store_test',
    'learner.brains.action_postprocessor_test',
    'learner.brains.demonstration_buffer_test',
    'learner.brains.egocentric_test',
    'learner.brains.eval_datastore_test',
    'learner.brains.imitation_loss_test',
    'learner.brains.layers_test',
    'learner.brains.networks_test',
    'learner.brains.numpy_replay_buffer_test',
    'learner.brains.observation_preprocessor_test',
    'learner.brains.policies_test',
    'learner.brains.specs_test',
    'learner.brains.tensor_nest_test',
    'learner.brains.weights_initializer_test',
    'learner.data_fetcher_test',
    'learner.model_manager_test',
    'log.falken_logging_test',
]


def _add_module_test_classes_to_global_namespace(test_classes, module):
  """Add test classes from the specified modules to this global namespace.

  Args:
    test_classes: Tuple of base classes for tests.
    module: Module to search for test classes.
  """
  for name, value in vars(module).items():
    if inspect.isclass(value):
      if issubclass(value, test_classes):
        globals()[name] = value


def run_absltests():
  """Run all absl tests in the current module."""
  # Run tests that need to be run on separate subprocesses so they do not
  # affect the other tests' environments.
  for subprocess_test in _SUBPROCESS_TESTS:
    subprocess.check_call(
        [sys.executable, os.path.join(
            os.path.dirname(__file__), subprocess_test)])

  # Can't import absl at the top of this file as it needs to be installed first.
  # pylint: disable=g-import-not-at-top.
  from absl.testing import absltest
  from absl.testing import parameterized
  # Import test modules.
  for module_name in _TEST_MODULES:
    _add_module_test_classes_to_global_namespace(
        (absltest.TestCase, parameterized.TestCase),
        importlib.import_module(module_name))
  absltest.main()


if __name__ == '__main__':
  run_absltests()
