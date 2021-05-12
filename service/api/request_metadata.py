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
"""Handles metadata from RPC contexts."""


def extract_metadata_value(context, key):
  """Extract value from server-side context metadata given a key.

  Args:
    context: RPC context containing metadata such as the user-agent.
    key: Key existing in the metadata, such as 'user-agent'.

  Returns:
    Value string, e.g. 'grpc-c/16.0.0 (linux; chttp2)'
  """
  metadata = context.invocation_metadata()
  value_list = [kv[1] for kv in metadata if kv[0] == key]
  if value_list:
    return value_list[0]
  return ''
