// Falken session SWIG C# generation.

%{
/* Includes the header in the wrapper code */
#include "falken/config.h"
#include "falken/episode.h"
#include "falken/session.h"
%}

%include "std_shared_ptr.i"
%include "std_string.i"
// Import Falken interfaces.
%include "src/core/swig/allocator.i"
%include "src/core/swig/attribute.i"
%include "src/core/swig/config.i"
%include "src/core/swig/brain.i"
%include "src/core/swig/episode.i"
%include "src/core/swig/null_check_this.i"
%include "src/core/swig/types.i"
%feature("nspace");

/* Parse the header file to generate wrappers */
%include "falken/session.h"

%template(EpisodePtr) std::shared_ptr<falken::Episode>;
%template(EpisodeVector) std::vector<std::shared_ptr<falken::Episode>>;
