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
using System.Reflection;
using NUnit.Framework;

// Do not warn about missing documentation.
#pragma warning disable 1591

namespace FalkenTests
{
    public class FalkenExampleActions : Falken.ActionsBase
    {
        [Falken.Range(-1f, 1f)]
        public float lookUpAngle = 0.5f;
        public bool jump = true;
        public FalkenWeaponEnum weapon = FalkenWeaponEnum.Shotgun;
        public Falken.Joystick joystick = new Falken.Joystick(
            Falken.AxesMode.DirectionXZ,
            Falken.ControlledEntity.Player,
            Falken.ControlFrame.Player);

        public Falken.Number numberAttribute = new Falken.Number(0, 1);
        public Falken.Category categoryAttribute = new Falken.Category(
            new List<string>() { "yes", "no", "yes, and" });
        public Falken.Boolean booleanAttribute = new Falken.Boolean();
    }

    public sealed class FalkenUnsupportedActionsTest : FalkenExampleActions
    {
        public Falken.PositionVector position = new Falken.PositionVector();
        public Falken.RotationQuaternion rotation = new Falken.RotationQuaternion();
    }


    public class ActionsTest
    {

        private FalkenInternal.falken.ActionsBase _actionsBase;

        [SetUp]
        public void Setup()
        {
            _actionsBase = new FalkenInternal.falken.ActionsBase();
        }

        [Test]
        public void BindActions()
        {
            FalkenExampleActions actions = new FalkenExampleActions();
            actions.BindActions(_actionsBase);
            Assert.IsTrue(actions.ContainsKey("lookUpAngle"));
            Assert.IsTrue(actions["lookUpAngle"] is Falken.Number);
            Assert.IsTrue(actions.ContainsKey("jump"));
            Assert.IsTrue(actions["jump"] is Falken.Boolean);
            Assert.IsTrue(actions.ContainsKey("weapon"));
            Assert.IsTrue(actions["weapon"] is Falken.Category);
            Assert.IsTrue(actions.ContainsKey("joystick"));
            Assert.IsTrue(actions["joystick"] is Falken.Joystick);
            Assert.IsTrue(actions.ContainsKey("numberAttribute"));
            Assert.AreEqual(actions.numberAttribute, actions["numberAttribute"]);
            Assert.IsTrue(actions.ContainsKey("booleanAttribute"));
            Assert.AreEqual(actions.booleanAttribute, actions["booleanAttribute"]);
            Assert.IsTrue(actions.ContainsKey("categoryAttribute"));
            Assert.AreEqual(actions.categoryAttribute, actions["categoryAttribute"]);
        }

        [Test]
        public void BindAlreadyBoundActions()
        {
            FalkenExampleActions actions = new FalkenExampleActions();
            actions.BindActions(_actionsBase);
            Assert.That(() => actions.BindActions(_actionsBase),
                        Throws.TypeOf<Falken.AlreadyBoundException>()
                        .With.Message.EqualTo("Can't bind actions more than once."));
        }

        [Test]
        public void BindActionsWithUnsupportedTypes()
        {
            FalkenUnsupportedActionsTest actions = new FalkenUnsupportedActionsTest();
            Assert.That(() => actions.BindActions(_actionsBase),
                        Throws.TypeOf<Falken.UnsupportedFalkenTypeException>()
                        .With.Message.EqualTo("Field 'position' " +
                                              "has unsupported type 'Falken.PositionVector' " +
                                              "or it does not have the necessary " +
                                              "implicit conversions."));
        }

        [Test]
        public void ModifyActionsSource()
        {
            FalkenExampleActions actions = new FalkenExampleActions();
            actions.BindActions(_actionsBase);
            // Since we bind the container and we modify it,
            // the initial state will be HumanDemonstration.
            Assert.AreEqual(
              Falken.ActionsBase.Source.HumanDemonstration,
              actions.ActionsSource);
            actions.ActionsSource = Falken.ActionsBase.Source.None;
            Assert.AreEqual(
              Falken.ActionsBase.Source.None,
              actions.ActionsSource);
            actions.ActionsSource = Falken.ActionsBase.Source.Invalid;
            Assert.AreEqual(
              Falken.ActionsBase.Source.Invalid,
              actions.ActionsSource);
            actions.ActionsSource = Falken.ActionsBase.Source.BrainAction;
            Assert.AreEqual(
              Falken.ActionsBase.Source.BrainAction,
              actions.ActionsSource);
            actions.ActionsSource = Falken.ActionsBase.Source.HumanDemonstration;
            Assert.AreEqual(
              Falken.ActionsBase.Source.HumanDemonstration,
              actions.ActionsSource);
        }

        [Test]
        public void SetActionsSourceUnbound()
        {
            FalkenExampleActions actions = new FalkenExampleActions();
            Assert.That(() => actions.ActionsSource = Falken.ActionsBase.Source.None,
                        Throws.TypeOf<Falken.ActionsNotBoundException>()
                        .With.Message.EqualTo("Can't set the source to an unbound action."));
        }

        [Test]
        public void GetActionsSourceUnbound()
        {
            FalkenExampleActions actions = new FalkenExampleActions();
            Falken.ActionsBase.Source source;
            Assert.That(() => source = actions.ActionsSource,
                        Throws.TypeOf<Falken.ActionsNotBoundException>()
                        .With.Message.EqualTo("Can't get the source from an unbound action."));
        }
    }
}
