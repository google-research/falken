// Makes sure any reference to self / this that references nullptr will throw
// an exception.
%typemap(check) SWIGTYPE *self %{
#ifndef NULL_CHECK_THIS_TO_STRING
#define NULL_CHECK_THIS_TO_STRING2(x) #x
#define NULL_CHECK_THIS_TO_STRING(x) NULL_CHECK_THIS_TO_STRING2(#x)
#endif  // NULL_CHECK_THIS_TO_STRING
  if (!$1) {
    SWIG_CSharpSetPendingExceptionArgument(
        SWIG_CSharpArgumentNullException,
        NULL_CHECK_THIS_TO_STRING($1_mangle) " has been disposed", 0);
    return $null;
  }
#undef NULL_CHECK_THIS_TO_STRING
#undef NULL_CHECK_THIS_TO_STRING2
%}
