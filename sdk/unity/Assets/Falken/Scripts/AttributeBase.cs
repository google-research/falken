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

namespace Falken
{

    /// <summary>
    /// <c>AttributeNotBoundException</c> thrown when access to an
    /// unbound attribute property is forbidden.
    /// </summary>
    [Serializable]
    public class AttributeNotBoundException : Exception
    {
        internal AttributeNotBoundException()
        {
        }

        internal AttributeNotBoundException(string message)
          : base(message) { }

        internal AttributeNotBoundException(string message, Exception inner)
          : base(message, inner) { }
    }

    /// <summary>
    /// <c>InheritedAttributeNotFoundException</c> thrown when an inherited
    /// Falken attribute could not be found.
    /// </summary>
    [Serializable]
    public class InheritedAttributeNotFoundException : Exception
    {
        internal InheritedAttributeNotFoundException()
        {
        }

        internal InheritedAttributeNotFoundException(string message)
          : base(message) { }

        internal InheritedAttributeNotFoundException(string message, Exception inner)
          : base(message, inner) { }
    }

    /// <summary>
    /// <c>FieldNameMismatchException</c> thrown when an Attribute has a name that does
    /// not match its field name.
    /// </summary>
    [Serializable]
    public class MismatchingFieldNameException : Exception
    {
        internal MismatchingFieldNameException()
        {
        }

        internal MismatchingFieldNameException(string message)
          : base(message) { }

        internal MismatchingFieldNameException(string message, Exception inner)
          : base(message, inner) { }
    }

    /// <summary>
    /// <c>AttributeBase</c> Base attribute class that establishes a connection
    /// with any Falken attribute.
    /// </summary>
    public abstract class AttributeBase
    {
        /// <summary>
        /// Falken attribute that this is bound to.
        /// </summary>
        protected FalkenInternal.falken.AttributeBase _attribute = null;
        /// <summary>
        /// Metadata of the field in _fieldContainer that this attribute represents.
        /// </summary>
        protected FieldInfo _fieldInfo = null;
        /// <summary>
        /// Container object for the field this attribute represents.
        /// </summary>
        protected object _fieldContainer = null;
        /// <summary>
        /// Name of the attribute, only when not using reflection.
        /// </summary>
        protected string _name = null;

        /// <summary>
        /// Implicit conversion method used to convert to values.
        /// </summary>
        private MethodInfo _implicitToConversion = null;

        /// <summary>
        /// Implicit conversion method used to convert from values.
        /// </summary>
        private MethodInfo _implicitFromConversion = null;

        /// <summary>
        /// Cache of conversion methods.
        /// </summary>
        private static Dictionary<KeyValuePair<Type, Type>, MethodInfo> _implicitConversionCache =
          new Dictionary<KeyValuePair<Type, Type>, MethodInfo>();

        /// <summary>
        /// Get the internal attribute this is bound to.
        /// Do NOT use this. There's no need to access this directly.
        /// </summary>
        internal FalkenInternal.falken.AttributeBase InternalAttribute
        {
            get
            {
                return _attribute;
            }
        }

        /// <summary>
        /// Check if the attribute is bound to a Falken's attribute.
        /// </summary>
        internal bool Bound
        {
            get
            {
                return _attribute != null;
            }
        }

        /// <summary>
        /// Check whether the attribute has an associated field value that is not itself.
        /// </summary>
        internal bool HasForeignFieldValue
        {
            get
            {
                return _fieldInfo != null && _fieldContainer != null
                    && _fieldInfo.GetValue(_fieldContainer) != this;
            }
        }

        /// <summary>
        /// Get the name of this attribute (which will be equal to the field name).
        /// Can return null if attribute is not bound.
        /// </summary>
        public string Name
        {
            get
            {
                if (Bound)
                {
                    return _attribute.name();
                }
                return null;
            }
        }

        /// <summary>
        /// Enable/disable clamping of out-of-range values for
        /// attribute types that support it. When it's enabled
        /// values will be clamped to the max or min value
        /// of the range.
        /// </summary>
        public bool EnableClamping {
            get
            {
                if (Bound)
                {
                    return _attribute.enable_clamping();
                }
                return false;
            }
            set
            {
                if (Bound)
                {
                    _attribute.set_enable_clamping(value);
                }
            }
        }

        /// <summary>
        /// Default attribute base constructor.
        /// </summary>
        protected AttributeBase()
        {
        }

        /// <summary>
        /// Construct the attribute base with the given name.
        /// Used when for attributes created dynamically, rather than using
        /// reflection.
        /// <exception>
        /// ArgumentNullException thrown when name is null.
        /// </exception>
        /// </summary>
        protected AttributeBase(string name)
        {
            if (name == null)
            {
                throw new ArgumentNullException(name);
            }
            _name = name;
        }

        /// <summary>
        /// Find an implicit conversion method and cache it.
        /// </summary>
        /// <param name="fromType">Type to convert from.</param>
        /// <param name="toType">Type to convert to.</param>
        /// <returns> MethodInfo if conversion is found, null otherwise.</returns>
        private static MethodInfo FindImplicitConversionOp(Type fromType, Type toType)
        {
            var key = new KeyValuePair<Type, Type>(fromType, toType);
            // Search the cache first.
            MethodInfo foundMethod;
            if (_implicitConversionCache.TryGetValue(key, out foundMethod))
            {
                return foundMethod;
            }

            // Search each type for a conversion method.
            foreach (var baseType in new[] { fromType, toType })
            {
                IEnumerable<MethodInfo> methods = baseType.GetMethods(
                  BindingFlags.Public | BindingFlags.Static).Where(
                    method => method.Name == "op_Implicit" && method.ReturnType == toType);
                foreach (MethodInfo method in methods)
                {
                    ParameterInfo[] parameters = method.GetParameters();
                    if (parameters.Length == 1 &&
                        parameters.FirstOrDefault().ParameterType == fromType)
                    {
                        foundMethod = method;
                        break;
                    }
                }
                if (foundMethod != null)
                {
                    break;
                }
            }
            _implicitConversionCache[key] = foundMethod;
            return foundMethod;
        }

        /// <summary>
        /// Verify that a given object can be converted/assigned to a value
        /// of a given type.
        /// </summary>
        protected static bool CanConvertToGivenType(Type type, object obj)
        {
            if (obj == null)
            {
                throw new ArgumentNullException("Given obj can't be null.");
            }
            Type objType = obj.GetType();
            if (objType.IsAssignableFrom(type))
            {
                return true;
            }
            if (FindImplicitMethods(objType, type))
            {
                return true;
            }
            return false;
        }

        /// <summary>
        /// Find the implicit conversion between types and cache them.
        /// if we do.
        /// <return> True if both methods are found, false otherwise. </return>
        /// </summary>
        protected static bool FindImplicitMethods(Type baseType, Type toType)
        {
            return FindImplicitConversionOp(baseType, toType) != null &&
              FindImplicitConversionOp(toType, baseType) != null;
        }

        /// <summary>
        /// Cast a given object value to type T.
        /// Does not check if the conversion is valid.
        /// </summary>
        /// <param name="value">Value to cast.</param>
        /// <returns>Object cast to typeof(T).</returns>
        /// <exception>InvalidCastException if conversion isn't possible.</exception>
        protected T CastTo<T>(object value)
        {
            Type valueType = value.GetType();
            if (typeof(IConvertible).IsAssignableFrom(valueType))
            {
                return (T)Convert.ChangeType(value, typeof(T));
            }
            else if (valueType == typeof(T))
            {
                return (T)value;
            }
            if (_implicitToConversion == null)
            {
                _implicitToConversion = FindImplicitConversionOp(valueType, typeof(T));
                if (_implicitToConversion == null)
                {
                    throw new InvalidCastException(
                      $"Unable to convert {value} from type {valueType} to {typeof(T)}");
                }
            }
            return (T)_implicitToConversion.Invoke(null, new[] { value });
        }

        /// <summary>
        /// Cast a given object value from another type to the bound field type.
        /// Does not check if the conversion is valid.
        /// </summary>
        /// <param name="value">Value to cast.</param>
        /// <returns>Object cast to _fieldInfo.FieldType.</returns>
        /// <exception>InvalidCastException if conversion isn't possible.</exception>
        protected object CastFrom<T>(T value)
        {
            Type valueType = typeof(T);
            Type fieldType = _fieldInfo.FieldType;
            if (typeof(IConvertible).IsAssignableFrom(fieldType))
            {
                return Convert.ChangeType(value, fieldType);
            }
            else if (valueType == fieldType)
            {
                return value;
            }
            if (_implicitFromConversion == null)
            {
                _implicitFromConversion = FindImplicitConversionOp(valueType, fieldType);
                if (_implicitFromConversion == null)
                {
                    throw new InvalidCastException(
                      $"Unable to convert {value} from type {valueType} to {fieldType}");
                }
            }
            return _implicitFromConversion.Invoke(null, new[] { (object)value });
        }

        /// <summary>
        /// If the attribute is already bound to a field throw an exception.
        /// </summary>
        /// <param name="fieldInfo">Optional field metadata to attempt to bind to.</param>
        /// <exception>AlreadyBoundException</exception> is thrown if the attribute is already
        /// bound to a field.
        protected void ThrowIfBound(FieldInfo fieldInfo)
        {
            if (Bound)
            {
                var newFieldName = fieldInfo != null ? fieldInfo.Name : "<unknown>";
                var existingFieldName = _fieldInfo != null ? _fieldInfo.Name : Name;
                throw new AlreadyBoundException($"Can't bind field {newFieldName} to " +
                                                $"attribute {Name} as it is " +
                                                $"already bound to field {existingFieldName}");
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
        internal abstract void BindAttribute(FieldInfo fieldInfo, object fieldContainer,
                                             FalkenInternal.falken.AttributeContainer container);

        /// <summary>
        /// Infer the attribute name based on name provided at construction (if any) and the
        /// associated fieldname.
        /// <exception>FieldNameMismatchException thrown when the attribute has a name
        /// that does not match its field name.</exception>
        /// </summary>
        internal void SetNameToFieldName(FieldInfo fieldInfo, object fieldContainer)
        {
            if (fieldInfo != null && fieldContainer != null)
            {
                var value = fieldInfo.GetValue(fieldContainer);

                if (value == this && _name != null && _name != fieldInfo.Name)
                {
                    throw new MismatchingFieldNameException(
                        $"Attribute {this} has set name {_name} which does not match its " +
                        $"associated field name {fieldInfo.Name}.");
                }

                _name = fieldInfo.Name;
            }

        }

        /// <summary>
        /// Clear all field and attribute bindings.
        /// </summary>
        protected virtual void ClearBindings()
        {
            _attribute = null;
            _fieldInfo = null;
            _fieldContainer = null;
        }

        /// <summary>
        /// Read a field value and cast to the attribute's data type.
        /// </summary>
        /// <returns>Field value or null if it can't be converted to the required type or the
        /// attribute isn't bound to a field.</returns>
        internal virtual object ReadField()
        {
            return Bound && HasForeignFieldValue ? _fieldInfo.GetValue(_fieldContainer) : null;
        }

        /// <summary>
        /// Update Falken's attribute value to reflect C# field's value.
        /// </summary>
        internal abstract void Read();

        /// <summary>
        /// Set internal attribute base directly without going through the binding process.
        /// </summary>
        /// <param name="attributeBase">Internal attribute to associate with this instance.</param>
        /// <param name="fieldInfo">Field metadata for a field on the fieldContainer object.</param>
        /// <param name="fieldContainer">Object that contains the field.</param>
        internal virtual void SetFalkenInternalAttribute(
          FalkenInternal.falken.AttributeBase attributeBase,
          FieldInfo fieldInfo, object fieldContainer)
        {
            if (!((fieldInfo == null && fieldContainer == null) ||
                  (fieldInfo != null && fieldContainer != null)))
            {
                ClearBindings();
                throw new ArgumentException("Both fieldInfo and fieldContainer must be " +
                                            "either null or not null.");
            }
            _attribute = attributeBase;
            _fieldInfo = fieldInfo;
            _fieldContainer = fieldContainer;
        }

        /// <summary>
        /// Change the internal attribute base. It's assumed that the given
        /// attribute is the same as the one that it's set.
        /// </summary>
        internal virtual void Rebind(FalkenInternal.falken.AttributeBase attributeBase)
        {
            _attribute = attributeBase;
            // Mark the contents of the attribute as invalid
            InvalidateNonFalkenFieldValue();
        }

        /// <summary>
        /// Write a value to the field bound to this object.
        /// </summary>
        /// <param name="value">Value to set to the field.</param>
        /// <returns>true if the value is set, false otherwise.</returns>
        internal virtual bool WriteField(object value)
        {
            if (HasForeignFieldValue)
            {
                _fieldInfo.SetValue(_fieldContainer, value);
                return true;
            }
            return false;
        }

        /// <summary>
        /// Set C# field's value to match Falken's internal one.
        /// </summary>
        internal abstract void Write();

        /// <summary>
        /// Read a field and check if the value is valid.
        /// </summary>
        /// <returns>
        /// Object boxed version of the attribute value.
        /// or null if invalid or unable to readValue stored in Falken's attribute.
        /// </returns>
        internal virtual object ReadFieldIfValid() {
            return ReadField();
        }

        /// <summary>
        /// Invalidates the value of any non-Falken field represented by this attribute.
        /// </summary>
        internal virtual void InvalidateNonFalkenFieldValue() {}
    }
}
