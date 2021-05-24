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
    public class FalkenFeelerContainer : Falken.AttributeContainer
    {
        public Falken.Feelers feeler =
          new Falken.Feelers(5.0f, 3.0f, 45.0f, 3,
            new List<string>() { "zero", "one", "two" });
    }

    public class FalkenFeelerNoIdsContainer : Falken.AttributeContainer
    {
        public Falken.Feelers feelerNoIds =
          new Falken.Feelers(5.0f, 3.0f, 45.0f, 3, null);
    }

    public class FeelerAttributeTest
    {

        private FalkenInternal.falken.AttributeContainer _falkenContainer;

        [SetUp]
        public void Setup()
        {
            _falkenContainer = new FalkenInternal.falken.AttributeContainer();
        }

        [Test]
        public void DeprecatedConstructorsThrowIfRecordDistancesFalseWithName()
        {
            #pragma warning disable 618
            Assert.That(() => new Falken.Feelers("feeler", 5.0f, 3.0f, 45.0f, 3, false,
                                                 new List<string>() { "zero" }),
                        Throws.TypeOf<InvalidOperationException>());
            #pragma warning restore 618
        }

        [Test]
        public void DeprecatedConstructorsThrowIfRecordDistancesFalseWithNoName()
        {
            #pragma warning disable 618
            Assert.That(() => new Falken.Feelers(5.0f, 3.0f, 45.0f, 3, false,
                                                 new List<string>() { "zero" }),
                        Throws.TypeOf<InvalidOperationException>());
            #pragma warning restore 618
        }

        [Test]
        public void CreateDynamicFeeler()
        {
            Falken.Feelers feeler = new Falken.Feelers("feeler",
                5.0f, 3.0f, 45.0f, 3,
                new List<string>() { "zero", "one", "two" });
            Assert.AreEqual(45.0f, feeler.FovAngle);
        }

        [Test]
        public void CreateDynamicFeelerNullName()
        {
            Assert.That(() => new Falken.Feelers(null, 5.0f, 3.0f, 45.0f, 3,
                                                 new List<string>() { "zero", "one", "two" }),
                        Throws.TypeOf<ArgumentNullException>());
        }

        [Test]
        public void CreateOneFeelerWithFovAngleDifferentThanZero()
        {
            Falken.Feelers feeler =
              new Falken.Feelers("feeler", 5.0f, 3.0f, 45.0f, 1, null);
            Assert.AreEqual(feeler.FovAngle, 0.0f);
        }

        [Test]
        public void BindFeeler()
        {
            FalkenFeelerContainer feelerContainer = new FalkenFeelerContainer();
            FieldInfo feelerField =
              typeof(FalkenFeelerContainer).GetField("feeler");
            Falken.Feelers feeler = new Falken.Feelers(
              5.0f, 3.0f, 45.0f, 3,
              new List<string>() { "zero", "one", "two" });
            feeler.BindAttribute(feelerField, feelerContainer, _falkenContainer);
            Assert.AreEqual(5.0f, feeler.Length);
            Assert.AreEqual(3.0f, feeler.Thickness);
            Assert.AreEqual(45.0f, feeler.FovAngle);

            List<Falken.Number> distances = feeler.Distances;
            Assert.AreEqual(3, distances.Count);

            foreach (Falken.Number distance in distances)
            {
                Assert.AreEqual(0.0f, distance.Minimum);
                Assert.AreEqual(5.0f, distance.Maximum);
                Assert.AreEqual(0.0f, distance.Value);
            }
            distances[0].Value = 0.5f;
            Assert.AreEqual(0.5f, distances[0].Value);
            distances[1].Value = 3.0f;
            Assert.AreEqual(3.0f, distances[1].Value);

            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Assert.That(() => distances[2].Value = 8.0f,
                            Throws.TypeOf<System.ApplicationException>());
            }

            Assert.AreEqual(0.0f, distances[2].Value);

            List<Falken.Category> ids = feeler.Ids;
            Assert.AreEqual(3, ids.Count);

            foreach (Falken.Category id in ids)
            {
                Assert.AreEqual(0, id.Value);
                Assert.IsTrue(
                  Enumerable.SequenceEqual(new string[] { "zero", "one", "two" },
                    (List<string>)id.CategoryValues));
            }
            ids[0].Value = 1;
            Assert.AreEqual(1, ids[0].Value);
            ids[1].Value = 2;
            Assert.AreEqual(2, ids[1].Value);

            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Assert.That(() => ids[2].Value = 500000,
                            Throws.TypeOf<System.ApplicationException>());
            }

            Assert.AreEqual(0, ids[2].Value);
        }


        [Test]
        public void FeelerClampingTest()
        {
            FalkenFeelerContainer feelerContainer = new FalkenFeelerContainer();
            FieldInfo feelerField =
              typeof(FalkenFeelerContainer).GetField("feeler");
            Falken.Feelers feeler = new Falken.Feelers(
              5.0f, 3.0f, 45.0f, 3,
              new List<string>() { "zero", "one", "two" });
            feeler.BindAttribute(feelerField, feelerContainer, _falkenContainer);

            var recovered_logs = new List<String>();
            System.EventHandler<Falken.Log.MessageArgs> handler = (
                object source, Falken.Log.MessageArgs args) =>
            {
                recovered_logs.Add(args.Message);
            };
            Falken.Log.OnMessage += handler;

            // default clamping value (off)
            var expected_logs = new List<String>() {
                  "Unable to set value of attribute 'distance_0' to -10" +
                      " as it is out of the specified range 0 to 5.",
                  "Unable to set value of attribute 'distance_0' to 10" +
                      " as it is out of the specified range 0 to 5." };

            List<Falken.Number> distances = feeler.Distances;
            Assert.AreEqual(3, distances.Count);

            var distance = distances[0];

            // default clamping value (off)
            recovered_logs.Clear();
            Assert.IsFalse(feeler.EnableClamping);
            distance.Value = 2.0f;
            Assert.AreEqual(2.0f, distance.Value);
            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Assert.That(() => distance.Value = -10.0f,
                    Throws.TypeOf<ApplicationException>());
                Assert.That(() => distance.Value = 10.0f,
                    Throws.TypeOf<ApplicationException>());
            }
            Assert.That(recovered_logs, Is.EquivalentTo(expected_logs));

            // with clamping on
            recovered_logs.Clear();
            feeler.EnableClamping = true;
            Assert.IsTrue(feeler.EnableClamping);
            distance.Value = 2.0f;
            Assert.AreEqual(2.0f, distance.Value);
            distance.Value = -10.0f;
            Assert.AreEqual(0.0f, distance.Value);
            distance.Value = 10.0f;
            Assert.AreEqual(5.0f, distance.Value);
            Assert.AreEqual(recovered_logs.Count, 0);

            // with clamping off
            recovered_logs.Clear();
            feeler.EnableClamping = false;
            Assert.IsFalse(feeler.EnableClamping);
            distance.Value = 2.0f;
            Assert.AreEqual(2.0f, distance.Value);
            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Assert.That(() => distance.Value = -10.0f,
                    Throws.TypeOf<ApplicationException>());
                Assert.That(() => distance.Value = 10.0f,
                    Throws.TypeOf<ApplicationException>());
            }
            Assert.That(recovered_logs, Is.EquivalentTo(expected_logs));

            recovered_logs.Clear();
            Assert.AreEqual(recovered_logs.Count, 0);
            // test per-feeler clamping management
            feeler.EnableClamping = false;
            Assert.IsFalse(feeler.EnableClamping);
            Assert.IsFalse(feeler.Distances[0].EnableClamping);
            Assert.IsFalse(feeler.Distances[1].EnableClamping);
            Assert.IsFalse(feeler.Distances[2].EnableClamping);
            // no warning should be logged if all distances clamp config match
            Assert.AreEqual(recovered_logs.Count, 0);

            recovered_logs.Clear();
            Assert.AreEqual(recovered_logs.Count, 0);
            // test per-feeler clamping management
            feeler.EnableClamping = false;
            Assert.IsFalse(feeler.EnableClamping);
            Assert.IsFalse(feeler.Distances[0].EnableClamping);
            feeler.Distances[1].EnableClamping = true;
            Assert.IsTrue(feeler.Distances[1].EnableClamping);
            Assert.IsFalse(feeler.Distances[2].EnableClamping);
            bool clamping_state = false;
            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                clamping_state = feeler.EnableClamping;
            }
            Assert.IsFalse(clamping_state);
            expected_logs = new List<String>() {
                  "The individual distances within attribute feeler" +
                      " of type Feelers have been configured with clamping" +
                      " configurations that differ from that of the parent" +
                      " attribute, please read the individual clamping" +
                      " configurations for each distance"};
            Assert.That(recovered_logs, Is.EquivalentTo(expected_logs));

            recovered_logs.Clear();
            Assert.AreEqual(recovered_logs.Count, 0);
            // test per-feeler clamping management
            feeler.EnableClamping = true;
            Assert.IsTrue(feeler.EnableClamping);
            Assert.IsTrue(feeler.Distances[0].EnableClamping);
            Assert.IsTrue(feeler.Distances[1].EnableClamping);
            Assert.IsTrue(feeler.Distances[2].EnableClamping);
            // no warning should be logged if all distances clamp config match
            Assert.AreEqual(recovered_logs.Count, 0);

            recovered_logs.Clear();
            Assert.AreEqual(recovered_logs.Count, 0);
            // test per-feeler clamping management
            feeler.EnableClamping = true;
            Assert.IsTrue(feeler.EnableClamping);
            Assert.IsTrue(feeler.Distances[0].EnableClamping);
            feeler.Distances[1].EnableClamping = false;
            Assert.IsFalse(feeler.Distances[1].EnableClamping);
            Assert.IsTrue(feeler.Distances[2].EnableClamping);
            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                clamping_state = feeler.EnableClamping;
            }
            Assert.IsTrue(clamping_state);
            expected_logs = new List<String>() {
                  "The individual distances within attribute feeler" +
                      " of type Feelers have been configured with clamping" +
                      " configurations that differ from that of the parent" +
                      " attribute, please read the individual clamping" +
                      " configurations for each distance"};
            Assert.That(recovered_logs, Is.EquivalentTo(expected_logs));
        }


        [Test]
        public void BindFeelerNoIds()
        {
            FalkenFeelerNoIdsContainer feelerContainer =
              new FalkenFeelerNoIdsContainer();
            FieldInfo feelerField =
              typeof(FalkenFeelerNoIdsContainer).GetField("feelerNoIds");
            // Constructing Feelers with an empty string list of IDs is the same as using a null
            // reference to IDs.
            Falken.Feelers feeler = new Falken.Feelers(5.0f, 3.0f, 45.0f, 3, new List<string>());
            feeler.BindAttribute(feelerField, feelerContainer, _falkenContainer);
            Assert.AreEqual(5.0f, feeler.Length);
            Assert.AreEqual(3.0f, feeler.Thickness);
            Assert.AreEqual(45.0f, feeler.FovAngle);

            List<Falken.Number> distances = feeler.Distances;
            Assert.AreEqual(3, distances.Count);

            List<Falken.Category> ids = feeler.Ids;
            Assert.AreEqual(0, ids.Count);
        }

        [Test]
        public void RebindFeeler()
        {
            Falken.AttributeContainer container = new Falken.AttributeContainer();
            Falken.Feelers feeler = new Falken.Feelers("feeler",
              5.0f, 3.0f, 45.0f, 3,
              new List<string>() { "zero", "one", "two" });
            feeler.BindAttribute(null, null, _falkenContainer);
            FalkenInternal.falken.AttributeContainer otherContainer =
              new FalkenInternal.falken.AttributeContainer();
            FalkenInternal.falken.AttributeBase newFeeler =
              new FalkenInternal.falken.AttributeBase(otherContainer, "feeler",
                3, 5.0f, 45.0f, 3.0f,
                new FalkenInternal.std.StringVector(new string[] { "zero", "one", "two" }));

            List<Falken.Number> distances = feeler.Distances;
            distances[0].Value = 0.5f;
            Assert.AreEqual(0.5f, distances[0].Value);
            distances[1].Value = 3.0f;
            Assert.AreEqual(3.0f, distances[1].Value);

            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Assert.That(() => distances[2].Value = 8.0f,
                            Throws.TypeOf<System.ApplicationException>());
            }

            Assert.AreEqual(0.0f, distances[2].Value);

            List<Falken.Category> ids = feeler.Ids;
            ids[0].Value = 1;
            Assert.AreEqual(1, ids[0].Value);
            ids[1].Value = 2;
            Assert.AreEqual(2, ids[1].Value);

            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Assert.That(() => ids[2].Value = 500000,
                            Throws.TypeOf<System.ApplicationException>());
            }

            Assert.AreEqual(0, ids[2].Value);

            feeler.Rebind(newFeeler);
            Assert.AreEqual(0.0f, distances[0].Value);
            Assert.AreEqual(0.0f, distances[1].Value);
            Assert.AreEqual(0.0f, distances[2].Value);
            Assert.AreEqual(0, ids[0].Value);
            Assert.AreEqual(0, ids[1].Value);
            Assert.AreEqual(0, ids[2].Value);
        }
    }

    public class FeelerContainerTest
    {
        private FalkenInternal.falken.AttributeContainer _falkenContainer;

        [SetUp]
        public void Setup()
        {
            _falkenContainer = new FalkenInternal.falken.AttributeContainer();
        }

        [Test]
        public void BindFeelersContainer()
        {
            FalkenFeelerContainer feelersContainer =
              new FalkenFeelerContainer();
            feelersContainer.BindAttributes(_falkenContainer);
            Assert.IsTrue(feelersContainer["feeler"] is Falken.Feelers);
            Falken.Feelers feeler = feelersContainer.feeler;
            Assert.AreEqual(5.0f, feeler.Length);
            Assert.AreEqual(3.0f, feeler.Thickness);
            Assert.AreEqual(45.0f, feeler.FovAngle);

            List<Falken.Number> distances = feeler.Distances;
            Assert.AreEqual(3, distances.Count);

            foreach (Falken.Number distance in distances)
            {
                Assert.AreEqual(0.0f, distance.Minimum);
                Assert.AreEqual(5.0f, distance.Maximum);
                Assert.AreEqual(0.0f, distance.Value);
            }
            distances[0].Value = 0.5f;
            Assert.AreEqual(0.5f, distances[0].Value);
            distances[1].Value = 3.0f;
            Assert.AreEqual(3.0f, distances[1].Value);

            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Assert.That(() => distances[2].Value = 8.0f,
                            Throws.TypeOf<System.ApplicationException>());
            }

            Assert.AreEqual(0.0f, distances[2].Value);

            List<Falken.Category> ids = feeler.Ids;
            Assert.AreEqual(3, ids.Count);

            foreach (Falken.Category id in ids)
            {
                Assert.AreEqual(0, id.Value);
                Assert.IsTrue(
                  Enumerable.SequenceEqual(new string[] { "zero", "one", "two" },
                    (List<string>)id.CategoryValues));
            }
            ids[0].Value = 1;
            Assert.AreEqual(1, ids[0].Value);
            ids[1].Value = 2;
            Assert.AreEqual(2, ids[1].Value);

            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Assert.That(() => ids[2].Value = 500000,
                            Throws.TypeOf<System.ApplicationException>());
            }

            Assert.AreEqual(0, ids[2].Value);
        }

        [Test]
        public void BindFeelerNoIdsContainer()
        {
            FalkenFeelerNoIdsContainer feelersContainer =
              new FalkenFeelerNoIdsContainer();
            feelersContainer.BindAttributes(_falkenContainer);
            Assert.IsTrue(feelersContainer["feelerNoIds"] is Falken.Feelers);
            Falken.Feelers feeler = feelersContainer.feelerNoIds;
            Assert.AreEqual(5.0f, feeler.Length);
            Assert.AreEqual(3.0f, feeler.Thickness);
            Assert.AreEqual(45.0f, feeler.FovAngle);

            List<Falken.Number> distances = feeler.Distances;
            Assert.AreEqual(3, distances.Count);

            foreach (Falken.Number distance in distances)
            {
                Assert.AreEqual(0.0f, distance.Minimum);
                Assert.AreEqual(5.0f, distance.Maximum);
                Assert.AreEqual(0.0f, distance.Value);
            }
            distances[0].Value = 0.5f;
            Assert.AreEqual(0.5f, distances[0].Value);
            distances[1].Value = 3.0f;
            Assert.AreEqual(3.0f, distances[1].Value);

            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Assert.That(() => distances[2].Value = 8.0f,
                            Throws.TypeOf<System.ApplicationException>());
            }

            Assert.AreEqual(0.0f, distances[2].Value);

            List<Falken.Category> ids = feeler.Ids;
            Assert.AreEqual(0, ids.Count);
        }

        [Test]
        public void BindDynamicFeeler()
        {
            Falken.AttributeContainer container = new Falken.AttributeContainer();
            Falken.Feelers feeler = new Falken.Feelers("feeler",
              5.0f, 3.0f, 45.0f, 3,
              new List<string>() { "zero", "one", "two" });
            container["feeler"] = feeler;
            container.BindAttributes(_falkenContainer);
            Assert.AreEqual(1, container.Values.Count);
            Assert.IsTrue(container.ContainsKey("feeler"));
            Assert.AreEqual("feeler", feeler.Name);
        }

        [Test]
        public void ModifyBoundFeeler()
        {
            FalkenFeelerContainer feelersContainer =
              new FalkenFeelerContainer();
            feelersContainer.BindAttributes(_falkenContainer);
            FalkenInternal.falken.AttributeBase feelerAttribute =
              feelersContainer["feeler"].InternalAttribute;
            var internalDistances = feelerAttribute.feelers_distances();
            List<Falken.Number> distances = feelersContainer.feeler.Distances;
            Assert.AreEqual(0.0f, internalDistances[0].number());
            distances[0].Value = 0.5f;
            Assert.AreEqual(0.5f, distances[0].Value);
            Assert.AreEqual(0.5f, internalDistances[0].number());

            Assert.AreEqual(0.0f, internalDistances[1].number());
            distances[1].Value = 1.5f;
            Assert.AreEqual(1.5f, distances[1].Value);
            Assert.AreEqual(1.5f, internalDistances[1].number());

            var internalIds = feelerAttribute.feelers_ids();
            List<Falken.Category> ids = feelersContainer.feeler.Ids;
            Assert.AreEqual(0, internalIds[0].category());
            ids[0].Value = 1;
            Assert.AreEqual(1, ids[0].Value);
            Assert.AreEqual(1, internalIds[0].category());

            Assert.AreEqual(0, internalIds[1].category());
            ids[1].Value = 2;
            Assert.AreEqual(2, ids[1].Value);
            Assert.AreEqual(2, internalIds[1].category());
        }
    }
}
