%{
// Includes the header in the wrapper code.
#include "falken/attribute_base.h"
%}

%include "src/core/swig/allocator.i"
%include "src/core/swig/attribute_container.i"
%include "src/core/swig/config.i"
%include "src/core/swig/fixed_size_vector.i"
%include "src/core/swig/log.i"
%include "src/core/swig/null_check_this.i"
%include "src/core/swig/primitives.i"
%include "src/core/swig/types.i"
%feature("nspace");

// Ignore all upcasting methods as they result in unmanaged references to
// the underlying AttributeBase object.
%ignore falken::AttributeBase::AsBool;
%ignore falken::AttributeBase::AsCategorical;
%ignore falken::AttributeBase::AsFeelers;
%ignore falken::AttributeBase::AsJoystick;
%ignore falken::AttributeBase::AsPosition;
%ignore falken::AttributeBase::AsRotation;

// Don't generate C# code for the copy operator.
%ignore falken::AttributeBase::operator=(const AttributeBase& other);
// Use the copy constructors rather than the move overloads.
%ignore falken::AttributeBase::AttributeBase(AttributeBase&& other);
%ignore falken::AttributeBase::AttributeBase(AttributeContainer& container,
                                             AttributeBase&& other);

// Ignore const versions of these functions since they are not needed on
// the public interface
%ignore falken::AttributeBase::feelers_distances() const;
%ignore falken::AttributeBase::feelers_ids() const;

%include "falken/attribute_base.h"

