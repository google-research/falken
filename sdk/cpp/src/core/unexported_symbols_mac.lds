# Hide all C symbols since they are not needed.
_[a-z]*
# Hide upper case C symbols except for those starting with _FC
# Character classes with multiple ranges are not supported by ld on macOS.
_[ABCDEGHIJKLMNOPQRSTUVWXYZ][ABDEFGHIJKLMNOPQRSTUVWXYZ][A-Z]*
_[A-Z][a-z]*
# Hide C++ type information, type info names and v-tables for all methods in
# the default namespace.
__ZT[ISV][FP]*
# Hide C++ type information, type info names and v-tables for everything that
# doesn't contain a 6 character namespace starting with "f".
__ZT[ISV]N[ABCDEFGHIJKLMNOPQRSTUVWXYZ012345789][ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdeghijklmnopqrstuvwxyz]*
# Hide new / delete overrides
__Zda*
__Zdl*
__Zna*
__Znw*
# Hide globals in zlib
__dist_code
__length_code
__tr_*
