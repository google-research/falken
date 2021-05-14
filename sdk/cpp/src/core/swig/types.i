// Falken types SWIG C# generation.

// Globally enable exception checking.
%feature("except:canthrow", "1");

%{
// Includes the header in the wrapper code.
#include "falken/types.h"
%}

%include <std_set.i>
%include <std_string.i>
%include <std_vector.i>

// Use System.IntPtr for all instances of void*.
%apply void *VOID_INT_PTR { void * }

%include "src/core/swig/allocator.i"
%include "src/core/swig/config.i"
%include "src/core/swig/null_check_this.i"

%feature("nspace");

%template(StringSet) std::set<std::string>;
%template(StringVector) std::vector<std::string>;

// Parse the header file to generate wrappers.
%include "falken/types.h"

%template() falken::Vector<std::string>;
