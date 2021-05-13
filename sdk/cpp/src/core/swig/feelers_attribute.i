%{
// Includes the header in the wrapper code.
#include "falken/feelers_attribute.h"
%}

%include "src/core/swig/allocator.i"
%include "src/core/swig/attribute_base.i"
%include "src/core/swig/config.i"
%include "src/core/swig/categorical_attribute.i"
%include "src/core/swig/null_check_this.i"
%include "src/core/swig/number_attribute.i"
%feature("nspace");

// Use copy rather than move constructor overloads.
%ignore falken::FeelersAttribute::FeelersAttribute(
  AttributeContainer& container, FeelersAttribute&& attribute);
%ignore falken::FeelersAttribute::FeelersAttribute(
  FeelersAttribute&& attribute);

// Ignore copy operator, in favor of the copy constructor.
%ignore falken::FeelersAttribute::operator=(const FeelersAttribute& attribute);

// Ignore const versions of these functions since they are not needed on
// the public interface
%ignore falken::FeelersAttribute::distances() const;
%ignore falken::FeelersAttribute::ids() const;

%include "falken/feelers_attribute.h"

%template(NumberAttributeVector)
  std::vector<falken::NumberAttribute<float>*>;
%template() falken::Vector<falken::NumberAttribute<float>*>;

%template(CategoricalAttributeVector)
  std::vector<falken::CategoricalAttribute*>;
%template() falken::Vector<falken::CategoricalAttribute*>;

FALKEN_FIXED_SIZED_VECTOR(FixedSizeNumberAttributeVector,
                          falken::NumberAttribute<float>);
FALKEN_FIXED_SIZED_VECTOR(FixedSizeCategoricalAttributeVector,
                          falken::CategoricalAttribute);
