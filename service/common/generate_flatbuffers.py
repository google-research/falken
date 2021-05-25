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
"""Module to generate flatbuffer code for use by Falken service.

Rather than generating flatbuffers at each use, we commit generated_flatbuffers
directory in the repository. If it must be regenerated, first remove the
generated_flatbuffers directory, and run the code as normal, imported as a
module in the code that needs the flatbuffers.
"""
import glob
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

_FLATBUFFERS_DIR = 'generated_flatbuffers'

_EXTERNAL_FLATBUFFERS = [(
    'https://raw.githubusercontent.com/tensorflow/tensorflow/v2.5.0-rc1/',
    'tensorflow/lite/schema/schema.fbs')]

_FLATBUFFERS_REPO = (
    'https://github.com/google/flatbuffers/archive/refs/tags/v1.12.0.tar.gz')


def get_generated_flatbuffers_dir():
  """Returns path to the directory to contain the generated flatbuffers code.

  Returns:
    Path string, defaults to falken/flatbuffers.
  """
  return os.path.normpath(os.path.join(
      os.environ.get('FALKEN_GENERATED_FLATBUFFERS_DIR',
                     os.path.dirname(os.path.dirname(
                         os.path.abspath(__file__)))),
      _FLATBUFFERS_DIR))


def download_external_fbs(temp_dir):
  """Downloads external flatbuffer schemas to the fbs directory.

  Args:
    temp_dir: Temporary directory for installing temporary flatbuffer files,
      such as the downloaded external .fbs files.

  Returns:
    Path to where the flatbuffer schema are downloaded.
  """
  downloaded_fbs_dir = os.path.join(temp_dir, 'downloaded_flatbuffers')
  if not os.path.exists(downloaded_fbs_dir):
    for fbs_url, fbs_path in _EXTERNAL_FLATBUFFERS:
      file_name = os.path.join(downloaded_fbs_dir, fbs_path)
      os.makedirs(os.path.dirname(file_name))
      urllib.request.urlretrieve(os.path.join(fbs_url, fbs_path), file_name)
  return os.path.normpath(downloaded_fbs_dir)


def install_flatc(temp_dir):
  """Installs flatbuffers compiler, flatc.

  This requires us to download the flatbuffers repo, and run cmake.

  Args:
    temp_dir: Temporary directory for installing temporary flatbuffer files,
      such as the flatbuffers repository.

  Returns:
    Path to the downloaded and extracted repository.
  """
  flatbuffers_download_dir = os.path.join(temp_dir, 'flatbuffers')
  flatbuffers_repo_dir = os.path.abspath(os.path.join(
      flatbuffers_download_dir, 'flatbuffers-1.12.0'))
  if not os.path.exists(flatbuffers_download_dir):
    os.makedirs(flatbuffers_download_dir)
    file_name, _ = urllib.request.urlretrieve(
        _FLATBUFFERS_REPO, os.path.join(flatbuffers_download_dir,
                                        'flatbuffers.tar.gz'))
    flatbuffer_tar = tarfile.open(name=file_name)
    flatbuffer_tar.extractall(path=flatbuffers_download_dir)
    subprocess.check_call(
        ['cmake', '.'], cwd=flatbuffers_repo_dir)
    subprocess.check_call(
        ['cmake', '--build', '.', '--target', 'flatc', '-j'],
        cwd=flatbuffers_repo_dir)
  return flatbuffers_repo_dir


def write_apache_license_header(generated_fbs_dir):
  """Update generated flatbuffer py files with apache license header."""
  generated_py_files = glob.glob(f'{generated_fbs_dir}/**/*.py', recursive=True)
  apache_license_header = ''
  apache_license_header_file = os.path.join(os.path.dirname(__file__),
                                            'apache_license_header.txt')
  with open(apache_license_header_file, 'r') as f:
    apache_license_header = f.read()
  for file in generated_py_files:
    with open(file, 'r') as f:
      content = f.read()
    with open(file, 'w') as f:
      f.write(apache_license_header + content)


def generate():
  """Generates flatbuffer python files.

  Flatbuffer schema files are read from falken/service/fbs/ and generated in
  /fbs_dir under the current working directory unless the parent path is
  explicitly specified in environment variable FALKEN_GENERATED_FLATBUFFERS_DIR.

  Also inserts the apache license text at the top of each generated flatbuffer
  python file.
  """
  generated_fbs_dir = get_generated_flatbuffers_dir()
  if not os.path.exists(generated_fbs_dir):
    temp_dir = tempfile.mkdtemp()
    flatc = os.path.normpath(
        os.path.join(
            install_flatc(temp_dir),
            'Debug' if platform.system() == 'Windows' else '',
            'flatc.exe' if platform.system() == 'Windows' else 'flatc'))
    generated_fbs_dir = get_generated_flatbuffers_dir()
    if not os.path.exists(generated_fbs_dir):
      os.makedirs(generated_fbs_dir)
    downloaded_fbs_dir = download_external_fbs(temp_dir)
    args = [
        flatc, '--python',
        '-o', generated_fbs_dir,
        '-I', downloaded_fbs_dir,
        '--gen-object-api',
    ]

    args.extend(glob.glob(f'{downloaded_fbs_dir}/**/*.fbs', recursive=True))
    subprocess.run(args, check=True)

    shutil.rmtree(temp_dir)
    write_apache_license_header(generated_fbs_dir)

  os.environ['FALKEN_GENERATED_FLATBUFFERS_DIR'] = (
      os.path.abspath(os.path.join(generated_fbs_dir, os.pardir)))
  sys.path.append(generated_fbs_dir)


if int(os.environ.get('FALKEN_AUTO_GENERATE_FLATBUFFERS', 1)):
  generate()
