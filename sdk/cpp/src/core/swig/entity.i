// Falken entity SWIG C# generation.

%{
// Includes the header in the wrapper code.
#include "falken/attribute.h"
#include "falken/entity.h"
%}

%include "std_set.i"
%include "std_string.i"
%include "std_vector.i"
// Import Falken interfaces.
%include "src/core/swig/allocator.i"
%include "src/core/swig/attribute.i"
%include "src/core/swig/null_check_this.i"
%include "src/core/swig/types.i"
%feature("nspace");

%template(EntityBaseVector) std::vector<falken::EntityBase*>;
%template() falken::Vector<falken::EntityBase*>;
// Parse the header file to generate wrappers.
%include "falken/entity.h"
