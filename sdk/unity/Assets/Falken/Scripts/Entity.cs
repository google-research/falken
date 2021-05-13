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
    /// <c>EntityBase</c> Observations.
    /// </summary>
    public class EntityBase : Falken.AttributeContainer
    {
        /// <summary>
        /// <c>EntityNotBoundException</c> thrown when access to an
        /// unbound entity property is forbidden.
        /// </summary>
        [Serializable]
        public class EntityNotBoundException : Exception
        {
            internal EntityNotBoundException()
            {
            }

            internal EntityNotBoundException(string message)
              : base(message) { }

            internal EntityNotBoundException(string message, Exception inner)
              : base(message, inner) { }
        }

        // Do not warn about this field being unused as we are explicitly holding a reference to an
        // unmanaged object.
#pragma warning disable 0414
        // Internal falken's entity that this instance
        // is linked to.
        private FalkenInternal.falken.EntityBase _entity = null;
#pragma warning restore 0414

        // Name used for dynamic entities. Will set to null
        // once this entity is bound.
        private string _name = null;

        /// <summary>
        /// Position in world space.
        /// </summary>
        [FalkenInherited]
        public Falken.PositionVector position = new Falken.PositionVector();

        /// <summary>
        /// Rotation in world space.
        /// </summary>
        [FalkenInherited]
        public Falken.RotationQuaternion rotation = new Falken.RotationQuaternion();

        /// <summary>
        /// Check if the entity is bound to a Falken's entity.
        /// </summary>
        internal new bool Bound
        {
            get
            {
                return _entity != null;
            }
        }

        /// <summary>
        /// Create a empty Falken.Entity that is bound to a field.
        /// </summary>
        public EntityBase()
        {
        }

        /// <summary>
        /// Create a dynamic Falken.Entity.
        /// <exception>
        /// ArgumentNullException thrown if name is null.
        /// </exception>
        /// </summary>
        public EntityBase(string name)
        {
            if (name == null)
            {
                throw new ArgumentNullException(name);
            }
            _name = name;
        }

        /// <summary>
        /// Get the name of this entity (which will be equal to the field name).
        /// </summary>
        public string Name
        {
            get
            {
                if (Bound)
                {
                    return _entity.name();
                }
                throw new EntityNotBoundException(
                  "Can't retrieve the name if the entity is not bound.");
            }
        }

        /// <summary>
        /// Establish a connection for all the C# attributes defined
        /// in this instance.
        /// <exception> AlreadyBoundException thrown when trying to
        /// bind the entity when it was bound already. </exception>
        /// </summary>
        internal void BindEntity(FieldInfo field,
          FalkenInternal.falken.EntityContainer container)
        {
            if (Bound)
            {
                throw new AlreadyBoundException(
                  "Can't bind entity more than once.");
            }
            FalkenInternal.falken.EntityBase entity = null;
            if (field != null)
            {
                if (System.Attribute.GetCustomAttribute(field,
                    typeof(FalkenInheritedAttribute)) == null)
                {
                    entity = new FalkenInternal.falken.EntityBase(container,
                      field.Name);
                }
                else
                {
                    entity = container.entity(field.Name);
                    if (entity == null)
                    {
                        throw new InheritedAttributeNotFoundException(
                          $"Inherited entity field '{field.Name}' was not found " +
                          $"in the entity container.");
                    }
                }
            }
            else
            {
                entity = new FalkenInternal.falken.EntityBase(container, _name);
                _name = null;
            }
            base.BindAttributes(entity);
            _entity = entity;
        }

        /// <summary>
        /// Change the internal entity and rebind all the attributes.
        /// It's assumed that the attributes of the given entity are exactly
        /// the same as the ones defined.
        /// </summary>
        internal void Rebind(FalkenInternal.falken.EntityBase entity)
        {
            base.Rebind(entity);
            _entity = entity;
        }

        /// <summary>
        /// Load the attributes that are in the internal entity.
        /// </summary>
        internal void LoadEntity(FalkenInternal.falken.EntityBase entity)
        {
            base.LoadAttributes(entity,
              new HashSet<string>() { "position", "rotation" });
            _entity = entity;
        }
    }
}
