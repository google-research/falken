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
# pylint: disable=g-bad-import-order, g-import-not-at-top, reimported
"""Tests that protos are generated after using the generate_protos module."""
import glob
import os
import subprocess
import sys
import tempfile
from unittest import mock

from absl.testing import absltest
# Set the environment variable to false so the test can call the method to
# generate protos explicitly.
os.environ['FALKEN_AUTO_GENERATE_PROTOS'] = '0'
import generate_protos


class GenerateProtosTest(absltest.TestCase):
  """Test generate_protos module."""

  def setUp(self):
    super().setUp()
    # Clean up any generated proto state that may have remained from other
    # processes run before this test.
    generate_protos.clean_up()
    os.environ['FALKEN_GENERATED_PROTOS_DIR'] = ''
    self._temp_dir = tempfile.TemporaryDirectory()

  def tearDown(self):
    """Tear down the testing environment."""
    super().tearDown()
    self._temp_dir.cleanup()
    generate_protos.clean_up()

  def test_get_generated_protos_dir(self):
    """Get the generated protos directory."""
    self.assertEqual(
        generate_protos._PROTO_GEN_DIR,
        os.path.basename(generate_protos.get_generated_protos_dir()))
    os.environ['FALKEN_GENERATED_PROTOS_DIR'] = (
        os.path.join('custom', 'dir'))
    self.assertEqual(
        os.path.join('custom', 'dir', generate_protos._PROTO_GEN_DIR),
        generate_protos.get_generated_protos_dir())

  @mock.patch.object(generate_protos, 'get_generated_protos_dir')
  @mock.patch.object(generate_protos, 'clean_up')
  @mock.patch.object(subprocess, 'check_call')
  def test_generate_protos_failed(self, mock_check_call, mock_clean_up,
                                  mock_get_generated_protos_dir):
    """Call the generate method and make sure it cleans up on failure."""
    mock_get_generated_protos_dir.return_value = os.path.join(
        self._temp_dir.name, generate_protos._PROTO_GEN_DIR)
    mock_check_call.side_effect = subprocess.CalledProcessError(1, 'fake')
    with self.assertRaises(subprocess.CalledProcessError):
      generate_protos.generate()
    mock_clean_up.called_once()

  @mock.patch.object(generate_protos, 'get_generated_protos_dir')
  def test_generate_protos(self, mock_get_generated_protos_dir):
    """Call the generate method and verify generation and use."""
    generated_dir = os.path.join(self._temp_dir.name,
                                 generate_protos._PROTO_GEN_DIR)
    mock_get_generated_protos_dir.return_value = generated_dir
    generate_protos.generate()
    source_protos = []
    for d in generate_protos.get_source_proto_dirs():
      source_protos += glob.glob(f'{d}/*.proto')

    def extract_generated_proto_path(source_proto_path, generated_dir):
      """Create generated proto path with the proto name.

      This can then be concatenated with a suffix like .py, _pb2.py,
      or _pb2_grpc.py.

      Args:
        source_proto_path: Proto path of the source proto file.
        generated_dir: Directory containing the generated protos.

      Returns:
        String that follows
          /generated_dir/source_proto's proto name without extension.
          e.g. '/falken/service/proto_gen_module/brain'
      """
      return os.path.join(generated_dir,
                          os.path.basename(source_proto_path).split('.')[0])

    all_expected_protos = ([
        extract_generated_proto_path(proto_name, generated_dir) + '_pb2.py'
        for proto_name in source_protos
    ] + [
        extract_generated_proto_path(proto_name, generated_dir) + '_pb2_grpc.py'
        for proto_name in source_protos
    ])

    generated_protos = glob.glob(f'{generated_dir}/*.py')
    self.assertSameElements(generated_protos, all_expected_protos)
    import primitives_pb2
    self.assertIsNotNone(primitives_pb2.Rotation())

  @mock.patch.object(generate_protos, 'get_generated_protos_dir')
  def test_generate_protos_cache(self, mock_get_generated_protos_dir):
    """Verify calling generate_proto multiple times without clean_up works."""
    mock_get_generated_protos_dir.return_value = os.path.join(
        self._temp_dir.name, generate_protos._PROTO_GEN_DIR)
    # First, verify that importing brain_pb2 before generate_protos is called
    # raises a ModuleNotFoundError.
    with self.assertRaises(ModuleNotFoundError):
      import brain_pb2
    old_sys_path = sys.path[:]

    # Call generate for the first time.
    generate_protos.generate()
    import brain_pb2
    self.assertIsNotNone(brain_pb2.Brain())

    # Restore the sys.path to what it was before calling generate().
    sys.path = old_sys_path

    # Because the sys.path does not contain the path to the generated protos,
    # snapshot_pb2 cannot be found.
    with self.assertRaises(ModuleNotFoundError):
      import snapshot_pb2

    # Generate the protos again, which does not actually re-generate the protos,
    # but adds the path to the sys.path. Now snapshot_pb2 can be found.
    generate_protos.generate()
    import snapshot_pb2
    self.assertIsNotNone(snapshot_pb2.Snapshot())


if __name__ == '__main__':
  absltest.main()
