// Falken attributes SWIG C# generation.
%{
// Includes the header in the wrapper code.
#include "falken/attribute.h"
%}

// Import Falken interfaces.
%include "src/core/swig/attribute_container.i"
%include "src/core/swig/attribute_base.i"
%include "src/core/swig/bool_attribute.i"
%include "src/core/swig/categorical_attribute.i"
%include "src/core/swig/number_attribute.i"
%include "src/core/swig/feelers_attribute.i"
%include "src/core/swig/position_attribute.i"
%include "src/core/swig/rotation_attribute.i"
%include "src/core/swig/unconstrained_attribute.i"


