# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# tensorflow-lite uses find_package for this package, so override the system
# installation and build from source instead.
include(fft2d)
if(fft2d_POPULATED)
  set(FFT2D_FOUND TRUE CACHE BOOL "Found FF2D")
  get_target_property(FFT2D_INCLUDE_DIRS fft2d INCLUDE_DIRECTORIES)
  set(FFT2D_INCLUDE_DIRS ${FFT2D_INCLUDE_DIRS} CACHE STRING
    "FFT2D include dirs"
  )
  set(FFT2D_LIBRARIES
    fft2d_alloc
    fft2d_fft4f2d
    fft2d_fftsg
    fft2d_fftsg2d
    fft2d_fftsg3d
    fft2d_shrtdct
    CACHE
    STRING
    "FFT2D libraries"
  )
endif()
