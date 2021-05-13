// Falken brain SWIG C# generation.

%rename ("GetSessionByIndex", fullname=1) falken::BrainBase::GetSession(int);
%rename ("GetSessionById", fullname=1)
  falken::BrainBase::GetSession(const char*);

%{
/* Includes the header in the wrapper code */
#include "falken/brain.h"
#include "falken/session.h"
%}

%include "stdint.i"
%include "std_shared_ptr.i"
%include "std_string.i"
// Import Falken interfaces.
%include "src/core/swig/allocator.i"
%include "src/core/swig/brain_spec.i"
%include "src/core/swig/null_check_this.i"
%include "src/core/swig/service.i"
%include "src/core/swig/session.i"
%include "src/core/swig/types.i"
%feature("nspace");
// Ignore warnings about the copy operators being used instead of the move
// operators and non-const accessors being used instead of const accessors.
%warnfilter(516) BrainBase;

/* Parse the header file to generate wrappers */
%include "falken/brain.h"

%template(SessionPtr) std::shared_ptr<falken::Session>;
%template(SessionVector) std::vector<std::shared_ptr<falken::Session>>;
