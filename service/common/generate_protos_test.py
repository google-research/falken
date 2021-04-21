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
# pylint: disable=g-bad-import-order, g-import-not-at-top
"""Tests that protos are generated after importing generate_protos module."""
import glob
import os

from absl.testing import absltest
# Set the environment variable to false so the test can call the method to
# generate protos explicitly.
os.environ['FALKEN_GENERATE_PROTOS'] = '0'
import common.generate_protos


class GenerateProtosTest(absltest.TestCase):
  """Test generate_protos module."""

  def tearDown(self):
    """Tear down the testing environment."""
    super(GenerateProtosTest, self).tearDown()
    common.generate_protos.clean_up()

  def test_generate_protos(self):
    """Import the generate_protos module and verify generation and use."""
    common.generate_protos.generate()
    source_protos = glob.glob(
        f'{common.generate_protos.get_source_proto_dir()}/*.proto')
    generated_dir = common.generate_protos.get_generated_protos_dir()

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
    import brain_pb2
    self.assertIsNotNone(brain_pb2.Brain())


if __name__ == '__main__':
  absltest.main()
