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
"""Tests that protos are generated after importing generate_protos module."""
import glob
import os
import sys

from absl.testing import absltest
# Set the environment variable to false so the test can call the method to
# generate protos explicitly.
os.environ['FALKEN_AUTO_GENERATE_PROTOS'] = '0'
import generate_protos


class GenerateProtosTest(absltest.TestCase):
  """Test generate_protos module."""

  def setUp(self):
    super(GenerateProtosTest, self).setUp()
    # Clean up any generated proto state that may have remained from other
    # processes run before this test.
    generate_protos.clean_up()

  def tearDown(self):
    """Tear down the testing environment."""
    super(GenerateProtosTest, self).tearDown()
    generate_protos.clean_up()

  def test_generate_protos(self):
    """Import the generate_protos module and verify generation and use."""
    generate_protos.generate()
    source_protos = []
    for d in generate_protos.get_source_proto_dirs():
      source_protos += glob.glob(f'{d}/*.proto')
    generated_dir = generate_protos.get_generated_protos_dir()

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

  def test_generate_protos_cache(self):
    """Verify calling generate_proto multiple times without clean_up works."""
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
