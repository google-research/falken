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
using NUnit.Framework;

// Do not warn about missing documentation.
#pragma warning disable 1591

using TestBrainSpec =
    Falken.BrainSpec<FalkenTests.FalkenExampleObservations, FalkenTests.FalkenExampleActions>;

namespace FalkenTests
{
    public class EpisodeTest
    {
        private const string _kBrainName = "test_brain";

        [Test]
        public void FromInternalCompletionState()
        {
            Falken.Episode.CompletionState state =
              Falken.Episode.FromInternalCompletionState(
                FalkenInternal.falken.Episode.CompletionState.kCompletionStateInvalid);
            Assert.AreEqual(Falken.Episode.CompletionState.Invalid, state);
            state =
              Falken.Episode.FromInternalCompletionState(
                FalkenInternal.falken.Episode.CompletionState.kCompletionStateSuccess);
            Assert.AreEqual(Falken.Episode.CompletionState.Success, state);
            state =
              Falken.Episode.FromInternalCompletionState(
                FalkenInternal.falken.Episode.CompletionState.kCompletionStateFailure);
            Assert.AreEqual(Falken.Episode.CompletionState.Failure, state);
            state =
              Falken.Episode.FromInternalCompletionState(
                FalkenInternal.falken.Episode.CompletionState.kCompletionStateAborted);
            Assert.AreEqual(Falken.Episode.CompletionState.Aborted, state);
        }

        [Test]
        public void ToInternalCompletionState()
        {
            FalkenInternal.falken.Episode.CompletionState state =
              Falken.Episode.ToInternalCompletionState(
                Falken.Episode.CompletionState.Invalid);
            Assert.AreEqual(state,
              FalkenInternal.falken.Episode.CompletionState.kCompletionStateInvalid);
            state =
              Falken.Episode.ToInternalCompletionState(
                Falken.Episode.CompletionState.Success);
            Assert.AreEqual(state,
              FalkenInternal.falken.Episode.CompletionState.kCompletionStateSuccess);
            state =
              Falken.Episode.ToInternalCompletionState(
                Falken.Episode.CompletionState.Failure);
            Assert.AreEqual(state,
              FalkenInternal.falken.Episode.CompletionState.kCompletionStateFailure);
            state =
              Falken.Episode.ToInternalCompletionState(
                Falken.Episode.CompletionState.Aborted);
            Assert.AreEqual(state,
              FalkenInternal.falken.Episode.CompletionState.kCompletionStateAborted);
        }

        [Test]
        public void EpisodeId()
        {
            Falken.Service service = Falken.Service.Connect(null, null, null);
            Assert.IsNotNull(service);
            Falken.Brain<TestBrainSpec> brain = service.CreateBrain<TestBrainSpec>(_kBrainName);
            Falken.Session session = brain.StartSession(
              Falken.Session.Type.InteractiveTraining, 5);
            Falken.Episode episode = session.StartEpisode();
            Assert.IsNotEmpty(episode.Id);
            session.Stop();
        }
    }
}