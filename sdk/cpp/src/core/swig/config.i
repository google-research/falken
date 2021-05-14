// Falken config SWIG C# generation.

%{
// Includes the header in the wrapper code.
#include "falken/config.h"
%}

%feature("nspace");
// Parse the header file to generate wrappers.
%include "falken/config.h"
