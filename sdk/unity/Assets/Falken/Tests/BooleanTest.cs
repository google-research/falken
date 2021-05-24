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
using NUnit.Framework;

// Do not warn about missing documentation.
#pragma warning disable 1591

namespace FalkenTests
{
    public class FalkenCustomBool
    {
        private bool _value;
        public FalkenCustomBool(bool value)
        {
            _value = value;
        }

        public bool Value
        {
            get
            {
                return _value;
            }
            set
            {
                _value = value;
            }
        }

        public static implicit operator bool(FalkenCustomBool value) =>
          value._value;
        public static implicit operator FalkenCustomBool(bool value) =>
          new FalkenCustomBool(value);
    }

    public class FalkenBoolMissingImplicitConversion
    {
        private bool _value;
        public FalkenBoolMissingImplicitConversion(bool value)
        {
            _value = value;
        }

        public static implicit operator FalkenBoolMissingImplicitConversion(
          bool value) => new FalkenBoolMissingImplicitConversion(value);
    }

    public class BooleanContainer : Falken.AttributeContainer
    {
        public bool jump = true;
    }

    public class CustomBooleanContainer : Falken.AttributeContainer
    {
        public FalkenCustomBool customBool = new FalkenCustomBool(true);
    }

    public class CustomBooleanContainerMissingConversion : Falken.AttributeContainer
    {
        public FalkenBoolMissingImplicitConversion customBool =
          new FalkenBoolMissingImplicitConversion(false);
    }

    public class BooleanAttributeTest
    {
        private FalkenInternal.falken.AttributeContainer _falkenContainer;

        [SetUp]
        public void Setup()
        {
            _falkenContainer = new FalkenInternal.falken.AttributeContainer();
        }

        [Test]
        public void CreateDynamicBoolean()
        {
            Falken.Boolean attribute = new Falken.Boolean("boolean");
        }

        [Test]
        public void CreateDynamicBooleanNullName()
        {
            Assert.That(() => new Falken.Boolean(null), Throws.TypeOf<ArgumentNullException>()
                        .With.Message.EqualTo("Value cannot be null."));
        }

        [Test]
        public void BindBoolean()
        {
            BooleanContainer booleanContainer = new BooleanContainer();
            FieldInfo jumpField = typeof(BooleanContainer).GetField("jump");
            Falken.Boolean boolean = new Falken.Boolean();
            boolean.BindAttribute(jumpField, booleanContainer, _falkenContainer);
            Assert.AreEqual(true, boolean.Value);
            // Values set on the attribute are reflected in the container.
            boolean.Value = false;
            Assert.AreEqual(false, booleanContainer.jump);
            Assert.AreEqual(false, boolean.Value);
            boolean.Value = true;
            Assert.AreEqual(true, booleanContainer.jump);
            Assert.AreEqual(true, boolean.Value);
            // Values set on the container are reflected in the attribute.
            booleanContainer.jump = false;
            Assert.AreEqual(false, boolean.Value);
            booleanContainer.jump = true;
            Assert.AreEqual(true, boolean.Value);
        }

        [Test]
        public void BooleanClampingTest()
        {
            BooleanContainer booleanContainer = new BooleanContainer();
            FieldInfo jumpField = typeof(BooleanContainer).GetField("jump");
            Falken.Boolean attribute = new Falken.Boolean();
            attribute.BindAttribute(jumpField, booleanContainer, _falkenContainer);

            var recovered_logs = new List<String>();
            System.EventHandler<Falken.Log.MessageArgs> handler = (
                object source, Falken.Log.MessageArgs args) =>
            {
                recovered_logs.Add(args.Message);
            };
            Falken.Log.OnMessage += handler;

            // default clamping value (off)
            var expected_logs = new List<String>() {
                "Attempted to set the clamping configuration" +
                  " of attribute jump, which is of type Bool" +
                  " and therefore it does not support clamping",
                "Attempted to read the clamping configuration of attribute" +
                  " jump, which is of type Bool and therefore it" +
                  " does not support clamping" };

            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                attribute.EnableClamping = true;
                Assert.IsTrue(attribute.EnableClamping);
            }
            Assert.That(recovered_logs, Is.EquivalentTo(expected_logs));
        }

        [Test]
        public void BindCustomBool()
        {
            CustomBooleanContainer booleanContainer =
              new CustomBooleanContainer();
            FieldInfo customBooleanField =
              typeof(CustomBooleanContainer).GetField("customBool");
            Falken.Boolean boolean = new Falken.Boolean();
            boolean.BindAttribute(customBooleanField, booleanContainer, _falkenContainer);
            Assert.AreEqual(true, boolean.Value);
            // Values set on the attribute are reflected in the container.
            boolean.Value = false;
            Assert.AreEqual(false, booleanContainer.customBool.Value);
            Assert.AreEqual(false, boolean.Value);
            boolean.Value = true;
            Assert.AreEqual(true, booleanContainer.customBool.Value);
            Assert.AreEqual(true, boolean.Value);
            // Values set on the container are reflected in the attribute.
            booleanContainer.customBool.Value = false;
            Assert.AreEqual(false, boolean.Value);
            booleanContainer.customBool.Value = true;
            Assert.AreEqual(true, boolean.Value);
        }

        [Test]
        public void BindCustomBoolMissingConversion()
        {
            CustomBooleanContainerMissingConversion booleanContainer =
              new CustomBooleanContainerMissingConversion();
            FieldInfo customBooleanField =
              typeof(CustomBooleanContainerMissingConversion).GetField("customBool");
            Falken.Boolean boolean = new Falken.Boolean();
            Assert.That(() => boolean.BindAttribute(customBooleanField, booleanContainer,
                                                    _falkenContainer),
                        Throws.TypeOf<Falken.UnsupportedFalkenTypeException>()
                        .With.Message.EqualTo(
                          $"Field '{customBooleanField.Name}' is not a bool or can't " +
                          "be converted to/from a boolean."));
        }

        [Test]
        public void RebindBoolean()
        {
            Falken.AttributeContainer container = new Falken.AttributeContainer();
            Falken.Boolean boolean = new Falken.Boolean("boolean");
            boolean.BindAttribute(null, null, _falkenContainer);
            boolean.Value = true;
            Assert.IsTrue(boolean.Value);
            FalkenInternal.falken.AttributeContainer otherContainer =
              new FalkenInternal.falken.AttributeContainer();
            FalkenInternal.falken.AttributeBase newBoolean =
              new FalkenInternal.falken.AttributeBase(otherContainer, "boolean",
                FalkenInternal.falken.AttributeBase.Type.kTypeBool);
            boolean.Rebind(newBoolean);
            Assert.IsFalse(boolean.Value);
            Assert.IsFalse(newBoolean.boolean());
            boolean.Value = true;
            Assert.IsTrue(boolean.Value);
            Assert.IsTrue(newBoolean.boolean());
        }

        [Test]
        public void WriteBoolean()
        {
            BooleanContainer booleanContainer =
              new BooleanContainer();
            booleanContainer.BindAttributes(_falkenContainer);
            Falken.Boolean attribute = (Falken.Boolean)booleanContainer["jump"];
            Assert.IsTrue(attribute.Value);
            Assert.IsTrue(booleanContainer.jump);
            FalkenInternal.falken.AttributeBase internalAttribute =
              attribute.InternalAttribute;
            internalAttribute.set_boolean(false);
            Assert.IsTrue(booleanContainer.jump);
            attribute.Write();
            Assert.IsFalse(booleanContainer.jump);
        }

        [Test]
        public void WriteCustomBoolean()
        {
            CustomBooleanContainer booleanContainer =
              new CustomBooleanContainer();
            booleanContainer.BindAttributes(_falkenContainer);
            Falken.Boolean attribute = (Falken.Boolean)booleanContainer["customBool"];
            Assert.IsTrue(attribute.Value);
            Assert.IsTrue(booleanContainer.customBool.Value);
            FalkenInternal.falken.AttributeBase internalAttribute =
              attribute.InternalAttribute;
            internalAttribute.set_boolean(false);
            Assert.IsTrue(booleanContainer.customBool.Value);
            attribute.Write();
            Assert.IsFalse(booleanContainer.customBool.Value);
        }
    }

    public class BooleanContainerTest
    {
        private FalkenInternal.falken.AttributeContainer _falkenContainer;

        [SetUp]
        public void Setup()
        {
            _falkenContainer = new FalkenInternal.falken.AttributeContainer();
        }

        [Test]
        public void BindBooleanContainer()
        {
            BooleanContainer booleanContainer =
              new BooleanContainer();
            booleanContainer.BindAttributes(_falkenContainer);
            Assert.IsTrue(booleanContainer.Bound);
            Assert.IsTrue(booleanContainer["jump"] is Falken.Boolean);
            Falken.Boolean jump = (Falken.Boolean)booleanContainer["jump"];
            Assert.AreEqual(true, jump.Value);
        }

        [Test]
        public void BindCustomBooleanContainer()
        {
            CustomBooleanContainer booleanContainer =
              new CustomBooleanContainer();
            booleanContainer.BindAttributes(_falkenContainer);
            Assert.IsTrue(booleanContainer.Bound);
            Assert.IsTrue(booleanContainer["customBool"] is Falken.Boolean);
            Falken.Boolean customBool =
              (Falken.Boolean)booleanContainer["customBool"];
            Assert.AreEqual(true, customBool.Value);
        }

        [Test]
        public void BindCustomBooleanContainerMissingConversion()
        {
            CustomBooleanContainerMissingConversion booleanContainer =
              new CustomBooleanContainerMissingConversion();
            Assert.That(() => booleanContainer.BindAttributes(_falkenContainer),
                        Throws.TypeOf<Falken.UnsupportedFalkenTypeException>()
                        .With.Message.EqualTo(
                            $"Field 'customBool' " +
                            $"has unsupported type " +
                            $"'{typeof(FalkenBoolMissingImplicitConversion).ToString()}' " +
                            "or it does not have the necessary implicit conversions."));
        }

        [Test]
        public void BindDynamicBoolean()
        {
            Falken.AttributeContainer container = new Falken.AttributeContainer();
            container["boolean"] = new Falken.Boolean("boolean");
            container.BindAttributes(_falkenContainer);
            Assert.AreEqual(1, container.Values.Count);
            Assert.IsTrue(container.ContainsKey("boolean"));
            Assert.AreEqual("boolean", container["boolean"].Name);
        }
    }
}
