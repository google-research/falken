#!/usr/bin/python
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


"""Merge the content of multiple zip files in one zip file. """

import os
import tempfile
import zipfile

from absl import app  # type: ignore
from absl import flags  # type: ignore

FLAGS = flags.FLAGS

flags.DEFINE_spaceseplist('inputs', None, 'Zip files to merge.')
flags.DEFINE_string('output', None, 'Output zip filename.')

def main(unused_argv):
  """Merge content of given zip files into another zip file."""
  output_full_path = os.path.abspath(FLAGS.output)
  output_dir = os.path.dirname(output_full_path)
  os.makedirs(output_dir, exist_ok=True)
  with zipfile.ZipFile(
      output_full_path, 'w', zipfile.ZIP_DEFLATED) as output_file:
    for input_zipfile in FLAGS.inputs:
      with zipfile.ZipFile(input_zipfile, 'r') as input_zip:
        for input_item_info in input_zip.infolist():
          with input_zip.open(input_item_info.filename) as input_item_file:
            input_data = input_item_file.read()
            if input_item_info.filename not in output_file.namelist():
              output_file.writestr(input_item_info, input_data)
            else:
              with output_file.open(input_item_info.filename) as (
                  existing_item_file):
                if input_data != existing_item_file.read():
                      raise IOError("{} contents differs in input zip"
                                    "files {}".format(input_item_info.filename, FLAGS.inputs))

if __name__ == '__main__':
  flags.mark_flag_as_required('inputs')
  flags.mark_flag_as_required('output')
  app.run(main)
