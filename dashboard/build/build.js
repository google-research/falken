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
const yargs = require('yargs/yargs');

const { launchGrpcWebProxy } = require( './grpcWebProxy');
const { generateGrpcWebInterface } = require('./grpcWeb');
const { writeFile } = require('./file');
const { spawnSubprocess } = require('./subprocess');

// Directory that contains the dashboard.
const dashboardDirectory = path.resolve(__dirname, '..');
// Generated dashboard files directory.
const dashboardGenDirectory = path.join(dashboardDirectory, 'gen');
// Directory that contains built files for distribution.
const dashboardDistDirectory = path.join(dashboardDirectory, 'dist');
// Directory that contains the service.
const serviceDirectory = path.resolve(dashboardDirectory, '..', 'service');
// Directory containing the RPC interface for the service.
const serviceProtoInterfaceDirectory = path.join(serviceDirectory, 'proto');

/**
 * Parse command line arguments.
 *
 * @returns {Object} Where each argument value accessible as a property.
 */
function parseArguments(argv) {
  // NOTE: Number options are treated as strings so that it's possible to
  // expand node environment variables.
  let options = {
    'serve_mode': {
      description: ('Whether to run a local webserver after building. ' +
                    'watch rebuilds if source changes are detected, ' +
                    'serve just runs a local web server.'),
      choices: ['watch', 'serve'],
    },
    'serve_port': {
      type: 'string',
      description: ('localhost port used to run a webserver when ' +
                    'serve_mode is "serve"'),
      default: '8000',
      convert_to: 'number',
    },
    'endpoint_url': {
      type: 'string',
      description: 'URL to connect to Falken service.',
      default: 'http://localhost:50051',
    },
    'proxy_url': {
      type: 'string',
      description: 'URL to host the Falken service proxy.',
      default: 'http://localhost:50052',
    },
    'cert_file': {
      type: 'string',
      description: 'Public cert PEM file for the proxy.',
      default: path.join(serviceDirectory, 'cert.pem'),
    },
    'key_file': {
      type: 'string',
      description: 'Private cert PEM file for the proxy.',
      default: path.join(serviceDirectory, 'key.pem'),
    },
    'deploy': {
      description: 'Channel to deploy to.',
      choices: ['preview', 'public'],
    }
  };

  let args = yargs(argv);
  for (const optionName of Object.keys(options)) {
    args.option(optionName, options[optionName]);
  }
  let parsedArgs = args.argv;
  // Expand string options that reference npm environment variables.
  for (const optionName of Object.keys(options)) {
    let value = parsedArgs[optionName];
    if (typeof value == 'string' && value.startsWith('$npm_')) {
      parsedArgs[optionName] = process.env[value.slice(1)];
    }
  }
  // Convert any string arguments that should be numbers.
  for (const optionName of Object.keys(options)) {
    let value = parsedArgs[optionName];
    if (options[optionName].convert_to == 'number' && value) {
      parsedArgs[optionName] = parseInt(value);
    }
  }
  return parsedArgs;
}

/**
 * Generate service endpoint configuration.
 *
 * @param {string} endpointUrl - URL used to connect to the gRPC or proxy
 * endpoint.
 *
 * @returns {Promise<string>} - Fullfills with the generated config on success.
 */
async function generateEndpointConfiguration(endpointUrl) {
  let devUrl = endpointUrl;
  let prodUrl = endpointUrl;
  const config = `
/**
 * Get the URL for the endpoint.
 *
 * @param {boolean} isDev - Whether to return the development endpoint.
 *
 * @returns URL of the Falken service.
 */
function getServiceUrl(isDev) {
  return isDev ? '${devUrl}' : '${prodUrl}';
}

export { getServiceUrl }
`;
  return writeFile(path.join(dashboardGenDirectory, 'endpoint.js'), config);
}

/**
 * Build the site.
 *
 * @param {string} serveMode - Can be 'watch' to build and rebuild on
 * local changes, 'serve' to launch a local webserver and null to
 * just build.
 * @param {number} port - Port to run local server.
 *
 * @returns {Promise} - Fullfills with undefined upon success.
 */
async function build(serveMode, port) {
  const config = `
module.exports = {
  mode: 'development',
  context: '${dashboardDirectory}',
  entry: '${path.resolve(dashboardDirectory, 'src', 'falken.js')}',
  output: {
    filename: 'falken.js',
    path: '${dashboardDistDirectory}',
    libraryTarget: 'var',
    library: 'FalkenLib'
  },
  devServer: {
    contentBase: '${dashboardDistDirectory}',
    compress: true,
    port: ${port},
    // Workaround for https://github.com/webpack/webpack-dev-server/issues/2484
    injectClient: false,
    headers: {
      'Access-Control-Allow-Origin': 'http://localhost:${port}/',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
      'Access-Control-Allow-Headers': (
        'X-Requested-With, content-type, Authorization')
    }
  }
};
`;
  let configFile = path.join(dashboardGenDirectory, 'webpack.config.js');
  _ = await writeFile(configFile, config);
  let webpackArgs = ['webpack'];
  if (serveMode == 'watch') {
    webpackArgs.push('--watch');
  } else if (serveMode == 'serve') {
    webpackArgs.push('serve');
  }
  webpackArgs.push('-c', configFile);
  return spawnSubprocess('npx', webpackArgs);
}

/**
 * Publish the built site if deploy is 'public' or 'preview' otherwise just
 * call onSuccess.
 *
 * @param {string} deploy - Environment to deploy to. This can be
 * 'public', 'preview' or null / undefined.
 *
 * @returns {Promise} - Fullfills with undefined upon success.
 */
async function publish(deploy) {
  if (deploy == 'public') {
    return spawnSubprocess('npx', ['firebase', 'deploy', '--only hosting']);
  } else if (deploy == 'preview') {
    return spawnSubprocess('npx', ['firebase', 'hosting:channel:deploy',
                                   'preview']);
  }
  return Promise.resolve();
}

/**
 * Build and optionally deploy the site.
 */
async function main() {
  let argv = parseArguments(process.argv);
  _ = await generateEndpointConfiguration(argv.proxy_url);
  _ = await generateGrpcWebInterface(
      fs.readdirSync(serviceProtoInterfaceDirectory)
        .map(filename => path.join(serviceProtoInterfaceDirectory, filename))
        .concat([path.join('${googleApisInclude}', 'google', 'rpc',
                           'status.proto')]),
      [serviceProtoInterfaceDirectory],
      path.join(dashboardDirectory, '.grpcWeb'),
      dashboardGenDirectory, 'falken_service_grpc_web_pb.js',
      path.join(dashboardDistDirectory, 'falken_grpc-bundle.js'),
      'falkenProto');
  if (argv.serve_mode == 'serve') {
    _ = launchGrpcWebProxy(argv.serve_port, argv.proxy_url, argv.endpoint_url,
                           argv.cert_file, argv.key_file,
                           path.join(dashboardDirectory, '.grpcWebProxy'));
  }
  _ = await build(argv.serve_mode, argv.serve_port);
  _ = await publish(argv.deploy);
  return Promise.resolve();
}

// Run main if this isn't imported as a module.
if(!module.parent) {
  main();
}
