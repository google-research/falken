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
const debug = require('debug')('falken:download');
const { mkdirs } = require('./file');
const { https } = require('follow-redirects');
const path = require('path');
const url = require('url');
const AdmZip = require('adm-zip');

/**
 * Download a URL.
 *
 * @param {string} downloadUrl - URL to download.
 * @param {string} filename - Local file to write downloaded data to. If this
 * file exists the function does nothing.
 *
 * @returns {Promise} - Fullfills with undefined upon success.
 */
async function download(downloadUrl, filename) {
  try {
    await fs.promises.access(filename, fs.constants.R_OK);
    return Promise.resolve();
  } catch(e) {
    // Ignore missing file error.
  }
  await mkdirs(path.dirname(filename));
  let outputStream = fs.createWriteStream(filename);
  debug(`Downloading ${downloadUrl} --> ${filename}...`);
  return new Promise((resolve, reject) => {
    https.get(downloadUrl, (response) => {
      if (response.statusCode == 200 /* Status OK */) {
        response.pipe(outputStream);
        outputStream.on('close', () => {
          outputStream.close(() => {
            debug(`Download ${downloadUrl} --> ${filename} complete`);
            resolve(null);
          });
        });
      } else {
        console.error(`Failed to download ${downloadUrl} to ${filename}: ` +
                      `status = ${response.statusCode}`);
        reject(null);
      }
    }).on('error', (error) => {
      console.error(`Failed to download ${downloadUrl} to ${filename}: ` +
                    `${error}`);
      reject(null);
    });
  });
}

/**
 * Download a zip file and extract to a directory.
 *
 * Files existing at target locations will be not be extracted from the archive.
 *
 * @param {string} downloadUrl - URL of the zip file to download.
 * @param {string} extractDirectory - Where to extract the downloaded file.
 * @param {number} componentsToIgnore - Number of path components to remove
 * from each archive path prior to extraction. For example, given an archived
 * filename of a/b/c if componentsToIgnore is 1 the extracted path would be
 * b/c.
 *
 * @returns {Promise} - Fullfills with undefined upon success.
 */
async function downloadZipAndExtract(downloadUrl, extractDirectory,
                                     componentsToIgnore=0) {
  await mkdirs(extractDirectory);
  let parsedDownloadUrl = new url.URL(downloadUrl);
  let downloadFilename = path.resolve(
      __dirname, extractDirectory, path.basename(parsedDownloadUrl.pathname));
  await download(downloadUrl, downloadFilename);
  let archive = new AdmZip(downloadFilename);
  archive.getEntries().forEach((zipEntry) => {
    if (!zipEntry.isDirectory) {
      // Convert to POSIX path separators and split into components.
      let entryComponents = zipEntry.entryName.replace(/\\/g, '/').split('/');
      if (entryComponents.length <= componentsToIgnore) {
        throw (`Path of ${zipEntry.entryName} in archive ${downloadUrl} is ` +
               `has too few components ${entryComponents.length} to be ` +
               `trimmed by ${componentsToIgnore} component.`);
      }
      let targetPath = path.join(
          extractDirectory,
          path.join(...entryComponents.slice(componentsToIgnore)));
      try {
        fs.accessSync(targetPath, fs.constants.R_OK);
      } catch (e) {
        // If the file doesn't exist, extract it.
        archive.extractEntryTo(zipEntry, path.dirname(targetPath), false);
      }
    }
  });
  return Promise.resolve();
}

exports.download = download;
exports.downloadZipAndExtract = downloadZipAndExtract;
