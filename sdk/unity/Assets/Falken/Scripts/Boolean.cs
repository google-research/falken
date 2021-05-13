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

using System.Reflection;

namespace Falken
{
    /// <summary>
    /// <c>Boolean</c> Establishes a connection with a Falken's BooleanAttribute
    /// </summary>
    public sealed class Boolean : Falken.AttributeBase
    {

        /// <summary>
        /// Verify that the given object can be converted/assigned
        /// to a boolean.
        /// </summary>
        static internal bool CanConvertToBooleanType(object obj)
        {
            return CanConvertToGivenType(typeof(bool), obj);
        }

        /// <summary>
        /// Create an empty Falken.Boolean that will be bound later
        /// using a field from a class that contains this attribute.
        /// </summary>
        public Boolean()
        {
        }

        /// <summary>
        /// Create a Falken.Boolean that will be bound later
        /// using the provided name.
        /// <exception>
        /// ArgumentNullException thrown when name is null.
        /// </exception>
        /// </summary>
        public Boolean(string name) : base(name)
        {
        }

        /// <summary>
        /// Get Falken's boolean attribute value.
        /// <exception> AttributeNotBoundException if attribute is
        /// not bound. </exception>
        /// <returns> Value stored in Falken's attribute. </returns>
        /// </summary>
        public bool Value
        {
            get
            {
                if (Bound)
                {
                    Read();
                    return _attribute.boolean();
                }
                throw new AttributeNotBoundException(
                  "Can't retrieve the value if the attribute is not bound.");
            }
            set
            {
                if (Bound)
                {
                    _attribute.set_boolean(value);
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
                var value = fieldInfo.GetValue(fieldContainer);
                if (value != this)
                {
                    // Represents a field that has a non-Falken bool type.
                    if (!CanConvertToBooleanType(value))
                    {
                        ClearBindings();
                        throw new UnsupportedFalkenTypeException(
                            $"Field '{fieldInfo.Name}' is not a bool or can't be converted " +
                            "to/from a boolean.");
                    }
                    Log.Warning($"Please note that {typeof(Boolean).ToString()} is unable to check" +
                                    $" if a {fieldInfo.FieldType.ToString()} field such as" +
                                    $" \"{fieldInfo.Name}\" has been properly set on each" +
                                    " frame. Please make sure that a value is set" +
                                    " on the field at least once every frame.");
                }
            }
            else
            {
                // Attribute represents no field.
                ClearBindings();
            }
            SetFalkenInternalAttribute(new FalkenInternal.falken.AttributeBase(
                                           container, _name,
                                           FalkenInternal.falken.AttributeBase.Type.kTypeBool),
                                       fieldInfo, fieldContainer);
        }

        /// <summary>
        /// Read a field value and cast to the attribute's data type.
        /// </summary>
        /// <returns>Field value or null if it can't be converted to the required type or the
        /// attribute isn't bound to a field.</returns>
        internal override object ReadField()
        {
            object value = base.ReadField();
            return value != null ? (object)CastTo<bool>(value) : null;
        }
        /// <summary>
        /// Update Falken's attribute value to reflect C# field's value.
        /// </summary>
        internal override void Read()
        {
            var value = ReadField();
            if (value != null)
            {
                _attribute.set_boolean((bool)value);
            }
        }

        /// <summary>
        /// Update C# field's value to match Falken's attribute value.
        /// </summary>
        internal override void Write()
        {
            if (Bound && HasForeignFieldValue)
            {
                WriteField(CastFrom<bool>(_attribute.boolean()));
            }
        }

        /// <summary>
        /// Invalidates the value of any non-Falken field represented by this attribute.
        /// </summary>
        internal override void InvalidateNonFalkenFieldValue()
        {
            // We have no way to know for sure if a boolean has not been modified or not
        }
    }
}
