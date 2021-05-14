%{
// Includes the header in the wrapper code.
#include "falken/joystick_attribute.h"
%}

%include "src/core/swig/allocator.i"
%include "src/core/swig/attribute_base.i"
%include "src/core/swig/config.i"
%include "src/core/swig/null_check_this.i"
%include "src/core/swig/number_attribute.i"
%feature("nspace");

// Use copy rather than move constructor overloads.
%ignore falken::JoystickAttribute::JoystickAttribute(
  AttributeContainer& container, JoystickAttribute&& other);
%ignore falken::JoystickAttribute::JoystickAttribute(JoystickAttribute&& other);

%include "falken/joystick_attribute.h"
