//  Copyright 2021 Google LLC
//
//  Licensed under the Apache License, Version 2.0 (the "License");
//  you may not use this file except in compliance with the License.
//  You may obtain a copy of the License at
//
//       http://www.apache.org/licenses/LICENSE-2.0
//
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_JOYSTICK_ATTRIBUTE_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_JOYSTICK_ATTRIBUTE_H_

#include <utility>

#include "falken/attribute_base.h"

namespace falken {

/// Register a joystick attribute where axes control pitch and yaw.
///
/// In a joystick of this type, axis values are interpreted to be the desired
/// change in pitch and yaw (y-axis pitch, x-axis yaw). The object that is
/// rotated is provided as controlled_entity argument.
///
/// Example use:
///
/// struct MyActions : ActionsBase {
///   Actions() :
///     FALKEN_JOYSTICK_DELTA_PITCH_YAW(
///         joystick, falken::kControlledEntityPlayer) {}
///   JoystickAttribute joystick;
/// };
#define FALKEN_JOYSTICK_DELTA_PITCH_YAW(member_name, controlled_entity) \
  member_name(*this, #member_name, falken::kAxesModeDeltaPitchYaw,      \
              controlled_entity, falken::kControlFrameWorld)

/// Register a joystick attribute where axes indicate a desired direction.
///
/// In a joystick of this type, axis values are interpreted to be the desired
/// direction in some reference frame, e.g., a positive y-axis may indicate
/// that the player should move away from the camera. Falken interprets the
/// desired direction as being projected onto the XZ plane of the controlled
/// object.
///
/// Example 1: Camera-relative avatar movement.
///
/// struct MyActions : ActionsBase {
///   Actions() :
///     FALKEN_JOYSTICK_DIRECTION_XZ(
///         joystick,
///         falken::kControlledEntityPlayer,
///         falken::kControlFrameCamera) {}
///   JoystickAttribute joystick;
/// };
///
/// Example 2: FPS-style WASD movement.
///
/// struct MyActions : ActionsBase {
///   Actions() :
///     FALKEN_JOYSTICK_DIRECTION_XZ(
///         joystick,
///         falken::kControlledEntityPlayer,
///         falken::kControlFramePlayer) {}
///   JoystickAttribute joystick;
/// };
///
/// Example 3: Directional stick aiming in a 2D game, where up is the z-axis.
///
/// struct MyActions : ActionsBase {
///   Actions() :
///     FALKEN_JOYSTICK_DIRECTION_XZ(
///         joystick,
///         falken::kControlledEntityPlayer,
///         falken::kControlFrameWorld) {}
///   JoystickAttribute joystick;
/// };
#define FALKEN_JOYSTICK_DIRECTION_XZ(member_name, controlled_entity, \
                                     control_frame)                  \
  member_name(*this, #member_name, falken::kAxesModeDirectionXZ,     \
              controlled_entity, control_frame)

/// An attribute representing a joystick with an x axis and a y axis.
class FALKEN_EXPORT JoystickAttribute : public AttributeBase {
 public:
  /// Create a joystick attribute.
  ///
  /// @param name Joystick attribute name.
  /// @param axes_mode How the joystick axes are interpreted.
  /// @param controlled_entity Name of the entity being controlled.
  /// @param control_frame Name of the entity specifying the reference frame.
  JoystickAttribute(AttributeContainer& container, const char* name,
                    AxesMode axes_mode, ControlledEntity controlled_entity,
                    ControlFrame control_frame);

  /// Copy a joystick attribute and migrate it to a new container.
  ///
  /// @param container Container where to add the new feelers attribute.
  /// @param other Attribute to copy.
  JoystickAttribute(AttributeContainer& container,
                    const JoystickAttribute& other);

  /// Move a joystick attribute and migrate it to a new container.
  ///
  /// @param container Container where to add the new joystick attribute.
  /// @param other Attribute to move.
  JoystickAttribute(AttributeContainer& container, JoystickAttribute&& other);

  /// Move a josyick attribute attribute.
  ///
  /// @param other Attribute to move
  JoystickAttribute(JoystickAttribute&& other);

  /// Set the x-axis of the joystick.
  ///
  /// @param x_axis The value between -1 and 1 to set.
  bool set_x_axis(float x_axis);

  /// Set the y-axis of the joystick.
  ///
  /// @param y_axis The value between -1 and 1 to set.
  bool set_y_axis(float y_axis);

  /// Get the current x-axis value of the joystick.
  ///
  /// @return Current x-axis value between -1 and 1.
  float x_axis() const;
  /// Get the current y-axis value of the joystick.
  ///
  /// @return Current y-axis value between -1 and 1.
  float y_axis() const;

  /// Get the axes_mode.
  ///
  /// @return The AxesMode the joystick is set to.
  AxesMode axes_mode() const;

  /// Get the name of the controlled_entity.
  ///
  /// @return The name of the controlled entity.
  ControlledEntity controlled_entity() const;

  // Get the control_frame (or empty string if no frame).
  ///
  /// @return The name of the control_frame entity (if set).
  ControlFrame control_frame() const;
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_JOYSTICK_ATTRIBUTE_H_
