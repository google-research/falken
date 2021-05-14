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
using System.Reflection;

namespace Falken
{
    /// <summary>
    /// <c>RotationQuaternion</c> defines the rotation of an object as
    /// a quaternion.
    /// </summary>
    [Serializable]
    public sealed class RotationQuaternion
    {
        /// <summary>
        /// X component of the quaternion.
        /// </summary>
        public float X
        {
            get
            {
                return _internalRotation.x;
            }
            set
            {
                _internalRotation.x = value;
            }
        }

        /// <summary>
        /// Y component of the quaternion.
        /// </summary>
        public float Y
        {
            get
            {
                return _internalRotation.y;
            }
            set
            {
                _internalRotation.y = value;
            }
        }

        /// <summary>
        /// Z component of the quaternion.
        /// </summary>
        public float Z
        {
            get
            {
                return _internalRotation.z;
            }
            set
            {
                _internalRotation.z = value;
            }
        }

        /// <summary>
        /// W component of the quaternion.
        /// </summary>
        public float W
        {
            get
            {
                return _internalRotation.w;
            }
            set
            {
                _internalRotation.w = value;
            }
        }

        /// <summary>
        /// Default constructor. Set every component to 0.0f.
        /// </summary>
        public RotationQuaternion()
        {
            _internalRotation = new FalkenInternal.falken.Rotation();
        }

        /// <summary>
        /// Initialize every component to the same value.
        /// </summary>
        public RotationQuaternion(float initializationValue) : this()
        {
            X = initializationValue;
            Y = initializationValue;
            Z = initializationValue;
            W = 1.0f;
        }

#if UNITY_5_3_OR_NEWER
        /// <summary>
        /// Initialize the quaternion using a Unity's quaternion.
        /// </summary>
        public RotationQuaternion(UnityEngine.Quaternion unityQuaternion) : this()
        {
            X = unityQuaternion.x;
            Y = unityQuaternion.y;
            Z = unityQuaternion.z;
            W = unityQuaternion.w;
        }
#endif  // UNITY_5_3_OR_NEWER

        /// <summary>
        /// Construct a Quaternion with the given component values.
        /// </summary>
        public RotationQuaternion(float newX, float newY, float newZ, float newW) : this()
        {
            X = newX;
            Y = newY;
            Z = newZ;
            W = newW;
        }

        /// <summary>
        /// Initialize the rotation with the internal Falken rotation class.
        /// </summary>
        internal RotationQuaternion(FalkenInternal.falken.Rotation rotation) : this()
        {
            X = rotation.x;
            Y = rotation.y;
            Z = rotation.z;
            W = rotation.w;
        }

        /// <summary>
        /// Modify a falken internal rotation with the instance's attributes.
        /// </summary>
        /// <returns> Internal Rotation object.</returns>
        internal FalkenInternal.falken.Rotation ToInPlaceInternalRotation(
          FalkenInternal.falken.Rotation rotation)
        {
            rotation.x = X;
            rotation.y = Y;
            rotation.z = Z;
            rotation.w = W;
            return rotation;
        }

        /// <summary>
        /// Convert to internal rotation.
        /// </summary>
        /// <returns> Internal Rotation object.</returns>
        internal FalkenInternal.falken.Rotation ToInternalRotation()
        {
            return _internalRotation;
        }

#if UNITY_5_3_OR_NEWER
        /// <summary>
        /// Convert a Falken.RotationQuaternion to a UnityEngine.Quaternion.
        /// </summary>
        public static implicit operator UnityEngine.Quaternion(
          Falken.RotationQuaternion value) =>
            new UnityEngine.Quaternion(value.X, value.Y, value.Z, value.W);

        /// <summary>
        /// Convert a UnityEngine.Quaternion to a Falken.RotationQuaternion.
        /// </summary>
        public static implicit operator Falken.RotationQuaternion(
          UnityEngine.Quaternion value) =>
            new Falken.RotationQuaternion(value);
#endif  // UNITY_5_3_OR_NEWER

        /// <summary>
        /// Construct a Quaternion from a direction vector. This vector must be normalized.
        /// </summary>
        /// <param name="vector"> Vector3 to convet. Values must be normalized.</param>
        public static RotationQuaternion FromDirectionVector(Vector3 vector)
        {
            // Call internal method to generate rotation.
            var rotation =
                FalkenInternal.falken.Rotation.FromDirectionVector(vector.ToInternalVector3());
            return new RotationQuaternion(rotation);
        }

        /// <summary>
        /// Construct a Quaternion from a direction vector. This vector must be normalized.
        /// </summary>
        /// <param name="x"> X component of the vector.</param>
        /// <param name="y"> Y component of the vector.</param>
        /// <param name="z"> Z component of the vector.</param>
        public static RotationQuaternion FromDirectionVector(float x, float y, float z)
        {
            // Call internal method to generate rotation.
            var rotation =
                FalkenInternal.falken.Rotation.FromDirectionVector(x, y, z);
            return new RotationQuaternion(rotation);
        }

        /// <summary>
        /// Construct a Quaternion from Euler angles vector. The conversion follows Body 2-1-3
        /// sequence convention (rotate Pitch, then Roll and last Yaw). The type of
        /// rotation is extrinsic.
        /// </summary>
        /// <param name="eulerAngles"> EulerAngles to convert.</param>
        public static RotationQuaternion FromEulerAngles(EulerAngles eulerAngles)
        {
            // Call internal method to generate rotation.
            var rotation =
                FalkenInternal.falken.Rotation.FromEulerAngles(eulerAngles.ToInternalEulerAngles());
            return new RotationQuaternion(rotation);
        }

        /// <summary>
        /// Construct a Quaternion from Euler angles. The conversion follows Body 2-1-3
        /// sequence convention (rotate Pitch, then Roll and last Yaw). The type of
        /// rotation is extrinsic.
        /// </summary>
        /// <param name="roll"> Roll component of the vector in degrees.</param>
        /// <param name="pitch"> Pitch component of the vector in degrees.</param>
        /// <param name="yaw"> Yaw component of the vector in degrees.</param>
        public static RotationQuaternion FromEulerAngles(float roll, float pitch, float yaw)
        {
            // Call internal method to generate rotation.
            var rotation =
                FalkenInternal.falken.Rotation.FromDirectionVector(
                    Utils.DegreesToRadians(roll),
                    Utils.DegreesToRadians(pitch),
                    Utils.DegreesToRadians(yaw));
            return new RotationQuaternion(rotation);
        }

        /// <summary>
        /// Convert quaternion to euler angles. Values are in degrees.
        /// </summary>
        /// <returns> Internal Rotation object.</returns>
        public static EulerAngles ToEulerAngles(RotationQuaternion rotation)
        {
            var internalRotation = rotation.ToInternalRotation();
            return new EulerAngles(FalkenInternal.falken.Rotation.ToEulerAngles(internalRotation));
        }

        private FalkenInternal.falken.Rotation _internalRotation;

    }

    /// <summary>
    /// <c>Rotation</c> Establishes a connection with a Falken's RotationAttribute.
    /// A rotation attribute is embedded in Entity's class and there's no
    /// support for more than rotation attribute.
    /// </summary>
    public sealed class Rotation : Falken.AttributeBase
    {

        /// <summary>
        /// Verify that the given object can be converted/assigned
        /// to a RotationQuaternion.
        /// </summary>
        static private bool CanConvertToQuaternionType(object obj)
        {
            return CanConvertToGivenType(typeof(Falken.RotationQuaternion), obj);
        }

#if UNITY_5_3_OR_NEWER
        /// <summary>
        /// Verify that the given object can be converted/assigned
        /// to a UnityEngine.Quaternion
        /// </summary>
        static private bool CanConvertToUnityQuaternionType(object obj)
        {
            return CanConvertToGivenType(typeof(UnityEngine.Quaternion), obj);
        }
#endif  // UNITY_5_3_OR_NEWER

        /// <summary>
        /// Verify that the given object can be converted/assigned
        /// to any supported position type.
        /// </summary>
        static internal bool CanConvertToRotationType(object obj)
        {
            bool canConvert = CanConvertToQuaternionType(obj);
#if UNITY_5_3_OR_NEWER
            canConvert |= CanConvertToUnityQuaternionType(obj);
#endif  // UNITY_5_3_OR_NEWER
            return canConvert;
        }

        // Type of the rotation field.
        // Useful to distinguish between UnityEngine.Quaternion and Falken's
        // RotationQuaternion
        private Type _rotationType = typeof(Falken.RotationQuaternion);

        /// <summary>
        /// Get Falken's rotation attribute value.
        /// <exception> AttributeNotBoundException if attribute is
        /// not bound. </exception>
        /// <returns> Value stored in Falken's attribute. </returns>
        /// </summary>
        public Falken.RotationQuaternion Value
        {
            get
            {
                if (Bound)
                {
                    Read();
                    return new Falken.RotationQuaternion(_attribute.rotation());
                }
                throw new AttributeNotBoundException(
                  "Can't retrieve the value if the attribute is not bound.");
            }
            set
            {
                if (Bound)
                {
                    _attribute.set_rotation(CastTo<Falken.RotationQuaternion>(value)
                        .ToInPlaceInternalRotation(_attribute.rotation()));
                    Write();
                    return;
                }
                throw new AttributeNotBoundException(
                  "Can't set value if the attribute is not bound.");
            }
        }

        /// <summary>
        /// Establish a connection between a C# attribute and a Falken's attribute.
        /// </summary>
        /// <param name="fieldInfo">Metadata information of the field this is being bound
        /// to.</param>
        /// <param name="fieldContainer">Object that contains the value of the field.</param>
        /// <param name="container">Internal container to add the attribute to.</param>
        /// <exception>AlreadyBoundException thrown when trying to bind the attribute when it was
        /// bound already.</exception>
        internal override void BindAttribute(FieldInfo fieldInfo, object fieldContainer,
                                             FalkenInternal.falken.AttributeContainer container)
        {
            ThrowIfBound(fieldInfo);
            SetNameToFieldName(fieldInfo, fieldContainer);

            if (fieldInfo != null && fieldContainer != null)
            {
                object value = fieldInfo.GetValue(fieldContainer);
                if (value != this)
                {
                    // Attribute represents a field with non-Falken value.
                    _rotationType = null;
#if UNITY_5_3_OR_NEWER
                    if (CanConvertToUnityQuaternionType(value))
                    {
                        _rotationType = typeof(UnityEngine.Quaternion);
                    }
#endif  // UNITY_5_3_OR_NEWER
                    if (_rotationType == null && CanConvertToQuaternionType(value))
                    {
                        _rotationType = typeof(Falken.RotationQuaternion);
                    }
                    if (_rotationType == null)
                    {
                        ClearBindings();
                        throw new UnsupportedFalkenTypeException(
                            $"Field '{fieldInfo.Name}' is not a Falken.RotationQuaternion" +
                            " or a UnityEngine.Quaternion or it does not have the" +
                            " necessary implicit conversions to support it.");
                    }
                }
            }
            else
            {
                // Attribute does not represent a field.
                _name = "rotation";
                ClearBindings();
            }
            FalkenInternal.falken.AttributeBase attributeBase;
            if (fieldInfo == null ||
                System.Attribute.GetCustomAttribute(fieldInfo,
                                                    typeof(FalkenInheritedAttribute)) == null)
            {
                attributeBase = new FalkenInternal.falken.AttributeBase(
                  container, _name, FalkenInternal.falken.AttributeBase.Type.kTypeRotation);
            }
            else
            {
                attributeBase = container.attribute(_name);
                if (attributeBase == null)
                {
                    ClearBindings();
                    throw new InheritedAttributeNotFoundException(
                        $"Inherited field '{_name}' was not found in the container.");
                }
                else if (attributeBase.type() !=
                         FalkenInternal.falken.AttributeBase.Type.kTypeRotation)
                {
                    ClearBindings();
                    throw new InheritedAttributeNotFoundException(
                        $"Inherited field '{_name}' has a rotation type but the " +
                        $"attribute type is '{attributeBase.type()}'");
                }
            }
            SetFalkenInternalAttribute(attributeBase, fieldInfo, fieldContainer);
            Read();
            InvalidateNonFalkenFieldValue();
        }

        /// <summary>
        /// Clear all field and attribute bindings.
        /// </summary>
        protected override void ClearBindings()
        {
            base.ClearBindings();
            _rotationType = typeof(Falken.RotationQuaternion);
        }

        /// <summary>
        /// Read a field and check if the value is valid.
        /// </summary>
        /// <returns>
        /// Object boxed version of the attribute value.
        /// or null if invalid or unable to readValue stored in Falken's attribute.
        /// </returns>
        internal override object ReadFieldIfValid()
        {
            object value = base.ReadField();
            RotationQuaternion rotation = null;
            if (value != null)
            {
                if (_rotationType == typeof(RotationQuaternion))
                {
                    rotation = CastTo<RotationQuaternion>(value);
                }
#if UNITY_5_3_OR_NEWER
                if (_rotationType == typeof(UnityEngine.Quaternion))
                {
                    rotation = CastTo<UnityEngine.Quaternion>(value);
                }
#endif  // UNITY_5_3_OR_NEWER
                if (Single.IsNaN(rotation.X) || Single.IsNaN(rotation.Y)
                        || Single.IsNaN(rotation.Z) || Single.IsNaN(rotation.W)) {
                    return null;
                }

            }
            return rotation;
        }

        /// <summary>
        /// Update Falken's attribute value to reflect C# field's value.
        /// </summary>
        internal override void Read()
        {
            var value = ReadFieldIfValid();
            if (value != null)
            {
                _attribute.set_rotation(
                    ((RotationQuaternion)value).ToInPlaceInternalRotation(_attribute.rotation()));
            }
        }

        /// <summary>
        /// Update C# field's value to match Falken's attribute value.
        /// </summary>
        internal override void Write()
        {
            if (Bound && HasForeignFieldValue)
            {
                WriteField(CastFrom<RotationQuaternion>(
                    new RotationQuaternion(_attribute.rotation())));
            }
        }

        /// <summary>
        /// Invalidates the value of any non-Falken field represented by this attribute.
        /// </summary>
        internal override void InvalidateNonFalkenFieldValue()
        {
            if (HasForeignFieldValue) {
                RotationQuaternion rotation = new RotationQuaternion
                {
                    X = Single.NaN,
                    Y = Single.NaN,
                    Z = Single.NaN,
                    W = Single.NaN
                };
                WriteField(CastFrom<RotationQuaternion>(rotation));
            }
        }
    }
}
