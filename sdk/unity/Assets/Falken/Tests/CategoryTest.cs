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
    public enum FalkenWeaponEnum
    {
        Pistol = 0,
        Shotgun = 1,
        SMG = 2,
    }

    public enum FalkenSpellEnum
    {
        Thunder = 5000,
        Bio = 7543
    }

    public class WeaponEnumContainer : Falken.AttributeContainer
    {
        public FalkenWeaponEnum weapon =
          FalkenWeaponEnum.Shotgun;
    }

    public class SpellEnumContainer : Falken.AttributeContainer
    {
        public FalkenSpellEnum spell =
          FalkenSpellEnum.Bio;
    }

    public class CategoryAttributeTest
    {
        private FalkenInternal.falken.AttributeContainer _falkenContainer;

        [SetUp]
        public void Setup()
        {
            _falkenContainer = new FalkenInternal.falken.AttributeContainer();
        }

        [Test]
        public void BindZeroStartEnumCategory()
        {
            WeaponEnumContainer weaponContainer = new WeaponEnumContainer();
            FieldInfo weaponField =
              typeof(WeaponEnumContainer).GetField("weapon");
            Falken.Category category = new Falken.Category();
            category.BindAttribute(weaponField, weaponContainer, _falkenContainer);
            Assert.AreEqual((int)FalkenWeaponEnum.Shotgun, category.Value);
            Assert.AreEqual(FalkenWeaponEnum.Shotgun, category.AsEnum<FalkenWeaponEnum>());
            string[] enum_names = typeof(FalkenWeaponEnum).GetEnumNames();
            Assert.IsTrue(Enumerable.SequenceEqual(enum_names,
                                                   (List<string>)category.CategoryValues));
            category.Value = (int)FalkenWeaponEnum.SMG;
            Assert.AreEqual(FalkenWeaponEnum.SMG, weaponContainer.weapon);
            weaponContainer.weapon = FalkenWeaponEnum.Pistol;
            Assert.AreEqual((int)FalkenWeaponEnum.Pistol, category.Value);
        }

        [Test]
        public void BindRandomValueInitializationEnumCategory()
        {
            SpellEnumContainer spellContainer = new SpellEnumContainer();
            FieldInfo spellField =
              typeof(SpellEnumContainer).GetField("spell");
            Falken.Category category = new Falken.Category();
            category.BindAttribute(spellField, spellContainer, _falkenContainer);
            Assert.AreEqual(1, category.Value);
            Assert.AreEqual(FalkenSpellEnum.Bio, category.AsEnum<FalkenSpellEnum>());
            string[] enum_names = typeof(FalkenSpellEnum).GetEnumNames();
            Assert.IsTrue(Enumerable.SequenceEqual(enum_names,
                                                   (List<string>)category.CategoryValues));
            category.Value = 0;
            Assert.AreEqual(FalkenSpellEnum.Thunder, spellContainer.spell);
            spellContainer.spell = FalkenSpellEnum.Bio;
            Assert.AreEqual(1, category.Value);
        }

        [Test]
        public void ThrowEnumTypeMismatchException()
        {
            WeaponEnumContainer weaponContainer = new WeaponEnumContainer();
            FieldInfo weaponField =
              typeof(WeaponEnumContainer).GetField("weapon");
            Falken.Category category = new Falken.Category();
            category.BindAttribute(weaponField, weaponContainer, _falkenContainer);
            Assert.That(() => category.AsEnum<FalkenSpellEnum>(),
                        Throws.TypeOf<Falken.Category.EnumTypeMismatchException>()
                        .With.Message.EqualTo("Can't cast to a different enum type. " +
                                              "Given enum type is " +
                                              typeof(FalkenSpellEnum) +
                                              " and this attribute was created with a " +
                                              typeof(FalkenWeaponEnum)));
        }

        [Test]
        public void CreateDynamicCategory()
        {
            List<string> categoryValues = new List<string>() { "zero" };
            Falken.Category attribute =
              new Falken.Category("category", categoryValues);
        }

        [Test]
        public void CreateDynamicCategoryNullName()
        {
            Assert.That(() => new Falken.Category(null, null),
                        Throws.TypeOf<ArgumentNullException>());
        }

        [Test]
        public void CreateDynamicCategoryEmptyCategories()
        {
            List<string> emptyCategories = new List<string>();
            Assert.That(() => new Falken.Category("category", emptyCategories),
                        Throws.TypeOf<ArgumentException>()
                        .With.Message.EqualTo("There's no category in the given category values."));
        }

        [Test]
        public void RebindCategory()
        {
            Falken.AttributeContainer container = new Falken.AttributeContainer();
            string[] categoryValues = new string[] { "zero", "one" };
            Falken.Category category =
              new Falken.Category("category", categoryValues);
            category.BindAttribute(null, null, _falkenContainer);
            category.Value = 1;
            Assert.AreEqual(1, category.Value);
            FalkenInternal.falken.AttributeContainer otherContainer =
              new FalkenInternal.falken.AttributeContainer();
            FalkenInternal.falken.AttributeBase newCategory =
              new FalkenInternal.falken.AttributeBase(otherContainer, "category",
                new FalkenInternal.std.StringVector(categoryValues));
            category.Rebind(newCategory);
            Assert.AreEqual(0, category.Value);
            Assert.AreEqual(0, newCategory.category());
            category.Value = 1;
            Assert.AreEqual(1, category.Value);
            Assert.AreEqual(1, newCategory.category());
        }

        [Test]
        public void WriteCategory()
        {
            WeaponEnumContainer categoryContainer =
              new WeaponEnumContainer();
            categoryContainer.BindAttributes(_falkenContainer);
            Falken.Category attribute = (Falken.Category)categoryContainer["weapon"];
            Assert.AreEqual(1, attribute.Value);
            FalkenInternal.falken.AttributeBase internalAttribute =
              attribute.InternalAttribute;
            internalAttribute.set_category(2);
            attribute.Write();
            Assert.AreEqual(FalkenWeaponEnum.SMG, categoryContainer.weapon);
        }

        [Test]
        public void CategoryValidity()
        {
            WeaponEnumContainer weaponContainer = new WeaponEnumContainer();
            FieldInfo weaponField =
              typeof(WeaponEnumContainer).GetField("weapon");
            Falken.Category category = new Falken.Category();
            category.BindAttribute(weaponField, weaponContainer, _falkenContainer);
            Assert.AreEqual((int)FalkenWeaponEnum.Shotgun, category.Value);
            Assert.IsNull(category.ReadFieldIfValid());
            category.Value = 0;
            Assert.IsNotNull(category.ReadFieldIfValid());
            category.Value = 1;
            Assert.IsNotNull(category.ReadFieldIfValid());
            category.InvalidateNonFalkenFieldValue();
            Assert.IsNull(category.ReadFieldIfValid());
        }
    }

    public class CategoryContainerTest
    {

        private FalkenInternal.falken.AttributeContainer _falkenContainer;

        [SetUp]
        public void Setup()
        {
            _falkenContainer = new FalkenInternal.falken.AttributeContainer();
        }

        [Test]
        public void BindZeroStartEnumContainer()
        {
            WeaponEnumContainer weaponContainer = new WeaponEnumContainer();
            weaponContainer.BindAttributes(_falkenContainer);
            Assert.IsTrue(weaponContainer.Bound);
            Assert.IsTrue(weaponContainer["weapon"] is Falken.Category);
            Falken.Category weapon = (Falken.Category)weaponContainer["weapon"];
            Assert.AreEqual(1, weapon.Value);
            Assert.AreEqual(FalkenWeaponEnum.Shotgun,
              weapon.AsEnum<FalkenWeaponEnum>());
        }

        [Test]
        public void BindRandomValueInitializationContainer()
        {
            SpellEnumContainer spellContainer = new SpellEnumContainer();
            spellContainer.BindAttributes(_falkenContainer);
            Assert.IsTrue(spellContainer.Bound);
            Assert.IsTrue(spellContainer["spell"] is Falken.Category);
            Falken.Category spell = (Falken.Category)spellContainer["spell"];
            Assert.AreEqual(1, spell.Value);
            Assert.AreEqual(FalkenSpellEnum.Bio,
              spell.AsEnum<FalkenSpellEnum>());
        }

        [Test]
        public void BindDynamicCategory()
        {
            Falken.AttributeContainer container = new Falken.AttributeContainer();
            List<string> category_values = new List<string>() { "zero", "one", "two" };
            Falken.Category category = new Falken.Category("category", category_values);
            container["category"] = category;
            container.BindAttributes(_falkenContainer);
            Assert.AreEqual(1, container.Values.Count);
            Assert.IsTrue(container.ContainsKey("category"));
            Assert.IsTrue(
              Enumerable.SequenceEqual(category_values,
                (List<string>)category.CategoryValues));
        }
    }
}
