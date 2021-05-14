%{
// Includes the header in the wrapper code.
#include "falken/fixed_size_vector.h"
%}

%include "std_vector.i"
%include "src/core/swig/null_check_this.i"

// Parse the header file to generate wrappers.
%include "falken/fixed_size_vector.h"

// Macro that creates a C# IEnumerable interface for FixedSizeVector.
%define FALKEN_FIXED_SIZED_VECTOR(CSHARP_TYPE_NAME, CONTAINED_TYPE)
// Ignore the internal constructor, C# code never constructs this object.
%ignore falken::FixedSizeVector<CONTAINED_TYPE>::FixedSizeVector(
  std::vector<CONTAINED_TYPE>*);
// Ignore vector iterator methods.
%ignore falken::FixedSizeVector<CONTAINED_TYPE>::begin;
%ignore falken::FixedSizeVector<CONTAINED_TYPE>::end;
%ignore falken::FixedSizeVector<CONTAINED_TYPE>::rbegin;
%ignore falken::FixedSizeVector<CONTAINED_TYPE>::rend;
%ignore falken::FixedSizeVector<CONTAINED_TYPE>::cbegin;
%ignore falken::FixedSizeVector<CONTAINED_TYPE>::cend;
%ignore falken::FixedSizeVector<CONTAINED_TYPE>::crbegin;
%ignore falken::FixedSizeVector<CONTAINED_TYPE>::crend;
%ignore falken::FixedSizeVector<CONTAINED_TYPE>::data;
%ignore falken::FixedSizeVector<CONTAINED_TYPE>::front;
%ignore falken::FixedSizeVector<CONTAINED_TYPE>::back;
%ignore falken::FixedSizeVector<CONTAINED_TYPE>::data;
%ignore falken::FixedSizeVector<CONTAINED_TYPE>::at(size_t) const;
%ignore falken::FixedSizeVector<CONTAINED_TYPE>::operator=;
%ignore falken::FixedSizeVector<CONTAINED_TYPE>::operator[];
%typemap(csinterfaces) falken::FixedSizeVector<CONTAINED_TYPE> "
    System.IDisposable,
    System.Collections.IEnumerable,
    System.Collections.Generic.IEnumerable<$typemap(cstype, CONTAINED_TYPE)>";
%typemap(cscode) falken::FixedSizeVector<CONTAINED_TYPE> %{
  public int Count { get { return (int)size(); } }

  public $typemap(cstype, CONTAINED_TYPE) this[int index] {
    get { return at((uint)index); }
  }

  public bool IsEmpty { get { return empty(); } }

  // Construct the type-safe enumerator for this object.
  System.Collections.Generic.IEnumerator<$typemap(cstype, CONTAINED_TYPE)>
    System.Collections.Generic.IEnumerable<
      $typemap(cstype, CONTAINED_TYPE)>.GetEnumerator() {
    return new $csclassnameEnumerator(this);
  }

  // Construct the enumerator for this object.
  System.Collections.IEnumerator
      System.Collections.IEnumerable.GetEnumerator() {
    return new $csclassnameEnumerator(this);
  }

  // Construct the generated enumerator for this object.
  public $csclassnameEnumerator GetEnumerator() {
    return new $csclassnameEnumerator(this);
  }

  // Enumerator for this object.
  public sealed class $csclassnameEnumerator :
      System.IDisposable,
      System.Collections.IEnumerator,
      System.Collections.Generic.IEnumerator<$typemap(cstype, CONTAINED_TYPE)> {

    private $csclassname enumerable;
    private int index;
    private object current;

    // Construct from a vector instance.
    public $csclassnameEnumerator($csclassname vector) {
      enumerable = vector;
      Reset();
    }

    // Get the current type-safe object.
    public $typemap(cstype, CONTAINED_TYPE) GetCurrent() {
      if (index < 0 || index >= enumerable.Count || current == null) {
        throw new System.InvalidOperationException(
          "Enumerator in an invalid state.");
      }
      return ($typemap(cstype, CONTAINED_TYPE))current;
    }

    // Generic.IEnumerator.Current.
    public $typemap(cstype, CONTAINED_TYPE) Current {
      get { return GetCurrent(); }
    }

    // IEnumerator.Current.
    object System.Collections.IEnumerator.Current {
      get { return GetCurrent(); }
    }

    // Move to the next item.
    public bool MoveNext() {
      index++;
      if (index >= enumerable.Count) {
        current = null;
        return false;
      }
      current = enumerable[index];
      return true;
    }

    // Reset enumeration.
    public void Reset() {
      index = -1;
      current = null;
    }

    // Remove references to the object an collection.
    public void Dispose() {
      enumerable = null;
      index = -1;
      current = null;
    }
  }
%}

%template(CSHARP_TYPE_NAME) falken::FixedSizeVector<CONTAINED_TYPE>;
%enddef  // FALKEN_FIXED_SIZED_VECTOR(CSHARP_TYPE_NAME, CONTAINED_TYPE)
