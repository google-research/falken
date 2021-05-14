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
    /// <c>Session</c> represents a period of time during which
    /// Falken was learning how to play a game, playing a game, or both.
    /// </summary>
    public sealed class Session
    {
        // Internal session.
        private FalkenInternal.falken.Session _session = null;
        // BrainBase that owns this session.
        private Falken.BrainBase _brainBase = null;

        /// Enum to indicate valid session types.
        public enum Type
        {
            /// An invalid session.
            Invalid = 0,
            /// An interactive training session.
            InteractiveTraining = 1,
            /// A session that performs no training.
            Inference = 2,
            /// A session that evaluates models trained in a previous session.
            Evaluation = 3,
        }

        /// Enum to indicate valid training states.
        public enum TrainingState
        {
            /// Do not use. Internal usage only.
            Invalid = 0,
            /// There is still training to be completed for this session.
            Training,
            /// There is no more work being done for this session.
            Complete,
            /// Models are being deployed for online evaluation.
            Evaluating
        }

        /// <summary>
        /// Get the brain that owns this session.
        /// </summary>
        public Falken.BrainBase BrainBase
        {
            get
            {
                return _brainBase;
            }
        }

        /// <summary>
        /// Convert a given an internal Session.Type to the
        /// public Session Type.
        /// </summary>
        internal static Falken.Session.Type FromInternalType(
          FalkenInternal.falken.Session.Type internalType)
        {
            Falken.Session.Type type =
              Falken.Session.Type.Invalid;
            switch (internalType)
            {
                case FalkenInternal.falken.Session.Type.kTypeInvalid:
                    type = Falken.Session.Type.Invalid;
                    break;
                case FalkenInternal.falken.Session.Type.kTypeInteractiveTraining:
                    type = Falken.Session.Type.InteractiveTraining;
                    break;
                case FalkenInternal.falken.Session.Type.kTypeInference:
                    type = Falken.Session.Type.Inference;
                    break;
                case FalkenInternal.falken.Session.Type.kTypeEvaluation:
                    type = Falken.Session.Type.Evaluation;
                    break;
            }
            return type;
        }

        /// <summary>
        /// Convert a given public session type to the internal representation.
        /// </summary>
        internal static FalkenInternal.falken.Session.Type ToInternalType(
          Falken.Session.Type type)
        {
            FalkenInternal.falken.Session.Type internalType =
              FalkenInternal.falken.Session.Type.kTypeInvalid;
            switch (type)
            {
                case Falken.Session.Type.Invalid:
                    internalType = FalkenInternal.falken.Session.Type.kTypeInvalid;
                    break;
                case Falken.Session.Type.InteractiveTraining:
                    internalType = FalkenInternal.falken.Session.Type.kTypeInteractiveTraining;
                    break;
                case Falken.Session.Type.Inference:
                    internalType = FalkenInternal.falken.Session.Type.kTypeInference;
                    break;
                case Falken.Session.Type.Evaluation:
                    internalType = FalkenInternal.falken.Session.Type.kTypeEvaluation;
                    break;
            }
            return internalType;
        }

        //////////////////////////////////////////////////////

        /// <summary>
        /// Convert a given an internal Session.TrainingState to the
        /// public Session TrainingState.
        /// </summary>
        private static Falken.Session.TrainingState FromInternalTrainingState(
          FalkenInternal.falken.Session.TrainingState internalState)
        {
            Falken.Session.TrainingState state =
              Falken.Session.TrainingState.Invalid;
            switch (internalState)
            {
                case FalkenInternal.falken.Session.TrainingState.kTrainingStateInvalid:
                    state = Falken.Session.TrainingState.Invalid;
                    break;
                case FalkenInternal.falken.Session.TrainingState.kTrainingStateTraining:
                    state = Falken.Session.TrainingState.Training;
                    break;
                case FalkenInternal.falken.Session.TrainingState.kTrainingStateComplete:
                    state = Falken.Session.TrainingState.Complete;
                    break;
                case FalkenInternal.falken.Session.TrainingState.kTrainingStateEvaluating:
                    state = Falken.Session.TrainingState.Evaluating;
                    break;
            }
            return state;
        }

        /// <summary>
        /// Convert a given public training state to the internal representation.
        /// </summary>
        private static FalkenInternal.falken.Session.TrainingState ToInternalTrainingState(
          Falken.Session.TrainingState state)
        {
            FalkenInternal.falken.Session.TrainingState internalState =
              FalkenInternal.falken.Session.TrainingState.kTrainingStateInvalid;
            switch (state)
            {
                case Falken.Session.TrainingState.Invalid:
                    internalState =
                      FalkenInternal.falken.Session.TrainingState.kTrainingStateInvalid;
                    break;
                case Falken.Session.TrainingState.Training:
                    internalState =
                      FalkenInternal.falken.Session.TrainingState.kTrainingStateTraining;
                    break;
                case Falken.Session.TrainingState.Complete:
                    internalState =
                      FalkenInternal.falken.Session.TrainingState.kTrainingStateComplete;
                    break;
                case Falken.Session.TrainingState.Evaluating:
                    internalState =
                      FalkenInternal.falken.Session.TrainingState.kTrainingStateEvaluating;
                    break;
            }
            return internalState;
        }

        /// <summary>
        /// Create a Falken.Session with the given internal session
        /// and brain.
        /// </summary>
        internal Session(FalkenInternal.falken.Session session,
          Falken.BrainBase brain)
        {
            _session = session;
            _brainBase = brain;
        }

        /// <summary>
        /// Start an episode if one hasn't been started.
        /// </summary>
        /// <exception> InvalidOperationException thrown when episode
        /// could not be created.null </exception>
        /// <returns> Started episode. </returns>
        public Falken.Episode StartEpisode()
        {
            FalkenInternal.falken.Episode episode = _session.StartEpisode();
            if (episode == null)
            {
                throw new InvalidOperationException(
                  $"Episode in session with id '{_session.id()}' " +
                  "could not be created. Possible reasons are:\n" +
                  "1. Brain got cleaned up before this session.\n" +
                  "2. An error ocurred in the service.");
            }
            return new Falken.Episode(episode, this);
        }

        /// <summary>
        /// Whether the session has been stopped.
        /// </summary>
        public bool Stopped
        {
            get
            {
                return _session.stopped();
            }
        }

        /// <summary>
        /// Stop a session.
        /// </summary>
        /// <returns> A snapshot id that can be used for new sessions. Empty if a
        /// failure occurs while stopping the session. </returns>
        public string Stop()
        {
            return _session.Stop();
        }

        /// <summary>
        /// Get the session id.
        /// </summary>
        /// <returns> ID of the session. </returns>
        public string Id
        {
            get
            {
                return _session.id();
            }
        }

        /// <summary>
        /// Get the current session training state.
        /// </summary>
        /// <returns> Training state of the session. </returns>
        public TrainingState SessionTrainingState
        {
            get
            {
                return FromInternalTrainingState(_session.training_state());
            }
        }

        /// <summary>
        /// Get the fraction of training time completed for the current session.
        /// </summary>
        /// <returns> Training progress for the session (a number between 0 and 1).
        /// </returns>
        public float SessionTrainingProgress
        {
            get
            {
                return _session.training_progress();
            }
        }

        /// <summary>
        /// Get the session type.
        /// </summary>
        /// <returns> Type of the session. </returns>
        public Falken.Session.Type SessionType
        {
            get
            {
                return FromInternalType(_session.type());
            }
        }

        /// <summary>
        /// Get the session creation time in milliseconds since the Unix epoch
        /// (see https://en.wikipedia.org/wiki/Unix_time).
        /// </summary>
        /// <returns> Creation time of the session in milliseconds. </returns>
        public long CreationTime
        {
            get
            {
                return _session.creation_time();
            }
        }

        /// <summary>
        /// Get session information as a human readable string.
        /// </summary>
        /// <returns> Human readable session information. </returns>
        public string Info
        {
            get
            {
                return _session.info();
            }
        }

        /// <summary>
        /// Get the number of episodes in the session.
        /// </summary>
        /// <returns> Number of episodes in the session. </returns>
        public int EpisodeCount
        {
            get
            {
                return _session.GetEpisodeCount();
            }
        }

        /// <summary> Get a read-only episode by index in the session. </summary>
        /// <param name="index"> Episode index </param>
        /// <returns> Read-only episode. </returns>
        public Falken.Episode GetEpisode(int index)
        {
            FalkenInternal.falken.Episode internalEpisode = _session.GetEpisode(index);
            if (internalEpisode == null)
            {
                return null;
            }
            return new Falken.Episode(internalEpisode, this);
        }
    }
}
