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
import re
import subprocess
import sys
from common import pip_installer  # pylint: disable=unused-import

# These imports must be placed after the pip_installer,
# to ensure absl is installed.
# pylint: disable=g-bad-import-order.
from absl import flags
from absl.testing import absltest
from absl.testing import parameterized

flags.DEFINE_string(
    'modules_to_test', '.*',
    'Modules to test regex pattern; by default, test all modules.')

FLAGS = flags.FLAGS

# Add search paths for all modules.
_SERVICE_MODULE_PATHS = ['data_store', 'log', 'learner', 'learner/brains']
sys.path.extend(
    [os.path.join(os.path.dirname(__file__), p) for p in _SERVICE_MODULE_PATHS]
)

_DEFAULT_SUBPROCESS_TESTS = [
    'launcher_test.py',
    'common/generate_flatbuffers_test.py',
    'common/generate_protos_test.py',
    'common/pip_installer_test.py',
    'tools/generate_sdk_configuration_test.py',
]

_DEFAULT_TEST_MODULES = [
    'api.create_brain_handler_test',
    'api.list_brains_handler_test',
    'api.falken_service_test',
    'api.proto_conversion_test',
    'api.resource_id_test',
    'data_store.data_store_test',
    'data_store.file_system_test',
    'data_store.resource_id_test',
    'learner.brains.action_postprocessor_test',
    'learner.brains.brain_cache_test',
    'learner.brains.continuous_imitation_brain_test',
    'learner.brains.demonstration_buffer_test',
    'learner.brains.egocentric_test',
    'learner.brains.eval_datastore_test',
    'learner.brains.imitation_loss_test',
    'learner.brains.layers_test',
    'learner.brains.networks_test',
    'learner.brains.numpy_replay_buffer_test',
    'learner.brains.observation_preprocessor_test',
    'learner.brains.policies_test',
    'learner.brains.quaternion_test',
    'learner.brains.saved_model_to_tflite_model_test',
    'learner.brains.specs_test',
    'learner.brains.tensor_nest_test',
    'learner.brains.weights_initializer_test',
    'learner.data_fetcher_test',
    'learner.file_system_test',
    'learner.model_manager_test',
    'learner.stats_collector_test',
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

  # Filter out the modules using --modules_to_test.
  FLAGS(sys.argv)
  modules_to_test_re = re.compile(FLAGS.modules_to_test)
  def filter_tests(tests):
    return [t for t in tests if modules_to_test_re.match(t)]
  subprocess_tests = filter_tests(_DEFAULT_SUBPROCESS_TESTS)
  test_modules = filter_tests(_DEFAULT_TEST_MODULES)
  if not subprocess_tests and not test_modules:
    raise ValueError(f'No tests match {FLAGS.modules_to_test}.')

  # Run tests that need to be run on separate subprocesses so they do not
  # affect the other tests' environments.
  for subprocess_test in subprocess_tests:
    subprocess.check_call(
        [sys.executable, os.path.join(
            os.path.dirname(__file__), subprocess_test)])

  # Import test modules.
  for module_name in test_modules:
    _add_module_test_classes_to_global_namespace(
        (absltest.TestCase, parameterized.TestCase),
        importlib.import_module(module_name))
  absltest.main()


if __name__ == '__main__':
  run_absltests()
