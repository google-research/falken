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
    public class AttributeContainerTest
    {
        private FalkenInternal.falken.AttributeContainer _falkenContainer;

        [SetUp]
        public void Setup()
        {
            _falkenContainer = new FalkenInternal.falken.AttributeContainer();
        }

        [Test]
        public void AddAttributes()
        {
            Falken.AttributeContainer container =
              new Falken.AttributeContainer();
            container.Add("boolean", new Falken.Boolean("boolean"));
            Assert.IsTrue(container.ContainsKey("boolean"));
            container.Add(new KeyValuePair<string, Falken.AttributeBase>(
              "boolean2", new Falken.Boolean("boolean2")));
            Assert.IsTrue(container.ContainsKey("boolean2"));
            container["boolean3"] = new Falken.Boolean("boolean3");
            Assert.AreEqual(3, container.Count);
        }

        [Test]
        public void AddAttributeToBoundContainer()
        {
            Falken.AttributeContainer container =
              new Falken.AttributeContainer();
            container.Add("boolean", new Falken.Boolean("boolean"));
            container.BindAttributes(_falkenContainer);
            Assert.That(() => container.Add("boolean2", new Falken.Boolean("boolean2")),
                        Throws.TypeOf<InvalidOperationException>());
            Assert.IsFalse(container.ContainsKey("boolean2"));
            Assert.AreEqual(1, container.Count);
            Assert.That(() => container.Add(new KeyValuePair<string, Falken.AttributeBase>(
                                              "boolean2", new Falken.Boolean("boolean2"))),
                        Throws.TypeOf<InvalidOperationException>());
            Assert.IsFalse(container.ContainsKey("boolean2"));
            Assert.AreEqual(1, container.Count);
            Assert.That(() => container["boolean2"] = new Falken.Boolean("boolean2"),
                        Throws.TypeOf<InvalidOperationException>());
            Assert.IsFalse(container.ContainsKey("boolean2"));
            Assert.AreEqual(1, container.Count);
        }

        [Test]
        public void RemoveAttributeBoundContainer()
        {
            Falken.AttributeContainer container =
              new Falken.AttributeContainer();
            container.Add("boolean", new Falken.Boolean("boolean"));
            container.BindAttributes(_falkenContainer);
            Assert.That(() => container.Remove("boolean"),
                        Throws.TypeOf<InvalidOperationException>());
            Assert.IsTrue(container.ContainsKey("boolean"));
            Assert.That(() => container.Remove(new KeyValuePair<string, Falken.AttributeBase>(
                                                 "boolean", new Falken.Boolean("boolean"))),
                        Throws.TypeOf<InvalidOperationException>());
            Assert.IsTrue(container.ContainsKey("boolean"));
        }

        [Test]
        public void ClearContainer()
        {
            Falken.AttributeContainer container =
              new Falken.AttributeContainer();
            container.Add("boolean", new Falken.Boolean("boolean"));
            Assert.AreEqual(1, container.Count);
            container.Clear();
            Assert.AreEqual(0, container.Count);
            container.Clear();
            Assert.AreEqual(0, container.Count);
        }

        [Test]
        public void ClearBoundContainer()
        {
            Falken.AttributeContainer container =
              new Falken.AttributeContainer();
            container.Add("boolean", new Falken.Boolean("boolean"));
            container.BindAttributes(_falkenContainer);
            Assert.That(() => container.Clear(), Throws.TypeOf<InvalidOperationException>());
        }

        [Test]
        public void RemoveAttributes()
        {
            Falken.AttributeContainer container =
              new Falken.AttributeContainer();
            container["boolean"] = new Falken.Boolean("boolean");
            container["boolean2"] = new Falken.Boolean("boolean2");
            Assert.IsTrue(container.ContainsKey("boolean"));
            Assert.AreEqual(2, container.Count);
            Assert.IsTrue(container.Remove("boolean"));
            Assert.IsFalse(container.ContainsKey("boolean"));
            Assert.AreEqual(1, container.Count);
            Assert.IsTrue(container.Remove(
              new KeyValuePair<string, Falken.AttributeBase>("boolean2", null)));
            Assert.IsFalse(container.ContainsKey("boolean2"));
            Assert.AreEqual(0, container.Count);
            Assert.IsFalse(container.Remove("nonExistent"));
        }

        [Test]
        public void GetKeys()
        {
            Falken.AttributeContainer container =
              new Falken.AttributeContainer();
            container["boolean"] = new Falken.Boolean("boolean");
            container["boolean2"] = new Falken.Boolean("boolean2");
            ICollection<string> keys = container.Keys;
            Assert.AreEqual(2, keys.Count);
            Assert.IsTrue(keys.Contains("boolean"));
            Assert.IsTrue(keys.Contains("boolean2"));
        }

        [Test]
        public void GetValues()
        {
            Falken.AttributeContainer container =
              new Falken.AttributeContainer();
            container["boolean"] = new Falken.Boolean("boolean");
            container["boolean2"] = new Falken.Boolean("boolean2");
            ICollection<Falken.AttributeBase> values = container.Values;
            Assert.AreEqual(2, values.Count);
        }

        [Test]
        public void TryGetValue()
        {
            Falken.AttributeContainer container =
              new Falken.AttributeContainer();
            container["boolean"] = new Falken.Boolean("boolean");

            Falken.AttributeBase boolean = null;
            Assert.IsTrue(container.TryGetValue("boolean", out boolean));
            Assert.IsNotNull(boolean);
            Assert.IsTrue(boolean is Falken.Boolean);
        }

        [Test]
        public void TryGetNonExistentValue()
        {
            Falken.AttributeContainer container =
              new Falken.AttributeContainer();

            Falken.AttributeBase boolean = null;
            Assert.IsFalse(container.TryGetValue("boolean", out boolean));
            Assert.IsNull(boolean);
        }

        [Test]
        public void BindContainerWithBoundAttribute()
        {
            Falken.AttributeContainer container =
              new Falken.AttributeContainer();
            Falken.Boolean sharedAttribute = new Falken.Boolean("boolean");
            container["boolean"] = sharedAttribute;
            container.BindAttributes(_falkenContainer);

            Falken.AttributeContainer anotherContainer =
              new Falken.AttributeContainer();
            anotherContainer["boolean"] = sharedAttribute;
            Assert.That(() => anotherContainer.BindAttributes(_falkenContainer),
                        Throws.TypeOf<Falken.AlreadyBoundException>()
                        .With.Message.EqualTo("Can't bind container. Dynamic attribute 'boolean' " +
                                              "is already bound. Make sure to create a " +
                                              "new attribute per container."));
        }

        [Test]
        public void RebindContainer()
        {
            Falken.AttributeContainer container = new Falken.AttributeContainer();
            Falken.Boolean boolean = new Falken.Boolean("boolean");
            container["boolean"] = boolean;
            container.BindAttributes(_falkenContainer);
            boolean.Value = true;
            Assert.IsTrue(boolean.Value);
            FalkenInternal.falken.AttributeContainer otherContainer =
              new FalkenInternal.falken.AttributeContainer();
            FalkenInternal.falken.AttributeBase newBoolean =
              new FalkenInternal.falken.AttributeBase(otherContainer, "boolean",
                FalkenInternal.falken.AttributeBase.Type.kTypeBool);

            container.Rebind(otherContainer);
            Assert.IsFalse(boolean.Value);
        }

        [Test]
        public void LoadAttributes()
        {
            FalkenInternal.falken.AttributeBase boolean =
              new FalkenInternal.falken.AttributeBase(
                _falkenContainer, "boolean",
                FalkenInternal.falken.AttributeBase.Type.kTypeBool);
            FalkenInternal.falken.AttributeBase number =
              new FalkenInternal.falken.AttributeBase(
                _falkenContainer, "number", -1.0f, 1.0f);
            FalkenInternal.falken.AttributeBase category =
              new FalkenInternal.falken.AttributeBase(
                _falkenContainer, "category",
                new FalkenInternal.std.StringVector() { "zero", "one" });
            FalkenInternal.falken.AttributeBase position =
              new FalkenInternal.falken.AttributeBase(
                _falkenContainer, "position",
                FalkenInternal.falken.AttributeBase.Type.kTypePosition);
            FalkenInternal.falken.AttributeBase rotation =
              new FalkenInternal.falken.AttributeBase(
                _falkenContainer, "rotation",
                FalkenInternal.falken.AttributeBase.Type.kTypeRotation);
            FalkenInternal.falken.AttributeBase feeler =
              new FalkenInternal.falken.AttributeBase(
                _falkenContainer, "feeler", 2,
                5.0f, (float)(45.0f / 180.0f * Math.PI /* Convert to radians */), 1.0f,
                new FalkenInternal.std.StringVector() { "zero", "one" });

            Falken.AttributeContainer container = new Falken.AttributeContainer();
            container.LoadAttributes(_falkenContainer);

            Assert.IsTrue(container.Bound);
            Assert.IsTrue(container.ContainsKey("boolean"));
            Assert.IsTrue(container["boolean"] is Falken.Boolean);
            Assert.IsTrue(container["boolean"].Bound);

            Assert.IsTrue(container.ContainsKey("number"));
            Assert.IsTrue(container["number"] is Falken.Number);
            Assert.IsTrue(container["number"].Bound);
            Falken.Number numberAttribute = (Falken.Number)container["number"];
            Assert.AreEqual(-1.0f, numberAttribute.Minimum);
            Assert.AreEqual(1.0f, numberAttribute.Maximum);

            Assert.IsTrue(container.ContainsKey("category"));
            Assert.IsTrue(container["category"] is Falken.Category);
            Assert.IsTrue(container["category"].Bound);
            Falken.Category categoryAttribute = (Falken.Category)container["category"];
            Assert.IsTrue(
              Enumerable.SequenceEqual(categoryAttribute.CategoryValues,
                new string[] { "zero", "one" }));

            Assert.IsTrue(container.ContainsKey("position"));
            Assert.IsTrue(container["position"] is Falken.Position);
            Assert.IsTrue(container["position"].Bound);

            Assert.IsTrue(container.ContainsKey("rotation"));
            Assert.IsTrue(container["rotation"] is Falken.Rotation);
            Assert.IsTrue(container["rotation"].Bound);

            Assert.IsTrue(container.ContainsKey("feeler"));
            Assert.IsTrue(container["feeler"] is Falken.Feelers);
            Assert.IsTrue(container["feeler"].Bound);
            Falken.Feelers feelerAttribute = (Falken.Feelers)container["feeler"];
            Assert.AreEqual(5.0f, feelerAttribute.Length);
            Assert.AreEqual(45.0f, feelerAttribute.FovAngle);
            Assert.AreEqual(1.0f, feelerAttribute.Thickness);
            Assert.AreEqual(2, feelerAttribute.Ids.Count);
            Assert.AreEqual(2, feelerAttribute.Distances.Count);
        }
    }
}
