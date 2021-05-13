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
    /// An <c>Episode</c> represents a sequence of interactions with a clear
    /// beginning, middle, and end (like starting a race,
    /// driving around the track, and crossing the finish line).
    /// </summary>
    public sealed class Episode
    {
        // Internal episode.
        private FalkenInternal.falken.Episode _episode = null;
        // Session that owns this episode.
        private Falken.Session _session = null;
        /// Enum to indicate valid episode completion states.
        public enum CompletionState
        {
            /// Invalid state, should never be set.
            Invalid = 0,
            /// A brain completed the episode successfully.
            Success = 2,
            /// A brain failed to complete the episode.
            Failure = 3,
            /// The application aborted the episode. For example, if the game player
            /// exits the current level there was no way to complete the episode
            /// successfully so the episode should be completed with the aborted state.
            Aborted = 4,
        };

        /// <summary>
        /// Convert a given an internal Episode.CompletionState to the
        /// public Episode CompletionState.
        /// </summary>
        internal static Falken.Episode.CompletionState FromInternalCompletionState(
          FalkenInternal.falken.Episode.CompletionState internalCompletionState)
        {
            Falken.Episode.CompletionState completionState =
              Falken.Episode.CompletionState.Invalid;
            switch (internalCompletionState)
            {
                case FalkenInternal.falken.Episode.CompletionState.kCompletionStateInvalid:
                    completionState = Falken.Episode.CompletionState.Invalid;
                    break;
                case FalkenInternal.falken.Episode.CompletionState.kCompletionStateSuccess:
                    completionState = Falken.Episode.CompletionState.Success;
                    break;
                case FalkenInternal.falken.Episode.CompletionState.kCompletionStateFailure:
                    completionState = Falken.Episode.CompletionState.Failure;
                    break;
                case FalkenInternal.falken.Episode.CompletionState.kCompletionStateAborted:
                    completionState = Falken.Episode.CompletionState.Aborted;
                    break;
            }
            return completionState;
        }

        /// <summary>
        /// Convert a given public completion state to the internal representation.
        /// </summary>
        internal static FalkenInternal.falken.Episode.CompletionState ToInternalCompletionState(
          Falken.Episode.CompletionState completionState)
        {
            FalkenInternal.falken.Episode.CompletionState internalCompletionState =
              FalkenInternal.falken.Episode.CompletionState.kCompletionStateInvalid;
            switch (completionState)
            {
                case Falken.Episode.CompletionState.Invalid:
                    internalCompletionState =
                      FalkenInternal.falken.Episode.CompletionState.kCompletionStateInvalid;
                    break;
                case Falken.Episode.CompletionState.Success:
                    internalCompletionState =
                      FalkenInternal.falken.Episode.CompletionState.kCompletionStateSuccess;
                    break;
                case Falken.Episode.CompletionState.Failure:
                    internalCompletionState =
                      FalkenInternal.falken.Episode.CompletionState.kCompletionStateFailure;
                    break;
                case Falken.Episode.CompletionState.Aborted:
                    internalCompletionState =
                      FalkenInternal.falken.Episode.CompletionState.kCompletionStateAborted;
                    break;
            }
            return internalCompletionState;
        }

        internal Episode(FalkenInternal.falken.Episode episode,
          Falken.Session session)
        {
            _episode = episode;
            _session = session;
        }

        /// <summary>
        /// Execute a step of the episode.
        /// Apply the current observations and actions (if any) of the brain
        /// associated with the episode. The actions are applied only if the source
        /// of them is not HumanProvided. It's not possible to execute a step of an
        /// episode after it is complete.
        /// </summary>
        /// <returns> true if the step was successfully executed, false otherwise.
        /// </returns>
        public bool Step(float? reward = null)
        {
            Falken.ActionsBase actions = _session.BrainBase.BrainSpecBase.ActionsBase;
            Falken.ActionsBase.Source actionsSource = actions.ActionsSource;
            // We don't know if the user modified the observations and actions
            // with those attributes that use reflection, therefore we save
            // the action source set by the user and we set it back.
            _session.BrainBase.Read();
            if (actionsSource == Falken.ActionsBase.Source.BrainAction)
            {
                actions.ActionsSource = actionsSource;
            }
            bool stepped = reward.HasValue ? _episode.Step(reward.Value) : _episode.Step();
            if (stepped)
            {
                if (actions.ActionsSource == Falken.ActionsBase.Source.BrainAction)
                {
                    actions.WriteAttributes();
                }
            }
            _session.BrainBase.BrainSpecBase.InvalidateAttributeValues(
                actions.ActionsSource != Falken.ActionsBase.Source.BrainAction
            );
            return stepped;
        }

        /// <summary>
        /// Determine whether the episode is complete.
        /// </summary>
        public bool Completed
        {
            get
            {
                return _episode.completed();
            }
        }

        /// <summary>
        /// Complete the episode.
        /// </summary>
        /// <param name="completionState"> Completion state of the episode.</param>
        /// <returns>true if the completion was successfully executed, false otherwise.</returns>
        public bool Complete(Falken.Episode.CompletionState completionState)
        {
            return _episode.Complete(ToInternalCompletionState(completionState));
        }

        /// <summary>
        /// Get the session that owns this episode.
        /// </summary>
        /// <returns> Session that owns this episode. </returns>
        public Falken.Session Session
        {
            get
            {
                return _session;
            }
        }

        /// <summary>
        /// Get the number of steps submitted in the episode.
        /// </summary>
        public int StepCount
        {
            get
            {
                return _episode.GetStepCount();
            }
        }

        /// <summary>
        /// Read a step from the episode by index storing the results in brain's
        /// observations and actions.
        /// </summary>
        /// <param name="index">Step to read.</param>
        /// <returns>true if the step was read successfully, false otherwise.</returns>
        public bool ReadStep(int index)
        {
            bool read = _episode.ReadStep(index);
            if (read)
            {
                Falken.ActionsBase actions =
                  _session.BrainBase.BrainSpecBase.ActionsBase;
                actions.WriteAttributes();
                Falken.ObservationsBase observations =
                  _session.BrainBase.BrainSpecBase.ObservationsBase;
                observations.Write();
            }
            return read;
        }

        /// <summary>
        /// Get the reward for the current step.
        /// </summary>
        public float Reward
        {
            get
            {
                return _episode.reward();
            }
        }

        /// <summary>
        /// Returns the ID of the current episode.
        /// </summary>
        public string Id
        {
            get
            {
                return _episode.id();
            }
        }
    }
}
