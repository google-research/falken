%{
// Includes the header in the wrapper code.
#include "falken/bool_attribute.h"
%}

%include "src/core/swig/allocator.i"
%include "src/core/swig/attribute_base.i"
%include "src/core/swig/config.i"
%include "src/core/swig/null_check_this.i"
%feature("nspace");

// Use copy rather than move constructor overloads.
%ignore falken::BoolAttribute::BoolAttribute(AttributeContainer& container,
                                             BoolAttribute&& attribute);
%ignore falken::BoolAttribute::BoolAttribute(BoolAttribute&& attribute);

// Ignore implicit conversions.
%ignore falken::BoolAttribute::operator=(bool value);
%ignore falken::BoolAttribute::operator bool() const;
// Ignore copy operator, in favor of the copy constructor.
%ignore falken::BoolAttribute::operator=(const BoolAttribute& attribute);

%include "falken/bool_attribute.h"
