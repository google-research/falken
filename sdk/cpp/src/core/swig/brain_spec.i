// Falken brain_spec SWIG C# generation.

%{
/* Includes the header in the wrapper code */
#include "falken/brain_spec.h"
%}

// Import Falken interfaces.
%include "src/core/swig/allocator.i"
%include "src/core/swig/actions.i"
%include "src/core/swig/observations.i"
%include "src/core/swig/null_check_this.i"
%include "src/core/swig/types.i"
%feature("nspace");
// Ignore warnings about the copy operators being used instead of the move
// operators and non-const accessors being used instead of const accessors.
%warnfilter(516) BrainSpecBase;
/* Parse the header file to generate wrappers */
%include "falken/brain_spec.h"
