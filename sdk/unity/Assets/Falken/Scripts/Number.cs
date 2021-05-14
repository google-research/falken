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
    /// Adds a range to a numeric field
    /// </summary>
    [AttributeUsage(AttributeTargets.Field, Inherited = true, AllowMultiple = false)]
    public sealed class RangeAttribute : Attribute
    {
        /// <summary>
        /// Minimum value in the range.
        /// </summary>
        public readonly float min;

        /// <summary>
        /// Maximum value in the range.
        /// </summary>
        public readonly float max;

        /// <summary>
        /// Construct a range attribute.
        /// </summary>
        /// <param name="minimum">The minimum allowed value.</param>
        /// <param name="maximum">The maximum allowed value.</param>
        public RangeAttribute(float minimum, float maximum)
        {
            min = minimum;
            max = maximum;
        }
    }

    /// <summary>
    /// <c>Number</c> Establishes a connection with a Falken's NumberAttribute
    /// </summary>
    public sealed class Number : Falken.AttributeBase
    {
        // Saved number type to cast the value properly
        // later when the value is read by Falken.
        private Type _numberType = null;

        // Max value that this number can have. Only
        // used for non-reflection attributes and valid
        // before attribute binding.
        private float? _max = null;

        // Min value that this number can have. Only
        // used for non-reflection attributes and valid
        // before attribute binding.
        private float? _min = null;

        /// <summary>
        /// Verify that the given object can be converted/assigned
        /// to a float or integer.
        /// </summary>
        static internal bool CanConvertToNumberType(object obj)
        {
            return CanConvertToIntNumberType(obj) ||
              CanConvertToFloatNumberType(obj);
        }

        /// <summary>
        /// Verify that the given object can be converted/assigned
        /// to a integer.
        /// </summary>
        static private bool CanConvertToIntNumberType(object obj)
        {
            return CanConvertToGivenType(typeof(int), obj);
        }

        /// <summary>
        /// Verify that the given object can be converted/assigned
        /// to a float.
        /// </summary>
        static private bool CanConvertToFloatNumberType(object obj)
        {
            return CanConvertToGivenType(typeof(float), obj);
        }

        /// <summary>
        /// Create an empty Falken.Number that will be bound later
        /// using a field from a class that contains this attribute.
        /// </summary>
        public Number()
        {
        }

        /// <summary>
        /// Create a Falken.Number that will be bound using the given
        /// parameters.
        /// <exception>
        /// ArgumentNullException thrown when name is null.
        /// </exception>
        /// <exception>
        /// ArgumentException thrown when min is bigger than max.
        /// </exception>
        /// </summary>
        public Number(string name, float min, float max) : base(name)
        {
            InitializeRange(min, max);
        }

        /// <summary>
        /// Create a Falken.Number that will be bound using the given
        /// parameters and the name of the enclosing field.
        /// <exception>
        /// ArgumentNullException thrown when name is null.
        /// </exception>
        /// <exception>
        /// ArgumentException thrown when min is bigger than max.
        /// </exception>
        /// </summary>
        public Number(float min, float max)
        {
            InitializeRange(min, max);
        }

        /// <summary>
        /// Initialize range boundaries during construction.
        /// </summary>
        private void InitializeRange(float min, float max)
        {
            if (min > max)
            {
                throw new ArgumentException(
                  $"Min '{min}' can't be bigger than '{max}'");
            }
            _min = min;
            _max = max;
        }

        /// <summary>
        /// Get Falken's number attribute minimum value.
        /// <exception> AttributeNotBoundException if attribute is
        /// not bound. </exception>
        /// <returns> Minimum value specified by the range attribute. </returns>
        /// </summary>
        public float Minimum
        {
            get
            {
                if (Bound)
                {
                    return _attribute.number_minimum();
                }
                throw new AttributeNotBoundException(
                  "Can't retrieve the minimum if the attribute is not bound.");
            }
        }

        /// <summary>
        /// Get Falken's number attribute maximum value.
        /// <exception> AttributeNotBoundException if attribute is
        /// not bound. </exception>
        /// <returns> Maximum value specified by the range attribute. </returns>
        /// </summary>
        public float Maximum
        {
            get
            {
                if (Bound)
                {
                    return _attribute.number_maximum();
                }
                throw new AttributeNotBoundException(
                  "Can't retrieve the maximum if the attribute is not bound.");
            }
        }

        /// <summary>
        /// Get Falken's number attribute value.
        /// <exception> AttributeNotBoundException if attribute is
        /// not bound. </exception>
        /// <returns> Value stored in Falken's attribute. </returns>
        /// </summary>
        public float Value
        {
            get
            {
                if (Bound)
                {
                    Read();
                    return _attribute.number();
                }
                throw new AttributeNotBoundException(
                  "Can't retrieve the value if the attribute is not bound.");
            }
            set
            {
                if (Bound)
                {
                    _attribute.set_number(value);
                    Write();
                    return;
                }
                throw new AttributeNotBoundException(
                  "Can't retrieve the value if the attribute is not bound.");
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

            float min = float.MaxValue;
            float max = float.MinValue;

            if (fieldInfo != null && fieldContainer != null)
            {
                var value = fieldInfo.GetValue(fieldContainer);
                if (value != this)
                {
                    _numberType = CanConvertToFloatNumberType(value) ? typeof(float) :
                    CanConvertToIntNumberType(value) ? typeof(int) : null;
                    if (_numberType == null)
                    {
                        ClearBindings();
                        throw new UnsupportedFalkenTypeException(
                          $"Field '{fieldInfo.Name}' is not a float or integer or it does" +
                          " not have the implicit conversions defined.");
                    }
#if UNITY_5_3_OR_NEWER
                    var unityRange = fieldInfo.GetCustomAttribute<UnityEngine.RangeAttribute>();
                    if (unityRange != null)
                    {
                        min = unityRange.min;
                        max = unityRange.max;
                    }
#endif  // UNITY_5_3_OR_NEWER

                    var range = fieldInfo.GetCustomAttribute<Falken.RangeAttribute>();
                    if (range != null)
                    {
                      min = range.min;
                      max = range.max;
                    }

                    if (min == float.MaxValue && max == float.MinValue)
                    {
                        ClearBindings();
                        throw new UnsupportedFalkenTypeException(
                          $"Number field '{fieldInfo.Name}' can't be bound since there's no" +
                          " range attribute defined. You must supply a min and max value" +
                          " for Falken to work with numbers.");
                    }
                }
                else
                {
                    // Attribute represents a field containing itself.
                    min = _min.Value;
                    max = _max.Value;
                }
            }
            else
            {
                // Attribute represents no field.
                min = _min.Value;
                max = _max.Value;
                ClearBindings();
            }
            SetFalkenInternalAttribute(new FalkenInternal.falken.AttributeBase(
                                           container, _name, min, max),
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
            _min = null;
            _max = null;
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
            if (HasForeignFieldValue && (value != null)) {
                if (_numberType == typeof(float)) {
                   return Single.IsNaN(CastTo<float>(value)) ? null : (object)CastTo<float>(value);
                } else {
                    return CastTo<int>(value) == int.MinValue ?
                        null : (object)Convert.ToSingle(CastTo<int>(value));
                }
            }
            return null;
        }

        /// <summary>
        /// Update Falken's attribute value to reflect C# field's value.
        /// </summary>
        internal override void Read()
        {
            var value = ReadFieldIfValid();
            if (value != null)
            {
                _attribute.set_number((float)value);
            }
        }

        /// <summary>
        /// Update C# field's value to match Falken's attribute value.
        /// </summary>
        internal override void Write()
        {
            if (Bound && HasForeignFieldValue)
            {
                WriteField(CastFrom<float>(_attribute.number()));
            }
        }

        /// <summary>
        /// Invalidates the value of any non-Falken field represented by this attribute.
        /// </summary>
        internal override void InvalidateNonFalkenFieldValue() {
            if (HasForeignFieldValue)
            {
                if (_numberType == typeof(float)) {
                    WriteField(CastFrom<float>(Single.NaN));
                } else {
                    WriteField(CastFrom<int>(int.MinValue));
                }
            }
        }
    }
}
