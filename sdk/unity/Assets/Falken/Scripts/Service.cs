// Copyright 2021 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Reflection;

namespace Falken
{

    /// <summary>
    /// <c>Service</c> class used for brain creation and loading.
    /// </summary>
    public sealed class Service
    {
        // Internal Falken service.
        private FalkenInternal.falken.Service _service = null;

        /// <summary>
        /// Create a Falken.Service by assigning a internal service.
        /// </summary>
        private Service(FalkenInternal.falken.Service service)
        {
            _service = service;
        }

        /// <summary>
        /// Connect to a Falken's project.
        /// <param name="projectId"> This parameter is optional if jsonConfig
        /// specifies it. If set, this value overrides the project_id value in
        /// jsonConfig. </param>
        /// <param name="apiKey"> This parameter is optional if jsonConfig
        /// specifies it. If set, this value overrides the api_key value in
        /// jsonConfig. </param>
        /// <param name="jsonConfig"> json_config Configuration as a JSON.
        /// This parameter is optional if
        /// projectId and apiKey are specified. It must follow the following
        /// format:
        /// {
        ///   "api_key": "API_KEY",
        ///   "project_id": "PROJECT_ID"
        /// }
        /// API_KEY: API key used to connect to Falken. This defaults
        /// to an empty string so must be set via this configuration value or the
        /// apiKey argument.
        /// PROJECT_ID: Falken project ID to use. This defaults to an
        /// empty string so must be set via this configuration value or the
        /// projectId argument.
        /// If jsonConfig is null, the code will try to load a .json file
        /// in the StreamingAssets directory.
        /// That file must be called "falken_config.json" to be loaded.
        /// </param>
        /// <exception> InvalidOperationException thrown when the service
        /// could not be created. </exception>
        /// </summary>
        public static Service Connect(
          string projectId = null, string apiKey = null, string jsonConfig = null)
        {
            if (String.IsNullOrEmpty(jsonConfig))
            {
                string streamingPath = Directory.GetCurrentDirectory();
#if UNITY_5_3_OR_NEWER
                streamingPath = UnityEngine.Application.streamingAssetsPath;
#endif  // UNITY_5_3_OR_NEWER
                string jsonConfigFile =
                  Path.Combine(streamingPath, "falken_config.json");
                if (File.Exists(jsonConfigFile))
                {
                    jsonConfig = File.ReadAllText(jsonConfigFile);
                }
            }
            FalkenInternal.falken.Service service =
              FalkenInternal.falken.Service.Connect(projectId, apiKey, jsonConfig);
            if (service == null)
            {
                throw new InvalidOperationException(
                  "Service could not be created with\n" +
                  $"Project id : '{projectId}'\n" +
                  $"ApiKey: '{apiKey}'\n" +
                  $"JsonConfig: '{jsonConfig}'");
            }
            return new Falken.Service(service);
        }

        /// <summary> Create a brain in this service with the given
        /// brain spec using the given delegate function.
        /// <exception> ArgumentNullException thrown if the brain's name
        /// is either empty or null. </exception>
        /// </summary>
        private BrainBase CreateBrain(
          string displayName, Falken.BrainSpecBase brainSpecBase,
          Func<FalkenInternal.falken.BrainBase, Falken.BrainBase> createBrainDelegate)
        {
            if (String.IsNullOrEmpty(displayName))
            {
                throw new ArgumentNullException(displayName);
            }
            brainSpecBase.BindBrainSpec();
            FalkenInternal.falken.BrainBase brainBase =
              _service.CreateBrain(displayName, brainSpecBase.InternalBrainSpec);
            if (brainBase == null)
            {
                throw new InvalidOperationException(
                  "Brain could not be created. Ensure that you have more than one " +
                  "attribute created for actions.");
            }
            Falken.BrainBase brain = createBrainDelegate(brainBase);
            brain.BindCreatedBrain(brainSpecBase);
            return brain;
        }


        /// <summary> Create a brain in this service with the given
        /// brain spec. </summary>
        /// <param name="displayName"> Brain display name. </param>
        /// <param name="brainSpecBase"> Specification for the new brain. </param>
        /// <exception> InvalidOperationException thrown if the brain could not
        /// be created. </exception>
        /// <exception> ArgumentNullException thrown if the given brain spec
        /// is null. </exception>
        /// <exception> Any other exception that can be thrown when binding
        /// a Falken.BrainSpecBase. </exception>
        /// <returns> Created Brain instance. </returns>
        public BrainBase CreateBrain(
          string displayName, Falken.BrainSpecBase brainSpecBase)
        {
            if (brainSpecBase == null)
            {
                throw new ArgumentNullException("brainSpecBase");
            }
            return CreateBrain(
              displayName, brainSpecBase,
              (internalBrain) => new Falken.BrainBase(internalBrain, this));
        }

        /// <summary> Create a brain in this service. Dynamic attributes
        /// for the brain spec are not supported. </summary>
        /// <param name="displayName"> Brain display name. </param>
        /// <exception> InvalidOperationException thrown if the brain could not
        /// be created. </exception>
        /// <exception> ArgumentNullException thrown if the brain's name
        /// is either empty or null. </exception>
        /// <exception> Any other exception that can be thrown when binding
        /// a Falken.BrainSpec. </exception>
        /// <returns> Created Brain instance. </returns>
        public Brain<BrainSpecClass> CreateBrain<BrainSpecClass>(
          string displayName)
          where BrainSpecClass : Falken.BrainSpecBase, new()
        {
            return (Brain<BrainSpecClass>)CreateBrain(
              displayName, new BrainSpecClass(),
              (internalBrain) => new Falken.Brain<BrainSpecClass>(internalBrain, this));
        }

        /// <summary> Create a brain in this service using types that are
        /// subclasses of the generic types (or equal). Dynamic attributes
        /// for the brain spec are not supported. </summary>
        /// <param name="displayName"> Brain display name. </param>
        /// <param name="observationType"> Type of the observation. </param>
        /// <param name="actionType"> Type of the action. </param>
        /// <exception> InvalidOperationException thrown if the brain could not
        /// be created. </exception>
        /// <exception> ArgumentNullException thrown if the brain's name
        /// is either empty or null. </exception>
        /// <exception> Any other exception that can be thrown when binding
        /// a Falken.BrainSpec. </exception>
        /// <returns> Created Brain instance. </returns>
        public Brain<BrainSpecClass> CreateBrain<BrainSpecClass>(
          string displayName, Type observationType, Type actionType)
          where BrainSpecClass : Falken.BrainSpecBase, new()
        {
            BrainSpecClass brainSpec = (BrainSpecClass)Activator.CreateInstance(
                typeof(BrainSpecClass), observationType, actionType);
            return (Brain<BrainSpecClass>)CreateBrain(
              displayName, brainSpec,
              (internalBrain) => new Falken.Brain<BrainSpecClass>(internalBrain, this));
        }

        /// Find a brain with the specified ID.
        /// When loading a brain using the base class for ObservationsBase,
        /// entities will be called "entity_#", where '#' starts from zero
        /// and increasing by one for each non inherited entity.
        /// If using a custom class (using reflection), the field's name
        /// will be preserved.
        /// <param name="brainId"> Brain ID. </param>
        /// <param name="snapshotId"> Optional snapshot ID. </param>
        /// <exception> ArgumentNullException thrown if brainId is null.
        /// </exception>
        /// <exception> InvalidOperationException if brain does not
        /// exists. </exception>
        /// <returns> Loaded Brain instance. </returns>
        public Brain<BrainSpecClass> LoadBrain<BrainSpecClass>(
          string brainId, string snapshotId = null)
          where BrainSpecClass : Falken.BrainSpecBase, new()
        {
            if (String.IsNullOrEmpty(brainId))
            {
                throw new ArgumentNullException(brainId);
            }
            FalkenInternal.falken.BrainBase brainBase =
              _service.LoadBrain(brainId, snapshotId);
            if (brainBase == null)
            {
                throw new InvalidOperationException(
                  $"Brain with id '{brainId}' does not exists.");
            }
            var brain = new Brain<BrainSpecClass>(brainBase, this);
            brain.LoadBrain(brainBase.brain_spec_base());
            return brain;
        }

        /// Find a brain with the specified ID.
        /// When loading a brain using the base class for ObservationsBase,
        /// entities will be called "entity_#", where '#' starts from zero
        /// and increasing by one for each non inherited entity.
        /// If using a custom class (using reflection), the field's name
        /// will be preserved.
        /// <param name="brainId"> Brain ID. </param>
        /// <param name="observationType"> Type used to create the observations. </param>
        /// <param name="actionType"> Type used to create the actions. </param>
        /// <param name="snapshotId"> Optional snapshot ID. </param>
        /// <exception> ArgumentNullException thrown if brainId is null.
        /// </exception>
        /// <exception> InvalidOperationException if brain does not
        /// exists. </exception>
        /// <returns> Loaded Brain instance. </returns>
        public Brain<BrainSpecClass> LoadBrain<BrainSpecClass>(
          string brainId, Type observationType, Type actionType,
          string snapshotId = null)
          where BrainSpecClass : Falken.BrainSpecBase, new()
        {
            if (String.IsNullOrEmpty(brainId))
            {
                throw new ArgumentNullException(brainId);
            }
            FalkenInternal.falken.BrainBase brainBase =
              _service.LoadBrain(brainId, snapshotId);
            if (brainBase == null)
            {
                throw new InvalidOperationException(
                  $"Brain with id '{brainId}' does not exists.");
            }
            var brain = new Brain<BrainSpecClass>(brainBase, this, observationType, actionType);
            brain.LoadBrain(brainBase.brain_spec_base());
            return brain;
        }
    }
}
