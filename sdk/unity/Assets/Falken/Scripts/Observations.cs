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
using System.Reflection;

namespace Falken
{
    /// <summary>
    /// <c>ObservationsBase</c> Generic interface used to generate a set of
    /// observations. Entities added to this object are other entities in
    /// the observation set. Also it defines a player entity
    /// that can be assigned to any class that inherits from entity.
    /// </summary>
    public class ObservationsBase : Falken.EntityContainer
    {
        // Do not warn about this field being unused as we are explicitly holding a reference to an
        // unmanaged object.
#pragma warning disable 0414
        // Internal Falken observations that this instance uses
        // to establish the connections against entities.
        private FalkenInternal.falken.ObservationsBase _observations = null;
#pragma warning restore 0414

        /// <summary>
        /// Player entity.
        /// </summary> 
        [FalkenInheritedAttribute]
        public Falken.EntityBase player = null;

        /// <summary>
        /// Bind all defined entities.
        /// <exception> AlreadyBoundException thrown when trying to
        /// bind the observations when it was bound already. </exception>
        /// </summary>
        internal void BindObservations(
          FalkenInternal.falken.ObservationsBase observations)
        {
            if (Bound)
            {
                throw new AlreadyBoundException(
                  "Can't bind observations more than once.");
            }
            base.BindEntities(observations);
            _observations = observations;
        }

        internal void Rebind(
          FalkenInternal.falken.ObservationsBase observations)
        {
            base.Rebind(observations, new HashSet<string>() { "player" });
            _observations = observations;
        }

        internal void LoadObservations(
          FalkenInternal.falken.ObservationsBase observations)
        {
            base.LoadEntities(observations);
            _observations = observations;
        }
    }
}
