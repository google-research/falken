%{
// Includes the header in the wrapper code.
#include "falken/unconstrained_attribute.h"
%}

%include "src/core/swig/allocator.i"
%include "src/core/swig/attribute_base.i"
%include "src/core/swig/config.i"
%include "src/core/swig/null_check_this.i"
%feature("nspace");

// Use copy rather than move constructor overloads.
%ignore falken::UnconstrainedAttribute::UnconstrainedAttribute(
  AttributeContainer& container, UnconstrainedAttribute&& attribute);
%ignore falken::UnconstrainedAttribute::UnconstrainedAttribute(
  UnconstrainedAttribute&& attribute);

// Ignore copy operators, in favor of copy constructors.
%ignore falken::UnconstrainedAttribute::operator=;
// Ignore implicit conversion.
%ignore falken::UnconstrainedAttribute::operator T() const;

%include "falken/unconstrained_attribute.h"
