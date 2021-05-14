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
using System.Reflection;
using System.Collections.Generic;

namespace Falken
{

    /// <summary>
    /// <c>BrainSpecBase</c> defines the set of observations and actions
    /// that falken will use.
    /// </summary>
    public class BrainSpecBase
    {
        // Internal observations that will be used to bind the Falken.Observations.
        private FalkenInternal.falken.ObservationsBase _internalObservations = null;
        // Internal actions that will be used to bind the Falken.ActionsBase.
        private FalkenInternal.falken.ActionsBase _internalActions = null;
        // Internal brain spec that will own reference both, the internal actions
        // and the internal observations.
        private FalkenInternal.falken.BrainSpecBase _brainSpec = null;
        // Actions that will be used by this brain spec.
        private Falken.ActionsBase _actionsBase = null;
        // Observations that will be used by this brain spec.
        private Falken.ObservationsBase _observationsBase = null;

        /// <summary>
        /// Create a Falken.ActionsBase instance that will be used by this brain spec.
        /// </summary>
        internal virtual Falken.ActionsBase CreateOrGetActions()
        {
            if (_actionsBase == null)
            {
                _actionsBase = new Falken.ActionsBase();
            }
            return _actionsBase;
        }

        /// <summary>
        /// Create a Falken.Observations instance that will be used by this brain spec.
        /// </summary>
        internal virtual Falken.ObservationsBase CreateOrGetObservations()
        {
            if (_observationsBase == null)
            {
                _observationsBase = new Falken.ObservationsBase();
            }
            return _observationsBase;
        }

        /// <summary>
        /// Read observations and actions.
        /// </summary>
        internal void Read()
        {
            _observationsBase.Read();
            _actionsBase.ReadAttributes();
        }

        /// <summary>
        /// Check if both, actions and observations are bound.
        /// </summary>
        public bool Bound
        {
            get
            {
                return _actionsBase != null && _actionsBase.Bound &&
                  _observationsBase != null && _observationsBase.Bound;
            }
        }

        /// <summary>
        /// Get the actions that this brain spec is using.
        /// </summary>
        public Falken.ActionsBase ActionsBase
        {
            get
            {
                return _actionsBase;
            }
        }

        /// <summary>
        /// Get the observations that this brain spec is using.
        /// </summary>
        public Falken.ObservationsBase ObservationsBase
        {
            get
            {
                return _observationsBase;
            }
        }

        /// <summary>
        /// Create an empty BrainSpecBase.
        /// </summary>
        public BrainSpecBase()
        {
        }

        /// <summary>
        /// Create a BrainSpecBase with the given actions and observations.
        /// </summary>
        public BrainSpecBase(Falken.ActionsBase actions,
          Falken.ObservationsBase observations)
        {
            _actionsBase = actions;
            _observationsBase = observations;
        }

        /// <summary>
        /// Get the internal brain spec that this owns.
        /// </summary>
        internal FalkenInternal.falken.BrainSpecBase InternalBrainSpec
        {
            get
            {
                return _brainSpec;
            }
        }

        /// <summary>
        /// Bind the brain spec by binding the actions
        /// and the observations.
        /// <exception> AlreadyBoundException thrown if the brain spec
        /// was already bound. </exception>
        /// <exception> Any exception thrown from BindActions or BindObservations.
        /// </exception>
        /// </summary>
        internal void BindBrainSpec()
        {
            if (Bound)
            {
                throw new AlreadyBoundException(
                  "Can't rebind a brain spec that was bind.");
            }
            _actionsBase = CreateOrGetActions();
            _observationsBase = CreateOrGetObservations();
            _internalActions = new FalkenInternal.falken.ActionsBase();
            _internalObservations = new FalkenInternal.falken.ObservationsBase();
            _brainSpec = new FalkenInternal.falken.BrainSpecBase(
              _internalObservations, _internalActions);
            try
            {
                _actionsBase.BindActions(_internalActions);
                _observationsBase.BindObservations(_internalObservations);
            }
            catch
            {
                _internalActions = null;
                _internalObservations = null;
                _brainSpec = null;
                throw;
            }
        }

        /// <summary>
        /// Rebind the observation and actions using the given internal
        /// brain spec base.
        /// </summary>
        internal void Rebind(FalkenInternal.falken.BrainSpecBase brainSpecBase)
        {
            _brainSpec = brainSpecBase;
            _internalActions = brainSpecBase.actions_base();
            _internalObservations = brainSpecBase.observations_base();
            _observationsBase.Rebind(_internalObservations);
            _actionsBase.Rebind(_internalActions);
        }

        /// <summary>
        /// Load the brain spec by loading the actions and observations
        /// using the given internal brain spec.
        /// </summary>
        internal void LoadBrainSpec(FalkenInternal.falken.BrainSpecBase brainSpecBase)
        {
            _actionsBase = CreateOrGetActions();
            _observationsBase = CreateOrGetObservations();
            if (_observationsBase.GetType() == typeof(Falken.ObservationsBase))
            {
                _internalObservations = brainSpecBase.observations_base();
                _observationsBase.LoadObservations(_internalObservations);
            }
            else
            {
                _internalObservations = new FalkenInternal.falken.ObservationsBase();
                _observationsBase.BindObservations(_internalObservations);
            }
            if (_actionsBase.GetType() == typeof(Falken.ActionsBase))
            {
                _internalActions = brainSpecBase.actions_base();
                _actionsBase.LoadActions(_internalActions);
            }
            else
            {
                _internalActions = new FalkenInternal.falken.ActionsBase();
                _actionsBase.BindActions(_internalActions);
            }
            _brainSpec =
              new FalkenInternal.falken.BrainSpecBase(_internalObservations,
                _internalActions);
        }

        /// <summary>
        /// Invalidates the attributes in observations to mark them
        /// as not updated. Optionally invalidate actions too.
        /// </summary>
        /// <param name="invalidateActions"> Set to true to invalidate actions too </param>
        internal void InvalidateAttributeValues(bool invalidateActions)
        {
            _observationsBase.InvalidateAttributeValues();
            if (invalidateActions)
            {
                _actionsBase.InvalidateAttributeValues();
            }
        }
    }

    /// <summary>
    /// <c>BrainSpec</c> with generic specifications.
    /// </summary>
    public class BrainSpec<ObservationClass, ActionClass> : Falken.BrainSpecBase
      where ObservationClass : Falken.ObservationsBase, new()
      where ActionClass : Falken.ActionsBase, new()
    {
        // Actions that will be used by this brain spec.
        private ActionClass _actions = null;
        // Observations that will be used by this brain spec.
        private ObservationClass _observations = null;
        // Action type used to create an instance.
        private Type _actionType;
        private Type _observationsType;

        /// <summary>
        /// Create a brainspec by assigning the types of the
        /// generic types.
        /// </summary>
        public BrainSpec()
        {
            _actionType = typeof(ActionClass);
            _observationsType = typeof(ObservationClass);
        }

        /// <summary>
        /// Create a brainspec with the given types.
        /// <exception> InvalidOperationException thrown if
        /// the given action or observation type is not equal
        /// or a subclass of the generic types.
        /// </exception>
        /// </summary>
        public BrainSpec(Type observationType, Type actionType)
        {
            if (observationType != typeof(ObservationClass) &&
              !observationType.IsSubclassOf(typeof(ObservationClass)))
            {
                throw new InvalidOperationException(
                  $"The given observation type '{observationType.ToString()}' " +
                  $"does not inherit from '{typeof(ObservationClass).ToString()}' " +
                  $"and it's not a '{typeof(ObservationClass).ToString()}' either.");
            }
            if (actionType != typeof(ActionClass) &&
              !actionType.IsSubclassOf(typeof(ActionClass)))
            {
                throw new InvalidOperationException(
                  $"The given action type '{actionType.ToString()}' " +
                  $"does not inherit from '{typeof(ActionClass).ToString()}' " +
                  $"and it's not a '{typeof(ActionClass).ToString()}' either.");
            }
            _actionType = actionType;
            _observationsType = observationType;
        }

        /// <summary>
        /// Create an instance of ActionClass.
        /// </summary>
        internal override Falken.ActionsBase CreateOrGetActions()
        {
            _actions = (ActionClass)Activator.CreateInstance(_actionType);
            return _actions;
        }

        /// <summary>
        /// Create an instance of ObservationClass.
        /// </summary>
        internal override Falken.ObservationsBase CreateOrGetObservations()
        {
            _observations = (ObservationClass)Activator.CreateInstance(_observationsType);
            return _observations;
        }

        /// <summary>
        /// Retrieve the actions used by this brain spec.
        /// </summary>
        public ActionClass Actions
        {
            get
            {
                return _actions;
            }
        }

        /// <summary>
        /// Retrieve the observations used by this brain spec.
        /// </summary>
        public ObservationClass Observations
        {
            get
            {
                return _observations;
            }
        }
    }
}
