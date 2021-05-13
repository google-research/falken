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
using System.Linq;
using System.Reflection;

namespace Falken
{

    /// <summary>
    /// A <c>BrainBase</c> represents the idea of the thing that observes, learns
    /// and acts. It’s also helpful to think about each Brain as being designed
    /// to accomplish a specific kind of task, like completing a lap in a
    /// racing game or defeating enemies while moving through a level in an FPS.
    /// </summary>
    public class BrainBase : IDisposable
    {
        // Internal Falken brain that is connected to this instance.
        private FalkenInternal.falken.BrainBase _brain = null;

        // Falken.BrainSpec used to create this brain.
        private Falken.BrainSpecBase _brainSpecBase = null;

        // Used to communicate with the remote service.
        private Falken.Service _service = null;

        /// <summary>
        /// Get the brainspec used to create this brain.
        /// </summary>
        public Falken.BrainSpecBase BrainSpecBase
        {
            get
            {
                return _brainSpecBase;
            }
        }

        /// <summary>
        /// Retrieve the brain's id. Useful to load the brain
        /// using the service.
        /// </summary>
        public string Id
        {
            get
            {
                return _brain.id();
            }
        }

        /// <summary>
        /// Retrieve the brain's display name.
        /// </summary>
        public string DisplayName
        {
            get
            {
                return _brain.display_name();
            }
        }

        /// <summary>
        /// Retrieve brain's current snapshot id. Useful to load the brain
        /// using the service.
        /// </summary>
        public string SnapshotId
        {
            get
            {
                return _brain.snapshot_id();
            }
        }

        /// <summary>
        /// Get the service used by this brain.
        /// </summary>
        public Falken.Service Service
        {
            get
            {
                return _service;
            }
        }

        /// <summary>
        /// Create a brain by assigning an internal one.
        /// </summary>
        internal BrainBase(FalkenInternal.falken.BrainBase brain, Falken.Service service)
        {
            _brain = brain;
            _service = service;
        }

        /// <summary>
        /// Finalize this object.
        /// </summary>
        ~BrainBase()
        {
            Dispose(false);
        }

        /// <summary>
        /// Deallocate this object.
        /// </summary>
        public void Dispose()
        {
            Dispose(true);
            GC.SuppressFinalize(this);
        }

        /// <summary>
        /// Deallocate this object.
        /// </summary>
        /// <param name="disposing">Whether to dispose of only unmanaged resources.</param>
        protected virtual void Dispose(bool disposing)
        {
            lock (this)
            {
                if (_brain != null)
                {
                    _brain.Dispose();
                    if (disposing)
                    {
                        _brain = null;
                        _brainSpecBase = null;
                        _service = null;
                    }
                }
            }
        }

        /// <summary>
        /// Bind the created brain with the given Falken.BrainSpec by rebinding
        /// each attribute defined in the actions and observations.
        /// <param name="brainSpec"> Brain spec that will be rebound to the
        /// internal observations and actions from the internal brain. </param>
        /// </summary>
        internal virtual void BindCreatedBrain(Falken.BrainSpecBase brainSpec)
        {
            _brainSpecBase = brainSpec;
            _brainSpecBase.Rebind(_brain.brain_spec_base());
        }

        /// <summary>
        /// Load the given brain spec by creating the actions and observations
        /// and binding them dynamically.
        /// </summary>
        internal void LoadBrain(FalkenInternal.falken.BrainSpecBase brainSpec)
        {
            _brainSpecBase = CreateBrainSpec();
            _brainSpecBase.LoadBrainSpec(brainSpec);
            if (!_brain.MatchesBrainSpec(_brainSpecBase.InternalBrainSpec))
            {
                _brainSpecBase = null;
                throw new InvalidOperationException(
                  $"Could not load brain with id '{_brain.id()}' because " +
                  "the actions or observations do not match.");
            }
            _brainSpecBase.Rebind(brainSpec);
        }

        /// <summary>
        /// Create a brain spec instance.
        /// </summary>
        internal virtual Falken.BrainSpecBase CreateBrainSpec()
        {
            return new Falken.BrainSpecBase();
        }

        /// <summary>
        /// Read brain spec.
        /// </summary>
        internal void Read()
        {
            _brainSpecBase.Read();
        }

        /// <summary>
        /// Start a session.
        /// </summary>
        /// <param name="type"> Session type. </param>
        /// <param name="maxStepsPerEpisode"> Maximum number of steps per episode. </param>
        /// <exception> InvalidOperationException thrown in case the session
        /// couldn't be created. </exception>
        /// <returns> Started session. </returns>
        public Falken.Session StartSession(Falken.Session.Type type,
          uint maxStepsPerEpisode)
        {
            FalkenInternal.falken.Session session = _brain.StartSession(
              Falken.Session.ToInternalType(type), maxStepsPerEpisode);
            if (session == null)
            {
                throw new InvalidOperationException(
                  $"Session in brain '{_brain.display_name()}' with id '{_brain.id()}' " +
                  "could not be created. Possible reasons are:\n" +
                  "1. Service got cleaned up before this brain.\n" +
                  $"2. Given session type ('{type.ToString()}') is 'Invalid'\n" +
                  "3. An error ocurred in the service.");
            }
            return new Falken.Session(session, this);
        }

        /// <summary>
        /// Get the number of sessions in the brain.
        /// </summary>
        /// <returns> Number of sessions in the brain. </returns>
        public int SessionCount
        {
            get
            {
                return _brain.GetSessionCount();
            }
        }

        /// <summary>
        /// Get an existing closed session by index in the brain.
        /// </summary>
        /// <param name="index"> Session index. </param>
        /// <returns> Session that can be read from but can not accept
        /// more training data. To continue to train the brain create
        /// a new session. </returns>
        public Falken.Session GetSession(int index)
        {
            FalkenInternal.falken.Session session = _brain.GetSessionByIndex(index);
            if (session == null)
            {
                return null;
            }
            return new Falken.Session(session, this);
        }

        /// <summary>
        /// Get a session by ID in the brain.
        /// </summary>
        /// <param name="sessionId"> Session ID. </param>
        /// <returns> Session. </returns>
        public Falken.Session GetSession(string sessionId)
        {
            FalkenInternal.falken.Session session = _brain.GetSessionById(sessionId);
            if (session == null)
            {
                return null;
            }
            return new Falken.Session(session, this);
        }
    }

    /// <summary>
    /// <c>Brain</c> with generic specifications.
    /// </summary>
    public sealed class Brain<BrainSpecClass> : Falken.BrainBase
      where BrainSpecClass : Falken.BrainSpecBase, new()
    {

        private class BrainSpecTypes
        {
            public BrainSpecTypes()
            {
                observationType = typeof(Falken.ObservationsBase);
                actionType = typeof(Falken.ActionsBase);
            }
            public BrainSpecTypes(Type observation, Type action)
            {
                observationType = observation;
                actionType = action;
            }
            // Observation type that will be used to create the brain spec.
            public Type observationType;
            // Action type that will be used to create the brain spec.
            public Type actionType;
        }

        // Falken.BrainSpec used to create this brain.
        private BrainSpecClass _brainSpec = null;

        // Store the types that will be used to create a brain spec
        // if given.
        private BrainSpecTypes _brainSpecTypes = null;

        /// <summary>
        /// Get generic brain spec.
        /// </summary>
        public BrainSpecClass BrainSpec
        {
            get
            {
                return _brainSpec;
            }
        }

        /// <summary>
        /// Create a brain by assigning an internal one.
        /// </summary>
        internal Brain(FalkenInternal.falken.BrainBase brain, Falken.Service service)
            : base(brain, service)
        {
        }

        /// <summary>
        /// Create a brain by assigning an internal one with the given
        /// types for observations and actions.
        /// </summary>
        internal Brain(FalkenInternal.falken.BrainBase brain, Falken.Service service,
                       Type observationType, Type actionType) : base(brain, service)
        {
            _brainSpecTypes = new BrainSpecTypes(observationType, actionType);
        }

        /// <summary>
        /// Call parent implementation and cast the given brain spec
        /// to the generic version.
        /// </summary>
        internal override void BindCreatedBrain(Falken.BrainSpecBase brainSpec)
        {
            base.BindCreatedBrain(brainSpec);
            _brainSpec = (BrainSpecClass)brainSpec;
        }

        /// <summary>
        /// Create the generic brain spec version.
        /// </summary>
        internal override Falken.BrainSpecBase CreateBrainSpec()
        {
            if (_brainSpecTypes != null)
            {
                _brainSpec = (BrainSpecClass)Activator.CreateInstance(
                  typeof(BrainSpecClass), _brainSpecTypes.observationType,
                  _brainSpecTypes.actionType);
            }
            else
            {
                _brainSpec = new BrainSpecClass();
            }
            return _brainSpec;
        }
    }
}
