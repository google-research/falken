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
using System.Linq;
using System.Reflection;
using System.Collections.Generic;

namespace Falken
{
    /// <summary>
    /// <c>Category</c> Establishes a connection with a Falken's
    /// CategoricalAttribute. This class maps
    /// the name of each entry in the enum to a index.
    /// </summary>
    public sealed class Category : Falken.AttributeBase
    {

        /// <summary>
        /// <c>EnumTypeMismatchException</c> thrown when
        /// the enum created for the category attribute
        /// is different to the one being requested.
        /// </summary>
        [Serializable]
        public class EnumTypeMismatchException : Exception
        {
            internal EnumTypeMismatchException()
            {
            }

            internal EnumTypeMismatchException(string message)
              : base(message) { }

            internal EnumTypeMismatchException(string message, Exception inner)
              : base(message, inner) { }
        }

        // Enum used to create this category.
        private Type _enumType = null;

        // Mapping of enum names to indexes.
        private Dictionary<string, int> _nameIndexMap =
          new Dictionary<string, int>();

        // List of category values. Used only
        // when constructing attributes when not using reflection.
        private string[] _categoryValues = null;

        /// Invalid enumerated code of the bound variable, used to mark unset
        /// attributes
        private int _badEnumCode;

        /// <summary>
        /// Verify that the given object is an enumeration.
        /// </summary>
        static internal bool CanConvertToCategoryType(object obj)
        {
            return obj.GetType().IsEnum;
        }

        /// <summary>
        /// Create an empty Falken.Category that will be bound later
        /// using a field from a class that contains this attribute.
        /// </summary>
        public Category()
        {
        }

        /// <summary>
        /// Create an Falken.Category with the given category values.
        /// <exception>
        /// ArgumentNullException thrown when name is null.
        /// </exception>
        /// <exception>
        /// ArgumentException thrown when there's no category.
        /// </exception>
        /// </summary>
        public Category(string name, IEnumerable<string> categoryValues) : base(name)
        {
            InitializeCategoryValues(categoryValues);
        }

        /// <summary>
        /// Create a Falken.Category with the given category values that will be bound
        /// later using a field from a class that contains this attribute.
        /// <exception>
        /// ArgumentNullException thrown when name is null.
        /// </exception>
        /// <exception>
        /// ArgumentException thrown when there's no category.
        /// </exception>
        /// </summary>
        public Category(IEnumerable<string> categoryValues)
        {
            InitializeCategoryValues(categoryValues);
        }

        /// <summary>
        /// Initialize category values during construction.
        /// </summary>
        private void InitializeCategoryValues(IEnumerable<string> categoryValues)
        {
            if (!categoryValues.Any())
            {
                throw new ArgumentException(
                  "There's no category in the given category values.");
            }
            _categoryValues = Enumerable.ToArray<string>(categoryValues);
        }

        /// <summary>
        /// Get all the category values that this attribute has
        /// (the name of each enum entry used to create this).
        /// </summary>
        public IList<string> CategoryValues
        {
            get
            {
                if (Bound)
                {
                    Read();
                    return new List<string>(_attribute.category_values());
                }
                throw new AttributeNotBoundException(
                  "Can't retrieve the value if the attribute is not bound.");
            }
        }

        /// <summary>
        /// Get Falken's categorical attribute value as index of the enum.
        /// <exception> AttributeNotBoundException if attribute is
        /// not bound. </exception>
        /// <returns> Value stored in Falken's attribute. </returns>
        /// </summary>
        public int Value
        {
            get
            {
                if (Bound)
                {
                    Read();
                    return _attribute.category();
                }
                throw new AttributeNotBoundException(
                  "Can't retrieve the value if the attribute is not bound.");
            }
            set
            {
                if (Bound)
                {
                    _attribute.set_category(value);
                    Write();
                    return;
                }
                throw new AttributeNotBoundException(
                  "Can't set value if the attribute is not bound.");
            }
        }

        /// <summary>
        /// Get Falken's categorical attribute value casted to the type
        /// that was created with.
        /// <exception> AttributeNotBoundException if attribute is
        /// not bound. </exception>
        /// <exception> EnumTypeMismatchException if the type of the enum
        /// to cast is different from the one used to create this category.
        /// </exception>
        /// <returns> Value stored in Falken's attribute casted to the enum used.
        /// </returns>
        /// </summary>
        public T AsEnum<T>()
        {
            if (!Bound)
            {
                throw new AttributeNotBoundException(
                  "Can't get value as enum if the attribute is not bound.");
            }
            if (typeof(T) != _enumType)
            {
                throw new EnumTypeMismatchException(
                  String.Format(
                    "Can't cast to a different enum type. Given enum type is " +
                    "{0} and this attribute was created with a {1}",
                    typeof(T).ToString(), _enumType.ToString()));
            }
            var values = Enum.GetValues(_enumType);
            int categoryValue = _attribute.category();
            if (categoryValue >= values.Length)
            {
                throw new IndexOutOfRangeException("Category value is out of range");
            }
            return (T)values.GetValue(categoryValue);
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
            string[] enumNames;
            SetNameToFieldName(fieldInfo, fieldContainer);

            if (fieldInfo != null && fieldContainer != null)
            {
                var value = fieldInfo.GetValue(fieldContainer);
                if (value != this)
                {
                    if (!CanConvertToCategoryType(value))
                    {
                        ClearBindings();
                        throw new UnsupportedFalkenTypeException(
                            $"Field '{fieldInfo.Name}' is not an enum");
                    }

                    Type fieldType = fieldInfo.FieldType;

                    enumNames = Enum.GetNames(fieldType);
                    _enumType = fieldType;

                    // Find a value that can be used as invalid or out of range
                    // in the enum encoding. We look for the largest
                    // positive code + 1.
                    var enumeratedTypeValuesArray = Enum.GetValues(_enumType);
                    Array.Sort(enumeratedTypeValuesArray);
                    _badEnumCode = (int)enumeratedTypeValuesArray.GetValue(
                        enumeratedTypeValuesArray.Length - 1) + 1;
                }
                else
                {
                    // Attribute represents a field containing itself.
                    enumNames = _categoryValues;
                }
            }
            else
            {
                // Attribute represents no field.
                enumNames = _categoryValues;
                ClearBindings();
            }
            int index = 0;
            foreach (string enumName in enumNames)
            {
                _nameIndexMap[enumName] = index;
                ++index;
            }
            SetFalkenInternalAttribute(new FalkenInternal.falken.AttributeBase(
                                           container, _name,
                                           new FalkenInternal.std.StringVector(enumNames)),
                                       fieldInfo, fieldContainer);
            // Sync with the initial value and then mark as invalid
            Read();
            InvalidateNonFalkenFieldValue();
        }

        /// <summary>
        /// Clear all field and attribute bindings.
        /// </summary>
        protected override void ClearBindings()
        {
            base.ClearBindings();
            // Deallocate fields used to construct the attribute.
            _categoryValues = null;
            _enumType = null;
        }

        /// <summary>
        /// Read a field and check if the value is valid.
        /// </summary>
        /// <returns>
        /// Object boxed version of the attribute value.
        /// or null if invalid or unable to readValue stored in Falken's attribute.
        /// </returns>
        internal override object ReadFieldIfValid() {
            var value = base.ReadField();
            return (value != null) && (CastTo<int>(value) != _badEnumCode) ?
                _enumType.GetEnumName(value) : null;
        }

        /// <summary>
        /// Update Falken's attribute value to reflect C# field's value.
        /// </summary>
        internal override void Read()
        {
            var value = ReadFieldIfValid();
            if (value != null)
            {
                _attribute.set_category(_nameIndexMap[(string)value]);
            }
        }

        /// <summary>
        /// Update C# field's value to match Falken's attribute value.
        /// </summary>
        internal override void Write()
        {
            if (Bound && HasForeignFieldValue && _enumType != null)
            {
                // If this Category attribute mirrors a primitive enum field, update that field.
                WriteField(Enum.GetValues(_enumType).GetValue(_attribute.category()));
            }
        }

        /// <summary>
        /// Invalidates the value of any non-Falken field represented by this attribute.
        /// </summary>
        internal override void InvalidateNonFalkenFieldValue() {
            if (HasForeignFieldValue)
            {
                WriteField(Convert.ChangeType(_badEnumCode, _enumType.GetEnumUnderlyingType()));
            }
        }
    }
}
