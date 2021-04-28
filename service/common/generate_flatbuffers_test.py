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
"""Tests that flatbuffers are generated using generate_flatbuffers module."""
import glob
import os
import tempfile
from unittest import mock

from absl.testing import absltest
# Set the environment variable to false so the test can call the method to
# generate flatbuffers explicitly.
os.environ['FALKEN_AUTO_GENERATE_FLATBUFFERS'] = '0'
import generate_flatbuffers


class GenerateFlatbuffersTest(absltest.TestCase):
  """Test generate_flatbuffers module."""

  def setUp(self):
    """Setup a temporary directory for flatbuffers generation."""
    super().setUp()
    # Ignore the generated flatbuffers directory from the environment.
    os.environ['FALKEN_GENERATED_FLATBUFFERS_DIR'] = ''
    self._temp_dir = tempfile.TemporaryDirectory()

  def tearDown(self):
    """Clean up the temporary directory for flatbuffers generation."""
    super().tearDown()
    self._temp_dir.cleanup()

  def test_get_generated_flatbuffers_dir(self):
    """Get the generated flatbuffers directory."""
    self.assertEqual(
        generate_flatbuffers._FLATBUFFERS_DIR,
        os.path.basename(generate_flatbuffers.get_generated_flatbuffers_dir()))
    os.environ['FALKEN_GENERATED_FLATBUFFERS_DIR'] = (
        os.path.join('custom', 'dir'))
    self.assertEqual(
        os.path.join('custom', 'dir', generate_flatbuffers._FLATBUFFERS_DIR),
        generate_flatbuffers.get_generated_flatbuffers_dir())

  @mock.patch.object(generate_flatbuffers, 'get_generated_flatbuffers_dir')
  def test_generate_flatbuffers(self, mock_get_generated_flatbuffers_dir):
    """Verify run of generate_flatbuffers script generates fbs py files."""
    generated_dir = os.path.join(self._temp_dir.name, 'test')
    mock_get_generated_flatbuffers_dir.return_value = generated_dir

    generate_flatbuffers.generate()
    self.assertTrue(os.path.exists(generated_dir))
    self.assertNotEmpty(os.listdir(generated_dir))

    generated_flatbuffers_py = glob.glob(f'{generated_dir}/**/*.py')

    def _read_apache_license_header():
      """Read apache license header and return its contents."""
      apache_license_header = ''
      apache_license_header_file = os.path.join(os.path.dirname(__file__),
                                                'apache_license_header.txt')
      with open(apache_license_header_file, 'r') as f:
        apache_license_header = f.read()
        # Verify file contains what we expect.
        self.assertIn('Copyright 2021 Google LLC', apache_license_header)
      return apache_license_header

    apache_license_header = _read_apache_license_header()
    for file in generated_flatbuffers_py:
      with open(file, 'r') as f:
        content = f.read()
      self.assertIn(apache_license_header, content)


if __name__ == '__main__':
  absltest.main()
