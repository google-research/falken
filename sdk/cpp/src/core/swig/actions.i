// Falken actions SWIG C# generation.

%{
/* Includes the header in the wrapper code */
#include "falken/config.h"
#include "falken/attribute.h"
#include "falken/actions.h"
%}

// Import Falken interfaces.
%include "src/core/swig/allocator.i"
%include "src/core/swig/attribute.i"
%include "src/core/swig/config.i"
%include "src/core/swig/null_check_this.i"
%include "src/core/swig/types.i"
%feature("nspace");
// Ignore warning about the copy operator being used instead of the move
// operator.
%warnfilter(516) ActionsBase;
/* Parse the header file to generate wrappers */
%include "falken/actions.h"
