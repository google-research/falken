%module falken_module

%feature("nspace");

// Override the static constructor for the intermediate (PINVOKE) class to
// initialize the logger before any C++ methods are called.
%pragma(csharp) imclasscode=%{
  static $imclassname()
  {
    Falken.Log.Debug("Installed C# log handler.");
  }
%}

// Disable XML documentation warnings for all generated code.
%typemap(csattributes) SWIGTYPE %{
  // Do not warn about missing documentation.
  #pragma warning disable 1591
%}

// Hide the falken_module class from the public interface.
%pragma(csharp) moduleclassmodifiers="internal class"

%include "std_shared_ptr.i"

%shared_ptr(falken::Service)
%shared_ptr(falken::BrainBase)
%shared_ptr(falken::Session)
%shared_ptr(falken::Episode)

%include "src/core/swig/actions.i"
%include "src/core/swig/allocator.i"
%include "src/core/swig/attribute_base.i"
%include "src/core/swig/attribute_container.i"
%include "src/core/swig/bool_attribute.i"
%include "src/core/swig/brain.i"
%include "src/core/swig/brain_spec.i"
%include "src/core/swig/categorical_attribute.i"
%include "src/core/swig/config.i"
%include "src/core/swig/entity.i"
%include "src/core/swig/episode.i"
%include "src/core/swig/feelers_attribute.i"
%include "src/core/swig/fixed_size_vector.i"
%include "src/core/swig/joystick_attribute.i"
%include "src/core/swig/log.i"
%include "src/core/swig/null_check_this.i"
%include "src/core/swig/number_attribute.i"
%include "src/core/swig/observations.i"
%include "src/core/swig/position_attribute.i"
%include "src/core/swig/primitives.i"
%include "src/core/swig/rotation_attribute.i"
%include "src/core/swig/service.i"
%include "src/core/swig/session.i"
%include "src/core/swig/types.i"
%include "src/core/swig/unconstrained_attribute.i"
