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
"""Tests for proto_conversion."""

from unittest import mock
import uuid

from absl.testing import absltest
from api import resource_id


class ResourceIdTest(absltest.TestCase):

  @mock.patch.object(uuid, 'uuid4')
  def test_generate_resource_id(self, uuid4):
    uuid4.return_value = '4adccb90-b03b-4397-b192-ee1941fd130b'
    self.assertEqual(resource_id.generate_resource_id(),
                     '4adccb90-b03b-4397-b192-ee1941fd130b')


if __name__ == '__main__':
  absltest.main()
