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
using NUnit.Framework;

// Do not warn about missing documentation.
#pragma warning disable 1591

namespace FalkenTests
{

  public class FalkenJoystickContainer : Falken.AttributeContainer
  {
    public Falken.Joystick joystick =
      new Falken.Joystick("joystick",
        Falken.AxesMode.DirectionXZ,
        Falken.ControlledEntity.Player,
        Falken.ControlFrame.Player);
  }

  public class JoystickAttributeTest
  {

    private FalkenInternal.falken.AttributeContainer _falkenContainer;

    [SetUp]
    public void Setup()
    {
      _falkenContainer = new FalkenInternal.falken.AttributeContainer();
    }

    [Test]
    public void FalkenInternalAxesModeConversion()
    {
      Falken.AxesMode Mode = Falken.AxesMode.Invalid;
      Assert.AreEqual(Falken.Joystick.ToInternalAxesMode(Mode),
        FalkenInternal.falken.AxesMode.kAxesModeInvalid);
      Mode = Falken.AxesMode.DeltaPitchYaw;
      Assert.AreEqual(Falken.Joystick.ToInternalAxesMode(Mode),
        FalkenInternal.falken.AxesMode.kAxesModeDeltaPitchYaw);
      Mode = Falken.AxesMode.DirectionXZ;
      Assert.AreEqual(Falken.Joystick.ToInternalAxesMode(Mode),
        FalkenInternal.falken.AxesMode.kAxesModeDirectionXZ);
    }

    [Test]
    public void FalkenInternalControlledEntityConversion()
    {
      Falken.ControlledEntity Entity =
        Falken.ControlledEntity.Player;
      Assert.AreEqual(Falken.Joystick.ToInternalControlledEntity(Entity),
        FalkenInternal.falken.ControlledEntity.kControlledEntityPlayer);
      Entity =
        Falken.ControlledEntity.Camera;
      Assert.AreEqual(Falken.Joystick.ToInternalControlledEntity(Entity),
        FalkenInternal.falken.ControlledEntity.kControlledEntityCamera);
    }

    [Test]
    public void FalkenInternalControlFrameConversion()
    {
      Falken.ControlFrame Frame =
        Falken.ControlFrame.Player;
      Assert.AreEqual(Falken.Joystick.ToInternalControlFrame(Frame),
        FalkenInternal.falken.ControlFrame.kControlFramePlayer);
      Frame =  Falken.ControlFrame.Camera;
      Assert.AreEqual(Falken.Joystick.ToInternalControlFrame(Frame),
        FalkenInternal.falken.ControlFrame.kControlFrameCamera);
      Frame =  Falken.ControlFrame.World;
      Assert.AreEqual(Falken.Joystick.ToInternalControlFrame(Frame),
        FalkenInternal.falken.ControlFrame.kControlFrameWorld);
    }

    [Test]
    public void CreateJoystickAttributeAxesModeDirectionXZ()
    {
      Falken.Joystick joystick = new Falken.Joystick("Stick1",
        Falken.AxesMode. DirectionXZ,
        Falken.ControlledEntity.Player,
        Falken.ControlFrame.Player);
      Assert.AreEqual(Falken.AxesMode.DirectionXZ, joystick.AxesMode);
      Assert.AreEqual(Falken.ControlledEntity.Player, joystick.ControlledEntity);
      Assert.AreEqual(Falken.ControlFrame.Player, joystick.ControlFrame);
    }

    [Test]
    public void CreateJoystickAttributeAxesModeDeltaPitchYaw()
    {
      Falken.Joystick joystick = new Falken.Joystick("Stick2",
        Falken.AxesMode.DeltaPitchYaw,
        Falken.ControlledEntity.Camera,
        Falken.ControlFrame.World);
      Assert.AreEqual(Falken.AxesMode.DeltaPitchYaw, joystick.AxesMode);
      Assert.AreEqual(Falken.ControlledEntity.Camera, joystick.ControlledEntity);
      Assert.AreEqual(Falken.ControlFrame.World, joystick.ControlFrame);
    }

    [Test]
    public void BindDynamicJoystick()
    {
      Falken.AttributeContainer container = new Falken.AttributeContainer();
      Falken.Joystick joystick = new Falken.Joystick("joystick",
        Falken.AxesMode.DirectionXZ,
        Falken.ControlledEntity.Player,
        Falken.ControlFrame.Player);
      container["joystick"] = joystick;
      container.BindAttributes(_falkenContainer);
      Assert.AreEqual(1, container.Values.Count);
      Assert.IsTrue(container.ContainsKey("joystick"));
      Assert.AreEqual("joystick", joystick.Name);
      Assert.AreEqual(Falken.AxesMode.DirectionXZ, joystick.AxesMode);
      Assert.AreEqual(Falken.ControlledEntity.Player, joystick.ControlledEntity);
      Assert.AreEqual(Falken.ControlFrame.Player, joystick.ControlFrame);
    }

    [Test]
    public void BindJoystickContainer()
    {
      FalkenJoystickContainer JoystickContainer =
        new FalkenJoystickContainer();
      JoystickContainer.BindAttributes(_falkenContainer);
      Assert.IsTrue(JoystickContainer.Bound);
      Assert.IsTrue(JoystickContainer["joystick"] is Falken.Joystick);
      Falken.Joystick joystick = (Falken.Joystick)JoystickContainer["joystick"];
      joystick.X = 0.5f;
      Assert.AreEqual(0.5f, joystick.X);
      joystick.Y = 0.5f;
      Assert.AreEqual(0.5f, joystick.Y);
      using (var ignoreErrorMessages = new IgnoreErrorMessages())
      {
        Assert.That(() => joystick.Y = -1.5f, Throws.Exception.TypeOf<ApplicationException>());
      }
    }

    [Test]
    public void JoystickXAxisClampingTest()
    {
      FalkenJoystickContainer JoystickContainer =
        new FalkenJoystickContainer();
      JoystickContainer.BindAttributes(_falkenContainer);
      Falken.Joystick joystick = (Falken.Joystick)JoystickContainer["joystick"];

      var recovered_logs = new List<String>();
      System.EventHandler<Falken.Log.MessageArgs> handler = (
          object source, Falken.Log.MessageArgs args) =>
      {
          recovered_logs.Add(args.Message);
      };
      Falken.Log.OnMessage += handler;

      var expected_logs = new List<String>() {
          "Unable to set value of attribute 'x_axis' to -2 as it is out" +
              " of the specified range -1 to 1.",
         "Unable to set value of attribute 'x_axis' to 2 as it is out" +
              " of the specified range -1 to 1." };

      // default clamping value (off)
      Assert.IsFalse(joystick.EnableClamping);
      joystick.X = 0.0f;
      Assert.AreEqual(0.0, joystick.X);

      using (var ignoreErrorMessages = new IgnoreErrorMessages())
      {
        Assert.That(() => joystick.X = -2.0f,
            Throws.TypeOf<ApplicationException>());
        Assert.That(() => joystick.X = 2.0f,
            Throws.TypeOf<ApplicationException>());
      }
      Assert.That(recovered_logs, Is.EquivalentTo(expected_logs));

      // with clamping on
      recovered_logs.Clear();
      joystick.EnableClamping = true;
      Assert.IsTrue(joystick.EnableClamping);
      joystick.X = 0.0f;
      Assert.AreEqual(0.0f, joystick.X);
      joystick.X = -2.0f;
      Assert.AreEqual(-1.0f, joystick.X);
      joystick.X = 2.0f;
      Assert.AreEqual(1.0f, joystick.X);
      Assert.AreEqual(0, recovered_logs.Count);

      // with clamping off
      recovered_logs.Clear();
      joystick.EnableClamping = false;
      Assert.IsFalse(joystick.EnableClamping);
      joystick.X = 0.0f;
      Assert.AreEqual(0.0f, joystick.X);

      using (var ignoreErrorMessages = new IgnoreErrorMessages())
      {
          Assert.That(() => joystick.X = -2.0f,
              Throws.TypeOf<ApplicationException>());
          Assert.That(() => joystick.X = 2.0f,
              Throws.TypeOf<ApplicationException>());
      }
      Assert.That(recovered_logs, Is.EquivalentTo(expected_logs));
    }

    [Test]
    public void JoystickYAxisClampingTest()
    {
      FalkenJoystickContainer JoystickContainer =
        new FalkenJoystickContainer();
      JoystickContainer.BindAttributes(_falkenContainer);
      Falken.Joystick joystick = (Falken.Joystick)JoystickContainer["joystick"];

      var recovered_logs = new List<String>();
      System.EventHandler<Falken.Log.MessageArgs> handler = (
          object source, Falken.Log.MessageArgs args) =>
      {
          recovered_logs.Add(args.Message);
      };
      Falken.Log.OnMessage += handler;

      var expected_logs = new List<String>() {
          "Unable to set value of attribute 'y_axis' to -2 as it is out" +
              " of the specified range -1 to 1.",
         "Unable to set value of attribute 'y_axis' to 2 as it is out" +
              " of the specified range -1 to 1." };

      // default clamping value (off)
      Assert.IsFalse(joystick.EnableClamping);
      joystick.Y = 0.0f;
      Assert.AreEqual(0.0, joystick.Y);

      using (var ignoreErrorMessages = new IgnoreErrorMessages())
      {
        Assert.That(() => joystick.Y = -2.0f,
            Throws.TypeOf<ApplicationException>());
        Assert.That(() => joystick.Y = 2.0f,
            Throws.TypeOf<ApplicationException>());
      }
      Assert.That(recovered_logs, Is.EquivalentTo(expected_logs));

      // with clamping on
      recovered_logs.Clear();
      joystick.EnableClamping = true;
      Assert.IsTrue(joystick.EnableClamping);
      joystick.Y = 0.0f;
      Assert.AreEqual(0.0f, joystick.Y);
      joystick.Y = -2.0f;
      Assert.AreEqual(-1.0f, joystick.Y);
      joystick.Y = 2.0f;
      Assert.AreEqual(1.0f, joystick.Y);
      Assert.AreEqual(0, recovered_logs.Count);

      // with clamping off
      recovered_logs.Clear();
      joystick.EnableClamping = false;
      Assert.IsFalse(joystick.EnableClamping);
      joystick.Y = 0.0f;
      Assert.AreEqual(0.0f, joystick.Y);

      using (var ignoreErrorMessages = new IgnoreErrorMessages())
      {
          Assert.That(() => joystick.Y = -2.0f,
              Throws.TypeOf<ApplicationException>());
          Assert.That(() => joystick.Y = 2.0f,
              Throws.TypeOf<ApplicationException>());
      }
      Assert.That(recovered_logs, Is.EquivalentTo(expected_logs));
    }


    [Test]
    public void GetandSetUnboundJoystickAttribute()
    {
      Falken.Joystick joystick = new Falken.Joystick("Stick2", Falken.AxesMode.DeltaPitchYaw,
                                                     Falken.ControlledEntity.Camera,
                                                     Falken.ControlFrame.World);

      using (var ignoreErrorMessages = new IgnoreErrorMessages())
      {
        Assert.That(() => joystick.Y = -0.5f,
          Throws.Exception.TypeOf<Falken.AttributeNotBoundException>());
        float x = 0;
        Assert.That(() => x = joystick.X,
         Throws.Exception.TypeOf<Falken.AttributeNotBoundException>());
      }
    }
  }
}
