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
"""Module to generate proto code for use by Falken service."""
import glob
import os
import shutil
import subprocess
import sys
import urllib.request

_PROTO_GEN_DIR = 'proto_gen_module'

_EXTERNAL_PROTOS = [(
    'https://raw.githubusercontent.com/googleapis/googleapis/common-protos-1_3_1/',
    'google/rpc/status.proto')]


def get_generated_protos_dir():
  """Returns path to the directory to contain the generated proto code."""
  return os.path.join(
      os.environ.get('FALKEN_GENERATED_PROTOS_DIR', os.getcwd()),
      _PROTO_GEN_DIR)


def get_service_dir():
  """Returns the /service directory."""
  # Since this file is in /service/common, return its parent dir.
  return os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)


def get_source_proto_dirs():
  """Returns list of directory paths containing .proto files.

  Since this file is in /service/common, go to its parent dir and go to the
  proto directory.
  """
  return [
      os.path.join(get_service_dir(), 'proto'),
      os.path.join(get_service_dir(), 'data_store', 'proto')
  ]


def download_external_protos():
  """Downloads external protos to the proto/external directory.

  Returns:
    Path to where the external protos are downloaded.
  """
  downloaded_proto_dir = os.path.join(get_service_dir(), 'proto', 'external')
  if not os.path.exists(downloaded_proto_dir):
    for proto_url, proto_path in _EXTERNAL_PROTOS:
      file_name = os.path.join(downloaded_proto_dir, proto_path)
      os.makedirs(os.path.dirname(file_name))
      urllib.request.urlretrieve(os.path.join(proto_url, proto_path), file_name)
  return downloaded_proto_dir


def generate():
  """Generates falken proto py files.

  Protos are read from falken/service/protos/ and generated in
  /proto_gen_module under the current working directory unless the parent path
  is explicitly specified in environment variable FALKEN_GENERATED_PROTOS_DIR.

  Adds the generated proto directory to the sys.path, so code subsequently can
  directly import the protos.
  """
  generated_protos_dir = get_generated_protos_dir()
  if not os.path.exists(generated_protos_dir):
    os.makedirs(generated_protos_dir)
    source_proto_dirs = get_source_proto_dirs()
    downloaded_proto_dir = download_external_protos()
    args = [
        sys.executable, '-m', 'grpc_tools.protoc',
        f'--proto_path={downloaded_proto_dir}',
        f'--python_out={generated_protos_dir}',
        f'--grpc_python_out={generated_protos_dir}'
    ] + [f'--proto_path={d}' for d in source_proto_dirs]
    for d in source_proto_dirs:
      args.extend(glob.glob(f'{d}/*.proto'))
    subprocess.run(args, check=True)
  if generated_protos_dir not in sys.path:
    sys.path.append(generated_protos_dir)
  os.environ['FALKEN_GENERATED_PROTOS_DIR'] = (
      os.path.abspath(os.path.join(generated_protos_dir, os.pardir)))


def clean_up():
  """Cleans up the generated protos directory created by generate()."""
  external_protos_dir = download_external_protos()
  if os.path.exists(external_protos_dir):
    shutil.rmtree(download_external_protos())
  generated_protos_dir = get_generated_protos_dir()
  if os.path.exists(generated_protos_dir):
    shutil.rmtree(generated_protos_dir)
  if generated_protos_dir in sys.path:
    sys.path.remove(generated_protos_dir)


if int(os.environ.get('FALKEN_AUTO_GENERATE_PROTOS', 1)):
  generate()
