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

namespace Falken
{

    /// <summary>
    /// <c>UnsupportedFalkenTypeException</c> thrown when an
    /// unsupported type is added as a public field in the class's fields.
    /// </summary>
    [Serializable]
    public class UnsupportedFalkenTypeException : Exception
    {
        internal UnsupportedFalkenTypeException()
        {
        }

        internal UnsupportedFalkenTypeException(string message)
          : base(message) { }

        internal UnsupportedFalkenTypeException(string message, Exception inner)
          : base(message, inner) { }
    }

    /// <summary>
    /// <c>AlreadyBoundException</c> thrown when an
    /// trying to bind an attribute or container that it's already bound.
    /// </summary>
    [Serializable]
    public class AlreadyBoundException : Exception
    {
        internal AlreadyBoundException()
        {
        }

        internal AlreadyBoundException(string message)
          : base(message) { }

        internal AlreadyBoundException(string message, Exception inner)
          : base(message, inner) { }
    }

    /// <summary>
    /// <c>AttributeContainer</c> is a dictionary that connects a C# field
    /// to a Falken's attribute or also enables the possibility to add
    /// dynamic attributes. Each attribute has to be unique, since the
    /// connection is one to one.
    /// </summary>
    public class AttributeContainer : IDictionary<string, Falken.AttributeBase>
    {
        // Map FalkenInternal attribute types to C# class types.
        static private Dictionary<FalkenInternal.falken.AttributeBase.Type, Type> _typeToClass =
          new Dictionary<FalkenInternal.falken.AttributeBase.Type, Type>()
          {
        {FalkenInternal.falken.AttributeBase.Type.kTypeBool, typeof(Falken.Boolean)},
        {FalkenInternal.falken.AttributeBase.Type.kTypeFloat, typeof(Falken.Number)},
        {FalkenInternal.falken.AttributeBase.Type.kTypeCategorical, typeof(Falken.Category)},
        {FalkenInternal.falken.AttributeBase.Type.kTypeFeelers, typeof(Falken.Feelers)},
        {FalkenInternal.falken.AttributeBase.Type.kTypePosition, typeof(Falken.Position)},
        {FalkenInternal.falken.AttributeBase.Type.kTypeRotation, typeof(Falken.Rotation)},
        {FalkenInternal.falken.AttributeBase.Type.kTypeJoystick, typeof(Falken.Joystick)},
          };

        /// <summary>
        /// Create an attribute instance based on the internal type.
        /// </summary>
        static private AttributeBase CreateByType(
          FalkenInternal.falken.AttributeBase.Type type)
        {
            return (Falken.AttributeBase)Activator.CreateInstance(_typeToClass[type]);
        }
        // List of attributes.
        private Dictionary<string, Falken.AttributeBase> _attributes =
          new Dictionary<string, Falken.AttributeBase>();
        // Internal Falken container this instance uses to create attributes.
        private FalkenInternal.falken.AttributeContainer _container = null;

        #region IEnumerator
        /// <summary>
        /// Get underlying attributes enumerator.
        /// </summary>
        IEnumerator IEnumerable.GetEnumerator()
        {
            return _attributes.GetEnumerator();
        }

        #endregion

        #region IEnumerator<KeyValuePair<string, Falken.AttributeBase>
        /// <summary>
        /// Get underlying attributes enumerator.
        /// </summary>
        public IEnumerator<KeyValuePair<string, Falken.AttributeBase>> GetEnumerator()
        {
            return _attributes.GetEnumerator();
        }

        #endregion

        #region ICollection
        /// <summary>
        /// Get amount of the attributes that were added to this container.
        /// </summary>
        public int Count
        {
            get
            {
                return _attributes.Count;
            }
        }

        /// <summary>
        /// Check if this is ReadOnly.
        /// <returns> True if the container is bound, false otherwise. </returns>
        /// </summary>
        public bool IsReadOnly
        {
            get
            {
                return Bound;
            }
        }

        /// <summary>
        /// Add an attribute to the container or replace it if it already
        /// exists.
        /// </summary>
        public void Add(KeyValuePair<string, Falken.AttributeBase> item)
        {
            Add(item.Key, item.Value);
        }

        /// <summary>
        /// Clear all attributes added unless it's bound.
        /// <exception> InvalidOperationException thrown when
        /// trying to clear a bound container. </exception>
        /// </summary>
        public void Clear()
        {
            if (!IsReadOnly)
            {
                _attributes.Clear();
            }
            else
            {
                throw new InvalidOperationException(
                  "Can't clear a bound container.");
            }
        }

        /// <summary>
        /// Check if a given item exists.
        /// </summary>
        public bool Contains(KeyValuePair<string, Falken.AttributeBase> item)
        {
            return ContainsKey(item.Key);
        }

        /// <summary>
        /// Copy attribute references from the container to the specified array.
        /// </summary>
        /// <param name="array">Array to copy to.</param>
        /// <param name="arrayIndex">Index to copy from the collection.</param>
        public void CopyTo(KeyValuePair<string, Falken.AttributeBase>[] array, int arrayIndex)
        {
            var collection = (ICollection<KeyValuePair<string, Falken.AttributeBase>>)_attributes;
            collection.CopyTo(array, arrayIndex);
        }

        /// <summary>
        /// Remove a given item if exists.
        /// </summary>
        public bool Remove(KeyValuePair<string, Falken.AttributeBase> item)
        {
            return Remove(item.Key);
        }

        #endregion

        #region IDictionary
        /// <summary>
        /// Get the attribute with a given name.
        /// <exception> KeyNotFoundException if attribute does not
        /// exists. </exception>
        /// <exception> InvalidOperationException if trying to modify
        /// the container that it's already bound </exception>
        /// </summary>
        public Falken.AttributeBase this[string key]
        {
            get
            {
                return _attributes[key];
            }

            set
            {
                if (!IsReadOnly)
                {
                    // TODO(bmarchi): Ensure that the attribute's name
                    // and the key used are the same.
                    _attributes[key] = value;
                }
                else
                {
                    throw new InvalidOperationException(
                      "You can't modify the container that it's bound.");
                }
            }
        }

        /// <summary>
        /// Get the name of all added attributes.
        /// </summary>
        public ICollection<string> Keys
        {
            get
            {
                return _attributes.Keys;
            }
        }

        /// <summary>
        /// Get all attributes.
        /// </summary>
        public ICollection<Falken.AttributeBase> Values
        {
            get
            {
                return _attributes.Values;
            }
        }

        /// <summary>
        /// Add an attribute or replace it if it does not exists.
        /// </summary>
        public void Add(string key, Falken.AttributeBase value)
        {
            this[key] = value;
        }

        /// <summary>
        /// Check if an attribute exists by name.
        /// </summary>
        public bool ContainsKey(string key)
        {
            return _attributes.ContainsKey(key);
        }

        /// <summary>
        /// Remove an attribute from the container only if it's not bound.
        /// <exception> InvalidOperationException thrown when trying to remove
        /// a key from the container when this is bound. </exception>
        /// </summary>
        public bool Remove(string key)
        {
            if (!Bound)
            {
                return _attributes.Remove(key);
            }
            throw new InvalidOperationException(
              "You can't remove attributes in a container that it's already bound.");
        }

        /// <summary>
        /// Get an attribute with given name.
        /// <returns> True if attribute found, false otherwise. </returns>
        /// </summary>
        public bool TryGetValue(string key, out Falken.AttributeBase value)
        {
            return _attributes.TryGetValue(key, out value);
        }

        #endregion

        /// <summary>
        /// Check if the container is bound.
        /// </summary>
        public bool Bound
        {
            get
            {
                return _container != null;
            }
        }

        /// <summary>
        /// Check if a given object is a supported type
        /// by this container.
        /// </summary>
        protected virtual bool SupportsType(object fieldValue)
        {
            return true;
        }

        /// <summary>
        /// Bind all supported fields to a Falken attribute.
        /// If any error ocurrs, the container will be cleared.
        /// <exception> AlreadyBoundException thrown when trying to
        /// bind the container when it was bound already. Also thrown
        /// when trying to bind a dynamic attribute that was already bound.
        /// </exception>
        /// <exception> UnsupportedFalkenTypeException thrown when
        /// a non supported type is added as a public field of the
        /// attribute container. </exception>
        /// <exception> NullReferenceException thrown when
        /// the field value is null. </exception>
        /// <exception> InvalidOperationException thrown when trying to
        /// bind the container when this instance was being used
        /// by manually adding each attribute instead of using
        /// reflection. </exception>
        /// </summary>
        internal void BindAttributes(FalkenInternal.falken.AttributeContainer container)
        {
            if (Bound)
            {
                throw new AlreadyBoundException(
                  "Can't bind the container more than once.");
            }
            // First bind the dynamically added attributes.
            foreach (Falken.AttributeBase attribute in _attributes.Values)
            {
                if (attribute.Bound)
                {
                    _attributes.Clear();
                    throw new AlreadyBoundException(
                      $"Can't bind container. Dynamic attribute '{attribute.Name}' " +
                      "is already bound. Make sure to create a new attribute " +
                      "per container.");
                }
                attribute.BindAttribute(null, null, container);
            }
            foreach (FieldInfo fieldInfo in GetType().GetFields(BindingFlags.Instance |
                                                                BindingFlags.Public))
            {
                Falken.AttributeBase attribute = null;
                object fieldValue = fieldInfo.GetValue(this);
                bool bindToFalkenAttribute = fieldValue.GetType().IsSubclassOf(
                    typeof(AttributeBase));
                if (fieldValue == null)
                {
                    Clear();
                    throw new NullReferenceException(
                      $"Field '{fieldInfo.Name}' value is null while trying to " +
                      $"bind the attributes for class '{GetType().ToString()}'");
                }
                else if (!bindToFalkenAttribute && !SupportsType(fieldValue))
                {
                    Clear();
                    throw new UnsupportedFalkenTypeException(
                      $"Field '{fieldInfo.Name}' " +
                      $"has unsupported type '{fieldInfo.FieldType.ToString()}' " +
                      "or it does not have the necessary implicit conversions.");
                }
                else if (ContainsKey(fieldInfo.Name))
                {
                    Clear();
                    throw new ArgumentException(
                      $"Can't bind '{fieldInfo.FieldType}' attribute '{fieldInfo.Name}' since " +
                      "another attribute with the same name exists.");
                }

                if (bindToFalkenAttribute)
                {
                    // The field is already an Attribute, so we don't need to create an Attribute
                    // to track it.
                    attribute = (AttributeBase) fieldValue;
                }
                else if (Number.CanConvertToNumberType(fieldValue))
                {
                    attribute = new Falken.Number();
                }
                else if (Boolean.CanConvertToBooleanType(fieldValue))
                {
                    attribute = new Falken.Boolean();
                }
                else if (Category.CanConvertToCategoryType(fieldValue))
                {
                    attribute = new Falken.Category();
                }
                else if (Position.CanConvertToPositionType(fieldValue))
                {
                    attribute = new Falken.Position();
                }
                else if (Rotation.CanConvertToRotationType(fieldValue))
                {
                    attribute = new Falken.Rotation();
                }
                else if (Joystick.CanConvertToJoystickType(fieldValue))
                {
                    attribute = (Falken.Joystick)fieldValue;
                }
                else if (Feelers.CanConvertToFeelersType(fieldValue))
                {
                    // We use the field value here since the feeler's attribute
                    // is used directly.
                    attribute = (Falken.Feelers)fieldValue;
                }
                if (attribute != null)
                {
                    try
                    {
                        attribute.BindAttribute(fieldInfo, this, container);
                    }
                    catch
                    {
                        Clear();
                        throw;
                    }
                    Add(fieldInfo.Name, attribute);

                    if (attribute.HasForeignFieldValue)
                    {
                        // If the attribute doesn't represent itself, make sure the represented
                        // field is readable.
                        attribute.ReadField();
                    }
                }
                else
                {
                    throw new UnsupportedFalkenTypeException(
                      $"Field '{fieldInfo.Name}' " +
                      $"has unsupported type '{fieldInfo.FieldType.ToString()}' " +
                      "or it does not have the necessary implicit conversions.");
                }
            }
            _container = container;
        }

        /// <summary>
        /// Change the internal container. It's assumed that the container
        /// has exactly the same attributes with the same properties and types.
        /// </summary>
        internal void Rebind(FalkenInternal.falken.AttributeContainer container)
        {
            foreach (FalkenInternal.falken.AttributeBase attribute in container.attributes())
            {
                // TODO(bmarchi): In theory, equality checks are useless since this
                // will be called when a brain is created. Since a brain is created
                // with a brain spec, is expected that it will have exactly the same
                // attributes and properties.
                Falken.AttributeBase falkenAttribute = this[attribute.name()];
                falkenAttribute.Rebind(attribute);
            }
            _container = container;
        }

        /// <summary>
        /// Clone and bind the attributes that are defined in the given container.
        /// </summary>
        internal void LoadAttributes(FalkenInternal.falken.AttributeContainer container,
          HashSet<string> inheritedAttributes = null)
        {
            foreach (FalkenInternal.falken.AttributeBase attributeBase in container.attributes())
            {
                string attributeName = attributeBase.name();
                Falken.AttributeBase attribute = CreateByType(attributeBase.type());
                FieldInfo fieldInfo;
                object fieldContainer;
                if (inheritedAttributes != null &&
                    inheritedAttributes.Contains(attributeName))
                {
                    // This is assumed to not be null since inherited
                    // attributes are only used by the Entity.
                    fieldInfo = GetType().GetField(attributeName);
                    fieldContainer = this;
                }
                else
                {
                    fieldInfo = null;
                    fieldContainer = null;
                }
                attribute.SetFalkenInternalAttribute(attributeBase, fieldInfo, fieldContainer);
                this[attributeName] = attribute;
            }
            _container = container;
        }

        /// <summary>
        /// Read each attribute.
        /// </summary>
        internal void ReadAttributes()
        {
            foreach (Falken.AttributeBase attribute in _attributes.Values)
            {
                attribute.Read();
            }
        }

        /// <summary>
        /// Write Falken's internal attributes value to C# fields.
        /// This does not do anything for dynamic attributes.
        /// </summary>
        internal void WriteAttributes()
        {
            foreach (Falken.AttributeBase attribute in _attributes.Values)
            {
                attribute.Write();
            }
        }

        /// <summary>
        /// Invalidates all the attributes to mark them as not updated.
        /// </summary>
        internal void InvalidateAttributeValues()
        {
            foreach (var attribute in _attributes)
            {
                attribute.Value.InvalidateNonFalkenFieldValue();
            }
        }
    }
}
