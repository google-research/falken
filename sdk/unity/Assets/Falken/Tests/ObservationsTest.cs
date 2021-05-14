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
using NUnit.Framework;

// Do not warn about missing documentation.
#pragma warning disable 1591

namespace FalkenTests
{
    public class FalkenExampleObservations : Falken.ObservationsBase
    {
        public FalkenExampleObservations()
        {
            player = new SimpleExampleEntity();
        }
        public EnemyExampleEntity enemy = new EnemyExampleEntity();
    }

    public sealed class FalkenObservationsWithFeelerTest : Falken.ObservationsBase
    {
        public FalkenObservationsWithFeelerTest()
        {
            player = new SimpleExampleEntityWithFeelers();
        }
    }

    public class ObservationsTest
    {

        private FalkenInternal.falken.ObservationsBase _observationsBase;

        [SetUp]
        public void Setup()
        {
            _observationsBase = new FalkenInternal.falken.ObservationsBase();
        }

        [Test]
        public void BindObservations()
        {
            FalkenExampleObservations observations =
              new FalkenExampleObservations();
            observations.BindObservations(_observationsBase);
            Assert.AreEqual(2, observations.Count);
            Assert.IsTrue(observations.ContainsKey("player"));
            Assert.IsTrue(observations["player"] is SimpleExampleEntity);
            Assert.IsTrue(observations.ContainsKey("enemy"));
        }
    }
}
