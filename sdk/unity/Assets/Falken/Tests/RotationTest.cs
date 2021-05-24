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
    public class QuaternionTest
    {
        [Test]
        public void ConstructDefaultQuaternion()
        {
            Falken.RotationQuaternion quaternion = new Falken.RotationQuaternion();
            Assert.AreEqual(0.0f, quaternion.X);
            Assert.AreEqual(0.0f, quaternion.Y);
            Assert.AreEqual(0.0f, quaternion.Z);
            Assert.AreEqual(1.0f, quaternion.W);
        }

        [Test]
        public void ConstructQuaternionSameValue()
        {
            Falken.RotationQuaternion quaternion = new Falken.RotationQuaternion(0.5f);
            Assert.AreEqual(0.5f, quaternion.X);
            Assert.AreEqual(0.5f, quaternion.Y);
            Assert.AreEqual(0.5f, quaternion.Z);
            Assert.AreEqual(1.0f, quaternion.W);
        }

        [Test]
        public void ConstructQuaternionDifferentComponents()
        {
            Falken.RotationQuaternion quaternion =
              new Falken.RotationQuaternion(0.25f, 0.5f, 0.75f, 0.0f);
            Assert.AreEqual(0.25f, quaternion.X);
            Assert.AreEqual(0.5f, quaternion.Y);
            Assert.AreEqual(0.75f, quaternion.Z);
            Assert.AreEqual(0.0f, quaternion.W);
        }

        [Test]
        public void ConstructQuaternionInternalFalkenRotation()
        {
            FalkenInternal.falken.Rotation falkenRotation =
              new FalkenInternal.falken.Rotation();
            falkenRotation.x = 0.5f;
            falkenRotation.y = 0.25f;
            falkenRotation.z = 0.75f;
            falkenRotation.w = 0.0f;
            Falken.RotationQuaternion quaternion =
              new Falken.RotationQuaternion(falkenRotation);
            Assert.AreEqual(0.5f, quaternion.X);
            Assert.AreEqual(0.25f, quaternion.Y);
            Assert.AreEqual(0.75f, quaternion.Z);
            Assert.AreEqual(0.0f, quaternion.W);
        }

        [Test]
        public void ConstructFromDirectionVector()
        {
            float kDeltaTolerance = 0.01f;
            // Construct from Vector3.
            var position = new Falken.Vector3(0.64f, 0.768f, 0.0f);
            var rotation = Falken.RotationQuaternion.FromDirectionVector(position);

            // Check if the quaternion is correct.
            Assert.AreEqual(-0.29f, rotation.X, kDeltaTolerance);
            Assert.AreEqual(-0.29f, rotation.Y, kDeltaTolerance);
            Assert.AreEqual(0.64f, rotation.Z, kDeltaTolerance);
            Assert.AreEqual(0.64f, rotation.W, kDeltaTolerance);

            // Construct from direction values.
            var rotation2 = Falken.RotationQuaternion.FromDirectionVector(0.64f, 0.768f, 0.0f);

            // Compare against the correct quaternion.
            Assert.AreEqual(rotation2.X, rotation.X, kDeltaTolerance);
            Assert.AreEqual(rotation2.Y, rotation.Y, kDeltaTolerance);
            Assert.AreEqual(rotation2.Z, rotation.Z, kDeltaTolerance);
            Assert.AreEqual(rotation2.W, rotation.W, kDeltaTolerance);
        }

        [Test]
        public void ConstructFromEulerAngles()
        {
            float kDeltaTolerance = 0.01f;
            // Construct from Vector3.
            var angles = new Falken.EulerAngles(35.0f, 130.0f, 90.0f);
            var rotation = Falken.RotationQuaternion.FromEulerAngles(angles);

            // Check quaternion.
            Assert.AreEqual(0.701f, rotation.X, kDeltaTolerance);
            Assert.AreEqual(0.521f, rotation.Y, kDeltaTolerance);
            Assert.AreEqual(0.092f, rotation.Z, kDeltaTolerance);
            Assert.AreEqual(0.477f, rotation.W, kDeltaTolerance);

            // Convert to euler and check values.
            var convertedAngles = Falken.RotationQuaternion.ToEulerAngles(rotation);
            Assert.AreEqual(angles.Roll, convertedAngles.Roll, kDeltaTolerance);
            Assert.AreEqual(angles.Pitch, convertedAngles.Pitch, kDeltaTolerance);
            Assert.AreEqual(angles.Yaw, convertedAngles.Yaw, kDeltaTolerance);
        }

#if UNITY_5_3_OR_NEWER
        [Test]
        public void ConstructQuaternionUsingUnityQuaternion()
        {
            UnityEngine.Quaternion unityQuaternion =
              new UnityEngine.Quaternion(1.0f, 0.0f, 0.0f, 1.0f);
            Falken.RotationQuaternion quaternion =
              new Falken.RotationQuaternion(unityQuaternion);
            Assert.AreEqual(1.0f, quaternion.X);
            Assert.AreEqual(0.0f, quaternion.Y);
            Assert.AreEqual(0.0f, quaternion.Z);
            Assert.AreEqual(1.0f, quaternion.W);
        }
#endif  // UNITY_5_3_OR_NEWER

#if UNITY_5_3_OR_NEWER
        [Test]
        public void ImplicitUnityQuaternionToFalkenQuaternion()
        {
            Falken.RotationQuaternion quaternion =
              new UnityEngine.Quaternion(1.0f, 0.0f, 0.0f, 1.0f);
            Assert.AreEqual(1.0f, quaternion.X);
            Assert.AreEqual(0.0f, quaternion.Y);
            Assert.AreEqual(0.0f, quaternion.Z);
            Assert.AreEqual(1.0f, quaternion.W);
        }
#endif  // UNITY_5_3_OR_NEWER

#if UNITY_5_3_OR_NEWER
        [Test]
        public void ImplicitFalkenQuaternionToUnityQuaternion()
        {
            UnityEngine.Quaternion quaternion =
              new Falken.RotationQuaternion(1.0f, 0.0f, 0.0f, 1.0f);
            Assert.AreEqual(1.0f, quaternion.x);
            Assert.AreEqual(0.0f, quaternion.y);
            Assert.AreEqual(0.0f, quaternion.z);
            Assert.AreEqual(1.0f, quaternion.w);
        }
#endif  // UNITY_5_3_OR_NEWER
    }

    public class FalkenQuaternionContainer : Falken.AttributeContainer
    {
        public Falken.RotationQuaternion quaternion =
          new Falken.RotationQuaternion(0.5f, -1.0f, 0.1f, 1.0f);
    }

    public class FalkenCustomQuaternion
    {
        private Falken.RotationQuaternion _value;
        public FalkenCustomQuaternion(Falken.RotationQuaternion value)
        {
            _value = value;
        }

        public Falken.RotationQuaternion Value
        {
            get
            {
                return _value;
            }
        }

        public static implicit operator Falken.RotationQuaternion(
          FalkenCustomQuaternion value) =>
            value._value;
        public static implicit operator FalkenCustomQuaternion(
          Falken.RotationQuaternion value) =>
            new FalkenCustomQuaternion(value);
    }

    public class CustomQuaternionContainer : Falken.AttributeContainer
    {
        public FalkenCustomQuaternion quaternion =
          new FalkenCustomQuaternion(new Falken.RotationQuaternion(0.5f, -1.0f, 0.1f, 1.0f));
    }

#if UNITY_5_3_OR_NEWER
    public class UnityQuaternionContainer : Falken.AttributeContainer
    {
        public UnityEngine.Quaternion quaternion =
          new UnityEngine.Quaternion(0.5f, -1.0f, 0.1f, 1.0f);
    }
#endif  // UNITY_5_3_OR_NEWER

    public class InheritedRotationContainer
    {
        [Falken.FalkenInheritedAttribute]
        public Falken.RotationQuaternion inheritedRotation =
          new Falken.RotationQuaternion();
    }

    public class RotationAttributeTest
    {
        private FalkenInternal.falken.AttributeContainer _falkenContainer;

        [SetUp]
        public void Setup()
        {
            _falkenContainer = new FalkenInternal.falken.AttributeContainer();
        }

        [Test]
        public void BindRotation()
        {
            FalkenQuaternionContainer rotationContainer =
              new FalkenQuaternionContainer();
            FieldInfo rotationField =
              typeof(FalkenQuaternionContainer).GetField("quaternion");
            Falken.Rotation rotation = new Falken.Rotation();
            rotation.BindAttribute(rotationField, rotationContainer, _falkenContainer);
            Falken.RotationQuaternion quaternion = rotation.Value;
            Assert.AreEqual(0.5f, quaternion.X);
            Assert.AreEqual(-1.0f, quaternion.Y);
            Assert.AreEqual(0.1f, quaternion.Z);
            Assert.AreEqual(1.0f, quaternion.W);
            Assert.AreEqual("quaternion", rotation.Name);
        }

        [Test]
        public void BindCustomRotation()
        {
            CustomQuaternionContainer rotationContainer =
              new CustomQuaternionContainer();
            FieldInfo rotationField =
              typeof(CustomQuaternionContainer).GetField("quaternion");
            Falken.Rotation rotation = new Falken.Rotation();
            rotation.BindAttribute(rotationField, rotationContainer, _falkenContainer);
            Falken.RotationQuaternion quaternion = rotation.Value;
            Assert.AreEqual(0.5f, quaternion.X);
            Assert.AreEqual(-1.0f, quaternion.Y);
            Assert.AreEqual(0.1f, quaternion.Z);
            Assert.AreEqual(1.0f, quaternion.W);
            Assert.AreEqual("quaternion", rotation.Name);
        }

        [Test]
        public void ModifyRotation()
        {
            FalkenQuaternionContainer rotationContainer =
              new FalkenQuaternionContainer();
            FieldInfo rotationField =
              typeof(FalkenQuaternionContainer).GetField("quaternion");
            Falken.Rotation rotation = new Falken.Rotation();
            rotation.BindAttribute(rotationField, rotationContainer, _falkenContainer);
            Falken.RotationQuaternion quaternion =
              new Falken.RotationQuaternion(1.0f, 0.0f, 0.0f, 1.0f);
            rotation.Value = quaternion;
            quaternion = rotation.Value;
            Assert.AreEqual(1.0f, quaternion.X);
            Assert.AreEqual(0.0f, quaternion.Y);
            Assert.AreEqual(0.0f, quaternion.Z);
            Assert.AreEqual(1.0f, quaternion.W);

            rotation.Value = new Falken.RotationQuaternion(5.0f);
            quaternion = rotation.Value;
            Assert.AreEqual(5.0f, quaternion.X);
            Assert.AreEqual(5.0f, quaternion.Y);
            Assert.AreEqual(5.0f, quaternion.Z);
            Assert.AreEqual(1.0f, quaternion.W);
        }

#if UNITY_5_3_OR_NEWER
        [Test]
        public void BindUnityQuaternion()
        {
            UnityQuaternionContainer rotationContainer = new UnityQuaternionContainer();
            FieldInfo unityQuaternionField =
              typeof(UnityQuaternionContainer).GetField("quaternion");
            Falken.Rotation rotation = new Falken.Rotation();
            rotation.BindAttribute(unityQuaternionField, rotationContainer, _falkenContainer);
            Falken.RotationQuaternion quaternion = rotation.Value;
            Assert.AreEqual(0.5f, quaternion.X);
            Assert.AreEqual(-1.0f, quaternion.Y);
            Assert.AreEqual(0.1f, quaternion.Z);
            Assert.AreEqual(1.0f, quaternion.W);

            rotation.Value = new UnityEngine.Quaternion(1.0f, 0.2f, 0.3f, 0.8f);
            quaternion = rotation.Value;
            Assert.AreEqual(1.0f, quaternion.X);
            Assert.AreEqual(0.2f, quaternion.Y);
            Assert.AreEqual(0.3f, quaternion.Z);
            Assert.AreEqual(0.8f, quaternion.W);

            rotationContainer.quaternion = new UnityEngine.Quaternion(-0.5496546f, 0.5617573f,
                                                                      -0.2243916f, 0.576157f);
            Assert.AreEqual(-0.5496546f, rotation.Value.X);
            Assert.AreEqual(0.5617573f, rotation.Value.Y);
            Assert.AreEqual(-0.2243916f, rotation.Value.Z);
            Assert.AreEqual(0.576157f, rotation.Value.W);

            rotation.Value =
                new UnityEngine.Quaternion(0.4005763f, -0.4005763f, -0.79923f, 0.20077f);
            Assert.AreEqual(0.4005763f, rotationContainer.quaternion.x);
            Assert.AreEqual(-0.4005763f, rotationContainer.quaternion.y);
            Assert.AreEqual(-0.79923f, rotationContainer.quaternion.z);
            Assert.AreEqual(0.20077f, rotationContainer.quaternion.w);
        }
#endif  // UNITY_5_3_OR_NEWER

        [Test]
        public void BindInheritedRotation()
        {
            InheritedRotationContainer rotationContainer =
              new InheritedRotationContainer();
            FieldInfo rotationField =
              typeof(InheritedRotationContainer).GetField("inheritedRotation");
            FalkenInternal.falken.AttributeBase attribute =
              new FalkenInternal.falken.AttributeBase(
                _falkenContainer, rotationField.Name,
                FalkenInternal.falken.AttributeBase.Type.kTypeRotation);
            Falken.Rotation rotation = new Falken.Rotation();
            rotation.BindAttribute(rotationField, rotationContainer, _falkenContainer);
        }

        [Test]
        public void BindInheritedRotationNotFound()
        {
            InheritedRotationContainer rotationContainer =
              new InheritedRotationContainer();
            FieldInfo rotationField =
              typeof(InheritedRotationContainer).GetField("inheritedRotation");
            Falken.Rotation rotation = new Falken.Rotation();
            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Assert.That(() => rotation.BindAttribute(rotationField, rotationContainer,
                                                         _falkenContainer),
                            Throws.TypeOf<Falken.InheritedAttributeNotFoundException>()
                            .With.Message.EqualTo("Inherited field 'inheritedRotation' was not " +
                                                  "found in the container."));
            }
        }

        [Test]
        public void BindInheritedRotationTypeMismatch()
        {
            InheritedRotationContainer rotationContainer =
              new InheritedRotationContainer();
            FieldInfo rotationField =
              typeof(InheritedRotationContainer).GetField("inheritedRotation");
            FalkenInternal.falken.AttributeBase attribute =
              new FalkenInternal.falken.AttributeBase(
                _falkenContainer, "inheritedRotation",
                FalkenInternal.falken.AttributeBase.Type.kTypePosition);
            Falken.Rotation rotation = new Falken.Rotation();
            Assert.That(() => rotation.BindAttribute(rotationField, rotationContainer,
                                                     _falkenContainer),
                        Throws.TypeOf<Falken.InheritedAttributeNotFoundException>()
                        .With.Message.EqualTo($"Inherited field '{rotationField.Name}' has a " +
                                              $"rotation type but the attribute type " +
                                              $"is '{attribute.type()}'"));
        }

        [Test]
        public void WriteRotation()
        {
            FalkenQuaternionContainer rotationContainer =
              new FalkenQuaternionContainer();
            rotationContainer.BindAttributes(_falkenContainer);
            //0.5f, 0.0f, 0.0f, 1.0f
            Falken.Rotation attribute = (Falken.Rotation)rotationContainer["quaternion"];
            Assert.AreEqual(0.5f, attribute.Value.X);
            Assert.AreEqual(-1.0f, attribute.Value.Y);
            Assert.AreEqual(0.1f, attribute.Value.Z);
            Assert.AreEqual(1.0f, attribute.Value.W);

            FalkenInternal.falken.AttributeBase internalAttribute =
              attribute.InternalAttribute;
            internalAttribute.set_rotation(
              new FalkenInternal.falken.Rotation(5.0f, 6.0f, 7.0f, 8.0f));
            attribute.Write();
            Assert.AreEqual(5.0f, attribute.Value.X);
            Assert.AreEqual(6.0f, attribute.Value.Y);
            Assert.AreEqual(7.0f, attribute.Value.Z);
            Assert.AreEqual(8.0f, attribute.Value.W);

            Assert.AreEqual(5.0f, rotationContainer.quaternion.X);
            Assert.AreEqual(6.0f, rotationContainer.quaternion.Y);
            Assert.AreEqual(7.0f, rotationContainer.quaternion.Z);
            Assert.AreEqual(8.0f, rotationContainer.quaternion.W);
        }

        [Test]
        public void WriteCustomRotation()
        {
            CustomQuaternionContainer rotationContainer = new CustomQuaternionContainer();
            rotationContainer.BindAttributes(_falkenContainer);
            Falken.Rotation attribute = (Falken.Rotation)rotationContainer["quaternion"];
            Assert.AreEqual(0.5f, attribute.Value.X);
            Assert.AreEqual(-1.0f, attribute.Value.Y);
            Assert.AreEqual(0.1f, attribute.Value.Z);
            Assert.AreEqual(1.0f, attribute.Value.W);

            FalkenInternal.falken.AttributeBase internalAttribute = attribute.InternalAttribute;
            internalAttribute.set_rotation(
                new FalkenInternal.falken.Rotation(5.0f, 6.0f, 7.0f, 1.0f));
            attribute.Write();
            Assert.AreEqual(5.0f, attribute.Value.X);
            Assert.AreEqual(6.0f, attribute.Value.Y);
            Assert.AreEqual(7.0f, attribute.Value.Z);
            Assert.AreEqual(1.0f, attribute.Value.W);

            Assert.AreEqual(5.0f, rotationContainer.quaternion.Value.X);
            Assert.AreEqual(6.0f, rotationContainer.quaternion.Value.Y);
            Assert.AreEqual(7.0f, rotationContainer.quaternion.Value.Z);
            Assert.AreEqual(1.0f, rotationContainer.quaternion.Value.W);
        }

        [Test]
        public void RotationValidity()
        {
          CustomQuaternionContainer rotationContainer = new CustomQuaternionContainer();
          FieldInfo quaternionField =
            typeof(CustomQuaternionContainer).GetField("quaternion");
          Falken.Rotation rotation = new Falken.Rotation();
          rotation.BindAttribute(quaternionField, rotationContainer, _falkenContainer);
          Falken.RotationQuaternion quaternion = rotation.Value;
          Assert.IsNull(rotation.ReadFieldIfValid());
          rotation.Value = quaternion;
          Assert.IsNotNull(rotation.ReadFieldIfValid());
          rotation.InvalidateNonFalkenFieldValue();
          Assert.IsNull(rotation.ReadFieldIfValid());
        }

        [Test]
        public void RotationClampingTest()
        {
          CustomQuaternionContainer rotationContainer =
              new CustomQuaternionContainer();
          FieldInfo quaternionField =
            typeof(CustomQuaternionContainer).GetField("quaternion");
          Falken.Rotation attribute = new Falken.Rotation();
          attribute.BindAttribute(quaternionField, rotationContainer, _falkenContainer);

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
                " of attribute quaternion, which is of type Rotation" +
                " and therefore it does not support clamping",
              "Attempted to read the clamping configuration of attribute" +
                " quaternion, which is of type Rotation and therefore it" +
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

    public class RotationContainerTest
    {

        private FalkenInternal.falken.AttributeContainer _falkenContainer;

        [SetUp]
        public void Setup()
        {
            _falkenContainer = new FalkenInternal.falken.AttributeContainer();
        }

        [Test]
        public void BindRotationContainer()
        {
            FalkenQuaternionContainer rotationContainer =
              new FalkenQuaternionContainer();
            rotationContainer.BindAttributes(_falkenContainer);
            Assert.IsTrue(rotationContainer["quaternion"] is Falken.Rotation);
            Falken.Rotation rotation = (Falken.Rotation)rotationContainer["quaternion"];
            Falken.RotationQuaternion quaternion = rotation.Value;
            Assert.AreEqual(0.5f, quaternion.X);
            Assert.AreEqual(-1.0f, quaternion.Y);
            Assert.AreEqual(0.1f, quaternion.Z);
            Assert.AreEqual(1.0f, quaternion.W);
        }

        [Test]
        public void BindCustomRotationContainer()
        {
            CustomQuaternionContainer rotationContainer =
              new CustomQuaternionContainer();
            rotationContainer.BindAttributes(_falkenContainer);
            Assert.IsTrue(rotationContainer["quaternion"] is Falken.Rotation);
            Falken.Rotation rotation = (Falken.Rotation)rotationContainer["quaternion"];
            Falken.RotationQuaternion quaternion = rotation.Value;
            Assert.AreEqual(0.5f, quaternion.X);
            Assert.AreEqual(-1.0f, quaternion.Y);
            Assert.AreEqual(0.1f, quaternion.Z);
            Assert.AreEqual(1.0f, quaternion.W);
        }

#if UNITY_5_3_OR_NEWER
        [Test]
        public void BindUnityQuaternionContainer()
        {
            UnityQuaternionContainer rotationContainer =
              new UnityQuaternionContainer();
            rotationContainer.BindAttributes(_falkenContainer);
            Assert.IsTrue(rotationContainer["quaternion"] is Falken.Rotation);
            Falken.Rotation rotation = (Falken.Rotation)rotationContainer["quaternion"];
            Falken.RotationQuaternion quaternion = rotation.Value;
            Assert.AreEqual(0.5f, quaternion.X);
            Assert.AreEqual(-1.0f, quaternion.Y);
            Assert.AreEqual(0.1f, quaternion.Z);
            Assert.AreEqual(1.0f, quaternion.W);

            rotation.Value = new UnityEngine.Quaternion(0.0f, 0.0f, 1.0f, 1.0f);
            quaternion = rotation.Value;
            Assert.AreEqual(0.0f, quaternion.X);
            Assert.AreEqual(0.0f, quaternion.Y);
            Assert.AreEqual(1.0f, quaternion.Z);
            Assert.AreEqual(1.0f, quaternion.W);
        }
#endif  // UNITY_5_3_OR_NEWER
    }
}
