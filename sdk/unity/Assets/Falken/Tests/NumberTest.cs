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
    public class FalkenCustomFloat
    {
        private float _value;
        public FalkenCustomFloat(float value)
        {
            _value = value;
        }

        public float Value
        {
            get
            {
                return _value;
            }
        }

        public static implicit operator float(FalkenCustomFloat value) =>
          value._value;
        public static implicit operator FalkenCustomFloat(float value) =>
          new FalkenCustomFloat(value);
    }

    public class FalkenCustomFloatMissingConversion
    {
        private float _value;
        public FalkenCustomFloatMissingConversion(float value)
        {
            _value = value;
        }

        public static implicit operator float(
          FalkenCustomFloatMissingConversion value) => value._value;
    }

    public class FalkenCustomInt
    {
        private int _value;
        public FalkenCustomInt(int value)
        {
            _value = value;
        }

        public static implicit operator int(FalkenCustomInt value) =>
          value._value;
        public static implicit operator FalkenCustomInt(int value) =>
          new FalkenCustomInt(value);
    }

#if UNITY_5_3_OR_NEWER
    public class FloatNumberContainerUnityRange : Falken.AttributeContainer
    {
        [UnityEngine.Range(-1f, 1f)]
        public float lookUpAngle = 0.5f;
    }
#endif  // UNITY_5_3_OR_NEWER

    public class FloatNumberContainerFalkenRange : Falken.AttributeContainer
    {
        [Falken.Range(-1f, 1f)]
        public float lookUpAngle = 0.5f;
    }

    public class CustomFloatNumberContainer : Falken.AttributeContainer
    {
        [Falken.Range(-1f, 1f)]
        public FalkenCustomFloat customFloat = new FalkenCustomFloat(0.5f);
    }

    public class IntNumberContainer : Falken.AttributeContainer
    {
        [Falken.Range(2, 5)]
        public int energy = 4;
    }

    public class CustomIntNumberContainer : Falken.AttributeContainer
    {
        [Falken.Range(3, 7)]
        public FalkenCustomInt energy = new FalkenCustomInt(4);
    }

    public class FloatContainerWithoutRange : Falken.AttributeContainer
    {
        public float noRange = 3.0f;
    }

    public class CustomFloatMissingImplicitConversion : Falken.AttributeContainer
    {
        [Falken.Range(-1f, 1f)]
        public FalkenCustomFloatMissingConversion customFloat =
          new FalkenCustomFloatMissingConversion(0.5f);
    }

    public class NumberAttributeTest
    {

        private FalkenInternal.falken.AttributeContainer _falkenContainer;

        [SetUp]
        public void Setup()
        {
            _falkenContainer = new FalkenInternal.falken.AttributeContainer();
        }

        [Test]
        public void CreateDynamicNumber()
        {
            Falken.Number number = new Falken.Number("number", 0.0f, 2.0f);
        }

        [Test]
        public void CreateDynamicNumberNullName()
        {
            Assert.That(() => new Falken.Number(null, 0.0f, 2.0f),
                        Throws.TypeOf<ArgumentNullException>());
        }

        [Test]
        public void CreateDynamicNumberMinBiggerThanMax()
        {
            Assert.That(() => new Falken.Number("number", 3.5f, -2.5f),
                        Throws.TypeOf<ArgumentException>()
                        .With.Message.EqualTo("Min '3.5' can't be bigger than '-2.5'"));
        }

        [Test]
        public void BindFloatNumberWithFalkenRange()
        {
            var numberContainer = new FloatNumberContainerFalkenRange();
            FieldInfo lookUpAngleField =
              typeof(FloatNumberContainerFalkenRange).GetField("lookUpAngle");
            Falken.Number number = new Falken.Number();
            number.BindAttribute(lookUpAngleField, numberContainer, _falkenContainer);
            Assert.AreEqual(-1.0f, number.Minimum);
            Assert.AreEqual(1.0f, number.Maximum);
            Assert.AreEqual(0.5f, number.Value);
            Assert.AreEqual("lookUpAngle", number.Name);
            number.Value = -0.5f;
            Assert.AreEqual(-0.5f, numberContainer.lookUpAngle);
            numberContainer.lookUpAngle = 0.707f;
            Assert.AreEqual(0.707f, number.Value);
        }

#if UNITY_5_3_OR_NEWER
        [Test]
        public void BindFloatNumberWithUnityRange()
        {
            var numberContainer = new FloatNumberContainerUnityRange();
            FieldInfo lookUpAngleField =
              typeof(FloatNumberContainerUnityRange).GetField("lookUpAngle");
            Falken.Number number = new Falken.Number();
            number.BindAttribute(lookUpAngleField, numberContainer, _falkenContainer);
            Assert.AreEqual(-1.0f, number.Minimum);
            Assert.AreEqual(1.0f, number.Maximum);
            Assert.AreEqual(0.5f, number.Value);
            Assert.AreEqual("lookUpAngle", number.Name);
            number.Value = -0.5f;
            Assert.AreEqual(-0.5f, numberContainer.lookUpAngle);
            numberContainer.lookUpAngle = 0.707f;
            Assert.AreEqual(0.707f, number.Value);
        }
#endif  // UNITY_5_3_OR_NEWER

        [Test]
        public void BindCustomFloatNumber()
        {
            CustomFloatNumberContainer numberContainer = new CustomFloatNumberContainer();
            FieldInfo customFloatField =
              typeof(CustomFloatNumberContainer).GetField("customFloat");
            Falken.Number number = new Falken.Number();
            number.BindAttribute(customFloatField, numberContainer, _falkenContainer);
            Assert.AreEqual(-1.0f, number.Minimum);
            Assert.AreEqual(1.0f, number.Maximum);
            Assert.AreEqual(0.5f, number.Value);
            Assert.AreEqual("customFloat", number.Name);
        }

        [Test]
        public void BindIntNumber()
        {
            IntNumberContainer numberContainer = new IntNumberContainer();
            FieldInfo energyField =
              typeof(IntNumberContainer).GetField("energy");
            Falken.Number number = new Falken.Number();
            number.BindAttribute(energyField, numberContainer, _falkenContainer);
            Assert.AreEqual(2.0f, number.Minimum);
            Assert.AreEqual(5.0f, number.Maximum);
            Assert.AreEqual(4.0f, number.Value);
            Assert.AreEqual("energy", number.Name);
        }

        [Test]
        public void BindCustomIntNumber()
        {
            CustomIntNumberContainer numberContainer = new CustomIntNumberContainer();
            FieldInfo customIntField =
              typeof(CustomIntNumberContainer).GetField("energy");
            Falken.Number number = new Falken.Number();
            number.BindAttribute(customIntField, numberContainer, _falkenContainer);
            Assert.AreEqual(3.0f, number.Minimum);
            Assert.AreEqual(7.0f, number.Maximum);
            Assert.AreEqual(4.0f, number.Value);
            Assert.AreEqual("energy", number.Name);
        }

        [Test]
        public void BindNoRangeFloatNumber()
        {
            FloatContainerWithoutRange numberContainer =
              new FloatContainerWithoutRange();
            FieldInfo field =
              typeof(FloatContainerWithoutRange).GetField("noRange");
            Falken.Number number = new Falken.Number();
            Assert.That(() => number.BindAttribute(field, numberContainer, _falkenContainer),
                        Throws.TypeOf<Falken.UnsupportedFalkenTypeException>()
                        .With.Message.EqualTo($"Number field '{field.Name}' can't be bound since " +
                                              "there's no range attribute defined. " +
                                              "You must supply a min and max value for " +
                                              "Falken to work with numbers."));
        }

        [Test]
        public void BindMissingImplicitConversionNumber()
        {
            CustomFloatMissingImplicitConversion numberContainer =
              new CustomFloatMissingImplicitConversion();
            FieldInfo customFloatField =
              typeof(CustomFloatMissingImplicitConversion).GetField("customFloat");
            Falken.Number number = new Falken.Number();
            Assert.That(() => number.BindAttribute(customFloatField, numberContainer,
                                                   _falkenContainer),
                        Throws.TypeOf<Falken.UnsupportedFalkenTypeException>()
                        .With.Message.EqualTo($"Field '{customFloatField.Name}' is not a float " +
                                              "or integer or it does not have the implicit " +
                                              "conversions defined."));
        }

        [Test]
        public void RebindNumber()
        {
            Falken.AttributeContainer container = new Falken.AttributeContainer();
            Falken.Number number =
              new Falken.Number("number", 1.5f, 3.0f);
            number.BindAttribute(null, null, _falkenContainer);
            number.Value = 2.0f;
            Assert.AreEqual(2.0f, number.Value);
            FalkenInternal.falken.AttributeContainer otherContainer =
              new FalkenInternal.falken.AttributeContainer();
            FalkenInternal.falken.AttributeBase newNumber =
              new FalkenInternal.falken.AttributeBase(otherContainer, "number",
                1.5f, 3.0f);
            number.Rebind(newNumber);
            Assert.AreEqual(1.5f, number.Value);
            Assert.AreEqual(1.5f, newNumber.number());
            number.Value = 2.0f;
            Assert.AreEqual(2.0f, number.Value);
            Assert.AreEqual(2.0f, newNumber.number());
        }

        [Test]
        public void WriteNumber()
        {
            var numberContainer = new FloatNumberContainerFalkenRange();
            numberContainer.BindAttributes(_falkenContainer);
            Falken.Number attribute = (Falken.Number)numberContainer["lookUpAngle"];
            Assert.AreEqual(0.5f, attribute.Value);
            FalkenInternal.falken.AttributeBase internalAttribute =
              attribute.InternalAttribute;
            internalAttribute.set_number(1.0f);
            attribute.Write();
            Assert.AreEqual(1.0f, numberContainer.lookUpAngle);
        }

        [Test]
        public void WriteCustomNumber()
        {
            CustomFloatNumberContainer numberContainer =
              new CustomFloatNumberContainer();
            numberContainer.BindAttributes(_falkenContainer);
            Falken.Number attribute = (Falken.Number)numberContainer["customFloat"];
            Assert.AreEqual(0.5f, attribute.Value);
            FalkenInternal.falken.AttributeBase internalAttribute =
              attribute.InternalAttribute;
            internalAttribute.set_number(1.0f);
            attribute.Write();
            Assert.AreEqual(1.0f, numberContainer.customFloat.Value);
        }

        [Test]
        public void NumberValidity()
        {
            var numberContainer = new FloatNumberContainerFalkenRange();
            FieldInfo lookUpAngleField =
              typeof(FloatNumberContainerFalkenRange).GetField("lookUpAngle");
            Falken.Number number = new Falken.Number();
            number.BindAttribute(lookUpAngleField, numberContainer, _falkenContainer);
            Assert.IsNull(number.ReadFieldIfValid());
            number.Value = 0.0f;
            Assert.IsNotNull(number.ReadFieldIfValid());
            number.Value = 0.5f;
            Assert.IsNotNull(number.ReadFieldIfValid());
            number.InvalidateNonFalkenFieldValue();
            Assert.IsNull(number.ReadFieldIfValid());
        }

        [Test]
        public void NumberClampingSettings()
        {
            var numberContainer = new FloatNumberContainerFalkenRange();
            FieldInfo lookUpAngleField =
              typeof(FloatNumberContainerFalkenRange).GetField("lookUpAngle");
            Falken.Number attribute = new Falken.Number();
            attribute.BindAttribute(lookUpAngleField, numberContainer, _falkenContainer);

            var recovered_logs = new List<String>();
            System.EventHandler<Falken.Log.MessageArgs> handler = (
                object source, Falken.Log.MessageArgs args) =>
            {
                recovered_logs.Add(args.Message);
            };
            Falken.Log.OnMessage += handler;

            // default clamping value (off)
            var expected_logs = new List<String>() {
                "Unable to set value of attribute 'lookUpAngle' to -2 as it is out" +
                    " of the specified range -1 to 1.",
                "Unable to set value of attribute 'lookUpAngle' to 2 as it is out" +
                    " of the specified range -1 to 1." };
            Assert.IsFalse(attribute.EnableClamping);
            attribute.Value = 0.0f;
            Assert.AreEqual(0.0f, attribute.Value);

            Falken.Log.Level = Falken.LogLevel.Fatal;
            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Assert.That(() => attribute.Value = -2.0f,
                            Throws.TypeOf<ApplicationException>());
                Assert.That(() => attribute.Value = 2.0f,
                            Throws.TypeOf<ApplicationException>());
            }
            Assert.That(recovered_logs, Is.EquivalentTo(expected_logs));

            // with clamping on
            recovered_logs.Clear();
            attribute.EnableClamping = true;
            Assert.IsTrue(attribute.EnableClamping);
            attribute.Value = 0.0f;
            Assert.AreEqual(0.0f, attribute.Value);
            attribute.Value = -2.0f;
            Assert.AreEqual(-1.0f, attribute.Value);
            attribute.Value = 2.0f;
            Assert.AreEqual(1.0f, attribute.Value);
            Assert.AreEqual(0, recovered_logs.Count);

            // with clamping off
            recovered_logs.Clear();
            attribute.EnableClamping = false;
            Assert.IsFalse(attribute.EnableClamping);
            attribute.Value = 0.0f;
            Assert.AreEqual(0.0f, attribute.Value);

            Falken.Log.Level = Falken.LogLevel.Fatal;
            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Assert.That(() => attribute.Value = -2.0f,
                            Throws.TypeOf<ApplicationException>());
                Assert.That(() => attribute.Value = 2.0f,
                            Throws.TypeOf<ApplicationException>());
            }
            Assert.That(recovered_logs, Is.EquivalentTo(expected_logs));
        }
    }

    public class NumberContainerTest
    {
        private FalkenInternal.falken.AttributeContainer _falkenContainer;

        [SetUp]
        public void Setup()
        {
            _falkenContainer = new FalkenInternal.falken.AttributeContainer();
        }

        [Test]
        public void BindFloatContainer()
        {
            var numberContainer = new FloatNumberContainerFalkenRange();
            numberContainer.BindAttributes(_falkenContainer);
            Assert.IsTrue(numberContainer.Bound);
            Assert.IsTrue(numberContainer["lookUpAngle"] is Falken.Number);
            Falken.Number lookUp = (Falken.Number)numberContainer["lookUpAngle"];
            Assert.AreEqual(-1.0f, lookUp.Minimum);
            Assert.AreEqual(1.0f, lookUp.Maximum);
            Assert.AreEqual(0.5f, lookUp.Value);
        }

        [Test]
        public void BindIntContainer()
        {
            IntNumberContainer numberContainer =
              new IntNumberContainer();
            numberContainer.BindAttributes(_falkenContainer);
            Assert.IsTrue(numberContainer.Bound);
            Assert.IsTrue(numberContainer["energy"] is Falken.Number);
            Falken.Number energy = (Falken.Number)numberContainer["energy"];
            Assert.AreEqual(2.0f, energy.Minimum);
            Assert.AreEqual(5.0f, energy.Maximum);
            Assert.AreEqual(4.0f, energy.Value);
        }

        [Test]
        public void BindCustomFloatContainer()
        {
            CustomFloatNumberContainer numberContainer =
              new CustomFloatNumberContainer();
            numberContainer.BindAttributes(_falkenContainer);
            Assert.IsTrue(numberContainer.Bound);
            Assert.IsTrue(numberContainer["customFloat"] is Falken.Number);
            Falken.Number customFloat = (Falken.Number)numberContainer["customFloat"];
            Assert.AreEqual(-1.0f, customFloat.Minimum);
            Assert.AreEqual(1.0f, customFloat.Maximum);
            Assert.AreEqual(0.5f, customFloat.Value);
        }

        [Test]
        public void BindCustomIntContainer()
        {
            CustomIntNumberContainer numberContainer =
              new CustomIntNumberContainer();
            numberContainer.BindAttributes(_falkenContainer);
            Assert.IsTrue(numberContainer.Bound);
            Assert.IsTrue(numberContainer["energy"] is Falken.Number);
            Falken.Number energy = (Falken.Number)numberContainer["energy"];
            Assert.AreEqual(3.0f, energy.Minimum);
            Assert.AreEqual(7.0f, energy.Maximum);
            Assert.AreEqual(4.0f, energy.Value);
        }

        [Test]
        public void BindNoRangeContainer()
        {
            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                FloatContainerWithoutRange numberContainer =
                  new FloatContainerWithoutRange();
                Assert.That(() => numberContainer.BindAttributes(_falkenContainer),
                            Throws.TypeOf<Falken.UnsupportedFalkenTypeException>()
                            .With.Message.EqualTo("Number field 'noRange' can't be bound since " +
                                                  "there's no range attribute defined. You " +
                                                  "must supply a min and max value for Falken " +
                                                  "to work with numbers."));
                Assert.IsFalse(numberContainer.ContainsKey("noRange"));
            }
        }

        [Test]
        public void BindMissingImplicitConversionContainer()
        {
            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                CustomFloatMissingImplicitConversion numberContainer =
                  new CustomFloatMissingImplicitConversion();
                Assert.That(() => numberContainer.BindAttributes(_falkenContainer),
                            Throws.TypeOf<Falken.UnsupportedFalkenTypeException>()
                            .With.Message.EqualTo(
                              "Field 'customFloat' has unsupported type " +
                              $"'{typeof(FalkenCustomFloatMissingConversion).ToString()}' " +
                              "or it does not have the necessary implicit conversions."));
                Assert.IsFalse(numberContainer.ContainsKey("customFloat"));
            }
        }

        public class ContainerWithUnsupportedField : Falken.AttributeContainer
        {
            [Falken.Range(-1f, 1f)]
            public float lookUpAngle = 0.5f;
            public double unsupportedType = 4.0;
        }

        [Test]
        public void BindContainerWithUnsupportedType()
        {
            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                ContainerWithUnsupportedField numberContainer = new ContainerWithUnsupportedField();
                Assert.That(() => numberContainer.BindAttributes(_falkenContainer),
                            Throws.TypeOf<Falken.UnsupportedFalkenTypeException>()
                            .With.Message.EqualTo(
                              "Field 'unsupportedType' has unsupported type " +
                              $"'{typeof(double).ToString()}' " +
                              "or it does not have the necessary implicit conversions."));
                Assert.IsFalse(numberContainer.ContainsKey("unsupportedType"));
            }
        }

        [Test]
        public void BindDynamicNumber()
        {
            Falken.AttributeContainer container = new Falken.AttributeContainer();
            Falken.Number number = new Falken.Number("number", 0.0f, 5.0f);
            container["number"] = number;
            container.BindAttributes(_falkenContainer);
            Assert.AreEqual(1, container.Values.Count);
            Assert.IsTrue(container.ContainsKey("number"));
            Assert.AreEqual("number", number.Name);
            Assert.AreEqual(0.0f, number.Minimum);
            Assert.AreEqual(5.0, number.Maximum);
        }
    }
}
