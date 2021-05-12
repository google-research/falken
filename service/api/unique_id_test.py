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
"""Tests for unique_id."""

import base64
from unittest import mock
import uuid

from absl.testing import absltest
from api import unique_id


class UniqueIdTest(absltest.TestCase):

  @mock.patch.object(uuid, 'uuid4')
  def test_generate_resource_id(self, uuid4):
    uuid4.return_value = '4adccb90-b03b-4397-b192-ee1941fd130b'
    self.assertEqual(unique_id.generate_unique_id(),
                     '4adccb90-b03b-4397-b192-ee1941fd130b')

  @mock.patch.object(uuid, 'uuid4')
  @mock.patch.object(base64, 'b64encode')
  def test_generate_base64_id(self, b64encode, uuid4):
    mock_uuid4 = mock.Mock()
    mock_uuid4.bytes = b'\xbb\xc40\x19%*HP\xb5\x1b\xab\\\xae\xef\x91\x16'
    uuid4.return_value = mock_uuid4
    b64encode.return_value = b'u8QwGSUqSFC1G6tcru+RFg=='
    self.assertEqual(unique_id.generate_base64_id(),
                     b64encode.return_value.decode('utf-8'))
    uuid4.called_once_with()
    b64encode.called_once_with(mock_uuid4.bytes)


if __name__ == '__main__':
  absltest.main()
