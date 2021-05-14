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
using System.Linq;
using System.Reflection;
using System.Collections.Generic;

namespace Falken
{
    /// <summary>
    /// <c>EntityContainer</c> represents a collection of entities.
    /// </summary>
    public class EntityContainer : IDictionary<string, Falken.EntityBase>
    {
        // List of entities.
        private Dictionary<string, Falken.EntityBase> _entities =
          new Dictionary<string, Falken.EntityBase>();
        // Internal Falken container this instance uses to create entities.
        private FalkenInternal.falken.EntityContainer _container = null;

        #region IEnumerator
        /// <summary>
        /// Get underlying attributes enumerator.
        /// </summary>
        IEnumerator IEnumerable.GetEnumerator()
        {
            return _entities.GetEnumerator();
        }

        #endregion

        #region IEnumerator<KeyValuePair<string, Falken.EntityBase>
        /// <summary>
        /// Get underlying attributes enumerator.
        /// </summary>
        public IEnumerator<KeyValuePair<string, Falken.EntityBase>> GetEnumerator()
        {
            return _entities.GetEnumerator();
        }

        #endregion

        #region ICollection
        /// <summary>
        /// Get amount of the entities that were added to this container.
        /// </summary>
        public int Count
        {
            get
            {
                return _entities.Count;
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
        /// Add an entity to the container or replace it if it already
        /// exists.
        /// </summary>
        public void Add(KeyValuePair<string, Falken.EntityBase> item)
        {
            Add(item.Key, item.Value);
        }

        /// <summary>
        /// Clear all entities added unless it's bound.
        /// <exception> InvalidOperationException thrown
        /// when trying to clear the container is bound.
        /// </exception>
        /// </summary>
        public void Clear()
        {
            if (!IsReadOnly)
            {
                _entities.Clear();
            }
            else
            {
                throw new InvalidOperationException(
                  "Can't clear bound entity container.");
            }
        }

        /// <summary>
        /// Check if a given item exists.
        /// </summary>
        /// <param name="item">Entity to search for in the container.</param>
        public bool Contains(KeyValuePair<string, Falken.EntityBase> item)
        {
            return ContainsKey(item.Key);
        }

        /// <summary>
        /// Copy entity references from the container to the specified array.
        /// </summary>
        /// <param name="array">Array to copy to.</param>
        /// <param name="arrayIndex">Index to copy from the collection.</param>
        public void CopyTo(KeyValuePair<string, Falken.EntityBase>[] array, int arrayIndex)
        {
            var collection = (ICollection<KeyValuePair<string, Falken.EntityBase>>)_entities;
            collection.CopyTo(array, arrayIndex);
        }

        /// <summary>
        /// Remove a given item if exists.
        /// </summary>
        /// <param name="item">Entity to remove from the container.</param>
        public bool Remove(KeyValuePair<string, Falken.EntityBase> item)
        {
            return Remove(item.Key);
        }

        #endregion

        #region IDictionary
        /// <summary>
        /// Get the entity with a given name.
        /// <exception> KeyNotFoundException if attribute does not
        /// exists. </exception>
        /// <exception> InvalidOperationException if trying to modify
        /// the container that it's already bound </exception>
        /// </summary>
        public Falken.EntityBase this[string key]
        {
            get
            {
                return _entities[key];
            }
            set
            {
                if (!IsReadOnly)
                {
                    _entities[key] = value;
                }
                else
                {
                    throw new InvalidOperationException(
                      "You can't modify the container that it's bound.");
                }
            }
        }

        /// <summary>
        /// Get the name of all added entities.
        /// </summary>
        public ICollection<string> Keys
        {
            get
            {
                return _entities.Keys;
            }
        }

        /// <summary>
        /// Get all entities.
        /// </summary>
        public ICollection<Falken.EntityBase> Values
        {
            get
            {
                return _entities.Values;
            }
        }

        /// <summary>
        /// Add an entity or replace it if it does not exists.
        /// </summary>
        public void Add(string key, Falken.EntityBase value)
        {
            this[key] = value;
        }

        /// <summary>
        /// Check if an attribute exists by name.
        /// </summary>
        public bool ContainsKey(string key)
        {
            return _entities.ContainsKey(key);
        }

        /// <summary>
        /// Remove an entity if exists from the container.
        /// <exception> InvalidOperationException thrown when
        /// trying to remove an entity from a bound container. </exception>
        /// </summary>
        public bool Remove(string key)
        {
            if (!IsReadOnly)
            {
                return _entities.Remove(key);
            }
            throw new InvalidOperationException(
              "Can't remove entity from container when this is bound.");
        }

        /// <summary>
        /// Get an entity with given name.
        /// <returns> True if attribute found, false otherwise. </returns>
        /// </summary>
        public bool TryGetValue(string key, out Falken.EntityBase value)
        {
            return _entities.TryGetValue(key, out value);
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
        /// Bind all supported fields to a Falken entity.
        /// Clear the container if an error ocurrs.
        /// </summary>
        /// <exception>UnsupportedFalkenTypeException is thrown when
        /// the entity class has an unsupported field type.</exception>
        /// <exception>AlreadyBoundException is thrown when trying to
        /// bind the entity container when it was bound already or if
        /// a dynamic entity was already bound.</exception>
        internal void BindEntities(FalkenInternal.falken.EntityContainer container)
        {
            if (Bound)
            {
                throw new AlreadyBoundException(
                  "Can't bind entity container more than once.");
            }
            // Bind dynamic entities first.
            // TODO(bmarchi): Ensure users do not add a entity called
            // player.
            foreach (Falken.EntityBase entity in _entities.Values)
            {
                if (entity.Bound)
                {
                    _entities.Clear();
                    throw new AlreadyBoundException(
                      $"Can't bind entity container. Entity '{entity.Name}' " +
                      "is already bound.");
                }
                entity.BindEntity(null, container);
            }
            FieldInfo[] fields = GetType().GetFields(
              BindingFlags.Instance | BindingFlags.Public);
            foreach (FieldInfo field in fields)
            {
                Falken.EntityBase entity = null;
                object fieldValue = field.GetValue(this);
                if (field.FieldType.IsSubclassOf(typeof(Falken.EntityBase)) ||
                    field.FieldType == typeof(Falken.EntityBase))
                {
                    if (fieldValue == null)
                    {
                        entity = (Falken.EntityBase)Activator.CreateInstance(field.FieldType);
                    }
                    else
                    {
                        entity = (Falken.EntityBase)fieldValue;
                    }
                }
                if (entity != null)
                {
                    try
                    {
                        entity.BindEntity(field, container);
                    }
                    catch
                    {
                        _entities.Clear();
                        throw;
                    }
                    Add(field.Name, entity);
                }
                else
                {
                    throw new UnsupportedFalkenTypeException(
                      $"Can't bind entity container because '{field.Name}' " +
                      $"has an unsupported type '{field.FieldType.ToString()}'. " +
                      $"Make sure that your field inherits from 'Falken.Entity'. ");
                }
            }
            _container = container;
        }

        /// <summary>
        /// Change the internal container while also changing the internal
        /// entity for each one. It's assumed that the given container
        /// has exactly the same entities with the same attributes.
        /// </summary>
        internal void Rebind(FalkenInternal.falken.EntityContainer container,
          HashSet<string> inheritedEntities = null)
        {
            var entityList = _entities.ToList();
            // The given container can come from a LoadBrain call, which any
            // entity that it's not the player does not have a name.
            // These entities are named "entity_#", where the # starts from zero.
            // Since the entities are sorted by name, we first ensure that the
            // loaded entities are sorted by name, so we can make a one-to-one
            // relationship.
            // For example, lets say that the internal container was created
            // with 3 entities, named "airplane", "player" and "weapon".
            // When we load a brain, these entities are mapped like the following:
            // "airplane" => "entity_0"
            // "weapon" => "entity_1"
            // "player" => "player"
            // It's important to notice that the "player" entity is a special entity
            // that belongs to the observations, therefore it's not called "entity_#".
            entityList.Sort((pair1, pair2) => pair1.Value.Name.CompareTo(pair2.Value.Name));
            int entityIndex = 0;
            int entityCount = Count;
            List<FalkenInternal.falken.EntityBase> inherited =
              new List<FalkenInternal.falken.EntityBase>();
            // Since we have the entities sorted by name, we now try to match them
            // by index.
            // Lets suppose then that the container looks like the previous
            // example. So initially, by index, it looks like the following:
            // 0 => "airplane" => "entity_0"
            // 1 => "player" => "player"
            // 2 => "weapon" => "entity_1"
            foreach (FalkenInternal.falken.EntityBase entityBase in container.entities())
            {
                // Find the first non-inherited internal entity.
                // In the previous example, entityBase's name is "entity_0",
                // it's not a inherited attribute, so lets continue.
                if (inheritedEntities != null && inheritedEntities.Contains(entityBase.name()))
                {
                    inherited.Add(entityBase);
                    continue;
                }
                // Since both containers are sorted by name, the first
                // index that it's not a inherited entity is the one that
                // correspond to the entityBase.
                // Notice that to get to this point, it's necessary that
                // at least one entity is not a "inherited entity", if not,
                // the for loop exits.
                Falken.EntityBase entity = entityList[entityIndex].Value;
                while (inheritedEntities != null && inheritedEntities.Contains(entity.Name) &&
                       entityIndex < entityCount - 1)
                {
                    ++entityIndex;
                    entity = entityList[entityIndex].Value;
                    continue;
                }
                // From the previous premise, this is always true.
                entity.Rebind(entityBase);
                ++entityIndex;
            }
            foreach (FalkenInternal.falken.EntityBase inheritedEntity in inherited)
            {
                this[inheritedEntity.name()].Rebind(inheritedEntity);
            }
            _container = container;
        }

        /// <summary>
        /// Load each entity that it's in the given internal container.
        /// </summary>
        internal void LoadEntities(FalkenInternal.falken.EntityContainer container)
        {
            foreach (FalkenInternal.falken.EntityBase entityBase in container.entities())
            {
                Falken.EntityBase entity = new Falken.EntityBase();
                entity.LoadEntity(entityBase);
                this[entityBase.name()] = entity;
            }
            _container = container;
        }

        /// <summary>
        /// Read each attribute of each entity.
        /// </summary>
        internal void Read()
        {
            foreach (Falken.EntityBase entity in _entities.Values)
            {
                entity.ReadAttributes();
            }
        }

        /// <summary>
        /// Write each attribute of each entity.
        /// </summary>
        internal void Write()
        {
            foreach (Falken.EntityBase entity in _entities.Values)
            {
                entity.WriteAttributes();
            }
        }

        /// <summary>
        /// Invalidates the attributes in all entities to mark them
        /// as not updated.
        /// </summary>
        internal void InvalidateAttributeValues() {
            foreach (Falken.EntityBase entity in _entities.Values)
            {
                entity.InvalidateAttributeValues();
            }
        }
    }
}
