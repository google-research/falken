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
    public class PositionVectorTest
    {
        [Test]
        public void ConstructDefaultPositionVector()
        {
            Falken.PositionVector positionVector = new Falken.PositionVector();
            Assert.AreEqual(0.0f, positionVector.X);
            Assert.AreEqual(0.0f, positionVector.Y);
            Assert.AreEqual(0.0f, positionVector.Z);
        }

        [Test]
        public void ConstructPositionVectorSameValue()
        {
            Falken.PositionVector positionVector = new Falken.PositionVector(3.0f);
            Assert.AreEqual(3.0f, positionVector.X);
            Assert.AreEqual(3.0f, positionVector.Y);
            Assert.AreEqual(3.0f, positionVector.Z);
        }

        [Test]
        public void ConstructPositionVectorDifferentComponents()
        {
            Falken.PositionVector positionVector =
              new Falken.PositionVector(1.0f, 1.5f, 5.0f);
            Assert.AreEqual(1.0f, positionVector.X);
            Assert.AreEqual(1.5f, positionVector.Y);
            Assert.AreEqual(5.0f, positionVector.Z);
        }

        [Test]
        public void ConstructPositionVectorInternalFalkenPosition()
        {
            FalkenInternal.falken.Position falkenPosition =
              new FalkenInternal.falken.Position();
            falkenPosition.x = 5.0f;
            falkenPosition.y = 2.0f;
            falkenPosition.z = 1.5f;
            Falken.PositionVector positionVector =
              new Falken.PositionVector(falkenPosition);
            Assert.AreEqual(5.0f, positionVector.X);
            Assert.AreEqual(2.0f, positionVector.Y);
            Assert.AreEqual(1.5f, positionVector.Z);
        }

#if UNITY_5_3_OR_NEWER
        [Test]
        public void ConstructPositionVectorUsingUnityVector()
        {
            UnityEngine.Vector3 vector =
              new UnityEngine.Vector3(0.5f, 1.0f, -3.0f);
            Falken.PositionVector positionVector =
              new Falken.PositionVector(vector);
            Assert.AreEqual(0.5f, positionVector.X);
            Assert.AreEqual(1.0f, positionVector.Y);
            Assert.AreEqual(-3.0f, positionVector.Z);
        }
#endif  // UNITY_5_3_OR_NEWER

#if UNITY_5_3_OR_NEWER
        [Test]
        public void ImplicitUnityVectorToPositionVector()
        {
            Falken.PositionVector positionVector =
              new UnityEngine.Vector3(1.0f, 2.0f, 3.0f);
            Assert.AreEqual(1.0f, positionVector.X);
            Assert.AreEqual(2.0f, positionVector.Y);
            Assert.AreEqual(3.0f, positionVector.Z);
        }
#endif  // UNITY_5_3_OR_NEWER

#if UNITY_5_3_OR_NEWER
        [Test]
        public void ImplicitPositionVectorToUnityVector()
        {
            UnityEngine.Vector3 vector =
              new Falken.PositionVector(1.0f, 2.0f, 3.0f);
            Assert.AreEqual(1.0f, vector.x);
            Assert.AreEqual(2.0f, vector.y);
            Assert.AreEqual(3.0f, vector.z);
        }
#endif  // UNITY_5_3_OR_NEWER
    }

    public class PositionVectorContainer : Falken.AttributeContainer
    {
        public Falken.PositionVector position =
          new Falken.PositionVector(1.0f, 2.0f, 2.5f);
    }

    public class FalkenCustomPositionVector
    {
        private Falken.PositionVector _value;
        public FalkenCustomPositionVector(Falken.PositionVector value)
        {
            _value = value;
        }

        public Falken.PositionVector Value
        {
            get
            {
                return _value;
            }
        }

        public static implicit operator Falken.PositionVector(
          FalkenCustomPositionVector value) =>
            value._value;
        public static implicit operator FalkenCustomPositionVector(
          Falken.PositionVector value) =>
            new FalkenCustomPositionVector(value);
    }

    public class CustomPositionVectorContainer : Falken.AttributeContainer
    {
        public FalkenCustomPositionVector position =
          new FalkenCustomPositionVector(new Falken.PositionVector(1.0f, 2.0f, 2.5f));
    }

#if UNITY_5_3_OR_NEWER
    public class UnityVectorContainer : Falken.AttributeContainer
    {
        public UnityEngine.Vector3 vector = new UnityEngine.Vector3(-1.0f, 2.5f, 3.0f);
    }
#endif  // UNITY_5_3_OR_NEWER

    public class InheritedPositionContainer
    {
        [Falken.FalkenInheritedAttribute]
        public Falken.PositionVector inheritedPosition =
          new Falken.PositionVector();
    }

    public class PositionAttributeTest
    {
        private FalkenInternal.falken.AttributeContainer _falkenContainer;

        [SetUp]
        public void Setup()
        {
            _falkenContainer = new FalkenInternal.falken.AttributeContainer();
        }

        [Test]
        public void BindPosition()
        {
            PositionVectorContainer positionContainer =
              new PositionVectorContainer();
            FieldInfo positionField =
              typeof(PositionVectorContainer).GetField("position");
            Falken.Position position = new Falken.Position();
            position.BindAttribute(positionField, positionContainer, _falkenContainer);
            Falken.PositionVector positionVector = position.Value;
            Assert.AreEqual(1.0f, positionVector.X);
            Assert.AreEqual(2.0f, positionVector.Y);
            Assert.AreEqual(2.5f, positionVector.Z);
            Assert.AreEqual("position", position.Name);
        }

        [Test]
        public void BindCustomPosition()
        {
            CustomPositionVectorContainer positionContainer =
              new CustomPositionVectorContainer();
            FieldInfo positionField =
              typeof(CustomPositionVectorContainer).GetField("position");
            Falken.Position position = new Falken.Position();
            position.BindAttribute(positionField, positionContainer, _falkenContainer);
            Falken.PositionVector positionVector = position.Value;
            Assert.AreEqual(1.0f, positionVector.X);
            Assert.AreEqual(2.0f, positionVector.Y);
            Assert.AreEqual(2.5f, positionVector.Z);
            Assert.AreEqual("position", position.Name);
        }

        [Test]
        public void ModifyPosition()
        {
            PositionVectorContainer positionContainer =
              new PositionVectorContainer();
            FieldInfo positionField =
              typeof(PositionVectorContainer).GetField("position");
            Falken.Position position = new Falken.Position();
            position.BindAttribute(positionField, positionContainer, _falkenContainer);
            Falken.PositionVector positionVector =
              new Falken.PositionVector(10.0f, 20.0f, 55.0f);
            position.Value = positionVector;
            positionVector = position.Value;
            Assert.AreEqual(10.0f, positionVector.X);
            Assert.AreEqual(20.0f, positionVector.Y);
            Assert.AreEqual(55.0f, positionVector.Z);

            position.Value = new Falken.PositionVector(5.0f);
            positionVector = position.Value;
            Assert.AreEqual(5.0f, positionVector.X);
            Assert.AreEqual(5.0f, positionVector.Y);
            Assert.AreEqual(5.0f, positionVector.Z);
        }

#if UNITY_5_3_OR_NEWER
        [Test]
        public void BindUnityVector()
        {
            UnityVectorContainer positionContainer =
              new UnityVectorContainer();
            FieldInfo vectorField =
              typeof(UnityVectorContainer).GetField("vector");
            Falken.Position position = new Falken.Position();
            position.BindAttribute(vectorField, positionContainer, _falkenContainer);
            Falken.PositionVector positionVector = position.Value;
            Assert.AreEqual(-1.0f, positionVector.X);
            Assert.AreEqual(2.5f, positionVector.Y);
            Assert.AreEqual(3.0f, positionVector.Z);

            position.Value = new UnityEngine.Vector3(1.0f, 2.5f, -0.5f);
            positionVector = position.Value;
            Assert.AreEqual(1.0f, positionVector.X);
            Assert.AreEqual(2.5f, positionVector.Y);
            Assert.AreEqual(-0.5f, positionVector.Z);

            positionContainer.vector = new UnityEngine.Vector3(3.0f, 2.0f, 1.0f);
            Assert.AreEqual(3.0f, position.Value.X);
            Assert.AreEqual(2.0f, position.Value.Y);
            Assert.AreEqual(1.0f, position.Value.Z);

            position.Value = new UnityEngine.Vector3(4.0f, 5.0f, 6.0f);
            Assert.AreEqual(4.0f, positionContainer.vector.x);
            Assert.AreEqual(5.0f, positionContainer.vector.y);
            Assert.AreEqual(6.0f, positionContainer.vector.z);
        }
#endif  // UNITY_5_3_OR_NEWER

        [Test]
        public void BindInheritedPosition()
        {
            InheritedPositionContainer positionContainer =
              new InheritedPositionContainer();
            FieldInfo positionField =
              typeof(InheritedPositionContainer).GetField("inheritedPosition");
            FalkenInternal.falken.AttributeBase attribute =
              new FalkenInternal.falken.AttributeBase(
                _falkenContainer, positionField.Name,
                FalkenInternal.falken.AttributeBase.Type.kTypePosition);
            Falken.Position position = new Falken.Position();
            position.BindAttribute(positionField, positionContainer, _falkenContainer);
        }

        [Test]
        public void BindInheritedPositionNotFound()
        {
            InheritedPositionContainer positionContainer =
              new InheritedPositionContainer();
            FieldInfo positionField =
              typeof(InheritedPositionContainer).GetField("inheritedPosition");
            Falken.Position position = new Falken.Position();
            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Assert.That(() => position.BindAttribute(positionField, positionContainer,
                                                         _falkenContainer),
                            Throws.TypeOf<Falken.InheritedAttributeNotFoundException>()
                            .With.Message.EqualTo("Inherited field 'inheritedPosition' " +
                                                  "was not found in the container."));
            }
        }

        [Test]
        public void BindInheritedPositionTypeMismatch()
        {
            InheritedPositionContainer positionContainer =
              new InheritedPositionContainer();
            FieldInfo positionField =
              typeof(InheritedPositionContainer).GetField("inheritedPosition");
            FalkenInternal.falken.AttributeBase attribute =
              new FalkenInternal.falken.AttributeBase(
                _falkenContainer, "inheritedPosition",
                FalkenInternal.falken.AttributeBase.Type.kTypeRotation);
            Falken.Position position = new Falken.Position();
            Assert.That(() => position.BindAttribute(positionField, positionContainer,
                                                     _falkenContainer),
                        Throws.TypeOf<Falken.InheritedAttributeNotFoundException>()
                        .With.Message.EqualTo($"Inherited field '{positionField.Name}' has " +
                                              $"a position type but the attribute type " +
                                              $"is '{attribute.type()}'"));
        }

        [Test]
        public void WritePosition()
        {
            PositionVectorContainer positionContainer =
              new PositionVectorContainer();
            positionContainer.BindAttributes(_falkenContainer);
            Falken.Position attribute = (Falken.Position)positionContainer["position"];
            Assert.AreEqual(1.0f, attribute.Value.X);
            Assert.AreEqual(2.0f, attribute.Value.Y);
            Assert.AreEqual(2.5f, attribute.Value.Z);

            FalkenInternal.falken.AttributeBase internalAttribute =
              attribute.InternalAttribute;
            internalAttribute.set_position(
              new FalkenInternal.falken.Position(5.0f, 6.0f, 7.0f));
            attribute.Write();
            Assert.AreEqual(5.0f, attribute.Value.X);
            Assert.AreEqual(6.0f, attribute.Value.Y);
            Assert.AreEqual(7.0f, attribute.Value.Z);

            Assert.AreEqual(5.0f, positionContainer.position.X);
            Assert.AreEqual(6.0f, positionContainer.position.Y);
            Assert.AreEqual(7.0f, positionContainer.position.Z);
        }

        [Test]
        public void WriteCustomPosition()
        {
            CustomPositionVectorContainer positionContainer =
              new CustomPositionVectorContainer();
            positionContainer.BindAttributes(_falkenContainer);
            Falken.Position attribute = (Falken.Position)positionContainer["position"];
            Assert.AreEqual(1.0f, attribute.Value.X);
            Assert.AreEqual(2.0f, attribute.Value.Y);
            Assert.AreEqual(2.5f, attribute.Value.Z);

            FalkenInternal.falken.AttributeBase internalAttribute =
              attribute.InternalAttribute;
            internalAttribute.set_position(
              new FalkenInternal.falken.Position(5.0f, 6.0f, 7.0f));
            attribute.Write();

            Assert.AreEqual(5.0f, attribute.Value.X);
            Assert.AreEqual(6.0f, attribute.Value.Y);
            Assert.AreEqual(7.0f, attribute.Value.Z);

            Assert.AreEqual(5.0f, positionContainer.position.Value.X);
            Assert.AreEqual(6.0f, positionContainer.position.Value.Y);
            Assert.AreEqual(7.0f, positionContainer.position.Value.Z);
        }

        [Test]
        public void PositionValidity()
        {
          PositionVectorContainer positionContainer =
            new PositionVectorContainer();
          FieldInfo vectorField =
            typeof(PositionVectorContainer).GetField("position");
          Falken.Position position = new Falken.Position();
          position.BindAttribute(vectorField, positionContainer, _falkenContainer);
          var positionVector = position.Value;
          Assert.IsNull(position.ReadFieldIfValid());
          position.Value = positionVector;
          Assert.IsNotNull(position.ReadFieldIfValid());
          position.InvalidateNonFalkenFieldValue();
          Assert.IsNull(position.ReadFieldIfValid());
        }

        [Test]
        public void PositionClampingTest()
        {
          PositionVectorContainer positionContainer =
            new PositionVectorContainer();
          FieldInfo vectorField =
            typeof(PositionVectorContainer).GetField("position");
          Falken.Position attribute = new Falken.Position();
          attribute.BindAttribute(vectorField, positionContainer, _falkenContainer);

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
                " of attribute position, which is of type Position" +
                " and therefore it does not support clamping",
              "Attempted to read the clamping configuration of attribute" +
                " position, which is of type Position and therefore it" +
                " does not support clamping" };
          Falken.Log.Level = Falken.LogLevel.Fatal;
          using (var ignoreErrorMessages = new IgnoreErrorMessages())
          {
            attribute.EnableClamping = true;
              Assert.IsTrue(attribute.EnableClamping);
          }
          Assert.That(recovered_logs, Is.EquivalentTo(expected_logs));
        }
    }

    public class PositionContainerTest
    {

        private FalkenInternal.falken.AttributeContainer _falkenContainer;

        [SetUp]
        public void Setup()
        {
            _falkenContainer = new FalkenInternal.falken.AttributeContainer();
        }

        [Test]
        public void BindPositionContainer()
        {
            PositionVectorContainer positionContainer = new PositionVectorContainer();
            positionContainer.BindAttributes(_falkenContainer);
            Assert.IsTrue(positionContainer["position"] is Falken.Position);
            Falken.Position position = (Falken.Position)positionContainer["position"];
            Falken.PositionVector positionVector = position.Value;
            Assert.AreEqual(1.0f, positionVector.X);
            Assert.AreEqual(2.0f, positionVector.Y);
            Assert.AreEqual(2.5f, positionVector.Z);
        }

        [Test]
        public void BindCustomPositionContainer()
        {
            CustomPositionVectorContainer positionContainer = new CustomPositionVectorContainer();
            positionContainer.BindAttributes(_falkenContainer);
            Assert.IsTrue(positionContainer["position"] is Falken.Position);
            Falken.Position position = (Falken.Position)positionContainer["position"];
            Falken.PositionVector positionVector = position.Value;
            Assert.AreEqual(1.0f, positionVector.X);
            Assert.AreEqual(2.0f, positionVector.Y);
            Assert.AreEqual(2.5f, positionVector.Z);
        }

#if UNITY_5_3_OR_NEWER
        [Test]
        public void BindUnityVectorContainer()
        {
            UnityVectorContainer positionContainer =
              new UnityVectorContainer();
            positionContainer.BindAttributes(_falkenContainer);
            Assert.IsTrue(positionContainer["vector"] is Falken.Position);
            Falken.Position position =
              (Falken.Position)positionContainer["vector"];
            Falken.PositionVector positionVector = position.Value;
            Assert.AreEqual(-1.0f, positionVector.X);
            Assert.AreEqual(2.5f, positionVector.Y);
            Assert.AreEqual(3.0f, positionVector.Z);

            position.Value = new UnityEngine.Vector3(1.0f, 2.5f, -0.5f);
            positionVector = position.Value;
            Assert.AreEqual(1.0f, positionVector.X);
            Assert.AreEqual(2.5f, positionVector.Y);
            Assert.AreEqual(-0.5f, positionVector.Z);
        }
#endif  // UNITY_5_3_OR_NEWER
    }
}
