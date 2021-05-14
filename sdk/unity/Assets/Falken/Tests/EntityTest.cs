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
using NUnit.Framework;

// Do not warn about missing documentation.
#pragma warning disable 1591

namespace FalkenTests
{
    public sealed class EnemyExampleEntity : Falken.EntityBase
    {
        [Falken.Range(-1f, 1f)]
        public float lookUpAngle = 0.5f;

        public bool shoot = true;

        [Falken.Range(2, 5)]
        public int energy = 3;

        public FalkenWeaponEnum weapon = FalkenWeaponEnum.Shotgun;

        public Falken.Number numberAttribute = new Falken.Number(0, 1);
        public Falken.Category categoryAttribute = new Falken.Category(
            new List<string>(){"yes", "no", "yes, and"});
        public Falken.Boolean booleanAttribute = new Falken.Boolean();
    }

    public sealed class SimpleExampleEntity : Falken.EntityBase
    {
        public bool friend = true;
    }

    public sealed class SimpleExampleEntityWithFeelers : Falken.EntityBase
    {
        public Falken.Feelers feeler =
          new Falken.Feelers(4.0f, 1.0f, 180.0f, 14,
            new List<string>() { "Nothing", "Enemy", "Wall" });
    }

    public class EnemyEntityTestContainer : Falken.EntityContainer
    {
        public EnemyExampleEntity enemy = new EnemyExampleEntity();
    }

    public sealed class TwoEntitiesTestContainer : EnemyEntityTestContainer
    {
        public SimpleExampleEntity simpleEnemy = new SimpleExampleEntity();
    }

    public sealed class UnsupportedTypesTestEntity : Falken.EntityBase
    {
        [Falken.Range(2, 5)]
        public int energy = 3;
        public double unsupportedType = 1.0;
    }

    public sealed class UnsupportedTypesEntityContainerTest :
      Falken.EntityContainer
    {
        public UnsupportedTypesTestEntity unsupportedEntity =
          new UnsupportedTypesTestEntity();
    }

    public sealed class UnsupportedFieldsInContainter : Falken.EntityContainer
    {
        public double unsupportedType = 4.0;
    }

    public class EntityTest
    {
        private FalkenInternal.falken.EntityContainer _falkenContainer;

        [SetUp]
        public void Setup()
        {
            _falkenContainer = new FalkenInternal.falken.EntityContainer();
        }

        [Test]
        public void CreateDynamicEntity()
        {
            Falken.EntityBase entity = new Falken.EntityBase("entity");
        }

        [Test]
        public void CreateDynamicEntityNullName()
        {
            Assert.That(() => new Falken.EntityBase(null),
                        Throws.TypeOf<ArgumentNullException>());
        }

        [Test]
        public void BindDynamicEntity()
        {
            Falken.EntityBase entity = new Falken.EntityBase("entity");
            Falken.Boolean boolean = new Falken.Boolean("boolean");
            entity["boolean"] = boolean;
            entity.BindEntity(null, _falkenContainer);
            // Position and rotation attributes are included.
            Assert.AreEqual(entity.Count, 3);
            Assert.IsTrue(entity.ContainsKey("boolean"));
            Falken.Boolean entityBoolean = (Falken.Boolean)entity["boolean"];
            Assert.IsTrue(entityBoolean.Bound);
            Assert.IsFalse(entityBoolean.Value);
            entityBoolean.Value = true;
            Assert.IsTrue(entityBoolean.Value);
        }

        [Test]
        public void BindEntity()
        {
            FieldInfo enemyField =
              typeof(EnemyEntityTestContainer).GetField("enemy");
            EnemyExampleEntity enemy = new EnemyExampleEntity();
            enemy.BindEntity(enemyField, _falkenContainer);
            Assert.IsNotNull(_falkenContainer.entity("enemy"));

            Assert.IsTrue(enemy.ContainsKey("lookUpAngle"));
            Assert.IsTrue(enemy["lookUpAngle"] is Falken.Number);
            Falken.Number number = (Falken.Number)enemy["lookUpAngle"];
            Assert.AreEqual(-1.0f, number.Minimum);
            Assert.AreEqual(1.0f, number.Maximum);
            Assert.AreEqual(0.5f, number.Value);

            Assert.IsTrue(enemy.ContainsKey("shoot"));
            Assert.IsTrue(enemy["shoot"] is Falken.Boolean);
            Falken.Boolean boolean = (Falken.Boolean)enemy["shoot"];
            Assert.AreEqual(true, boolean.Value);

            Assert.IsTrue(enemy.ContainsKey("energy"));
            Assert.IsTrue(enemy["energy"] is Falken.Number);
            Falken.Number energy = (Falken.Number)enemy["energy"];
            Assert.AreEqual(2.0f, energy.Minimum);
            Assert.AreEqual(5.0f, energy.Maximum);
            Assert.AreEqual(3.0f, energy.Value);

            Assert.IsTrue(enemy.ContainsKey("weapon"));
            Assert.IsTrue(enemy["weapon"] is Falken.Category);
            Falken.Category weapon = (Falken.Category)enemy["weapon"];
            Assert.AreEqual(1, weapon.Value);
            string[] enum_names = typeof(FalkenWeaponEnum).GetEnumNames();
            Assert.IsTrue(
              Enumerable.SequenceEqual(enum_names,
                weapon.CategoryValues));

            Assert.IsTrue(enemy.ContainsKey("numberAttribute"));
            Assert.IsTrue(enemy["numberAttribute"] == enemy.numberAttribute);
            enemy.numberAttribute.Value = 0.5f;
            Assert.AreEqual(enemy.numberAttribute.Value, 0.5f);

            Assert.IsTrue(enemy.ContainsKey("booleanAttribute"));
            Assert.IsTrue(enemy["booleanAttribute"] == enemy.booleanAttribute);
            enemy.booleanAttribute.Value = true;
            Assert.AreEqual(enemy.booleanAttribute.Value, true);

            Assert.IsTrue(enemy.ContainsKey("categoryAttribute"));
            Assert.IsTrue(enemy["categoryAttribute"] == enemy.categoryAttribute);
            enemy.categoryAttribute.Value = 1;
            Assert.AreEqual(enemy.categoryAttribute.Value, 1);


            Assert.IsTrue(enemy.ContainsKey("position"));
            Assert.IsTrue(enemy["position"] is Falken.Position);
            Falken.Position position = (Falken.Position)enemy["position"];
            Falken.PositionVector positionVector = position.Value;
            Assert.AreEqual(0.0f, positionVector.X);
            Assert.AreEqual(0.0f, positionVector.Y);
            Assert.AreEqual(0.0f, positionVector.Z);

            Assert.IsTrue(enemy.ContainsKey("rotation"));
            Assert.IsTrue(enemy["rotation"] is Falken.Rotation);
            Falken.Rotation rotation = (Falken.Rotation)enemy["rotation"];
            Falken.RotationQuaternion rotationQuaternion = rotation.Value;
            Assert.AreEqual(0.0f, rotationQuaternion.X);
            Assert.AreEqual(0.0f, rotationQuaternion.Y);
            Assert.AreEqual(0.0f, rotationQuaternion.Z);
            Assert.AreEqual(1.0f, rotationQuaternion.W);
        }

        [Test]
        public void BindEntityWithUnsupportedTypes()
        {
            FieldInfo unsupportedTypesEntityField =
              typeof(UnsupportedTypesEntityContainerTest).GetField("unsupportedEntity");
            UnsupportedTypesTestEntity unsupportedTypesEntity =
              new UnsupportedTypesTestEntity();
            Assert.That(() => unsupportedTypesEntity.BindEntity(unsupportedTypesEntityField,
                                                                _falkenContainer),
                        Throws.TypeOf<Falken.UnsupportedFalkenTypeException>()
                        .With.Message.EqualTo($"Field 'unsupportedType' has unsupported " +
                                              $"type '{typeof(double).ToString()}' " +
                                              "or it does not have the necessary " +
                                              "implicit conversions."));
        }

        [Test]
        public void LoadEntity()
        {
            FalkenInternal.falken.EntityBase entity =
              new FalkenInternal.falken.EntityBase(_falkenContainer, "entity");
            FalkenInternal.falken.AttributeBase boolean =
              new FalkenInternal.falken.AttributeBase(
                entity, "boolean",
                FalkenInternal.falken.AttributeBase.Type.kTypeBool);
            FalkenInternal.falken.AttributeBase number =
              new FalkenInternal.falken.AttributeBase(
                entity, "number", -1.0f, 1.0f);
            FalkenInternal.falken.AttributeBase category =
              new FalkenInternal.falken.AttributeBase(
                entity, "category",
                new FalkenInternal.std.StringVector() { "zero", "one" });
            FalkenInternal.falken.AttributeBase feeler =
              new FalkenInternal.falken.AttributeBase(
                entity, "feeler", 2,
                5.0f, 45.0f, 1.0f,
                new FalkenInternal.std.StringVector() { "zero", "one" });

            Falken.EntityBase falkenEntity = new Falken.EntityBase("entity");
            falkenEntity.LoadEntity(entity);

            Assert.IsTrue(falkenEntity.ContainsKey("position"));
            Assert.IsTrue(falkenEntity["position"] is Falken.Position);
            Assert.IsTrue(falkenEntity["position"].Bound);

            Falken.Position positionAttribute = (Falken.Position)falkenEntity["position"];
            falkenEntity.position = new Falken.PositionVector(3.0f, 2.0f, 1.0f);
            Assert.AreEqual(3.0f, positionAttribute.Value.X);
            Assert.AreEqual(2.0f, positionAttribute.Value.Y);
            Assert.AreEqual(1.0f, positionAttribute.Value.Z);
            FieldInfo positionField = typeof(Falken.EntityBase).GetField("position");
            Assert.AreEqual(3.0f, positionAttribute.Value.X);
            Assert.AreEqual(2.0f, positionAttribute.Value.Y);
            Assert.AreEqual(1.0f, positionAttribute.Value.Z);
        }
    }

    public class InheritedEntityContainer : Falken.EntityContainer
    {
        [Falken.FalkenInheritedAttribute]
        public SimpleExampleEntity inheritedEntity =
          new SimpleExampleEntity();
    }

    public class EntityContainerTest
    {
        private FalkenInternal.falken.EntityContainer _falkenContainer;

        [SetUp]
        public void Setup()
        {
            _falkenContainer = new FalkenInternal.falken.EntityContainer();
        }

        [Test]
        public void AddEntity()
        {
            Falken.EntityContainer container = new Falken.EntityContainer();
            Falken.EntityBase random = new Falken.EntityBase("random");
            Assert.AreEqual(0, container.Count);
            container["random"] = random;
            Assert.IsTrue(container.ContainsKey("random"));
            Assert.AreEqual(1, container.Count);
            container.Add("random2", new Falken.EntityBase("random2"));
            Assert.IsTrue(container.ContainsKey("random2"));
            Assert.AreEqual(2, container.Count);
            container.Add(
              new KeyValuePair<string, Falken.EntityBase>(
                "random3", new Falken.EntityBase("random3")));
            Assert.IsTrue(container.ContainsKey("random3"));
            Assert.AreEqual(3, container.Count);
        }

        [Test]
        public void AddEntityBoundContainer()
        {
            Falken.EntityContainer container = new Falken.EntityContainer();
            Falken.EntityBase random = new Falken.EntityBase("random");
            random["boolean"] = new Falken.Boolean("boolean");
            container["random"] = random;
            container.BindEntities(_falkenContainer);
            Assert.That(() => container.Add("random2", new Falken.EntityBase("random2")),
                        Throws.TypeOf<InvalidOperationException>());
            Assert.IsFalse(container.ContainsKey("random2"));
            Assert.AreEqual(1, container.Count);
        }

        [Test]
        public void ClearContainer()
        {
            Falken.EntityContainer container = new Falken.EntityContainer();
            Falken.EntityBase random = new Falken.EntityBase("random");
            container["random"] = random;
            Assert.AreEqual(1, container.Count);
            container.Clear();
            Assert.AreEqual(0, container.Count);
        }

        [Test]
        public void ClearBoundContainer()
        {
            Falken.EntityContainer container = new Falken.EntityContainer();
            Falken.EntityBase random = new Falken.EntityBase("random");
            container["random"] = random;
            Assert.AreEqual(1, container.Count);
            container.BindEntities(_falkenContainer);
            Assert.That(() => container.Clear(),
                        Throws.TypeOf<InvalidOperationException>());
            Assert.AreEqual(1, container.Count);
        }

        [Test]
        public void RemoveEntities()
        {
            Falken.EntityContainer container = new Falken.EntityContainer();
            Falken.EntityBase random = new Falken.EntityBase("random");
            container["random"] = random;
            container["random2"] = new Falken.EntityBase("random2");
            Assert.IsTrue(container.ContainsKey("random"));
            Assert.IsTrue(container.Remove("random"));
            Assert.IsFalse(container.ContainsKey("random"));
            Assert.IsFalse(container.Remove("random"));
            Assert.IsTrue(container.ContainsKey("random2"));
        }

        [Test]
        public void RemoveEntitiesFromBoundContainer()
        {
            Falken.EntityContainer container = new Falken.EntityContainer();
            Falken.EntityBase random = new Falken.EntityBase("random");
            container["random"] = random;
            container["random2"] = new Falken.EntityBase("random2");
            container.BindEntities(_falkenContainer);
            Assert.That(() => container.Remove("random"),
                        Throws.TypeOf<InvalidOperationException>());
            Assert.IsTrue(container.ContainsKey("random"));
        }

        [Test]
        public void TryGetEntityValue()
        {
            Falken.EntityContainer container = new Falken.EntityContainer();
            container["random"] = new Falken.EntityBase("random");
            Falken.EntityBase entity = null;
            Assert.IsTrue(container.TryGetValue("random", out entity));
            Assert.IsNotNull(entity);
            Assert.IsFalse(container.TryGetValue("random2", out entity));
            Assert.IsNull(entity);
        }

        [Test]
        public void TryGetEntityValueBoundContainer()
        {
            Falken.EntityContainer container = new Falken.EntityContainer();
            container["random"] = new Falken.EntityBase("random");
            container.BindEntities(_falkenContainer);
            Falken.EntityBase entity = null;
            Assert.IsTrue(container.TryGetValue("random", out entity));
            Assert.IsNotNull(entity);
            Assert.IsFalse(container.TryGetValue("random2", out entity));
            Assert.IsNull(entity);
        }

        [Test]
        public void ReadOnly()
        {
            Falken.EntityContainer container = new Falken.EntityContainer();
            Assert.IsFalse(container.IsReadOnly);
            container["random"] = new Falken.EntityBase("random");
            container.BindEntities(_falkenContainer);
            Assert.IsTrue(container.IsReadOnly);
        }

        [Test]
        public void GetKeys()
        {
            Falken.EntityContainer container = new Falken.EntityContainer();
            container["random"] = new Falken.EntityBase("random");
            container["random2"] = new Falken.EntityBase("random2");
            ICollection<string> keys = container.Keys;
            Assert.AreEqual(2, keys.Count);
            Assert.IsTrue(keys.Contains("random"));
            Assert.IsTrue(keys.Contains("random2"));
        }

        [Test]
        public void GetValues()
        {
            Falken.EntityContainer container = new Falken.EntityContainer();
            container["random"] = new Falken.EntityBase("random");
            container["random2"] = new Falken.EntityBase("random2");
            ICollection<Falken.EntityBase> values = container.Values;
            Assert.AreEqual(2, values.Count);
        }

        [Test]
        public void BindDynamicEntity()
        {
            Falken.EntityBase entity = new Falken.EntityBase("entity");
            Falken.Boolean boolean = new Falken.Boolean("boolean");
            entity["boolean"] = boolean;
            Falken.EntityContainer container = new Falken.EntityContainer();
            container["entity"] = entity;
            container.BindEntities(_falkenContainer);
            Assert.AreEqual(container.Count, 1);
            Assert.IsTrue(container.ContainsKey("entity"));
            Assert.IsTrue(container["entity"].ContainsKey("boolean"));
        }

        [Test]
        public void BindSharedDynamicEntity()
        {
            Falken.EntityBase entity = new Falken.EntityBase("entity");
            Falken.Boolean boolean = new Falken.Boolean("boolean");
            entity["boolean"] = boolean;
            Falken.EntityContainer container = new Falken.EntityContainer();
            container["entity"] = entity;
            container.BindEntities(_falkenContainer);

            Falken.EntityContainer anotherContainer =
              new Falken.EntityContainer();
            anotherContainer["entity"] = entity;
            Assert.That(() => anotherContainer.BindEntities(_falkenContainer),
                        Throws.TypeOf<Falken.AlreadyBoundException>()
                        .With.Message.EqualTo($"Can't bind entity container. Entity " +
                                              $"'{entity.Name}' is already bound."));
        }

        [Test]
        public void BindEntityContainer()
        {
            TwoEntitiesTestContainer container =
              new TwoEntitiesTestContainer();
            container.BindEntities(_falkenContainer);
            Assert.IsTrue(container.ContainsKey("enemy"));
            Assert.IsTrue(container.ContainsKey("simpleEnemy"));
            Assert.IsTrue(container["simpleEnemy"].ContainsKey("friend"));
        }

        [Test]
        public void BindEntityContainerUnsupportedType()
        {
            UnsupportedFieldsInContainter container =
              new UnsupportedFieldsInContainter();
            Assert.That(() => container.BindEntities(_falkenContainer),
                        Throws.TypeOf<Falken.UnsupportedFalkenTypeException>()
                        .With.Message.EqualTo("Can't bind entity container because " +
                                              "'unsupportedType' has an unsupported " +
                                              "type 'System.Double'. Make sure that your field " +
                                              "inherits from 'Falken.Entity'. "));
        }

        [Test]
        public void BindInheritedEntityContainer()
        {
            FalkenInternal.falken.EntityBase inheritedEntity =
              new FalkenInternal.falken.EntityBase(
                _falkenContainer, "inheritedEntity");
            InheritedEntityContainer container =
              new InheritedEntityContainer();
            container.BindEntities(_falkenContainer);
            Assert.IsTrue(container.ContainsKey("inheritedEntity"));
        }

        [Test]
        public void BindInheritedEntityWrongNameContainer()
        {
            FalkenInternal.falken.EntityBase inheritedEntity =
              new FalkenInternal.falken.EntityBase(
                _falkenContainer, "anotherName");
            InheritedEntityContainer container =
              new InheritedEntityContainer();

            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Assert.That(() => container.BindEntities(_falkenContainer),
                            Throws.TypeOf<Falken.InheritedAttributeNotFoundException>()
                            .With.Message.EqualTo("Inherited entity field 'inheritedEntity' " +
                                                  "was not found in the entity container."));
            }
        }

        [Test]
        public void RebindEntityContainer()
        {
            EnemyEntityTestContainer enemyContainer = new EnemyEntityTestContainer();
            enemyContainer.BindEntities(_falkenContainer);

            FalkenInternal.falken.EntityContainer otherContainer =
              new FalkenInternal.falken.EntityContainer();
            FalkenInternal.falken.EntityBase enemyEntity =
              new FalkenInternal.falken.EntityBase(otherContainer, "enemy");
            FalkenInternal.falken.AttributeBase lookUpAttribute =
              new FalkenInternal.falken.AttributeBase(enemyEntity, "lookUpAngle", -1.0f, 1.0f);
            FalkenInternal.falken.AttributeBase shootAttribute =
              new FalkenInternal.falken.AttributeBase(enemyEntity, "shoot",
                FalkenInternal.falken.AttributeBase.Type.kTypeBool);
            FalkenInternal.falken.AttributeBase energyAttribute =
              new FalkenInternal.falken.AttributeBase(enemyEntity, "energy", 2.0f, 5.0f);
            FalkenInternal.falken.AttributeBase weaponAttribute =
              new FalkenInternal.falken.AttributeBase(enemyEntity, "weapon",
                new FalkenInternal.std.StringVector(
                  typeof(FalkenWeaponEnum).GetEnumNames()));

            FalkenInternal.falken.AttributeBase falkenNumberAttribute =
              new FalkenInternal.falken.AttributeBase(enemyEntity, "numberAttribute", 0.0f, 1.0f);
            FalkenInternal.falken.AttributeBase falkenBooleanAttribute =
              new FalkenInternal.falken.AttributeBase(enemyEntity, "booleanAttribute",
                FalkenInternal.falken.AttributeBase.Type.kTypeBool);
            FalkenInternal.falken.AttributeBase falkenCategoryAttribute =
              new FalkenInternal.falken.AttributeBase(enemyEntity, "categoryAttribute",
                new FalkenInternal.std.StringVector() { "yes", "no", "yes, and" });

            Falken.Boolean shootBoolean = (Falken.Boolean)enemyContainer["enemy"]["shoot"];
            shootBoolean.Value = true;
            Falken.Number lookUp = (Falken.Number)enemyContainer["enemy"]["lookUpAngle"];
            Falken.Number numberAttribute =
                (Falken.Number)enemyContainer["enemy"]["numberAttribute"];

            enemyContainer.Rebind(otherContainer);
            lookUp.Value = 0.5f;
            numberAttribute.Value = 0.5f;
            Assert.IsTrue(shootBoolean.Value);
            Assert.AreEqual(0.5f, lookUp.Value);
            Assert.AreEqual(0.5f, numberAttribute.Value);
        }
    }
}
