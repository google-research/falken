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
    /// <c>PositionVector</c> defines the location of an object in 3D Space.
    /// </summary>
    [Serializable]
    public sealed class PositionVector
    {
        /// <summary>
        /// X component of the position vector.
        /// </summary>
        public float X
        {
            get; set;
        }

        /// <summary>
        /// Y component of the position vector.
        /// </summary>
        public float Y
        {
            get; set;
        }

        /// <summary>
        /// Z component of the position vector.
        /// </summary>
        public float Z
        {
            get; set;
        }

        /// <summary>
        /// Default constructor. Set every component to 0.0f.
        /// </summary>
        public PositionVector()
        {
        }

        /// <summary>
        /// Initialize every component to the same value.
        /// </summary>
        public PositionVector(float initializationValue)
        {
            X = initializationValue;
            Y = initializationValue;
            Z = initializationValue;
        }

#if UNITY_5_3_OR_NEWER
        /// <summary>
        /// Initialize the position vector using a Unity's vector.
        /// </summary>
        public PositionVector(UnityEngine.Vector3 unityVector)
        {
            X = unityVector.x;
            Y = unityVector.y;
            Z = unityVector.z;
        }
#endif  // UNITY_5_3_OR_NEWER

        /// <summary>
        /// Construct a PositionVector with the given component values.
        /// </summary>
        public PositionVector(float newX, float newY, float newZ)
        {
            X = newX;
            Y = newY;
            Z = newZ;
        }

        /// <summary>
        /// Initialize the position with the internal Falken position class.
        /// </summary>
        internal PositionVector(FalkenInternal.falken.Position position)
        {
            X = position.x;
            Y = position.y;
            Z = position.z;
        }

        /// <summary>
        /// Modify a falken internal position with the instance's attributes.
        /// </summary>
        internal FalkenInternal.falken.Position ToInternalPosition(
          FalkenInternal.falken.Position position)
        {
            position.x = X;
            position.y = Y;
            position.z = Z;
            return position;
        }

#if UNITY_5_3_OR_NEWER
        /// <summary>
        /// Convert a PositionVector to a UnityEngine.Vector3.
        /// </summary>
        public static implicit operator UnityEngine.Vector3(PositionVector value) =>
          new UnityEngine.Vector3(value.X, value.Y, value.Z);

        /// <summary>
        /// Convert a UnityEngine.Vector3 to a PositionVector.
        /// </summary>
        public static implicit operator PositionVector(UnityEngine.Vector3 value) =>
          new PositionVector(value);
#endif  // UNITY_5_3_OR_NEWER
    }

    /// <summary>
    /// <c>Position</c> Establishes a connection with a Falken's PositionAttribute.
    /// A position attribute is embedded in Entity's class and there's no
    /// support for more than position attribute.
    /// </summary>
    public sealed class Position : Falken.AttributeBase
    {
        /// <summary>
        /// Verify that the given object can be converted/assigned
        /// to a PositionVector.
        /// </summary>
        static private bool CanConvertToPositionVectorType(object obj)
        {
            return CanConvertToGivenType(typeof(PositionVector), obj);
        }

#if UNITY_5_3_OR_NEWER
        /// <summary>
        /// Verify that the given object can be converted/assigned
        /// to a UnityEngine.Vector3
        /// </summary>
        static private bool CanConvertToUnityVectorType(object obj)
        {
            return CanConvertToGivenType(typeof(UnityEngine.Vector3), obj);
        }
#endif  // UNITY_5_3_OR_NEWER

        /// <summary>
        /// Verify that the given object can be converted/assigned
        /// to any supported position type.
        /// </summary>
        static internal bool CanConvertToPositionType(object obj)
        {
            bool canConvert = CanConvertToPositionVectorType(obj);
#if UNITY_5_3_OR_NEWER
            canConvert |= CanConvertToUnityVectorType(obj);
#endif  // UNITY_5_3_OR_NEWER
            return canConvert;
        }

        // Type of the position field.
        // Useful to distinguish between UnityEngine.Vector3 and Falken's
        // PositionVector
        private Type _positionType = typeof(Falken.PositionVector);

        /// <summary>
        /// Get Falken's position attribute value.
        /// <exception> AttributeNotBoundException if attribute is
        /// not bound. </exception>
        /// <returns> Value stored in Falken's attribute. </returns>
        /// </summary>
        public PositionVector Value
        {
            get
            {
                if (Bound)
                {
                    Read();
                    return new PositionVector(_attribute.position());
                }
                throw new AttributeNotBoundException(
                  "Can't retrieve the value if the attribute is not bound.");
            }
            set
            {
                if (Bound)
                {
                    _attribute.set_position(CastTo<PositionVector>(value).ToInternalPosition(
                        _attribute.position()));
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
#if UNITY_5_3_OR_NEWER
                    if (CanConvertToUnityVectorType(value))
                    {
                        _positionType = typeof(UnityEngine.Vector3);
                    }
#endif  // UNITY_5_3_OR_NEWER
                    if (_positionType == null || CanConvertToPositionVectorType(value))
                    {
                        _positionType = typeof(Falken.PositionVector);
                    }
                    if (_positionType == null)
                    {
                        ClearBindings();
                        throw new UnsupportedFalkenTypeException(
                            $"Field '{fieldInfo.Name}' is not a Falken.PositionVector" +
                            " or a UnityEngine.Vector3 or it does not have the" +
                            " necessary implicit conversions to support it.");
                    }

                }
            }
            else
            {
                _name = "position";
                ClearBindings();
            }

            FalkenInternal.falken.AttributeBase attributeBase;
            if (fieldInfo == null ||
                System.Attribute.GetCustomAttribute(
                    fieldInfo, typeof(FalkenInheritedAttribute)) == null)
            {
                attributeBase = new FalkenInternal.falken.AttributeBase(
                    container, _name,
                    FalkenInternal.falken.AttributeBase.Type.kTypePosition);
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
                         FalkenInternal.falken.AttributeBase.Type.kTypePosition)
                {
                    ClearBindings();
                    throw new InheritedAttributeNotFoundException(
                        $"Inherited field '{_name}' has a position type but the " +
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
            _positionType = typeof(Falken.PositionVector);
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
            PositionVector position = null;
            if (value != null)
            {
                if (_positionType == typeof(PositionVector))
                {
                    position = CastTo<PositionVector>(value);
                }
#if UNITY_5_3_OR_NEWER
                if (_positionType == typeof(UnityEngine.Vector3))
                {
                    position = CastTo<UnityEngine.Vector3>(value);
                }
#endif  // UNITY_5_3_OR_NEWER
                if (Single.IsNaN(position.X) || Single.IsNaN(position.Y)
                    || Single.IsNaN(position.Z)) {
                    return null;
                }
            }
            return position;
        }

        /// <summary>
        /// Update Falken's attribute value to reflect C# field's value.
        /// </summary>
        internal override void Read()
        {
            var value = ReadFieldIfValid();
            if (value != null)
            {
                _attribute.set_position(
                    ((PositionVector)value).ToInternalPosition(_attribute.position()));
            }
        }

        /// <summary>
        /// Update C# field's value to match Falken's attribute value.
        /// </summary>
        internal override void Write()
        {
            if (Bound && HasForeignFieldValue)
            {
                WriteField(CastFrom<PositionVector>(new PositionVector(_attribute.position())));
            }
        }

        /// <summary>
        /// Invalidates the value of any non-Falken field represented by this attribute.
        /// </summary>
        internal override void InvalidateNonFalkenFieldValue()
        {
            if (HasForeignFieldValue) {
                PositionVector pos = new PositionVector
                {
                    X = Single.NaN,
                    Y = Single.NaN,
                    Z = Single.NaN
                };
                WriteField(CastFrom<PositionVector>(pos));
            }
        }
    }
}
