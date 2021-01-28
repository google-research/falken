/**
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

const fs = require('fs');
const path = require('path');

/**
 * Recursively create a directory if it doesn't exist.
 *
 * @param {string} directory - Directory to create.
 *
 * @returns {Promise} - Fullfills with undefined upon success.
 */
async function mkdirs(directory) {
  let createDirectory = false;
  try {
    await fs.promises.access(directory, fs.constants.R_OK | fs.constants.W_OK);
  } catch (e) {
    createDirectory = true;
  }
  if (createDirectory) {
    await fs.promises.mkdir(directory, {recursive: true});
  }
  return Promise.resolve();
}

/**
 * Recursively list files in a directory.
 *
 * @param {string} directory - Directory to recursively list.
 *
 * @returns {Promise<string[]>} - Fullfills with a list of files under the
 * specified directory.
 */
async function walkDirectory(directory) {
  let files = [];
  for (const directoryEntry of
       await fs.promises.readdir(directory, {withFileTypes: true})) {
    let filename = path.resolve(directory, directoryEntry.name);
    files.push(filename);
    if (directoryEntry.isDirectory()) {
      files.push(...await walkDirectory(filename));
    }
  }
  return Promise.resolve(files.sort());
}

/**
 * Write a text file creating intermediate directories if required.
 *
 * @param {string} filename - File to write.
 * @param {string} contents - Text to write to the file.
 *
 * @returns {Promise} - Fullfills with the absolute path to the written file
 * upon success.
 */
async function writeFile(filename, contents) {
  await mkdirs(path.dirname(filename));
  await fs.promises.writeFile(filename, contents);
  return Promise.resolve(path.resolve(__dirname, filename));
}

exports.mkdirs = mkdirs;
exports.walkDirectory = walkDirectory;
exports.writeFile = writeFile;
