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
"""Installs dependencies using pip."""
import os
import subprocess
import sys

# Modules required to execute service modules and tests.
_REQUIRED_PYTHON_MODULES = [
    'absl-py',
    'tensorflow',
    'tensorflow-graphics',
    'tf-agents==0.8.0rc1',
    'grpcio-tools',
    'flatbuffers'
]


def install_dependencies():
  """Install all Python module dependencies."""
  for m in _REQUIRED_PYTHON_MODULES:
    subprocess.check_call([sys.executable, '-m', 'pip', '-q', 'install', m])


if int(os.environ.get('FALKEN_AUTO_INSTALL_DEPENDENCIES', 1)):
  install_dependencies()
