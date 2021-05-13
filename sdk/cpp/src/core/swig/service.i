// Falken service SWIG C# generation.

%{
// Includes the header in the wrapper code.
#include "falken/brain.h"
#include "falken/service.h"
%}

%include "std_shared_ptr.i"
%include "std_vector.i"

// Import Falken interfaces.
%include "src/core/swig/allocator.i"
%include "src/core/swig/brain.i"
%include "src/core/swig/config.i"
%include "src/core/swig/null_check_this.i"
%include "src/core/swig/session.i"
%include "src/core/swig/types.i"
%feature("nspace");

// Parse the header file to generate wrappers.
%include "falken/service.h"

%template(BrainPtr) std::shared_ptr<falken::BrainBase>;
%template(BrainVector) std::vector<std::shared_ptr<falken::BrainBase>>;
%template() falken::Vector<std::shared_ptr<falken::BrainBase>>;
%template(ServicePtr) std::shared_ptr<falken::Service>;
