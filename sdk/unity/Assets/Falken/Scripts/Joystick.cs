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
    /// Enum that sets the mode in which axes are interpreted.
    /// </summary>
    public enum AxesMode
    {
        /// Unset default value.
        Invalid = 0,
        /// The x-axis controls yaw, the y-axis pitch.
        DeltaPitchYaw = 1,
        /// The direction is interpreted as a direction in the controlled object's
        /// XZ plane. The direction is interpreted within a reference frame.
        DirectionXZ = 2
    }

    /// <summary>
    /// Enum that describes the frame of reference in which directional input
    /// is interpreted, either relative to the world, player or camera.
    /// </summary>
    public enum ControlFrame
    {
        /// Interpret directions relative to the world.
        World = 0,
        /// Interpret directions relative to the player.
        Player = 1,
        /// Interpret directions relative to the camera.
        Camera = 2
    }

    /// <summary>
    /// Enum that describes the entity that is being controlled by the
    /// joystick.
    /// </summary>
    public enum ControlledEntity
    {
        /// The joystick controls the player.
        Player = 0,
        /// The joystick controls the camera.
        Camera = 1
    }

    /// <summary>
    /// <c>Joystick</c> Establishes a connection with a Falken's JoystickAttribute.
    /// </summary>
    public class Joystick : Falken.AttributeBase
    {
        // Interpretation of the X/Y joystick axes.
        private Falken.AxesMode _axes_mode;
        // The entity controlled by the joystick.
        private Falken.ControlledEntity _controlled_entity;
        // The frame of reference for directional inputs.
        private Falken.ControlFrame _control_frame;

        /// <summary>
        /// Get the x axis value.
        /// </summary>
        public float X
        {
            get
            {
                if (Bound)
                {
                    return _attribute.joystick_x_axis();
                }
                throw new AttributeNotBoundException(
                  "Can't retrieve the value if the attribute is not bound.");
            }
            set
            {
                if (Bound)
                {
                    _attribute.set_joystick_x_axis(value);
                    return;
                }
                throw new AttributeNotBoundException(
                  "Can't retrieve the value if the attribute is not bound.");
            }
        }

        /// <summary>
        /// Get the x axis value.
        /// </summary>
        public float Y
        {
            get
            {
                if (Bound)
                {
                    return _attribute.joystick_y_axis();
                }
                throw new AttributeNotBoundException(
                  "Can't retrieve the value if the attribute is not bound.");
            }
            set
            {
                if (Bound)
                {
                    _attribute.set_joystick_y_axis(value);
                    return;
                }
                throw new AttributeNotBoundException(
                  "Can't retrieve the value if the attribute is not bound.");
            }
        }

        /// <summary>
        /// Get Joystick's axes mode.
        /// </summary>
        public AxesMode AxesMode
        {
            get
            {
                if (Bound)
                {
                    return FromInternalAxesMode(_attribute.joystick_axes_mode());
                }
                else
                {
                    return _axes_mode;
                }
            }
        }

        /// <summary>
        /// Get Joystick's controlled entity.
        /// </summary>
        public ControlledEntity ControlledEntity
        {
            get
            {
                if (Bound)
                {
                    return FromInternalControlledEntity(_attribute.joystick_controlled_entity());
                }
                else
                {
                    return _controlled_entity;
                }
            }
        }

        /// <summary>
        /// Get Joystick's axes mode.
        /// </summary>
        public ControlFrame ControlFrame
        {
            get
            {
                if (Bound)
                {
                    return FromInternalControlFrame(_attribute.joystick_control_frame());
                }
                else
                {
                    return _control_frame;
                }
            }
        }

        /// <summary>
        /// Verify that the given object can be converted/assigned
        /// to a float.
        /// </summary>
        static internal bool CanConvertToJoystickType(object obj)
        {
            Type objType = obj.GetType();
            return objType.IsSubclassOf(typeof(Joystick)) || objType == typeof(Joystick);
        }

        /// <summary>
        /// Convert an internal Falken.AxesMode to the public Joystick AxesMode.
        /// </summary>
        internal static AxesMode FromInternalAxesMode(FalkenInternal.falken.AxesMode InternalMode)
        {
            AxesMode Mode = AxesMode.Invalid;
            switch (InternalMode)
            {
                case FalkenInternal.falken.AxesMode.kAxesModeInvalid:
                    Mode = AxesMode.Invalid;
                    break;
                case FalkenInternal.falken.AxesMode.kAxesModeDeltaPitchYaw:
                    Mode = AxesMode.DeltaPitchYaw;
                    break;
                case FalkenInternal.falken.AxesMode.kAxesModeDirectionXZ:
                    Mode = AxesMode.DirectionXZ;
                    break;
            }
            return Mode;
        }

        /// <summary>
        /// Convert an internal Falken.ControlledEntity to the public Joystick ControlledEntity.
        /// </summary>
        internal static ControlledEntity FromInternalControlledEntity(
            FalkenInternal.falken.ControlledEntity InternalEntity)
        {
            ControlledEntity Entity = ControlledEntity.Player;
            switch (InternalEntity)
            {
                case FalkenInternal.falken.ControlledEntity.kControlledEntityPlayer:
                    Entity = ControlledEntity.Player;
                    break;
                case FalkenInternal.falken.ControlledEntity.kControlledEntityCamera:
                    Entity = ControlledEntity.Camera;
                    break;
            }
            return Entity;
        }

        /// <summary>
        /// Convert an internal Falken.ControlFrame to the public Joystick ControlFrame.
        /// </summary>
        internal static ControlFrame FromInternalControlFrame(
            FalkenInternal.falken.ControlFrame InternalFrame)
        {
            ControlFrame Frame = ControlFrame.World;
            switch (InternalFrame)
            {
                case FalkenInternal.falken.ControlFrame.kControlFrameWorld:
                    Frame = ControlFrame.World;
                    break;
                case FalkenInternal.falken.ControlFrame.kControlFramePlayer:
                    Frame = ControlFrame.Player;
                    break;
                case FalkenInternal.falken.ControlFrame.kControlFrameCamera:
                    Frame = ControlFrame.Camera;
                    break;
            }
            return Frame;
        }

        /// <summary>
        /// Convert an AxesMode to an internal AxesMode.
        /// </summary>
        internal static FalkenInternal.falken.AxesMode ToInternalAxesMode(AxesMode Mode)
        {
            FalkenInternal.falken.AxesMode InternalMode =
              FalkenInternal.falken.AxesMode.kAxesModeInvalid;
            switch (Mode)
            {
                case AxesMode.Invalid:
                    InternalMode = FalkenInternal.falken.AxesMode.kAxesModeInvalid;
                    break;
                case AxesMode.DeltaPitchYaw:
                    InternalMode = FalkenInternal.falken.AxesMode.kAxesModeDeltaPitchYaw;
                    break;
                case AxesMode.DirectionXZ:
                    InternalMode = FalkenInternal.falken.AxesMode.kAxesModeDirectionXZ;
                    break;
            }
            return InternalMode;
        }

        /// <summary>
        /// Convert a string into a ControlledEntity.
        /// </summary>
        internal static ControlledEntity FromStringToControlledEntity(
          string ControlledEntityString)
        {
            ControlledEntity ControlledEntity = ControlledEntity.Player;
            switch (ControlledEntityString)
            {
                case "player":
                    ControlledEntity = ControlledEntity.Player;
                    break;
                case "camera":
                    ControlledEntity = ControlledEntity.Camera;
                    break;
            }
            return ControlledEntity;
        }

        /// <summary>
        /// Convert a ControlledEntity to an internal ControlledEntity.
        /// </summary>
        internal static FalkenInternal.falken.ControlledEntity ToInternalControlledEntity(
          ControlledEntity Controlled)
        {
            FalkenInternal.falken.ControlledEntity InternalControlledEntity =
              FalkenInternal.falken.ControlledEntity.kControlledEntityPlayer;
            switch (Controlled)
            {
                case ControlledEntity.Player:
                    InternalControlledEntity =
                      FalkenInternal.falken.ControlledEntity.kControlledEntityPlayer;
                    break;
                case ControlledEntity.Camera:
                    InternalControlledEntity =
                      FalkenInternal.falken.ControlledEntity.kControlledEntityCamera;
                    break;
            }
            return InternalControlledEntity;
        }

        /// <summary>
        /// Convert a ControlFrame to an internal ControlFrame.
        /// </summary>
        internal static FalkenInternal.falken.ControlFrame ToInternalControlFrame(
          ControlFrame Frame)
        {
            FalkenInternal.falken.ControlFrame InternalControlFrame =
              FalkenInternal.falken.ControlFrame.kControlFrameWorld;
            switch (Frame)
            {
                case ControlFrame.World:
                    InternalControlFrame =
                      FalkenInternal.falken.ControlFrame.kControlFrameWorld;
                    break;
                case ControlFrame.Camera:
                    InternalControlFrame =
                      FalkenInternal.falken.ControlFrame.kControlFrameCamera;
                    break;
                case ControlFrame.Player:
                    InternalControlFrame =
                      FalkenInternal.falken.ControlFrame.kControlFramePlayer;
                    break;
            }
            return InternalControlFrame;
        }

        /// <summary>
        /// Create an empty Falken.Joystick. DO NOT USE.
        /// This is used internally only.
        /// </summary>
        public Joystick()
        {
        }

        /// <summary>
        /// Create a dynamic Falken.Joystick.
        /// </summary>
        /// <param name="name">Name of the joystick attribute.</param>
        /// <param name="axesMode">How the joystick axes are interpreted..</param>
        /// <param name="controlledEntity">The entity being controlled.</param>
        /// <param name="controlFrame">An optional entity specifying the reference frame. Only
        /// applicable if axesMode is DirectionXZ.
        ///  </param>
        public Joystick(string name, AxesMode axesMode,
          Falken.ControlledEntity controlledEntity,
          Falken.ControlFrame controlFrame = ControlFrame.World) : base(name)
        {
            Initialize(axesMode, controlledEntity, controlFrame);
        }

        /// <summary>
        /// Create a dynamic Falken.Joystick that uses the name of the field it's bound to.
        /// </summary>
        /// <param name="axesMode">How the joystick axes are interpreted..</param>
        /// <param name="controlledEntity">The entity being controlled.</param>
        /// <param name="controlFrame">An optional entity specifying the reference frame. Only
        /// applicable if axesMode is DirectionXZ.
        ///  </param>
        public Joystick(AxesMode axesMode,
          Falken.ControlledEntity controlledEntity,
          Falken.ControlFrame controlFrame = ControlFrame.World)
        {
            Initialize(axesMode, controlledEntity, controlFrame);
        }

        /// <summary>
        /// Initialize Joystick during construction.
        /// </summary>
        private void Initialize(
          AxesMode axesMode,
          Falken.ControlledEntity controlledEntity,
          Falken.ControlFrame controlFrame = ControlFrame.World)
        {
            _axes_mode = axesMode;
            _controlled_entity = controlledEntity;
            _control_frame = controlFrame;
        }


        /// <summary>
        /// Establish a connection between a C# attribute and a Falken's attribute.
        /// </summary>
        /// <param name="fieldInfo">Metadata information of the field this is being bound to.</param>
        /// <param name="fieldContainer">Object that contains the value of the field.</param>
        /// <param name="container">Internal container to add the attribute to.</param>
        /// <exception>AlreadyBoundException thrown when trying to bind the attribute when it was
        /// bound already.</exception>
        internal override void BindAttribute(FieldInfo fieldInfo, object fieldContainer,
                                         FalkenInternal.falken.AttributeContainer container)
        {
            ThrowIfBound(fieldInfo);
            SetNameToFieldName(fieldInfo, fieldContainer);

            if (fieldInfo != null && fieldContainer != null)
            {
                if (!CanConvertToGivenType(typeof(Joystick), fieldInfo.GetValue(fieldContainer)))
                {
                    ClearBindings();
                }
            }
            else
            {
                ClearBindings();
            }
            SetFalkenInternalAttribute(
                new FalkenInternal.falken.JoystickAttribute(
                    container, _name,
                    ToInternalAxesMode(AxesMode),
                    ToInternalControlledEntity(ControlledEntity),
                    ToInternalControlFrame(ControlFrame)),
                fieldInfo, fieldContainer);
        }

        /// <summary>
        /// Call parent implementation.
        /// </summary>
        /// <param name="attributeBase">Internal attribute to associate with this instance.</param>
        /// <param name="field">Field metadata for a field on the fieldContainer object.</param>
        /// <param name="fieldValue">Object that contains the field.</param>
        internal override void SetFalkenInternalAttribute(
          FalkenInternal.falken.AttributeBase attributeBase, FieldInfo field, object fieldValue)
        {
            base.SetFalkenInternalAttribute(attributeBase, field, fieldValue);
        }


        /// <summary>
        /// Update Falken's attribute value to reflect C# field's value.
        /// </summary>
        internal override void Read()
        {
            // Axes values are read directly. No need to do anything here.
        }

        /// <summary>
        /// Update C# field's value to match Falken's attribute value.
        /// </summary>
        internal override void Write()
        {
            // Axes values are written directly. No need to do anything here.
        }
    }
}
