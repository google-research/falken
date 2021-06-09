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

"""Used in GithubActions to extract the release name from the full tag ref"""

import argparse
import logging
import os
import typing
import sys

# pylint: disable=g-import-not-at-top
# pylint: disable=W0403
sys.path.append(os.path.dirname(__file__))
import shell
# pylint: enable=g-import-not-at-top
# pylint: enable=W0403

# Possible returning values of the script.
EXIT_SUCCESS = 0
EXIT_FAILURE = 1

def parse_arguments(args: typing.List[str]) -> argparse.Namespace:
  """Build an argument parser for the application.

  Args:
    args: Arguments to parse.

  Returns:
    A namespace populated with parsed arguments.
  """
  parser = argparse.ArgumentParser(
      description='Extract the release name from the full tag ref.',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument(
      '--valid-characters',
      default='01234567890.',
      help=('Valid set of characters that can be used in the release name.'))
  parser.add_argument(
      'input',
      help=('Tag ref to be parsed to extract the release name'))
  return parser.parse_args(args)


def process_ref(args: argparse.Namespace) -> bool:
  """Parses the tag ref string to extract the release name, and validates it.

  Args:
    args: A namespace populated with parsed arguments.

  Returns:
    A boolean valued True if a valid release name was found, False otherwise.
  """
  valid_characters = args.valid_characters
  full_tag_ref = args.input

  release_name = full_tag_ref.split("/")[-1]
  valid_char_set = set(valid_characters)

  if not (set(release_name) <= valid_char_set):
    logging.error('The extracted release name "{}" contains invalid characters.'
        .format(release_name))
    logging.error('Valid characters are "{}"'.format(valid_characters))
    return False

  print(release_name)
  return True

def main():
  """Extract the release name from the full tag ref.

  Returns:
    EXIT_SUCCESS when parsing was successful and the release name is valid.
    EXIT_FAILURE otherwise.
  """
  logging.getLogger().setLevel(logging.INFO)

  args = parse_arguments(sys.argv[1:])
  if process_ref(args):
    return EXIT_SUCCESS
  return EXIT_FAILURE

if __name__ == '__main__':
  sys.exit(main())
