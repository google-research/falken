// Falken observations SWIG C# generation.

%{
// Includes the header in the wrapper code.
#include "falken/observations.h"
%}

// Since C# does not support multiple inheritance, we have to create
// a method to get the ObservationsBase instance as an EntityBase
// so users can add attributes to the player attribute.
%extend falken::ObservationsBase {
    EntityBase* player() {
        return $self;
    }
}

// Import Falken interfaces.
%include "src/core/swig/allocator.i"
%include "src/core/swig/config.i"
%include "src/core/swig/entity.i"
%include "src/core/swig/null_check_this.i"
%feature("nspace");

// Ignore warning (516) about the copy operator being used instead of the move
// operator and the warning (833) regarding multiple inheritance of EntityBase
// being ignored in the generated code.
%warnfilter(516,833) ObservationsBase;
// Parse the header file to generate wrappers.
%include "falken/observations.h"
