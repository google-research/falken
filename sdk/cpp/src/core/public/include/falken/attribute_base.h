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

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_ATTRIBUTE_BASE_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_ATTRIBUTE_BASE_H_

#include <memory>
#include <sstream>
#include <string>
#include <vector>

#include "falken/allocator.h"
#include "falken/config.h"
#include "falken/fixed_size_vector.h"
#include "falken/log.h"
#include "falken/primitives.h"
#include "falken/types.h"

namespace falken {

class ActionsBase;
class AttributeBase;
class AttributeContainer;
class AttributeProtoConverter;
class AttributeTensorConverter;
class AttributeTest;
class BoolAttribute;
class CategoricalAttribute;
class FeelersAttribute;
class FeelersData;
class JoystickData;
template <typename T>
class NumberAttribute;
class PositionAttribute;
class RotationAttribute;
class JoystickAttribute;

/// Sets the mode in which axes are interpreted.
enum AxesMode {
  /// Unset default value.
  kAxesModeInvalid = 0,
  /// The x-axis controls yaw, the y-axis pitch.
  kAxesModeDeltaPitchYaw = 1,
  /// The direction is interpreted as a direction in the controlled object's
  /// XZ plane. The direction is interpreted within a reference frame.
  kAxesModeDirectionXZ = 2,
};

/// The frame of reference in which directional input is interpreted, either
/// relative to the world, player or camera.
enum ControlFrame {
  /// Interpret directions relative to the world.
  kControlFrameWorld = 0,
  /// Interpret directions relative to the player.
  kControlFramePlayer = 1,
  /// Interpret directions relative to the camera.
  kControlFrameCamera = 2
};

/// The entity that is being controlled by the joystick.
enum ControlledEntity {
  /// The joystick controls the player.
  kControlledEntityPlayer = 0,
  /// The joystick controls the camera.
  kControlledEntityCamera = 1
};

/// Represents an attribute and its range.
class FALKEN_EXPORT AttributeBase {
  friend class AttributeProtoConverter;
  friend class AttributeTensorConverter;
  friend class AttributeContainer;
  friend class AttributeTest;
  friend class FeelersData;
  friend class JoystickData;

 public:
  /// Enum to indicate valid attribute types.
  enum Type {
    /// Unknown attribute.
    kTypeUnknown,
    /// Number attribute.
    kTypeFloat,
    /// Categorical attribute.
    kTypeCategorical,
    /// Boolean attribute.
    kTypeBool,
    /// Position attribute.
    kTypePosition,
    /// Rotation attribute.
    kTypeRotation,
    /// Feeler attribute.
    kTypeFeelers,
    /// Joystick attribute.
    kTypeJoystick,
  };

  /// Construct a number base attribute.
  ///
  /// @param container Container where to add the new attribute.
  /// @param name Attribute name.
  /// @param minimum Lower bound value.
  /// @param maximum Upper bound value.
  AttributeBase(AttributeContainer& container, const char* name, float minimum,
                float maximum);

  /// Construct a categorical base attribute.
  ///
  /// @param container Container where to add the new attribute.
  /// @param name Attribute name.
  /// @param category_values List of categories.
  AttributeBase(AttributeContainer& container, const char* name,
                const std::vector<std::string>& category_values);

  /// Construct an unbound attribute.
  ///
  /// @param container Container where to add the new attribute.
  /// @param name Attribute name.
  /// @param type Attribute type.
  AttributeBase(AttributeContainer& container, const char* name, Type type);

  /// Construct a feeler base attribute.
  ///
  /// The feelers sense and collect data from the world around an entity.
  ///
  /// @param container Container where to add the new attribute.
  /// @param name Attribute name.
  /// @param number_of_feelers Number of feelers that are attached to an entity.
  /// @param feeler_length Maximum distance for the feelers.
  /// @param fov_angle Field of view angle in radians.
  /// @param feeler_thickness Thickness value for spherical raycast.
  ///     This parameter should be set to 0 if ray casts have no volume.
  /// @param ids Categories for the feelers.
  AttributeBase(
      AttributeContainer& container, const char* name, int number_of_feelers,
      float feeler_length, float fov_angle, float feeler_thickness,
      const std::vector<std::string>& ids = std::vector<std::string>());

  /// Construct a feeler base attribute.
  ///
  /// The feelers sense and collect data from the world around an entity.
  ///
  /// @deprecated Use the overload without <code>record_distances</code>
  /// instead.
  ///
  /// @param container Container where to add the new attribute.
  /// @param name Attribute name.
  /// @param number_of_feelers Number of feelers that are attached to an entity.
  /// @param feeler_length Maximum distance for the feelers.
  /// @param fov_angle Field of view angle in radians.
  /// @param feeler_thickness Thickness value for spherical raycast.
  ///     This parameter should be set to 0 if ray casts have no volume.
  /// @param record_distances Ignored, always record distances in feelers.
  /// @param ids Categories for the feelers.
  FALKEN_DEPRECATED AttributeBase(
      AttributeContainer& container, const char* name, int number_of_feelers,
      float feeler_length, float fov_angle, float feeler_thickness,
      bool record_distances,
      const std::vector<std::string>& ids = std::vector<std::string>());

  /// Construct a Joystick base atttribute.
  ///
  /// @param container Container where to add the new attribute.
  /// @param name Attribute name.
  /// @param axes_mode Interpretation of the X/Y joystick axes.
  /// @param controlled_entity The entity controlled by the joystick.
  /// @param control_frame The frame of reference for directional inputs.
  AttributeBase(AttributeContainer& container, const char* name,
                AxesMode axes_mode, ControlledEntity controlled_entity,
                ControlFrame control_frame);

  /// Remove the attribute from the container and destruct.
  virtual ~AttributeBase();

#if !defined(SWIG) && !defined(FALKEN_CSHARP)
  /// Copy assignment operator is deleted.
  AttributeBase& operator=(const AttributeBase& other) = delete;
#else
  /// Copy attribute values but the container is intact since we can't have more
  /// than one attribute with the same name in a container.
  /// The destination attribute is marked as unset (modified()
  /// returns false).
  AttributeBase& operator=(const AttributeBase& other);
#endif  // !defined(SWIG) && !defined(FALKEN_CSHARP)

  /// Copy an attribute and migrate it to a new container.
  /// The destination attribute is marked as unset (modified()
  /// returns false)
  ///
  /// @param container Container where to add the new attribute.
  /// @param other Attribute to copy.
  AttributeBase(AttributeContainer& container, const AttributeBase& other);

  /// Move an attribute.
  AttributeBase(AttributeBase&& other);

  /// Copy constructor is deleted.
  AttributeBase(const AttributeBase& other) = delete;

  /// Move an attribute and migrate it to a new container.
  ///
  /// @param container Container where to add the new attribute.
  /// @param other Attribute to move.
  AttributeBase(AttributeContainer& container, AttributeBase&& other);

  /// Get the attribute name.
  ///
  /// @return Name of the attribute.
  const char* name() const;

  /// Get the attribute type.
  ///
  /// @return Type of the attribute.
  Type type() const;

  /// Set a number attribute ensuring it is within the required constraints.
  ///
  /// @param number Number attribute value.
  /// @return true if the attribute was successfully set, false otherwise.
  bool set_number(float number);

  /// Get value of a number attribute.
  ///
  /// @return Number value of the attribute.
  float number() const;

  /// Get lower bound of a number attribute.
  ///
  /// @return Lower bound of the attribute.
  float number_minimum() const;

  /// Get upper bound of a number attribute.
  ///
  /// @return Upper bound of the attribute.
  float number_maximum() const;

  /// Set a categorical value attribute ensuring it is within the required
  /// constraints.
  ///
  /// @param category Categorical attribute value.
  /// @return true if the attribute was successfully set, false otherwise.
  bool set_category(int category);

  /// Get value of a categorical attribute.
  ///
  /// @return Categorical value of the attribute.
  int category() const;

  /// Get the available values for a categorical value attribute.
  ///
  /// @return Available categorical values.
  const Vector<String>& category_values() const;

  /// Set a boolean attribute.
  ///
  /// @param value Boolean attribute value.
  /// @return true if the attribute was successfully set, false otherwise.
  bool set_boolean(bool value);

  /// Get value of a boolean attribute.
  ///
  /// @return Boolean value of the attribute.
  bool boolean() const;

  /// Set a position attribute.
  ///
  /// @param position Position attribute value.
  /// @return true if the attribute was successfully set, false otherwise.
  bool set_position(const Position& position);

  /// Get value of a position attribute.
  ///
  /// @return Position value of the attribute.
  const Position& position() const;

  /// Set a rotation attribute.
  ///
  /// @param rotation Rotation attribute value.
  /// @return true if the attribute was successfully set, false otherwise.
  bool set_rotation(const Rotation& rotation);

  /// Get value of a rotation attribute.
  ///
  /// @return Rotation value of the attribute.
  const Rotation& rotation() const;

  /// Get number attributes of a feelers attribute.
  ///
  /// @return Number attributes of the attribute.
  FixedSizeVector<NumberAttribute<float>>& feelers_distances();

  /// Get number attributes of a feelers attribute.
  ///
  /// @return Number attributes of the attribute.
  const FixedSizeVector<NumberAttribute<float>>& feelers_distances() const;

  /// Get categorical attributes of a feelers attribute.
  ///
  /// @return Categorical attributes of the attribute.
  FixedSizeVector<CategoricalAttribute>& feelers_ids();

  /// Get categorical attributes of a feelers attribute.
  ///
  /// @return Categorical attributes of the attribute.
  const FixedSizeVector<CategoricalAttribute>& feelers_ids() const;

  /// Get length of a feelers attribute.
  ///
  /// @return Length value of the attribute.
  float feelers_length() const;

  /// Get radius of a feelers attribute.
  ///
  /// @deprecated Use feelers_thickness. This method will be
  /// removed in the future.
  /// @return Radius value of the attribute.
  FALKEN_DEPRECATED float feelers_radius() const;

  /// Get thickness of a feelers attribute.
  ///
  /// @return Thickness value of the attribute.
  float feelers_thickness() const;

  /// Get field of view angle of a feelers attribute.
  ///
  /// @return Field of view angle value in radians of the attribute.
  float feelers_fov_angle() const;

  // Get the x-axis of a Joystick action.
  //
  // @return The x-axis of the joystick.
  float joystick_x_axis() const;

  // Get the y-axis of a Joystick action.
  //
  // @return The y-axis of thej joystick.
  float joystick_y_axis() const;

  // Set the joystick x axis.
  //
  // @return True if the argument was in the range [-1, 1], false otherwise.
  bool set_joystick_x_axis(float x_axis);
  // Set the joystick y axis.
  //
  // @return True if the argument was in the range [-1, 1], false otherwise.
  bool set_joystick_y_axis(float y_axis);

  // Get the joystick controlled entity.
  //
  // @return A string representing the controlled entity.
  ControlledEntity joystick_controlled_entity() const;

  // Get the joystick control frame.
  //
  // @return A string representing the entity that provides the control frame.
  ControlFrame joystick_control_frame() const;

  // Get the joystick axes mode.
  //
  // @return An enum value representing the axes_mode.
  AxesMode joystick_axes_mode() const;

  /// Get a mutable number attribute by casting from an AttributeBase.
  ///
  /// @return Number attribute cast from attribute base.
  template <typename T>
  NumberAttribute<T>& AsNumber() {
    AssertIsType(kTypeFloat);
    return *static_cast<NumberAttribute<T>*>(this);
  }

  /// Get a number attribute by casting from an AttributeBase.
  ///
  /// @return Number attribute from attribute base.
  template <typename T>
  const NumberAttribute<T>& AsNumber() const {
    AssertIsType(kTypeFloat);
    return *static_cast<const NumberAttribute<T>*>(this);
  }

  /// Get a mutable categorical attribute by casting from an AttributeBase.
  ///
  /// @return Categorical attribute cast from attribute base.
  CategoricalAttribute& AsCategorical();

  /// Get a categorical attribute by casting from an AttributeBase.
  ///
  /// @return Categorical attribute from attribute base.
  const CategoricalAttribute& AsCategorical() const;

  /// Get a mutable boolean attribute by casting from an AttributeBase.
  ///
  /// @return Boolean attribute cast from attribute base.
  BoolAttribute& AsBool();

  /// Get a boolean attribute by casting from an AttributeBase.
  ///
  /// @return Boolean attribute from attribute base.
  const BoolAttribute& AsBool() const;

  /// Get a mutable position attribute by casting from an AttributeBase.
  ///
  /// @return Position attribute cast from attribute base.
  PositionAttribute& AsPosition();

  /// Get a position attribute by casting from an AttributeBase.
  ///
  /// @return Position attribute from attribute base.
  const PositionAttribute& AsPosition() const;

  /// Get a mutable rotation attribute by casting from an AttributeBase.
  ///
  /// @return Rotation attribute cast from attribute base.
  RotationAttribute& AsRotation();

  /// Get a rotation attribute by casting from an AttributeBase.
  ///
  /// @return Rotation attribute from attribute base.
  const RotationAttribute& AsRotation() const;

  /// Get a mutable feelers attribute by casting from an AttributeBase.
  ///
  /// @return Feelers attribute cast from attribute base.
  FeelersAttribute& AsFeelers();

  /// Get a feelers attribute by casting from an AttributeBase.
  ///
  /// @return Feelers attribute from attribute base.
  const FeelersAttribute& AsFeelers() const;

  /// Get a mutable joystick attribute by casting from an AttributeBase.
  ///
  /// @return Joystick attribute cast from attribute base.
  JoystickAttribute& AsJoystick();

  /// Get a mutable joystick attribute by casting from an AttributeBase.
  ///
  /// @return Joystick attribute cast from attribute base.
  const JoystickAttribute& AsJoystick() const;

  // Clamp a set value if it's out of range.
  void set_enable_clamping(bool enable);

  // Determine whether value should be clamped if out of range.
  bool enable_clamping() const;

  FALKEN_DEFINE_NEW_DELETE

 private:
  // Mark the attribute value as not updated since the start of the iteration
  void reset_modified();

  // Mark the attribute value as not updated since the start of the iteration
  bool modified() const;

  // Checks if the attribute has not been updated, and when that's true it adds
  // information about the missing attribute data to the vector it receives as
  // argument.
  bool IsNotModified(
      std::vector<std::string>& unmodified_attribute_names) const;

  void ClearContainer();

  // Notify the container that the attribute has been modified.
  bool SetModifiedAndNotifyContainer(bool value_set);

  // Set the notify container for a set of attributes.
  static void SetNotifyContainerOfAttributes(
      AttributeContainer& container, AttributeContainer* notify_container);

  FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_START
  // Private data.
  struct AttributeBaseData;
  std::unique_ptr<AttributeBaseData> attribute_data_;
  FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_END

  template <typename T>
  struct NumberValueAndRange {
    T value;
    T min_value;
    T max_value;

    bool set_value(const char* attribute_name, T value_to_set, bool clamp) {
      if (!IsInRange(value_to_set)) {
        if (clamp) {
          T clamped_value =
              std::max(min_value, std::min(max_value, value_to_set));
          // Log warning about the value being out of range.
          value_to_set = clamped_value;
        } else {
          std::stringstream ss;
          ss << "Unable to set value of attribute '" << attribute_name
             << "' to " << value_to_set
             << " as it is out of the specified "
                "range "
             << min_value << " to " << max_value << ".";
          std::shared_ptr<SystemLogger> logger = SystemLogger::Get();
          logger->Log(kLogLevelFatal, ss.str().c_str());
          return false;
        }
      }
      value = value_to_set;
      return true;
    }

    bool IsInRange(T value_to_check) {
      return value_to_check >= min_value && value_to_check <= max_value;
    }
  };

  // The following Union should use raw pointers (new / delete) to avoid complex
  // non POD members that have complex destructors.
  union Value {
    NumberValueAndRange<float> float_value;
    NumberValueAndRange<int> int_value;
    Position* position;
    Rotation* rotation;
    FeelersData* feelers;
    JoystickData* joystick;
  } value_;


  // Returns true if attribute is of type d_type, otherwise false.
  bool CheckType(Type d_type) const;

  // Asserts if attribute is of type d_type.
  void AssertIsType(Type d_type) const;

  // Set the required constraints of a number attribute.
  bool set_number_minimum(float minimum);
  bool set_number_maximum(float maximum);

  // Set the available values for a categorical value attribute.
  bool set_category_values(const std::vector<std::string>& category_values);

  // Set max ray cast length.
  bool set_feelers_length(float length);

  // Set feelers field of view angle.
  bool set_feelers_fov_angle(float angle);

  // Number of feelers.
  int number_of_feelers() const;

  // Number of feelers IDs.
  int number_of_feelers_ids() const;

  // Copy an attribute value.
  void CopyValue(const AttributeBase& other);

  // Move an attribute valuye.
  void MoveValue(AttributeBase&& other);

  // Initialize an Unconstrained attribute.
  void InitializeUnconstrained();
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_ATTRIBUTE_BASE_H_
