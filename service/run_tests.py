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
import multiprocessing
import os
import re
import subprocess
import sys

# We disable auto-generation of protos and flatbuffers, since they will be
# manually generated in the main function.
os.environ['FALKEN_AUTO_GENERATE_PROTOS'] = '0'
from common import generate_flatbuffers  # pylint: disable=g-import-not-at-top,unused-import
from common import generate_protos  # pylint: disable=g-import-not-at-top
from common import pip_installer  # pylint: disable=unused-import

# These imports must be placed after the pip_installer,
# to ensure absl is installed.
# pylint: disable=g-bad-import-order.
from absl import app
from absl import flags
from absl import logging
from absl.testing import absltest
from absl.testing import parameterized

flags.DEFINE_string(
    'modules_to_test', '.*',
    'Modules to test regex pattern; by default, test all modules.')

flags.DEFINE_integer(
    'num_shards', 10,
    'Number of tests to execute in parallel (shards).')


FLAGS = flags.FLAGS

# Add search paths for all modules.
_SERVICE_MODULE_PATHS = ['data_store', 'log', 'learner', 'learner/brains']
sys.path.extend(
    [os.path.join(os.path.dirname(__file__), p) for p in _SERVICE_MODULE_PATHS]
)

_DEFAULT_SUBPROCESS_TESTS = [
    'launcher_test',
    'common.generate_flatbuffers_test',
    'common.generate_protos_test',
    'common.pip_installer_test',
    'tools.generate_sdk_configuration_test',
]

_DEFAULT_TEST_MODULES = [
    'api.create_brain_handler_test',
    'api.create_session_handler_test',
    'api.data_cache_test',
    'api.get_handler_test',
    'api.get_session_count_handler_test',
    'api.model_selector_test',
    'api.model_selection_record_test',
    'api.list_handler_test',
    'api.stop_session_handler_test',
    'api.submit_episode_chunks_handler_test',
    'api.falken_service_test',
    'api.proto_conversion_test',
    'api.request_metadata_test',
    'api.sampling.online_eval_sampling_test',
    'api.unique_id_test',
    'data_store.assignment_monitor_test',
    'data_store.data_store_test',
    'data_store.file_system_test',
    'data_store.resource_id_test',
    'data_store.resource_store_test',
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
    'learner.assignment_processor_test',
    'learner.data_fetcher_test',
    'learner.file_system_test',
    'learner.model_exporter_test',
    'learner.model_manager_test',
    'learner.stats_collector_test',
    'learner.storage_test',
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


def run_absltests(shard_index=None):
  """Run all absl tests in the current module and selected shard.

  Args:
    shard_index: If test is run in parallel with sharding, this specifies the
      integer index of the current shard. If not set, all tests will be run.
  Returns:
    An integer representing a unix status code.
  """
  if (shard_index is not None) != bool(FLAGS.num_shards):
    raise ValueError(
        '"shard_index" should be provided exactly if "num_shards" flag is set.')
  if shard_index is not None:
    logging.info('Running test shard %d', shard_index)
  # Filter out the modules using --modules_to_test.
  modules_to_test_re = re.compile(FLAGS.modules_to_test)
  def filter_tests(tests):
    return [t for t in tests if modules_to_test_re.match(t)]
  subprocess_tests = filter_tests(_DEFAULT_SUBPROCESS_TESTS)
  test_modules = filter_tests(_DEFAULT_TEST_MODULES)
  if not subprocess_tests and not test_modules:
    raise ValueError(f'No tests match {FLAGS.modules_to_test}.')

  # Run tests that need to be run on separate subprocesses so they do not
  # affect the other tests' environments.
  for i, subprocess_test in enumerate(subprocess_tests):
    if shard_index is None or i % FLAGS.num_shards == shard_index:
      subprocess.check_call(
          [sys.executable, '-m', subprocess_test],
          cwd=os.path.dirname(__file__))

  # Import test modules.
  for module_name in test_modules:
    _add_module_test_classes_to_global_namespace(
        (absltest.TestCase, parameterized.TestCase),
        importlib.import_module(module_name))

  if shard_index is not None:
    # Setting these two flags will use the bazel sharding integration
    # inside absltest in order to shard the tests.
    os.environ['TEST_TOTAL_SHARDS'] = str(FLAGS.num_shards)
    os.environ['TEST_SHARD_INDEX'] = str(shard_index)

  try:
    absltest.main()
  except SystemExit as e:
    # We need to catch system exit here, to make this function work with
    # multiprocessing.
    return e.code


def main(unused_argv):
  # Regenerate protos to ensure the tests start with a clean environment.
  generate_protos.clean_up()
  generate_protos.generate()
  if not FLAGS.num_shards:
    sys.exit(run_absltests())
  else:
    with multiprocessing.Pool(FLAGS.num_shards) as pool:
      result_statuses = pool.map(run_absltests, range(FLAGS.num_shards))

    failing_shards = []
    for i, status_code in enumerate(result_statuses):
      if status_code:
        failing_shards.append(i)
    if failing_shards:
      logging.info('FAILED. Failing shard indices: %s', failing_shards)
      sys.exit(1)
    else:
      logging.info('OK. All shards succeeded.')
      sys.exit(0)


if __name__ == '__main__':
  app.run(main)
