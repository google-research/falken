// Falken primitives SWIG C# generation.

%{
// Includes the header in the wrapper code.
#include "falken/config.h"
#include "falken/primitives.h"
%}

// Import Falken interfaces.
%include "src/core/swig/config.i"
%include "src/core/swig/null_check_this.i"
%feature("nspace");

// Don't generate C# code for these operators.
%ignore falken::Rotation::operator=(const Rotation& other);

// Don't generate C# code for these overloaded methods.
%ignore falken::Rotation::Rotation(const Rotation &other);

// Parse the header file to generate wrappers.
%include "falken/primitives.h"
