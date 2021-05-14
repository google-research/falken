%{
// Includes the header in the wrapper code.
#include "falken/attribute_container.h"
%}

%include "std_set.i"
%include "std_string.i"
%include "std_vector.i"
// Import Falken interfaces.
%include "src/core/swig/allocator.i"
%include "src/core/swig/config.i"
%include "src/core/swig/null_check_this.i"
%include "src/core/swig/types.i"
%feature("nspace");

// Use the overloaded copy constructor instead of move.
%ignore falken::AttributeContainer::AttributeContainer(
  const std::set<std::string>& attributes_to_ignore,
  AttributeContainer&& other);

%include "falken/attribute_container.h"

%template(AttributeVector) std::vector<falken::AttributeBase*>;
%template() falken::Vector<falken::AttributeBase*>;

