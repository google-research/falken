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

#include "falken/attribute.h"

#include <string.h>

#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <memory>
#include <vector>

#include "src/core/assert.h"
#include "src/core/attribute_internal.h"
#include "src/core/globals.h"
#include "src/core/log.h"
#include "falken/attribute_base.h"
#include "falken/joystick_attribute.h"
#include "absl/strings/str_join.h"

namespace falken {

namespace {

static const char kAttributeTypeName[] = "Attribute";
static const AttributeBase::Type kAllValidTypes[] = {
    falken::AttributeBase::Type::kTypeFloat,
    falken::AttributeBase::Type::kTypeCategorical,
    falken::AttributeBase::Type::kTypeBool,
    falken::AttributeBase::Type::kTypePosition,
    falken::AttributeBase::Type::kTypeRotation,
    falken::AttributeBase::Type::kTypeFeelers,
    falken::AttributeBase::Type::kTypeJoystick,
    falken::AttributeBase::Type::kTypeUnknown,  // List terminator.
};

Vector<AttributeBase*>::const_iterator FindAttributeIteratorByName(
    const Vector<AttributeBase*>& attributes, const char* name,
    bool log_error) {
  return FindItemIteratorByName(attributes, name, log_error,
                                kAttributeTypeName);
}

AttributeBase* FindAttributeByName(const Vector<AttributeBase*>& attributes,
                                   const char* name, bool log_error) {
  return FindItemByName(attributes, name, log_error, kAttributeTypeName);
}

}  // namespace

// FeelersData struct holds all the feelers parameters, including the
// distances and IDs vectors of pointers.
class FeelersData : public AttributeContainer {
 public:
  // Ray cast max distance.
  float feeler_length_;
  // Thickness for spherical casts.
  float feeler_thickness_;
  // Field of view angle.
  float fov_angle_;

  // Distances and IDs attributes.
  FixedSizeVector<NumberAttribute<float>> distances_static_;
  FixedSizeVector<CategoricalAttribute> ids_static_;

  // Construct a FeelersData.
  FeelersData(AttributeContainer* notify_container, int number_of_feelers,
              float feeler_length, float fov_angle, float feeler_thickness,
              const std::vector<std::string>& ids);
  FeelersData(AttributeContainer* notify_container, const FeelersData& other);

  // Number of feelers.
  int number_of_feelers() const;
  // Number of feelers IDs.
  int number_of_feelers_ids() const;

 private:
  // Distances and IDs attributes that are allocated on construction.
  std::vector<NumberAttribute<float>> distances_;
  std::vector<CategoricalAttribute> ids_;

  void Initialize(AttributeContainer* notify_container, int number_of_feelers,
                  float feeler_length, float fov_angle, float feeler_thickness,
                  const std::vector<std::string>& ids);
};

class JoystickData : public AttributeContainer {
 public:
  explicit JoystickData(AttributeContainer* notify_container)
      : axes_mode_(kAxesModeInvalid),
        controlled_entity_(kControlledEntityPlayer),
        control_frame_(kControlFrameWorld),
        x_axis_(*this, "x_axis", -1.0f, 1.0f),
        y_axis_(*this, "y_axis", -1.0f, 1.0f) {
    AttributeBase::SetNotifyContainerOfAttributes(*this, notify_container);
  }

  JoystickData(AttributeContainer* notify_container,
               const JoystickData& other)
      : axes_mode_(other.axes_mode_),
        controlled_entity_(other.controlled_entity_),
        control_frame_(other.control_frame_),
        x_axis_(*this, other.x_axis_),
        y_axis_(*this, other.y_axis_) {
    AttributeBase::SetNotifyContainerOfAttributes(*this, notify_container);
  }

  AttributeBase* attribute_base_;
  AxesMode axes_mode_;
  ControlledEntity controlled_entity_;
  ControlFrame control_frame_;

  NumberAttribute<float> x_axis_, y_axis_;
};

const char* AttributeBaseTypeToString(falken::AttributeBase::Type type) {
  switch (type) {
    case falken::AttributeBase::Type::kTypeUnknown:
      return "Unknown Type";
    case falken::AttributeBase::Type::kTypeFloat:
      return "Number";
    case falken::AttributeBase::Type::kTypeCategorical:
      return "Categorical";
    case falken::AttributeBase::Type::kTypeBool:
      return "Bool";
    case falken::AttributeBase::Type::kTypePosition:
      return "Position";
    case falken::AttributeBase::Type::kTypeRotation:
      return "Rotation";
    case falken::AttributeBase::Type::kTypeFeelers:
      return "Feelers";
    case falken::AttributeBase::Type::kTypeJoystick:
      return "Joystick";
    default:
      return "Invalid";
  }
}

std::string TypeMismatchLog(const char* attribute_name,
                            const char* attribute_type,
                            const char* other_type) {
  std::stringstream ss;
  ss << "Type mismatch. Attribute '" << attribute_name << "' is not a '"
     << other_type << "'. Its type is '" << attribute_type << "'.";
  return ss.str();
}

AttributeContainer::AttributeContainer()
    : attribute_container_data_(std::make_unique<AttributeContainerData>(
          kAllValidTypes, "container")) {}

AttributeContainer::AttributeContainer(const AttributeBase::Type* valid_types,
                                       const char* container_name)
    : attribute_container_data_(std::make_unique<AttributeContainerData>(
          valid_types, container_name)) {}

AttributeContainer::AttributeContainer(
    const std::set<std::string>& attributes_to_ignore,
    const AttributeContainer& other)
    : attribute_container_data_(
          std::make_unique<AttributeContainerData>(kAllValidTypes)) {
  CopyAndAllocateAttributes(attributes_to_ignore, other);
}

AttributeContainer::AttributeContainer(
    const std::set<std::string>& attributes_to_ignore,
    AttributeContainer&& other)
    : attribute_container_data_(
          std::make_unique<AttributeContainerData>(kAllValidTypes)) {
  CopyAndAllocateAttributes(attributes_to_ignore, other);
}

AttributeContainer::~AttributeContainer() {
  FALKEN_LOCK_GLOBAL_MUTEX();
  for (AttributeBase* attribute : attribute_container_data_->attributes) {
    attribute->ClearContainer();
  }
}

const Vector<AttributeBase*>& AttributeContainer::attributes() const {
  return attribute_container_data_->attributes;
}

AttributeBase* AttributeContainer::attribute(const char* name) const {
  return FindAttributeByName(attribute_container_data_->attributes, name, true);
}

void AttributeContainer::AddAttribute(AttributeBase* attribute_base) {
  if (FindAttributeByName(attribute_container_data_->attributes,
                          attribute_base->name(), false)) {
    LogError(
        "Can't add attribute %s to the %s because an attribute "
        "with the same name is already present. Please change attribute "
        "name or use another container.",
        attribute_base->name(),
        attribute_base->attribute_data_->container->attribute_container_data_
            ->container_name);
    return;
  }
  if (attribute_container_data_->valid_types != nullptr) {
    bool valid = false;
    for (const AttributeBase::Type* it = attribute_container_data_->valid_types;
         *it; it++) {
      if (*it == attribute_base->type()) {
        valid = true;
        break;
      }
    }
    if (!valid) {
      LogFatal(
          "Can't add attribute %s to %s because it doesn't "
          "support type %s.",
          attribute_base->name(), attribute_container_data_->container_name,
          AttributeBaseTypeToString(attribute_base->type()));
      return;
    }
  }
  // Insert attributes sorted by name.
  attribute_container_data_->attributes.insert(
      std::upper_bound(attribute_container_data_->attributes.begin(),
                       attribute_container_data_->attributes.end(),
                       attribute_base,
                       [](const AttributeBase* lhs, const AttributeBase* rhs) {
                         return strcmp(lhs->name(), rhs->name()) < 0;
                       }),
      attribute_base);
}

void AttributeContainer::RemoveAttribute(AttributeBase* attribute) {
  auto it = FindAttributeIteratorByName(attribute_container_data_->attributes,
                                        attribute->name(), false);
  if (it != attribute_container_data_->attributes.end()) {
    attribute_container_data_->attributes.erase(it);
  } else {
    LogError(
        "Can't remove the attribute %s from the container. Check if the "
        "name is correct or if the attribute was already removed.",
        attribute->name());
  }
}

void AttributeContainer::CopyAndAllocateAttributes(
    const std::set<std::string>& attributes_to_ignore,
    const AttributeContainer& other) {
  attribute_container_data_->allocated_attributes.reserve(
      other.attributes().size());
  for (const AttributeBase* attribute_base : other.attributes()) {
    if (attributes_to_ignore.find(std::string(attribute_base->name())) ==
        attributes_to_ignore.end()) {
      attribute_container_data_->allocated_attributes.emplace_back(
          AttributeBase(*this, *attribute_base));
    }
  }
}

std::string AttributeContainer::GetAttributeNamesString() const {
  return absl::StrJoin(
      attribute_container_data_->attributes, ", ",
      [](std::string* out, const AttributeBase* a) { out->append(a->name()); });
}

void AttributeContainer::ClearAttributes() {
  attribute_container_data_->attributes.clear();
}

void AttributeContainer::set_modified(bool modified) {
  attribute_container_data_->modified = modified;
}

bool AttributeContainer::modified() const {
  return attribute_container_data_->modified;
}

void AttributeContainer::reset_attributes_dirty_flags() {
  for (AttributeBase* attribute_base : attributes()) {
    attribute_base->reset_modified();
  }
}

bool AttributeContainer::HasUnmodifiedAttributes(
    std::vector<std::string>& unset_attribute_names) const {
  bool has_unmodified_attributes = false;
  for (const AttributeBase* attribute : attributes()) {
    bool this_attribute_is_unchanged =
        attribute->IsNotModified(unset_attribute_names);
    has_unmodified_attributes =
        has_unmodified_attributes || this_attribute_is_unchanged;
  }
  return has_unmodified_attributes;
}

bool AttributeContainer::all_attributes_are_set() const {
  for (const AttributeBase* attribute_base : attributes()) {
    if (!attribute_base->modified()) {
      return false;
    }
  }
  return true;
}

AttributeBase::AttributeBase(AttributeContainer& container, const char* name,
                             float minimum, float maximum)
    : attribute_data_(
          std::make_unique<AttributeBaseData>(container, kTypeFloat, name)) {
  value_.float_value.min_value = minimum;
  value_.float_value.max_value = maximum;
  value_.float_value.set_value(name, value_.float_value.min_value,
                               attribute_data_->clamp_values);
  container.AddAttribute(this);
}

AttributeBase::AttributeBase(AttributeContainer& container, const char* name,
                             const std::vector<std::string>& category_values)
    : attribute_data_(std::make_unique<AttributeBaseData>(
          container, kTypeCategorical, name)) {
  for (auto& category_value : category_values) {
    attribute_data_->category_values.push_back(String(category_value.c_str()));
  }
  value_.int_value.min_value = 0;
  value_.int_value.max_value = category_values.size() - 1;
  value_.int_value.set_value(name, 0, false);
  container.AddAttribute(this);
}

AttributeBase::AttributeBase(AttributeContainer& container, const char* name,
                             Type type)
    : attribute_data_(
          std::make_unique<AttributeBaseData>(container, type, name)) {
  InitializeUnconstrained();
  container.AddAttribute(this);
}

AttributeBase::AttributeBase(AttributeContainer& container, const char* name,
                             AxesMode axes_mode,
                             ControlledEntity controlled_entity,
                             ControlFrame control_frame)
    : attribute_data_(
          std::make_unique<AttributeBaseData>(container, kTypeJoystick, name)) {
  InitializeUnconstrained();
  container.AddAttribute(this);
  ABSL_ASSERT(axes_mode == kAxesModeDeltaPitchYaw ||
              axes_mode == kAxesModeDirectionXZ);
  value_.joystick->axes_mode_ = axes_mode;
  value_.joystick->control_frame_ = control_frame;
  value_.joystick->controlled_entity_ = controlled_entity;
}

AttributeBase::AttributeBase(AttributeContainer& container, const char* name,
                             int number_of_feelers, float feeler_length,
                             float fov_angle, float feeler_thickness,
                             const std::vector<std::string>& ids)
    : attribute_data_(
          std::make_unique<AttributeBaseData>(container, kTypeFeelers, name)) {
  if (number_of_feelers == 1 && std::fpclassify(fov_angle) != FP_ZERO) {
    LogWarning("'%s' has only 1 feeler. Changing FoV angle from %f to 0.0",
               name, fov_angle);
    fov_angle = 0.0f;
  }

  value_.feelers =
      new FeelersData(attribute_data_->notify_container, number_of_feelers,
                      feeler_length, fov_angle, feeler_thickness, ids);
  container.AddAttribute(this);
}

AttributeBase::AttributeBase(AttributeContainer& container, const char* name,
                             int number_of_feelers, float feeler_length,
                             float fov_angle, float feeler_thickness,
                             bool record_distances,
                             const std::vector<std::string>& ids)
    : AttributeBase(container, name, number_of_feelers, feeler_length,
                    fov_angle, feeler_thickness, ids) {
  if (!record_distances) {
    LogWarning("Distances are required to construct feelers attribute %s.",
               name);
  }
}

AttributeBase::~AttributeBase() {
  switch (attribute_data_->type) {
    case kTypeRotation:
      delete value_.rotation;
      break;
    case kTypePosition:
      delete value_.position;
      break;
    case kTypeFeelers:
      delete value_.feelers;
      break;
    case kTypeJoystick:
      delete value_.joystick;
      break;
    case kTypeBool:
    case kTypeCategorical:
    case kTypeFloat:
    case kTypeUnknown:
      // Do nothing.
      break;
  }
  // Lock mutex here in case that this attribute is a feelers type.
  // If so, feelers have a vector of number and category attributes, which
  // will call the destructor of attribute base. If the lock was the first
  // thing to do, it will end up in a deadlock. Remember that this happens
  // only for GC languages, like C#.
  FALKEN_LOCK_GLOBAL_MUTEX();
  if (attribute_data_->container) {
    attribute_data_->container->RemoveAttribute(this);
  }
}

#if defined(SWIG) || defined(FALKEN_CSHARP)
/// Copy attribute values but the container is intact since we can't have more
/// than one attribute with the same name in a container.
/// The destination attribute is marked as unset (modified()
/// returns false).
AttributeBase& AttributeBase::operator=(const AttributeBase& other) {
  // An attribute will be an orphan if the container is destroyed
  // before the attribute or if it's moved. An attribute without a container
  // is not valid, therefore we shouldn't try to do anything with it.
  if (!attribute_data_->container) {
    return *this;
  }
  CopyValue(other);
  return *this;
}
#endif  // !defined(SWIG) && !defined(FALKEN_CSHARP)

void AttributeBase::InitializeUnconstrained() {
  switch (attribute_data_->type) {
    case kTypeUnknown:
      break;
    case kTypeFloat:
      value_.float_value.min_value = std::numeric_limits<float>::lowest();
      value_.float_value.max_value = std::numeric_limits<float>::max();
      value_.float_value.set_value(name(), 0.0f, attribute_data_->clamp_values);
      break;
    case kTypeRotation:
      value_.rotation = new Rotation();
      break;
    case kTypePosition:
      value_.position = new Position();
      break;
    case kTypeCategorical:
      if (attribute_data_->category_values.empty()) {
        LogFatal(
            "Can't construct categorical attribute '%s' without any "
            "categories. Please check if the provided type is correct or "
            "provide at least one category.",
            attribute_data_->name.c_str());
      } else {
        value_.int_value.min_value = 0;
        value_.int_value.max_value =
            attribute_data_->category_values.size() - 1;
        value_.int_value.set_value(name(), 0, false);
      }
      break;
    case kTypeBool:
      value_.int_value.min_value = 0;
      value_.int_value.max_value = 1;
      value_.int_value.set_value(name(), 0, false);
      break;
    case kTypeFeelers:
      value_.feelers = new FeelersData(attribute_data_->notify_container, 1,
                                       std::numeric_limits<float>::max(), 0.0f,
                                       1.0f, std::vector<std::string>());
      break;
    case kTypeJoystick:
      value_.joystick = new JoystickData(attribute_data_->notify_container);
      break;
  }
}

AttributeBase::AttributeBase(AttributeContainer& container,
                             const AttributeBase& other)
    : attribute_data_(std::make_unique<AttributeBaseData>(
          container, *other.attribute_data_)) {
  InitializeUnconstrained();
  CopyValue(other);
  container.AddAttribute(this);
}

AttributeBase::AttributeBase(AttributeBase&& other)
    : attribute_data_(std::make_unique<AttributeBaseData>(
          std::move(*other.attribute_data_))) {
  attribute_data_->container->RemoveAttribute(&other);
  other.attribute_data_->container = nullptr;
  other.attribute_data_->notify_container = nullptr;
  // Move parameter here so RemoveAttribute can log its name if an error
  // occurred.
  attribute_data_->name = std::move(other.attribute_data_->name);
  MoveValue(std::move(other));
  attribute_data_->container->AddAttribute(this);
}

AttributeBase::AttributeBase(AttributeContainer& container,
                             AttributeBase&& other)
    : attribute_data_(std::make_unique<AttributeBaseData>(
          container, std::move(*other.attribute_data_))) {
  other.attribute_data_->container->RemoveAttribute(&other);
  other.attribute_data_->container = nullptr;
  other.attribute_data_->notify_container = nullptr;
  // Move parameter here so RemoveAttribute can log its name if an error
  // occurred.
  attribute_data_->name = std::move(other.attribute_data_->name);
  MoveValue(std::move(other));
  attribute_data_->container->AddAttribute(this);
}

const char* AttributeBase::name() const {
  return attribute_data_->name.c_str();
}

AttributeBase::Type AttributeBase::type() const {
  return attribute_data_->type;
}

FeelersData::FeelersData(AttributeContainer* notify_container,
                         int number_of_feelers, float feeler_length,
                         float fov_angle, float feeler_thickness,
                         const std::vector<std::string>& ids)
    : distances_static_(&this->distances_), ids_static_(&this->ids_) {
  Initialize(notify_container, number_of_feelers, feeler_length, fov_angle,
             feeler_thickness, ids);
}

void FeelersData::Initialize(AttributeContainer* notify_container,
                             int number_of_feelers, float feeler_length,
                             float fov_angle, float feeler_thickness,
                             const std::vector<std::string>& ids) {
  this->feeler_length_ = feeler_length;
  this->feeler_thickness_ = feeler_thickness;
  if (number_of_feelers == 1 && std::fpclassify(fov_angle) != FP_ZERO) {
    LogWarning(
        "A Feeler attribute with 1 feeler and FoV angle different than 0.0 "
        "is not allowed. Changing FoV angle from %f to 0.0",
        fov_angle);
    fov_angle = 0.0f;
  }
  this->fov_angle_ = fov_angle;

  // Allow at least one odd and one even number of feelers per layer count.
  // See b/177243798 for context on the magic numbers.
  const std::set<int> kAllowedCounts{
    1, 2, 3, 4,  // No convo layers.
    14, 15,  // 1 convo layer.
    32, 33,  // 2 convo layers.
    68, 69,  // 3 convo layers.
    140, 141  // 4 convo layers.
  };
  if (kAllowedCounts.count(number_of_feelers) == 0) {
    std::string allowed_str = absl::StrJoin(kAllowedCounts, ", ");
    LogFatal(
        "Can't construct feeler attribute with '%d' feelers. Please use "
        "any of the allowed values: %s.",
        number_of_feelers, allowed_str.c_str());
  }

  distances_.reserve(number_of_feelers);
  for (int i = 0; i < number_of_feelers; i++) {
    distances_.emplace_back(NumberAttribute<float>(
        *this, ("distance_" + std::to_string(i)).c_str(), 0.0, feeler_length));
  }
  if (!ids.empty()) {
    this->ids_.reserve(number_of_feelers);
    for (int i = 0; i < number_of_feelers; i++) {
      this->ids_.emplace_back(CategoricalAttribute(
          *this, ("id_" + std::to_string(i)).c_str(), ids));
    }
  }
  AttributeBase::SetNotifyContainerOfAttributes(*this, notify_container);
}

FeelersData::FeelersData(AttributeContainer* notify_container,
                         const FeelersData& other)
    : distances_static_(&this->distances_), ids_static_(&this->ids_) {
  std::vector<std::string> other_ids;
  if (!other.ids_.empty()) {
    ConvertStringVector(other.ids_[0].category_values(), other_ids);
  }
  Initialize(notify_container, other.number_of_feelers(), other.feeler_length_,
             other.fov_angle_, other.feeler_thickness_, other_ids);
  for (int i = 0; i < other.distances_static_.size(); ++i) {
    distances_[i].set_value(other.distances_static_[i]);
  }
  for (int i = 0; i < other.ids_static_.size(); ++i) {
    ids_[i].set_value(other.ids_static_[i]);
  }
}

int FeelersData::number_of_feelers() const {
  FALKEN_DEV_ASSERT(ids_.empty() || distances_.empty() ||
                    ids_.size() == distances_.size());
  return std::max(ids_.size(), distances_.size());
}

int FeelersData::number_of_feelers_ids() const {
  return ids_.empty() ? 0 : ids_[0].category_values().size();
}

void AttributeBase::MoveValue(AttributeBase&& other) {
  if (attribute_data_->type != other.attribute_data_->type) {
    LogFatal(
        "Failed moving attributes: The type of the '%s' attribute is "
        "'%s', while the type of the destination attribute '%s' is '%s'.",
        other.attribute_data_->name.c_str(),
        AttributeBaseTypeToString(attribute_data_->type),
        attribute_data_->name.c_str(), AttributeBaseTypeToString(other.type()));
    return;
  }
  switch (attribute_data_->type) {
    case kTypeFloat:
      value_ = other.value_;
      break;
    case kTypeCategorical:
      value_ = other.value_;
      break;
    case kTypeBool:
      value_ = other.value_;
      break;
    case kTypePosition:
      value_.position = other.value_.position;
      other.value_.position = nullptr;
      break;
    case kTypeRotation:
      value_.rotation = other.value_.rotation;
      other.value_.rotation = nullptr;
      break;
    case kTypeFeelers:
      value_.feelers = other.value_.feelers;
      other.value_.feelers = nullptr;
      break;
    case kTypeJoystick:
      value_.joystick = other.value_.joystick;
      other.value_.joystick = nullptr;
      break;
    case kTypeUnknown:
      break;
  }
}

// Notify the container that the attribute has been modified.
bool AttributeBase::SetModifiedAndNotifyContainer(bool value_set) {
  if (value_set && attribute_data_->notify_container) {
    attribute_data_->notify_container->set_modified(true);
  }
  attribute_data_->dirty = attribute_data_->dirty || value_set;
  return value_set;
}

void AttributeBase::SetNotifyContainerOfAttributes(
    AttributeContainer& container, AttributeContainer* notify_container) {
  for (auto* attribute_base : container.attributes()) {
    attribute_base->attribute_data_->notify_container = notify_container;
  }
}

void AttributeBase::CopyValue(const AttributeBase& other) {
  if (attribute_data_->type != other.attribute_data_->type) {
    LogFatal(
        "Failed copying attributes: The type of the '%s' attribute is "
        "'%s', while the type of the destination attribute '%s' is '%s'.",
        other.attribute_data_->name.c_str(),
        AttributeBaseTypeToString(attribute_data_->type),
        attribute_data_->name.c_str(), AttributeBaseTypeToString(other.type()));
    return;
  }
  switch (attribute_data_->type) {
    case kTypePosition:
      *value_.position = *other.value_.position;
      break;
    case kTypeRotation:
      *value_.rotation = *other.value_.rotation;
      break;
    case kTypeFeelers:
      delete value_.feelers;
      value_.feelers = new FeelersData(attribute_data_->notify_container,
                                       *other.value_.feelers);
      break;
    case kTypeFloat:
      value_.float_value = other.value_.float_value;
      break;
    case kTypeCategorical:
      value_.int_value = other.value_.int_value;
      attribute_data_->category_values = other.attribute_data_->category_values;
      break;
    case kTypeBool:
      value_.int_value = other.value_.int_value;
      break;
    case kTypeJoystick:
      delete value_.joystick;
      value_.joystick = new JoystickData(attribute_data_->notify_container,
                                         *other.value_.joystick);
      break;
    case kTypeUnknown:
      break;
  }
  SetModifiedAndNotifyContainer(false);
}

bool AttributeBase::set_number(float number) {
  const auto modified = type() == kTypeFloat &&
                        value_.float_value.set_value(
                            name(), number, attribute_data_->clamp_values);
  return SetModifiedAndNotifyContainer(modified);
}

float AttributeBase::number() const {
  if (!CheckType(kTypeFloat)) {
    return 0.0f;
  }
  return value_.float_value.value;
}

float AttributeBase::number_minimum() const {
  if (!CheckType(kTypeFloat)) {
    return 0.0f;
  }
  return value_.float_value.min_value;
}

float AttributeBase::number_maximum() const {
  if (!CheckType(kTypeFloat)) {
    return 0.0f;
  }
  return value_.float_value.max_value;
}

bool AttributeBase::set_category(int category) {
  const auto modified = type() == kTypeCategorical &&
                        value_.int_value.set_value(name(), category, false);
  return SetModifiedAndNotifyContainer(modified);
}

int AttributeBase::category() const {
  if (!CheckType(kTypeCategorical)) {
    return 0;
  }
  return value_.int_value.value;
}

const Vector<String>& AttributeBase::category_values() const {
  return attribute_data_->category_values;
}

bool AttributeBase::set_boolean(bool value) {
  const auto modified =
      type() == kTypeBool &&
      value_.int_value.set_value(name(), value ? 1 : 0, false);
  return SetModifiedAndNotifyContainer(modified);
}

bool AttributeBase::boolean() const {
  if (!CheckType(kTypeBool)) {
    return false;
  }
  return value_.int_value.value != 0;
}

const Position& AttributeBase::position() const {
  FALKEN_ASSERT(CheckType(kTypePosition));
  return *value_.position;
}

bool AttributeBase::set_position(const Position& position) {
  if (!CheckType(kTypePosition)) {
    return false;
  }
  *value_.position = position;
  SetModifiedAndNotifyContainer(true);
  return true;
}

const Rotation& AttributeBase::rotation() const {
  FALKEN_ASSERT(CheckType(kTypeRotation));
  return *value_.rotation;
}

bool AttributeBase::set_rotation(const Rotation& rotation) {
  if (!CheckType(kTypeRotation)) {
    return false;
  }
  *value_.rotation = rotation;
  SetModifiedAndNotifyContainer(true);
  return true;
}

bool AttributeBase::CheckType(Type d_type) const {
  if (type() != d_type) {
    LogWarning("%s", TypeMismatchLog(attribute_data_->name.c_str(),
                                     AttributeBaseTypeToString(type()),
                                     AttributeBaseTypeToString(d_type))
                         .c_str());
    return false;
  }
  return true;
}

void AttributeBase::AssertIsType(Type d_type) const {
  if (!CheckType(d_type)) {
    LogFatal("Cannot cast base attribute to concrete attribute: %s",
             TypeMismatchLog(attribute_data_->name.c_str(),
                             AttributeBaseTypeToString(type()),
                             AttributeBaseTypeToString(d_type))
                 .c_str());
  }
}

bool AttributeBase::set_number_minimum(float minimum) {
  if (!CheckType(kTypeFloat)) {
    return false;
  }
  value_.float_value.min_value = minimum;
  return true;
}

bool AttributeBase::set_number_maximum(float maximum) {
  if (!CheckType(kTypeFloat)) {
    return false;
  }
  value_.float_value.max_value = maximum;
  return true;
}

bool AttributeBase::set_category_values(
    const std::vector<std::string>& category_values) {
  if (!CheckType(kTypeCategorical)) {
    return false;
  }
  ConvertStringVector(category_values, attribute_data_->category_values);
  value_.int_value.min_value = 0;
  value_.int_value.max_value = category_values.size() - 1;
  return true;
}

FixedSizeVector<NumberAttribute<float>>& AttributeBase::feelers_distances() {
  FALKEN_ASSERT(CheckType(kTypeFeelers));
  return value_.feelers->distances_static_;
}

const FixedSizeVector<NumberAttribute<float>>&
AttributeBase::feelers_distances() const {
  FALKEN_ASSERT(CheckType(kTypeFeelers));
  return value_.feelers->distances_static_;
}

FixedSizeVector<CategoricalAttribute>& AttributeBase::feelers_ids() {
  FALKEN_ASSERT(CheckType(kTypeFeelers));
  return value_.feelers->ids_static_;
}

const FixedSizeVector<CategoricalAttribute>& AttributeBase::feelers_ids()
    const {
  FALKEN_ASSERT(CheckType(kTypeFeelers));
  return value_.feelers->ids_static_;
}

float AttributeBase::feelers_length() const {
  FALKEN_ASSERT(CheckType(kTypeFeelers));
  return value_.feelers->feeler_length_;
}

float AttributeBase::feelers_radius() const { return feelers_thickness(); }

float AttributeBase::feelers_thickness() const {
  FALKEN_ASSERT(CheckType(kTypeFeelers));
  return value_.feelers->feeler_thickness_;
}

float AttributeBase::feelers_fov_angle() const {
  FALKEN_ASSERT(CheckType(kTypeFeelers));
  return value_.feelers->fov_angle_;
}

float AttributeBase::joystick_x_axis() const {
  FALKEN_ASSERT(CheckType(kTypeJoystick));
  return value_.joystick->x_axis_.number();
}

float AttributeBase::joystick_y_axis() const {
  FALKEN_ASSERT(CheckType(kTypeJoystick));
  return value_.joystick->y_axis_.number();
}

bool AttributeBase::set_joystick_x_axis(float x_axis) {
  FALKEN_ASSERT(CheckType(kTypeJoystick));
  return value_.joystick->x_axis_.set_value(x_axis);
}

bool AttributeBase::set_joystick_y_axis(float y_axis) {
  FALKEN_ASSERT(CheckType(kTypeJoystick));
  return value_.joystick->y_axis_.set_value(y_axis);
}

ControlFrame AttributeBase::joystick_control_frame() const {
  FALKEN_ASSERT(CheckType(kTypeJoystick));
  return value_.joystick->control_frame_;
}

ControlledEntity AttributeBase::joystick_controlled_entity() const {
  FALKEN_ASSERT(CheckType(kTypeJoystick));
  return value_.joystick->controlled_entity_;
}

AxesMode AttributeBase::joystick_axes_mode() const {
  FALKEN_ASSERT(CheckType(kTypeJoystick));
  return value_.joystick->axes_mode_;
}

bool AttributeBase::set_feelers_fov_angle(float angle) {
  if (!CheckType(kTypeFeelers)) {
    return false;
  }
  value_.feelers->fov_angle_ = angle;
  return true;
}

bool AttributeBase::set_feelers_length(float length) {
  if (!CheckType(kTypeFeelers)) {
    return false;
  }
  value_.feelers->feeler_length_ = length;
  return true;
}

int AttributeBase::number_of_feelers() const {
  if (!CheckType(kTypeFeelers)) {
    return 0;
  }
  return value_.feelers->number_of_feelers();
}

int AttributeBase::number_of_feelers_ids() const {
  if (!CheckType(kTypeFeelers)) {
    return 0;
  }
  return value_.feelers->number_of_feelers_ids();
}

void AttributeBase::reset_modified() {
  attribute_data_->dirty = false;
  switch (attribute_data_->type) {
    case kTypePosition:
      break;
    case kTypeRotation:
      break;
    case kTypeFloat:
      break;
    case kTypeCategorical:
      break;
    case kTypeBool:
      break;
    case kTypeFeelers:
      // FeelersData is a container of attributes, so we delegate on it
      // resetting the attributes within
      value_.feelers->reset_attributes_dirty_flags();
      break;
    case kTypeJoystick:
      // JoystickData is a container of attributes, so we delegate on it
      // resetting the attributes within
      value_.joystick->reset_attributes_dirty_flags();
      break;
    case kTypeUnknown:
      break;
  }
}

bool AttributeBase::modified() const {
  bool updated = false;
  switch (attribute_data_->type) {
    case kTypePosition:
      updated = attribute_data_->dirty;
      break;
    case kTypeRotation:
      updated = attribute_data_->dirty;
      break;
    case kTypeFeelers:
      // Feelers is a container of attributes, so we delegate on it checking
      // for modification of the attributes within attributes
      updated = value_.feelers->all_attributes_are_set();
      break;
    case kTypeFloat:
      updated = attribute_data_->dirty;
      break;
    case kTypeCategorical:
      updated = attribute_data_->dirty;
      break;
    case kTypeBool:
      updated = attribute_data_->dirty;
      break;
    case kTypeJoystick:
      // JoystickData is a container of attributes, so we delegate on it
      // checking for modification of the attributes within
      updated = value_.joystick->all_attributes_are_set();
      break;
    case kTypeUnknown:
      break;
  }
  return updated;
}

bool AttributeBase::IsNotModified(
    std::vector<std::string>& unmodified_attribute_names) const {
  if (modified()) {
    return false;
  }
  AttributeContainer* components = nullptr;
  switch (type()) {
    case kTypePosition:
    case kTypeRotation:
    case kTypeFloat:
    case kTypeCategorical:
    case kTypeBool:
    case kTypeUnknown:
      break;
    case kTypeFeelers:
      components = value_.feelers;
      break;
    case kTypeJoystick:
      components = value_.joystick;
      break;
  }
  if (components) {
    std::vector<std::string> unmodified_component_names;
    if (components->HasUnmodifiedAttributes(unmodified_component_names)) {
      for (auto& component_name : unmodified_component_names) {
        unmodified_attribute_names.push_back(
            absl::StrCat(name(), "/", component_name));
      }
    }
  } else {
    unmodified_attribute_names.push_back(name());
  }
  return true;
}

void AttributeBase::ClearContainer() { attribute_data_->container = nullptr; }

void AttributeBase::set_enable_clamping(bool enable) {
  attribute_data_->clamp_values = enable;
  switch (attribute_data_->type) {
    case falken::AttributeBase::Type::kTypeFloat:
      break;
    case falken::AttributeBase::Type::kTypeFeelers:
      for (auto& distance : value_.feelers->distances_static_) {
        distance.set_enable_clamping(enable);
      }
      break;
    case falken::AttributeBase::Type::kTypeJoystick:
      value_.joystick->x_axis_.set_enable_clamping(enable);
      value_.joystick->y_axis_.set_enable_clamping(enable);
      break;
    default:
      LogError(
          "Attempted to set the clamping configuration of attribute %s, which "
          "is of type %s and therefore it does not support clamping",
          attribute_data_->name.c_str(),
          AttributeBaseTypeToString(attribute_data_->type));
      break;
  }
}

bool AttributeBase::enable_clamping() const {
  switch (attribute_data_->type) {
    case falken::AttributeBase::Type::kTypeFloat:
      break;
    case falken::AttributeBase::Type::kTypeJoystick:
      break;
    case falken::AttributeBase::Type::kTypeFeelers: {
      auto distances_clamping_matches_attribute_clamping = true;
      for (const auto& distance : feelers_distances()) {
        distances_clamping_matches_attribute_clamping =
            distances_clamping_matches_attribute_clamping &&
            (distance.enable_clamping() == attribute_data_->clamp_values);
      }
      if (!distances_clamping_matches_attribute_clamping) {
        LogWarning(
            "The individual distances within attribute %s of type %s have been "
            "configured with clamping configurations that differ from that of "
            "the parent attribute, please read the individual clamping "
            "configurations for each distance",
            attribute_data_->name.c_str(),
            AttributeBaseTypeToString(attribute_data_->type));
      }
    } break;
    default:
      LogError(
          "Attempted to read the clamping configuration of attribute %s, which "
          "is of type %s and therefore it does not support clamping",
          attribute_data_->name.c_str(),
          AttributeBaseTypeToString(attribute_data_->type));
      break;
  }

  return attribute_data_->clamp_values;
}

CategoricalAttribute& AttributeBase::AsCategorical() {
  AssertIsType(kTypeCategorical);
  return *static_cast<CategoricalAttribute*>(this);
}

const CategoricalAttribute& AttributeBase::AsCategorical() const {
  AssertIsType(kTypeCategorical);
  return *static_cast<const CategoricalAttribute*>(this);
}

BoolAttribute& AttributeBase::AsBool() {
  AssertIsType(kTypeBool);
  return *static_cast<BoolAttribute*>(this);
}

const BoolAttribute& AttributeBase::AsBool() const {
  AssertIsType(kTypeBool);
  return *static_cast<const BoolAttribute*>(this);
}

PositionAttribute& AttributeBase::AsPosition() {
  AssertIsType(kTypePosition);
  return *static_cast<PositionAttribute*>(this);
}

const PositionAttribute& AttributeBase::AsPosition() const {
  AssertIsType(kTypePosition);
  return *static_cast<const PositionAttribute*>(this);
}

RotationAttribute& AttributeBase::AsRotation() {
  AssertIsType(kTypeRotation);
  return *static_cast<RotationAttribute*>(this);
}

const RotationAttribute& AttributeBase::AsRotation() const {
  AssertIsType(kTypeRotation);
  return *static_cast<const RotationAttribute*>(this);
}

FeelersAttribute& AttributeBase::AsFeelers() {
  AssertIsType(kTypeFeelers);
  return *static_cast<FeelersAttribute*>(this);
}

const FeelersAttribute& AttributeBase::AsFeelers() const {
  AssertIsType(kTypeFeelers);
  return *static_cast<const FeelersAttribute*>(this);
}

BoolAttribute::BoolAttribute(AttributeContainer& container, const char* name)
    : AttributeBase(container, name, kTypeBool) {}

BoolAttribute::BoolAttribute(AttributeContainer& container,
                             const BoolAttribute& attribute)
    : AttributeBase(container, attribute) {}

BoolAttribute::BoolAttribute(AttributeContainer& container,
                             BoolAttribute&& attribute)
    : AttributeBase(container, std::move(attribute)) {}

BoolAttribute::BoolAttribute(BoolAttribute&& attribute)
    : AttributeBase(std::move(attribute)) {}

bool BoolAttribute::set_value(bool value) { return set_boolean(value); }

BoolAttribute& BoolAttribute::operator=(bool value) {
  set_value(value);
  return *this;
}

bool BoolAttribute::value() const { return boolean(); }

BoolAttribute::operator bool() const { return value(); }  // NOLINT

CategoricalAttribute::CategoricalAttribute(
    AttributeContainer& container, const char* name,
    const std::vector<std::string>& category_values)
    : AttributeBase(container, name, category_values) {}

CategoricalAttribute::CategoricalAttribute(
    AttributeContainer& container, const CategoricalAttribute& attribute)
    : AttributeBase(container, attribute) {}

CategoricalAttribute::CategoricalAttribute(AttributeContainer& container,
                                           CategoricalAttribute&& attribute)
    : AttributeBase(container, std::move(attribute)) {}

CategoricalAttribute::CategoricalAttribute(CategoricalAttribute&& attribute)
    : AttributeBase(std::move(attribute)) {}

const Vector<String>& CategoricalAttribute::categories() const {
  return category_values();
}

bool CategoricalAttribute::set_value(int value) { return set_category(value); }

CategoricalAttribute& CategoricalAttribute::operator=(int value) {
  set_value(value);
  return *this;
}

int CategoricalAttribute::value() const { return category(); }

CategoricalAttribute::operator int() const { return value(); }  // NOLINT

FeelersAttribute::FeelersAttribute(AttributeContainer& container,
                                   const char* name, int number_of_feelers,
                                   float feeler_length, float fov_coverage,
                                   float feeler_thickness,
                                   const std::vector<std::string>& ids)
    : AttributeBase(container, name, number_of_feelers, feeler_length,
                    fov_coverage, feeler_thickness, ids) {}

FeelersAttribute::FeelersAttribute(AttributeContainer& container,
                                   const char* name, int number_of_feelers,
                                   float feeler_length, float fov_coverage,
                                   float feeler_thickness,
                                   bool record_distances,
                                   const std::vector<std::string>& ids)
    : AttributeBase(container, name, number_of_feelers, feeler_length,
                    fov_coverage, feeler_thickness, ids) {
  if (!record_distances) {
    LogFatal(
        "Creating Feeler attributes with record_distances set to false is "
        "not allowed anymore.");
    return;
  }
}

FeelersAttribute::FeelersAttribute(AttributeContainer& container,
                                   const FeelersAttribute& other)
    : AttributeBase(container, other) {}

FeelersAttribute::FeelersAttribute(AttributeContainer& container,
                                   FeelersAttribute&& other)
    : AttributeBase(container, std::move(other)) {}

FeelersAttribute::FeelersAttribute(FeelersAttribute&& other)
    : AttributeBase(std::move(other)) {}

float FeelersAttribute::length() const { return feelers_length(); }

float FeelersAttribute::radius() const { return thickness(); }

float FeelersAttribute::thickness() const { return feelers_thickness(); }

float FeelersAttribute::fov_angle() const { return feelers_fov_angle(); }

FixedSizeVector<CategoricalAttribute>& FeelersAttribute::ids() {
  return feelers_ids();
}

const FixedSizeVector<CategoricalAttribute>& FeelersAttribute::ids() const {
  return feelers_ids();
}

FixedSizeVector<NumberAttribute<float>>& FeelersAttribute::distances() {
  return feelers_distances();
}

const FixedSizeVector<NumberAttribute<float>>& FeelersAttribute::distances()
    const {
  return feelers_distances();
}

JoystickAttribute::JoystickAttribute(AttributeContainer& container,
                                     const char* name, AxesMode axes_mode,
                                     ControlledEntity controlled_entity,
                                     ControlFrame control_frame)
    : AttributeBase(container, name, axes_mode, controlled_entity,
                    control_frame) {}

JoystickAttribute::JoystickAttribute(AttributeContainer& container,
                                     const JoystickAttribute& other)
    : AttributeBase(container, other) {}

JoystickAttribute::JoystickAttribute(AttributeContainer& container,
                                     JoystickAttribute&& other)
    : AttributeBase(container, std::move(other)) {}

JoystickAttribute::JoystickAttribute(JoystickAttribute&& other)
    : AttributeBase(std::move(other)) {}

bool JoystickAttribute::set_x_axis(float x_axis) {
  return set_joystick_x_axis(x_axis);
}

bool JoystickAttribute::set_y_axis(float y_axis) {
  return set_joystick_y_axis(y_axis);
}

float JoystickAttribute::x_axis() const { return joystick_x_axis(); }

float JoystickAttribute::y_axis() const { return joystick_y_axis(); }

AxesMode JoystickAttribute::axes_mode() const { return joystick_axes_mode(); }

ControlledEntity JoystickAttribute::controlled_entity() const {
  return joystick_controlled_entity();
}

ControlFrame JoystickAttribute::control_frame() const {
  return joystick_control_frame();
}

PositionAttribute::PositionAttribute(AttributeContainer& container,
                                     const char* name)
    : UnconstrainedAttribute(container, name) {}

PositionAttribute::PositionAttribute(AttributeContainer& container,
                                     const PositionAttribute& other)
    : UnconstrainedAttribute(container, other) {}

PositionAttribute::PositionAttribute(AttributeContainer& container,
                                     PositionAttribute&& other)
    : UnconstrainedAttribute(container, std::move(other)) {}

PositionAttribute::PositionAttribute(PositionAttribute&& other)
    : UnconstrainedAttribute(std::move(other)) {}

void PositionAttribute::set_value(const Position& value) {
  set_position(value);
}

PositionAttribute& PositionAttribute::operator=(const Position& value) {
  set_value(value);
  return *this;
}

const Position& PositionAttribute::value() const { return position(); }

PositionAttribute::operator Position() const { return value(); }  // NOLINT

RotationAttribute::RotationAttribute(AttributeContainer& container,
                                     const char* name)
    : UnconstrainedAttribute(container, name) {}

RotationAttribute::RotationAttribute(AttributeContainer& container,
                                     const RotationAttribute& other)
    : UnconstrainedAttribute(container, other) {}

RotationAttribute::RotationAttribute(AttributeContainer& container,
                                     RotationAttribute&& other)
    : UnconstrainedAttribute(container, std::move(other)) {}

RotationAttribute::RotationAttribute(RotationAttribute&& other)
    : UnconstrainedAttribute(std::move(other)) {}

void RotationAttribute::set_value(const Rotation& value) {
  set_rotation(value);
}

RotationAttribute& RotationAttribute::operator=(const Rotation& value) {
  set_value(value);
  return *this;
}

const Rotation& RotationAttribute::value() const { return rotation(); }

RotationAttribute::operator Rotation() const { return value(); }  // NOLINT

}  // namespace falken
