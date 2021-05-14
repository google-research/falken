//  Copyright 2021 Google LLC
//
//  Licensed under the Apache License, Version 2.0 (the "License");
//  you may not use this file except in compliance with the License.
//  You may obtain a copy of the License at
//
//       http://www.apache.org/licenses/LICENSE-2.0
//
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_TYPES_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_TYPES_H_

#include <algorithm>
#include <string>
#include <vector>

#include "falken/allocator.h"

namespace falken {

/// std::string that uses Falken's allocator.
#if !defined(SWIG)
typedef std::basic_string<char, std::char_traits<char>, Allocator<char>> String;
#else
// When generating code with SWIG we always use Falken's allocator.
typedef std::string String;
#endif  // !defined(SWIG)

/// std::vector that uses Falken's allocator.
#if !defined(SWIG)
template <typename T>
using Vector = std::vector<T, Allocator<T>>;
#else
// When generating code with SWIG we always use Falken's allocator.
template <typename T>
using Vector = std::vector<T>;
#endif  // !defined(SWIG)

#if !defined(SWIG)
// Convert between string vector types.
template<typename InputVectorType, typename OutputVectorType>
inline OutputVectorType& ConvertStringVector(const InputVectorType& input,
                                             OutputVectorType& output) {
  output.resize(input.size());
  std::transform(
      input.begin(), input.end(), output.begin(),
      [](const typename InputVectorType::value_type& str) ->
          typename OutputVectorType::value_type {
        return typename OutputVectorType::value_type(str.c_str());
      });
  return output;
}
#endif  // !defined(SWIG)

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_TYPES_H_
