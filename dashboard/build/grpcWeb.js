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
const webpack = require('webpack');

const { download, downloadZipAndExtract } = require('./download');
const { mkdirs, walkDirectory } = require('./file');
const { spawnSubprocess } = require('./subprocess');

// Commit referenced by gRPC 1.30.0.
const GOOGLE_APIS_VERSION = '80ed4d0bbf65d57cc267dfc63bd2584557f11f9b';
const GRPC_WEB_VERSION = '1.2.1';
const PROTOBUF_VERSION = '3.17.1';
const WEB_IMPORT_STYLE = 'commonjs';
const WEB_MODE = 'grpcweb';

/**
 * Download protobuf, gRPC tools and common protos.
 *
 * @param {string} grpcWebVersion - gRPC tools version to download.
 * @param {string} protobufVersion - protobuf tools version to download.
 * @param {string} googleApisCommit - google-apis repo commit to download.
 * @param {string} downloadDirectory - Where to download the tools.
 *
 * @returns {Promise<Object>} - Fullfills with an object that has the following
 * properties:
 * - protoc: Path to protoc binary.
 * - protocInclude: Path to protobuf include directory.
 * - protocGenGrpcWeb: Path to protoc-gen-grpc-web plugin executable for protoc.
 * - googleApisInclude: Path to google-apis directory.
 */
async function downloadGrpcTools(grpcWebVersion, protobufVersion,
                                 googleApisCommit, downloadDirectory) {
  let grpcUrlPlatform;
  let protocUrlPlatform;
  let protocExtension = '';
  switch (os.platform()) {
    case 'win32':
      grpcUrlPlatform = 'windows-x86_64.exe';
      protocUrlPlatform = 'win64.zip';
      protocExtension = '.exe'
      break;
    case 'darwin':
      grpcUrlPlatform = 'darwin-x86_64';
      protocUrlPlatform = 'osx-x86_64.zip';
      break;
    case 'linux':
      grpcUrlPlatform = 'linux-x86_64';
      protocUrlPlatform = 'linux-x86_64.zip';
      break;
    default:
      return Promise.reject(`${os.platform()} platform not supported.`)
  }
  let protocDirectory = path.join(downloadDirectory, 'protoc');
  let protocArchiveUrl =
      'https://github.com/protocolbuffers/protobuf/releases/' +
      `download/v${protobufVersion}/protoc-${protobufVersion}-` +
      `${protocUrlPlatform}`;
  let protocExecutable = path.join(protocDirectory, 'bin',
                                   'protoc' + protocExtension);
  let downloadProtoc = downloadZipAndExtract(protocArchiveUrl, protocDirectory)
      .then(() => {
        // Make sure the protoc binary exists.
        return fs.promises.access(protocExecutable, fs.constants.R_OK);
      });

  let protocGenGrpcWebUrl =
      `https://github.com/grpc/grpc-web/releases/download/${grpcWebVersion}/` +
      `protoc-gen-grpc-web-${grpcWebVersion}-${grpcUrlPlatform}`;
  let protocGenGrpcDirectory = path.join(downloadDirectory, 'protocGenGrpcWeb');
  let protocGenGrpcWebFilename =
      path.join(protocGenGrpcDirectory,
                'protoc-gen-grpc-web' + path.extname(grpcUrlPlatform));
  let downloadGrpcWeb = download(protocGenGrpcWebUrl, protocGenGrpcWebFilename)
      .then(() => {
        // Make the downloaded binary, executable.
        return fs.promises.chmod(protocGenGrpcWebFilename,
                                 fs.constants.S_IRUSR |
                                 fs.constants.S_IWUSR |
                                 fs.constants.S_IXUSR |
                                 fs.constants.S_IRGRP |
                                 fs.constants.S_IXGRP |
                                 fs.constants.S_IROTH |
                                 fs.constants.S_IXOTH);
      });

  let googleApisArchiveUrl =
      'https:///github.com/googleapis/googleapis/archive/' +
      `${googleApisCommit}.zip`;
  let googleApisDirectory = path.join(downloadDirectory, 'google-apis');
  let downloadGoogleApis = downloadZipAndExtract(
      googleApisArchiveUrl, googleApisDirectory,
      1 /* Ignore the first directory component which contains the repo
           name. */)
      .then(() => {
        // Make sure the RPC protocol is present which is common to most
        // APIs.
        return fs.promises.access(path.join(googleApisDirectory, 'google',
                                            'rpc'), fs.constants.R_OK);
      });

  await Promise.all([downloadProtoc, downloadGrpcWeb, downloadGoogleApis]);

  return Promise.resolve(
      {protoc: protocExecutable,
       protocInclude: path.join(protocDirectory, 'include'),
       protocGenGrpcWeb: protocGenGrpcWebFilename,
       googleApisInclude: googleApisDirectory});
}

/**
 * Run protoc to generate a Javascript proto interface and a gRPC stub.
 *
 * @param {string} protoFilenames - List of proto schema files containing the
 * service and it's dependent protobufs. Paths can contain a
 * ${googleApisInclude} placeholder which is expanded to the path of the
 * local google-apis directory.
 * @param {string[]} protoPaths - Paths to search for referenced proto schemas.
 * @param {string} outputDirectory - Where to write generated code.
 * @param {string} downloadDirectory - Where to download gRPC and proto tools.
 *
 * @return {Array} Array of Javascript filenames generated by protoc.
 */
async function runProtoc(protoFilenames, protoPaths, outputDirectory,
                         downloadDirectory) {
  let grpcTools = await downloadGrpcTools(
      GRPC_WEB_VERSION, PROTOBUF_VERSION, GOOGLE_APIS_VERSION,
      downloadDirectory);
  let protoPathsIncludingSystem = protoPaths.concat(
      [grpcTools.protocInclude, grpcTools.googleApisInclude]);
  let protocArgs = [
    ...( protoPathsIncludingSystem.map(protoPath => `-I=${protoPath}`) ),
    `--plugin=protoc-gen-grpc-web=${grpcTools.protocGenGrpcWeb}`,
    `--js_out=import_style=${WEB_IMPORT_STYLE}:${outputDirectory}`,
    `--grpc-web_out=import_style=${WEB_IMPORT_STYLE},` +
        `mode=${WEB_MODE}:${outputDirectory}`,
    ...( protoFilenames.map(filename => filename.replace(
        /\${googleApisInclude}/g, grpcTools.googleApisInclude)) ),
  ];
  try {
    await mkdirs(outputDirectory);
    await spawnSubprocess(grpcTools.protoc, protocArgs);
  } catch (e) {
    console.error('Failed to generate gRPC-web interface from proto ' +
                  `${protoFilename}: ${e}`);
    throw e;
  }
  return (await walkDirectory(outputDirectory)).filter(
      filename => (filename.endsWith('_grpc_web_pb.js') ||
                   filename.endsWith('_pb.js')));
}

/**
 * Generate the RPC interface.
 *
 * @param {string} protoFilenames - List of proto schema files containing the
 * service and it's dependent protobufs. Paths can contain a
 * ${googleApisInclude} placeholder which is expanded to the path of the
 * local google-apis directory.
 * @param {string[]} protoPaths - Paths to search for referenced proto schemas.
 * @param {string} downloadDirectory - Where to download gRPC and proto tools.
 * @param {string} generatedDirectory - Directory for intermediate generated
 * files.
 * @param {string} generatedRpcInterfaceFilename - Path to the generated RPC
 * interface relative to generatedDirectory.
 * @param {string} bundleFilename - Output filename for the Javascript bundle.
 * @param {string} bundleModuleVariable - Variable name used to expose the
 * bundled module.
 *
 * @returns {Promise<string>} - Fullfills with the generated interface filename
 * on success.
 */
async function generateGrpcWebInterface(
    protoFilenames, protoPaths, downloadDirectory, generatedDirectory,
    generatedRpcInterfaceFilename, bundleFilename, bundleModuleVariable) {
  try {
    await fs.promises.access(bundleFilename, fs.constants.R_OK);
    return Promise.resolve();
  } catch (e) {
    // If the output file doesn't exist generate it.
  }
  _ = await runProtoc(protoFilenames, protoPaths, generatedDirectory,
                      downloadDirectory);
  let generatedInterface = path.join(generatedDirectory,
                                     generatedRpcInterfaceFilename);
  return new Promise((resolve, reject) => {
    webpack({
      mode: 'development',
      context: path.dirname(generatedInterface),
      entry: generatedInterface,
      output: {
        filename: path.basename(bundleFilename),
        path: path.dirname(bundleFilename),
        libraryTarget: 'var',
        library: bundleModuleVariable,
      },
    }, (err, stats) => {
      if (err) {
        reject(err);
      } else if (stats.hasErrors()) {
        reject(stats.toString());
      }
      resolve(bundleFilename);
    })
  });
}

exports.downloadGrpcTools = downloadGrpcTools;
exports.runProtoc = runProtoc;
exports.generateGrpcWebInterface = generateGrpcWebInterface;
