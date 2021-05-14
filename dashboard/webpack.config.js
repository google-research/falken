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

const path = require('path');

const falkenSrcDir = path.resolve(__dirname, './gen/falken_src/falken');
const buildDir = path.resolve(__dirname, 'dist');

module.exports = {
  mode: 'development',
  entry: './src/falken.js',
  output: {
    filename: 'falken.js',
    path: buildDir,
    libraryTarget: 'var',
    library: 'FalkenLib',
  },
  devServer: {
    contentBase: buildDir,
    compress: true,
    port: 8000,
    // Workaround for https://github.com/webpack/webpack-dev-server/issues/2484
    injectClient: false,
    headers: {
      'Access-Control-Allow-Origin': 'http://localhost:8000/',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
      'Access-Control-Allow-Headers': 'X-Requested-With, content-type, Authorization'
    },
  },
};
