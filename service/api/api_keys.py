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
"""Functions related to API key handling."""

from api import unique_id
from data_store import data_store

# pylint: disable=g-bad-import-order
import common.generate_protos  # pylint: disable=unused-import
import data_store_pb2


def get_or_create_api_key(datastore: data_store.DataStore,
                          project_id: str) -> str:
  """Return API key of existing project or create a new project and API key.

  If the project exists, return its API key, otherwise create a new project
  with the provided project ID and return its API key.

  Args:
    datastore: The datastore used for reading / writing the project.
    project_id: The ID of the project to get or write.
  Returns:
    The API key associated with the project.
  """
  try:
    return datastore.read_by_proto_ids(project_id=project_id).api_key
  except data_store.NotFoundError:
    # Project not found, create it.
    api_key = unique_id.generate_base64_id()
    project = data_store_pb2.Project(
        project_id=project_id, name=project_id, api_key=api_key)
    datastore.write(project)
    return api_key
