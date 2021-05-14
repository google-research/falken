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

namespace FalkenTests
{
    public class FalkenExtendedExampleObservations : FalkenExampleObservations
    {
        public EnemyExampleEntity enemy2 = new EnemyExampleEntity();
    }

    public class FalkenExtendedExampleActions : FalkenExampleActions
    {
        [Falken.Range(-1f, 1f)]
        public float steering = 1.0f;
    }

    public class BrainSpecTest
    {

        [Test]
        public void BindBrainSpecBase()
        {
            Falken.ActionsBase actions = new Falken.ActionsBase();
            Falken.Number number = new Falken.Number("number", 0.0f, 5.0f);
            actions["number"] = number;
            Falken.BrainSpecBase brainSpec = new Falken.BrainSpecBase(actions,
              new FalkenExampleObservations());
            brainSpec.BindBrainSpec();
            Assert.IsTrue(brainSpec.Bound);
            Assert.IsTrue(brainSpec.ActionsBase.ContainsKey("number"));
            Falken.ObservationsBase observations = brainSpec.ObservationsBase;
            Assert.IsTrue(observations.ContainsKey("enemy"));
            Assert.IsTrue(observations.ContainsKey("player"));
        }

        [Test]
        public void BindBrainSpec()
        {
            Falken.BrainSpec<FalkenExampleObservations, FalkenExampleActions> brainSpec =
              new Falken.BrainSpec<FalkenExampleObservations, FalkenExampleActions>();
            Assert.IsFalse(brainSpec.Bound);
            brainSpec.BindBrainSpec();
            Assert.IsTrue(brainSpec.Bound);

            FalkenExampleActions actions = brainSpec.Actions;
            Assert.IsTrue(actions.Bound);
            Assert.AreEqual(7, actions.Count);
            Assert.IsTrue(actions.ContainsKey("lookUpAngle"));
            Assert.IsTrue(actions.ContainsKey("jump"));
            Assert.IsTrue(actions.ContainsKey("weapon"));
            Assert.IsTrue(actions.ContainsKey("joystick"));
            Assert.IsTrue(actions.ContainsKey("numberAttribute"));
            Assert.IsTrue(actions.ContainsKey("categoryAttribute"));
            Assert.IsTrue(actions.ContainsKey("booleanAttribute"));
            FalkenExampleObservations observations = brainSpec.Observations;
            Assert.IsTrue(observations.Bound);
            Assert.AreEqual(2, observations.Count);
            Assert.IsTrue(observations.ContainsKey("player"));
            Assert.IsTrue(observations.ContainsKey("enemy"));
        }

        [Test]
        public void ConstructBrainSpecWithTypes()
        {
            var brainSpec =
              new Falken.BrainSpec<FalkenExampleObservations, FalkenExampleActions>(
                typeof(FalkenExtendedExampleObservations),
                typeof(FalkenExtendedExampleActions));
        }

        [Test]
        public void ConstructBrainSpecWithWrongObservationType()
        {
            Assert.That(() => new Falken.BrainSpec<FalkenExampleObservations,
                                                   FalkenExampleActions>(
                                typeof(Falken.ObservationsBase),
                                typeof(FalkenExampleActions)),
                        Throws.TypeOf<InvalidOperationException>());
        }

        [Test]
        public void ConstructBrainSpecWithWrongActionType()
        {
            Assert.That(() => new Falken.BrainSpec<FalkenExampleObservations,
                                                   FalkenExampleActions>(
                                typeof(FalkenExtendedExampleObservations),
                                typeof(Falken.ActionsBase)),
                        Throws.TypeOf<InvalidOperationException>());
        }

        [Test]
        public void ConstructBrainSpecWithSameType()
        {
            var brainSpec =
              new Falken.BrainSpec<FalkenExampleObservations, FalkenExampleActions>(
                typeof(FalkenExampleObservations),
                typeof(FalkenExampleActions));
        }

        [Test]
        public void BindBrainSpecWithTypes()
        {
            var brainSpec =
              new Falken.BrainSpec<FalkenExampleObservations, FalkenExampleActions>(
                typeof(FalkenExtendedExampleObservations),
                typeof(FalkenExtendedExampleActions));
            brainSpec.BindBrainSpec();

            FalkenExtendedExampleActions actions =
              (FalkenExtendedExampleActions)brainSpec.Actions;
            Assert.IsTrue(actions.Bound);
            Assert.AreEqual(8, actions.Count);
            Assert.IsTrue(actions.ContainsKey("lookUpAngle"));
            Assert.IsTrue(actions.ContainsKey("jump"));
            Assert.IsTrue(actions.ContainsKey("weapon"));
            Assert.IsTrue(actions.ContainsKey("joystick"));
            Assert.IsTrue(actions.ContainsKey("numberAttribute"));
            Assert.IsTrue(actions.ContainsKey("categoryAttribute"));
            Assert.IsTrue(actions.ContainsKey("booleanAttribute"));
            Assert.IsTrue(actions.ContainsKey("steering"));
            FalkenExtendedExampleObservations observations =
              (FalkenExtendedExampleObservations)brainSpec.Observations;
            Assert.IsTrue(observations.Bound);
            Assert.AreEqual(3, observations.Count);
            Assert.IsTrue(observations.ContainsKey("player"));
            Assert.IsTrue(observations.ContainsKey("enemy"));
            Assert.IsTrue(observations.ContainsKey("enemy2"));
        }
    }
}
