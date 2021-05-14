%{
// Includes the header in the wrapper code.
#include "falken/number_attribute.h"
%}

%include "src/core/swig/allocator.i"
%include "src/core/swig/attribute_base.i"
%include "src/core/swig/config.i"
%include "src/core/swig/null_check_this.i"
%feature("nspace");

// Use copy rather than move constructor overloads.
%ignore falken::NumberAttribute::NumberAttribute(
  AttributeContainer& container, NumberAttribute&& attribute);
%ignore falken::NumberAttribute::NumberAttribute(
  NumberAttribute&& attribute);

// Ignore implicit conversions.
%ignore falken::NumberAttribute::operator=(T value);
%ignore falken::NumberAttribute::operator T() const;
// Ignore copy operator, in favor of the copy constructor.
%ignore falken::NumberAttribute::operator=(const NumberAttribute& attribute);

%include "falken/number_attribute.h"

%template(NumberAttribute) falken::NumberAttribute<float>;
