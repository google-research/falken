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

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const rimraf = require('rimraf');

const { mkdirs, walkDirectory, writeFile } = require('./file');

describe('file', function() {
  it('#mkdirs', async function() {
    let directory = path.join(__dirname, '.mkdirsTest', 'foo', 'bar', 'baz');
    try {
      await mkdirs(directory);
      fs.accessSync(directory, fs.constants.R_OK | fs.constants.W_OK);
    } finally {
      rimraf.sync(path.join(__dirname, '.mkdirsTest'));
    }
    return Promise.resolve();
  });

  it('#mkdirsExisting', async function() {
    rimraf.sync('.testmkdirsExisting');
    let directory = path.join(__dirname, '.mkdirsExistsTest',
                              'foo', 'bar', 'baz');
    await fs.promises.mkdir(directory, {recursive: true});
    try {
      await mkdirs(directory);
      fs.accessSync(directory, fs.constants.R_OK | fs.constants.W_OK);
    } finally {
      rimraf.sync(path.join(__dirname, '.mkdirsExistsTest'));
    }
    return Promise.resolve();
  });

  it('#walkDirectory', async function() {
    let tempDir = path.join(__dirname, '.walkDirectory');
    let expectedContents = [
      path.join(tempDir, 'foo'),
      path.join(tempDir, 'foo', 'bar'),
      path.join(tempDir, 'foo', 'bar', 'leaf.txt'),
      path.join(tempDir, 'test.txt'),
    ];
    try {
      for (const filename of expectedContents) {
        if (filename.endsWith('.txt')) {
          await fs.promises.writeFile(filename, 'hello');
        } else {
          await fs.promises.mkdir(filename, {recursive: true});
        }
      }
      let contents = await walkDirectory(tempDir);
      assert.deepEqual(contents, expectedContents);
    } finally {
      rimraf.sync(tempDir);
    }
  });

  it('#writeFile', async function() {
    let testFile = path.join(__dirname, '.writeFileTest/foo/bar/hello');
    let content = 'hello\nworld\n';
    try {
      await writeFile(testFile, content);
      let readContent = await fs.promises.readFile(testFile);
      assert.equal(content, readContent);
    } finally {
      rimraf.sync(testFile);
    }
  });
});
