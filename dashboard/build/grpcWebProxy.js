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
const os = require('os');
const path = require('path');
const { spawn } = require('child_process');
const url = require('url');

const { downloadZipAndExtract } = require('./download');

const GRPC_WEB_PROXY_VERSION = '0.14.0';

/**
 * Download grpcwebproxy.
 *
 * @param {string} version - Version to download.
 * @param {string} downloadDirectory - Where to download grpcwebproxy.
 *
 * @returns {Promise<Object>} - Fullfills with the filename of the downloaded
 * grpcwebproxy binary.
 */
async function downloadGrpcWebProxy(version, downloadDirectory) {
  let platform = os.platform();
  let grpcWebProxyPlatformPostfix;
  switch (os.platform()) {
    case 'win32':
      grpcWebProxyPlatformPostfix = 'win64.exe';
      break;
    case 'darwin':
      grpcWebProxyPlatformPostfix = 'osx-x86_64';
      break;
    case 'linux':
      grpcWebProxyPlatformPostfix = 'linux-x86_64';
      break;
    default:
      return Promise.reject(`${os.platform()} platform not supported.`)
  }
  let executable = `grpcwebproxy-v${version}-${grpcWebProxyPlatformPostfix}`;
  let downloadedExecutable = path.join(downloadDirectory, executable)
  _ = await downloadZipAndExtract(
      ('https://github.com/improbable-eng/grpc-web/releases/download/' +
       `v${version}/${executable}.zip`), downloadDirectory,
      componentsToIgnore=1).then(() => {
        // Make sure the downloaded binary exists.
        return fs.promises.access(downloadedExecutable, fs.constants.R_OK);
      });
  return Promise.resolve(downloadedExecutable)
}

/**
 * Launch grpcwebproxy.
 *
 * @param {string} webServerPort - Local port allowed to connect to the proxy.
 * @param {string} proxyUrl - Where to host the proxy.
 * @param {string} endpointUrl - gRPC endpoint to connect the proxy to.
 * @param {string} certFile - Public cert PEM file for the proxy.
 * @param {string} keyFile - Private cert PEM file for the proxy.
 * @param {string} downloadDirectory - Directory to download grpcwebproxy.
 *
 * @returns {child_process.ChildProcess} - grpcwebproxy process object if it
 * starts successfully.
 */
async function launchGrpcWebProxy(webServerPort, proxyUrl, endpointUrl,
                                  certFile, keyFile, downloadDirectory) {
  let grpcWebProxy = await downloadGrpcWebProxy(GRPC_WEB_PROXY_VERSION,
                                                downloadDirectory);

  let parsedEndpointUrl;
  try {
    parsedEndpointUrl = new url.URL(endpointUrl);
  } catch (e) {
    throw `Failed to parse endpointUrl ${endpointUrl}: ${e}`;
  }
  if (!parsedEndpointUrl.host) {
    throw (`endpointUrl ${endpointUrl} must specify a host component to ` +
           'connect to a gRPC endpoint.');
  }
  let parsedProxyUrl;
  try {
    parsedProxyUrl = new url.URL(proxyUrl);
  } catch (e) {
    throw `Failed to parse proxyUrl ${proxyUrl}: ${e}`;
  }
  if (!parsedProxyUrl.port) {
    throw `proxyUrl ${proxyUrl} must specify a port to host the proxy.`;
  }
  let args =
      // Cert configuration to connect to the gRPC backend.
      [`--server_tls_cert_file=${certFile}`,
       `--server_tls_key_file=${keyFile}`,
       `--backend_addr=${parsedEndpointUrl.host}`,
       '--backend_tls=true',
       // Disable TLS verification for development since certs are not
       // automatically registered with a certificate authority.
       '--backend_tls_noverify',
       // Since the server doesn't have registered certs disable TLS/SSL
       // for connects to the proxy.
       '--run_tls_server=false',
       // Host on http://localhost:port
       `--server_http_debug_port=${parsedProxyUrl.port}`,
       `--allowed_origins=http://localhost:${webServerPort}`];
  return spawn(grpcWebProxy, args, { stdio: 'inherit', stderr: 'inherit' });
}

exports.downloadGrpcWebProxy = downloadGrpcWebProxy;
exports.launchGrpcWebProxy = launchGrpcWebProxy;
