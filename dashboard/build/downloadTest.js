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
const nock = require('nock');
const path = require('path');
const rimraf = require('rimraf');

const { download, downloadZipAndExtract } = require('./download');
const { walkDirectory } = require('./file');

describe('download', function() {
  var server;

  beforeEach(function() {
    server = nock('https://fake.server.com');
  });

  afterEach(function() {
    nock.cleanAll();
  });

  it('#downloadNonExistant', async function() {
    let targetFile = path.join(__dirname, '.downloadNonExistantTest');
    server.get('/some/file.json').reply(404, 'not found');
    try {
      await download('https://fake.server.com/some/file.json', targetFile);
      try {
        fs.accessSync(targetFile, fs.constants.R_OK | fs.constants.W_OK);
        assert.fail(`${targetFile} was created from an invalid URL.`);
      } catch (e) {
        // The target file should not exist.
      }
    } catch (e) {
      // An exception should be thrown as the URL does not exist.
    } finally {
      rimraf.sync(targetFile);
    }
    return Promise.resolve();
  });

  it('#downloadExists', async function() {
    let targetFile = path.join(__dirname, '.downloadExistsTest');
    let expectedContent = '{\n  "hello": "world"\n}\n';
    server.get('/some/file.json').reply(200, expectedContent);
    try {
      await download('https://fake.server.com/some/file.json', targetFile);
      let content = await fs.promises.readFile(targetFile);
      assert.equal(content, expectedContent);
    } finally {
      rimraf.sync(targetFile);
    }
    return Promise.resolve();
  });

  it('#downloadZipAndExtract', async function() {
    let targetDirectory = path.resolve(__dirname, '.downloadZipAndExtract');
    let expectedContents = [
      path.join(targetDirectory, 'file.zip'),
      path.join(targetDirectory, 'foo'),
      path.join(targetDirectory, 'foo', 'bar'),
      path.join(targetDirectory, 'foo', 'bar', 'hello.txt'),
      path.join(targetDirectory, 'foo', 'goodbye.txt'),
    ];
    server.get('/some/file.zip').reply(
        200, await fs.promises.readFile(path.resolve(__dirname, 'test_data',
                                                     'test.zip')));
    try {
      await downloadZipAndExtract('https://fake.server.com/some/file.zip',
                                  targetDirectory);
      let contents = await walkDirectory(targetDirectory);
      assert.deepEqual(contents, expectedContents);
    } finally {
      rimraf.sync(targetDirectory);
    }
    return Promise.resolve();
  });

  it('#downloadZipAndExtractIgnorePathComponents', async function() {
    let targetDirectory = path.resolve(__dirname, '.downloadZipAndExtract');
    let expectedContents = [
      path.join(targetDirectory, 'bar'),
      path.join(targetDirectory, 'bar', 'hello.txt'),
      path.join(targetDirectory, 'file.zip'),
      path.join(targetDirectory, 'goodbye.txt'),
    ];
    server.get('/some/file.zip').reply(
        200, await fs.promises.readFile(path.resolve(__dirname, 'test_data',
                                                     'test.zip')));
    try {
      await downloadZipAndExtract('https://fake.server.com/some/file.zip',
                                  targetDirectory, componentsToIgnore=1);
      let contents = await walkDirectory(targetDirectory);
      assert.deepEqual(contents, expectedContents);
    } finally {
      rimraf.sync(targetDirectory);
    }
    return Promise.resolve();
  });

  it('#downloadZipAndExtractIgnoreTooManyPathComponents', async function() {
    let targetDirectory = path.resolve(__dirname, '.downloadZipAndExtract');
    server.get('/some/file.zip').reply(
        200, await fs.promises.readFile(path.resolve(__dirname, 'test_data',
                                                     'test.zip')));
    try {
      await downloadZipAndExtract('https://fake.server.com/some/file.zip',
                                  targetDirectory, componentsToIgnore=2);
      assert.fail('Should have failed.');
    } catch (e) {
      // Should fail due to ignoring too many path components.
    } finally {
      rimraf.sync(targetDirectory);
    }
    return Promise.resolve();
  });
});
