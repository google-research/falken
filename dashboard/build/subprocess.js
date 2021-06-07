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

const debug = require('debug')('falken:subprocess');
const { spawn } = require('child_process');

/**
 * Run a subprocess and execute a callback on success. If the subprocess,
 * fails exit the application.
 *
 * @param {string} command - Command to execute.
 * @param {string[]} args - Arguments to pass to the command.
 * @param {boolean} exitOnFailure - Whether to exit the process if the
 * subprocess fails.
 *
 * @returns {Promise<int>} - Promise with the exit code of the process.
 */
async function spawnSubprocess(command, args, exitOnFailure=true) {
  debug([command, ...args].join(' '));
  return new Promise((resolve, reject) => {
    spawn(command, args, { stdio: 'inherit', stderr: 'inherit',
                           shell: true }).on(
        'exit', function(exitCode) {
          if (exitCode == 0) {
            resolve(exitCode);
          } else if (exitOnFailure) {
            process.exit(exitCode);
          } else {
            reject(exitCode);
          }
        });
  });
}

exports.spawnSubprocess = spawnSubprocess;
