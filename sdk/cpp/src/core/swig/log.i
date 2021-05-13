// Falken log SWIG C# generation.

%{
// Includes the header in the wrapper code.
#include "falken/log.h"
%}

%include "std_string.i"
%include "std_shared_ptr.i"

%include "src/core/swig/allocator.i"
%include "src/core/swig/config.i"
%include "src/core/swig/null_check_this.i"
%include "src/core/swig/types.i"
%feature("nspace");

// Tell SWIG that the C function pointer cfunc is the same as the C# delegate
// type csdelegate.
%define FALKEN_MAP_CFUNC_TO_CSDELEGATE(cfunc, csdelegate)
    %typemap(cstype) cfunc #csdelegate ;
%typemap(imtype) cfunc #csdelegate ;
%typemap(csin) cfunc "$csinput";
%typemap(in, canthrow=1) cfunc %{
  $1 = ($1_ltype)$input;
%}
%enddef  // FALKEN_MAP_CFUNC_TO_CSDELEGATE(cfunc, csdelegate)

// Map falken::LogCallback to LogMessageDelegate
FALKEN_MAP_CFUNC_TO_CSDELEGATE(
  falken::LogCallback,
  FalkenInternal.falken.LoggerNotifier.LogMessageDelegate)

// We don't need LoggerNotifier's move operator.
%ignore falken::LoggerNotifier::operator=(LoggerNotifier&& other);

%typemap(cscode) falken::LoggerNotifier %{
  // Notifies the C# layer of log messages from the logging library.
  public delegate void LogMessageDelegate(
      FalkenInternal.falken.LogLevel logLevel, string message,
      System.IntPtr context);
%}

// C# doesn't support multiple inheritance so expose each base class through
// an accessor.
%extend falken::SystemLogger {
  // Get LoggerBase interface to this instance.
  falken::LoggerBase* GetLoggerBase() { return $self; }

  // Get LoggerNotifier interface to this instance.
  falken::LoggerNotifier* GetLoggerNotifier() { return $self; }
}

%typemap(cscode) falken::SystemLogger %{
  // Since a reference to this class can be garbage collected before
  // the instance referencing this object, to keep a reference to the C++
  // falken::SystemLogger instance derive from this class then clean up
  // any C++->C# callbacks in the Dispose() method.
  internal SystemLogger() {
    // Get the global logger and copy the reference to this instance.
    var logger = Get();
    swigCMemOwnBase = true;
    swigCPtr = new global::System.Runtime.InteropServices.HandleRef(
        this, logger.swigCPtr.Handle);
    // Release reference to the global logger from the temporary instance.
    logger.swigCPtr = new global::System.Runtime.InteropServices.HandleRef(
        null, global::System.IntPtr.Zero);
  }
%}

%shared_ptr(falken::SystemLogger)

%include "falken/log.h"

