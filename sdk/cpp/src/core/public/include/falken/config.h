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

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_CONFIG_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_CONFIG_H_

#if defined(_MSC_VER)  // MSVC.

#if defined(FALKEN_BUILD_DLL)
#define FALKEN_EXPORT __declspec(dllexport)
#elif defined(FALKEN_STATIC_LIBRARY)
#define FALKEN_EXPORT  // Statically link C++ SDK.
#else
#define FALKEN_EXPORT __declspec(dllimport)
#endif  // defined(FALKEN_BUILD_DLL)

#define FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_START \
  __pragma(warning(push)) \
  __pragma(warning(disable : 4251))

#define FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_END \
  __pragma(warning(pop))

#elif defined(__GNUC__) || defined(__clang__)  // gcc or clang.

#define FALKEN_EXPORT __attribute__((visibility("default")))

#define FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_START
#define FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_END

#else  // Untested compiler.

#define FALKEN_EXPORT
#pragma warning Unknown dynamic link export semantics.

#define FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_START
#define FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_END

#endif  // defined(_MSC_VER)

#if defined(SWIG) || defined(DOXYGEN)
// SWIG needs to ignore the FALKEN_DEPRECATED tag.
#define FALKEN_DEPRECATED
#endif  // defined(SWIG) || defined(DOXYGEN)

#ifndef FALKEN_DEPRECATED
#ifdef __GNUC__
#define FALKEN_DEPRECATED __attribute__((deprecated))
#elif defined(_MSC_VER)
#define FALKEN_DEPRECATED __declspec(deprecated)
#else
// We don't know how to mark functions as "deprecated" with this compiler.
#define FALKEN_DEPRECATED
#endif
#endif  // FALKEN_DEPRECATED

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_CONFIG_H_
