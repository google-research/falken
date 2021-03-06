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
    /// <c>ActionsNotBoundException</c> thrown when access to an
    /// unbound action is forbidden.
    /// </summary>
    [Serializable]
    public class ActionsNotBoundException : Exception
    {
        internal ActionsNotBoundException()
        {
        }

        internal ActionsNotBoundException(string message)
          : base(message) { }

        internal ActionsNotBoundException(string message, Exception inner)
          : base(message, inner) { }
    }

    /// <summary>
    /// <c>ActionsBase</c> defines the set of attributes that
    /// can be generated by a brain or by a human.
    /// </summary>
    public class ActionsBase : Falken.AttributeContainer
    {

        /// <summary>
        /// Source of a set of actions.
        /// </summary>
        public enum Source
        {
            /// <summary>
            /// Should never be set.
            /// </summary>
            Invalid = 0,

            /// <summary>
            /// Actions were not generated by Falken.
            /// </summary>
            None,

            /// <summary>
            /// Actions were generated by a human demonstration.
            /// </summary>
            HumanDemonstration,

            /// <summary>
            /// Actions were generated by a Falken brain.
            /// </summary>
            BrainAction,
        };

        // Internal Falken actions container this instance uses
        // to create attributes.
        private FalkenInternal.falken.ActionsBase _actions = null;

        /// <summary>
        /// Check if a given object is one of the following types:
        /// * Number
        /// * Boolean
        /// * Category
        /// </summary>
        protected override bool SupportsType(object fieldValue)
        {
            return
              Number.CanConvertToNumberType(fieldValue) ||
              Boolean.CanConvertToBooleanType(fieldValue) ||
              Category.CanConvertToCategoryType(fieldValue) ||
              Joystick.CanConvertToJoystickType(fieldValue);
        }

        /// <summary>
        /// Bind all supported action types.
        /// <exception> AlreadyBoundException thrown when trying to
        /// bind the actions when it was bound already. </exception>
        /// </summary>
        internal void BindActions(FalkenInternal.falken.ActionsBase actions)
        {
            if (Bound)
            {
                throw new AlreadyBoundException(
                  "Can't bind actions more than once.");
            }
            base.BindAttributes(actions);
            _actions = actions;
        }

        internal void Rebind(FalkenInternal.falken.ActionsBase actions)
        {
            base.Rebind(actions);
            _actions = actions;
        }

        internal void LoadActions(FalkenInternal.falken.ActionsBase actions)
        {
            base.LoadAttributes(actions);
            _actions = actions;
        }

        /// <summary>
        /// Convert a given an internal ActionsBase.Source to the
        /// public actions source.
        /// </summary>
        private static Falken.ActionsBase.Source FromInternalSource(
          FalkenInternal.falken.ActionsBase.Source internalSource)
        {
            Falken.ActionsBase.Source source =
              Falken.ActionsBase.Source.None;
            switch (internalSource)
            {
                case FalkenInternal.falken.ActionsBase.Source.kSourceInvalid:
                    source = Falken.ActionsBase.Source.Invalid;
                    break;
                case FalkenInternal.falken.ActionsBase.Source.kSourceNone:
                    source = Falken.ActionsBase.Source.None;
                    break;
                case FalkenInternal.falken.ActionsBase.Source.kSourceHumanDemonstration:
                    source = Falken.ActionsBase.Source.HumanDemonstration;
                    break;
                case FalkenInternal.falken.ActionsBase.Source.kSourceBrainAction:
                    source = Falken.ActionsBase.Source.BrainAction;
                    break;
            }
            return source;
        }

        /// <summary>
        /// Convert a given public actions source to the internal representation.
        /// </summary>
        private static FalkenInternal.falken.ActionsBase.Source ToInternalSource(
          Falken.ActionsBase.Source source)
        {
            FalkenInternal.falken.ActionsBase.Source internalSource =
              FalkenInternal.falken.ActionsBase.Source.kSourceNone;
            switch (source)
            {
                case Falken.ActionsBase.Source.Invalid:
                    internalSource = FalkenInternal.falken.ActionsBase.Source.kSourceInvalid;
                    break;
                case Falken.ActionsBase.Source.None:
                    internalSource = FalkenInternal.falken.ActionsBase.Source.kSourceNone;
                    break;
                case Falken.ActionsBase.Source.HumanDemonstration:
                    internalSource =
                        FalkenInternal.falken.ActionsBase.Source.kSourceHumanDemonstration;
                    break;
                case Falken.ActionsBase.Source.BrainAction:
                    internalSource = FalkenInternal.falken.ActionsBase.Source.kSourceBrainAction;
                    break;
            }
            return internalSource;
        }

        /// <summary>
        /// Retrieve/set the source for this actions.
        /// </summary>
        public Falken.ActionsBase.Source ActionsSource
        {
            get
            {
                if (Bound)
                {
                    return FromInternalSource(_actions.source());
                }
                throw new ActionsNotBoundException(
                  "Can't get the source from an unbound action.");
            }
            set
            {
                if (Bound)
                {
                    _actions.set_source(ToInternalSource(value));
                    return;
                }
                throw new ActionsNotBoundException(
                  "Can't set the source to an unbound action.");
            }
        }
    }
}
