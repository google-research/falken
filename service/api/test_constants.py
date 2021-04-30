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
"""Constants used by tests across the service."""

TEST_BRAIN_SPEC = r"""
    observation_spec {
      player {
        position {}
        rotation {}
      }
      global_entities {
        position {}
        rotation {}
        entity_fields {
          name: "X"
          number {
            minimum: -1.0
            maximum: 1.0
          }
        }
      }
    }
    action_spec {
      actions {
        name: "TestNumberAction"
        number {
          minimum: -5
          maximum: 5
        }
      }
      actions {
        name: "TestCategoryAction"
        category {
          enum_values: "A"
          enum_values: "B"
          enum_values: "C"
        }
      }
    }
  """
