%{
// Includes the header in the wrapper code.
#include "falken/categorical_attribute.h"
%}

%include "src/core/swig/allocator.i"
%include "src/core/swig/attribute_base.i"
%include "src/core/swig/config.i"
%include "src/core/swig/null_check_this.i"
%include "src/core/swig/types.i"
%feature("nspace");

// Use copy rather than move constructor overloads.
%ignore falken::CategoricalAttribute::CategoricalAttribute(
  AttributeContainer& container, CategoricalAttribute&& attribute);
%ignore falken::CategoricalAttribute::CategoricalAttribute(
  CategoricalAttribute&& attribute);

// Ignore implicit conversions.
%ignore falken::CategoricalAttribute::operator=(int value);
%ignore falken::CategoricalAttribute::operator int() const;
// Ignore copy operator, in favor of the copy constructor.
%ignore falken::CategoricalAttribute::operator=(
  const CategoricalAttribute& attribute);

%include "falken/categorical_attribute.h"
