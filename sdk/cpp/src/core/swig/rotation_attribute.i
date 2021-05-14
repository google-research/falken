%{
// Includes the header in the wrapper code.
#include "falken/rotation_attribute.h"
%}

%include "src/core/swig/allocator.i"
%include "src/core/swig/attribute_base.i"
%include "src/core/swig/config.i"
%include "src/core/swig/null_check_this.i"
%include "src/core/swig/primitives.i"
%include "src/core/swig/unconstrained_attribute.i"
%feature("nspace");

// Use copy rather than move constructor overloads.
%ignore falken::RotationAttribute::RotationAttribute(
  AttributeContainer& container, RotationAttribute&& attribute);
%ignore falken::RotationAttribute::RotationAttribute(
  RotationAttribute&& attribute);

// Ignore implicit conversions.
%ignore falken::RotationAttribute::operator=(const Rotation& value);
%ignore falken::RotationAttribute::operator Rotation() const;
// Ignore copy operator, in favor of the copy constructor.
%ignore falken::RotationAttribute::operator=(
  const RotationAttribute& attribute);
// Ignore value method as it returns a reference to the value which
// can be deallocated if the owner AttributeBase is disposed.
%ignore falken::RotationAttribute::value() const;

// Expand the template for the base class.
%template(RotationAttributeBase) falken::UnconstrainedAttribute<
  falken::Rotation, falken::AttributeBase::kTypeRotation>;

%include "falken/rotation_attribute.h"
