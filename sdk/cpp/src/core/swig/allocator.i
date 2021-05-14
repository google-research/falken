// Falken allocator SWIG C# generation.

%{
// Includes the header in the wrapper code.
#include "falken/allocator.h"
%}

// We don't need to generate code for new / delete operators since SWIG will
// internally use these to correctly allocated / free objects. Therefore,
// disable warnings about ignoring code generation for the following
// operators in all .i files that include this interface:
// * new
// * new[]
// * delete
// * delete[]
#pragma SWIG nowarn=350,351,394,395

%feature("nspace");
%include "src/core/swig/config.i"
%include "src/core/swig/null_check_this.i"

%ignore falken::AllocatorCallbacks;
%ignore falken::Allocator;
// Parse the header file to generate wrappers.
%include "falken/allocator.h"

