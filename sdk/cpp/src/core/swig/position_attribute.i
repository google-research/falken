%{
// Includes the header in the wrapper code.
#include "falken/position_attribute.h"
%}

%include "src/core/swig/allocator.i"
%include "src/core/swig/attribute_base.i"
%include "src/core/swig/config.i"
%include "src/core/swig/null_check_this.i"
%include "src/core/swig/primitives.i"
%include "src/core/swig/unconstrained_attribute.i"
%feature("nspace");

// Use copy rather than move constructor overloads.
%ignore falken::PositionAttribute::PositionAttribute(
  AttributeContainer& container, PositionAttribute&& attribute);
%ignore falken::PositionAttribute::PositionAttribute(
  PositionAttribute&& attribute);

// Ignore implicit conversions.
%ignore falken::PositionAttribute::operator=(const Position& value);
%ignore falken::PositionAttribute::operator Position() const;
// Ignore copy operator, in favor of the copy constructor.
%ignore falken::PositionAttribute::operator=(
  const PositionAttribute& attribute);
// Ignore value method as it returns a reference to the value which
// can be deallocated if the owner AttributeBase is disposed.
%ignore falken::PositionAttribute::value() const;

// Expand the template for the base class.
%template(PositionAttributeBase) falken::UnconstrainedAttribute<
  falken::Position, falken::AttributeBase::kTypePosition>;

%include "falken/position_attribute.h"
