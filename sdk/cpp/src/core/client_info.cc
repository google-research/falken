// Copyright 2021 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include "src/core/client_info.h"

#include <utility>

#include "src/core/macros.h"

#if !defined(FALKEN_SDK_VERSION)
#define FALKEN_SDK_VERSION 0.0.0
#endif  // !defined(FALKEN_SDK_VERSION)
#if !defined(FALKEN_SDK_CHANGELIST)
#define FALKEN_SDK_CHANGELIST 0
#endif  // !defined(FALKEN_SDK_CHANGELIST)
#if !defined(FALKEN_SDK_COMMIT)
#define FALKEN_SDK_COMMIT 0
#endif  // !defined(FALKEN_SDK_COMMIT)

#define FALKEN_SDK_VERSION_STRING FALKEN_EXPAND_STRINGIFY(FALKEN_SDK_VERSION)
#define FALKEN_SDK_CHANGELIST_STRING \
  FALKEN_EXPAND_STRINGIFY(FALKEN_SDK_CHANGELIST)
#define FALKEN_SDK_COMMIT_STRING FALKEN_EXPAND_STRINGIFY(FALKEN_SDK_COMMIT)

namespace {

// clang-format=off
#if defined(NDEBUG)
static const char kBuildType[] = "release";
#else
static const char kBuildType[] = "debug";
#endif  // defined(NDEBUG)

// Detect operating system and architecture.
#if defined(_MSC_VER)  // MSVC.
const char kOperatingSystem[] = "windows";
#if defined(_DLL) && _DLL == 1
const char kCppRuntimeOrStl[] = "MD";
#else
const char kCppRuntimeOrStl[] = "MT";
#endif  // defined(_MT) && _MT == 1

#if ((defined(_M_X64) && _M_X64 == 100) || \
     (defined(_M_AMD64) && _M_AMD64 == 100))
const char kCpuArchitecture[] = "x86_64";
#elif defined(_M_IX86) && _M_IX86 == 600
const char kCpuArchitecture[] = "x86";
#elif defined(_M_ARM64) && _M_ARM64 == 1
const char kCpuArchitecture[] = "arm64";
#elif defined(_M_ARM) && _M_ARM == 7
const char kCpuArchitecture[] = "arm32";
#else
#error Unknown Windows architecture.
#endif  // Architecture

#elif defined(__APPLE__)
#include <TargetConditionals.h>  // NOLINT
const char kCppRuntimeOrStl[] = "libcpp";
#if TARGET_IPHONE_SIMULATOR || TARGET_OS_IPHONE
const char kOperatingSystem[] = "ios";
#elif TARGET_OS_MAC
const char kOperatingSystem[] = "darwin";
#else
#error Unknown Apple operating system.
#endif  // OS

#if __i386__
const char kCpuArchitecture[] = "x86";
#elif __amd64__
const char kCpuArchitecture[] = "x86_64";
#elif __aarch64__
const char kCpuArchitecture[] = "arm64";
#elif __arm__
const char kCpuArchitecture[] = "arm32";
#else
#error Unknown Apple architecture.
#endif  // Architecture

#elif defined(__ANDROID__)
const char* kOperatingSystem = "android";

#if __i386__
const char kCpuArchitecture[] = "x86";
#elif __amd64__
const char kCpuArchitecture[] = "x86_64";
#elif __aarch64__
const char kCpuArchitecture[] = "arm64";
#elif __ARM_EABI__ || __arm__
const char kCpuArchitecture[] = "armeabi-v7a";
#elif __mips__ || __mips
#if __mips__ == 32 || __mips == 32
const char kCpuArchitecture[] = "mips";
#elif __mips__ == 64 || __mips == 64
const char kCpuArchitecture[] = "mips64";
#else
#error Unknown MIPS version. __mips__
#endif  // __mips__
#else
#error Unknown Android architecture.
#endif  // Architecture

#if defined(_STLPORT_VERSION)
const char kCppRuntimeOrStl[] = "stlport";
#elif defined(_GLIBCXX_UTILITY)
const char kCppRuntimeOrStl[] = "gnustl";
#elif defined(_LIBCPP_STD_VER)
const char kCppRuntimeOrStl[] = "libcpp";
#else
#error Unknown Android STL.
#endif  // STL

#elif defined(__linux__) || defined(__ggp__)  // Linux variants.

#if defined(__ggp__)
const char kOperatingSystem[] = "stadia";
#else
const char kOperatingSystem[] = "linux";
#endif  // defined(__ggp__)

#if defined(_GLIBCXX_UTILITY)
const char kCppRuntimeOrStl[] = "gnustl";
#elif defined(_LIBCPP_STD_VER)
const char kCppRuntimeOrStl[] = "libcpp";
#else
#error Unknown STL.
#endif  // STL

#if __amd64__
const char kCpuArchitecture[] = "x86_64";
#elif __i386__
const char kCpuArchitecture[] = "x86";
#else
#error Unknown Linux architecture.
#endif  // Architecture
#else
#error Unknown operating system.
#endif  // Operating system
// clang-format=on

}  // namespace

namespace falken {

std::string GetVersionInformation() {
  static const char kFalkenSdkVersionString[] =
      "Version " FALKEN_SDK_VERSION_STRING " (CL: " FALKEN_SDK_CHANGELIST_STRING
      ", Commit: " FALKEN_SDK_COMMIT_STRING
#if !defined(NDEBUG)
      ", Debug"
#endif  // !defined(NDEBUG)
      ")";
  return std::string(kFalkenSdkVersionString);
}

std::string GetUserAgent() {
  static const char kFalkenUserAgentPrefix[] = "falken-";
  std::string user_agent;
  auto append_to_user_agent = [&user_agent](const char* key,
                                            const char* value) {
    if (!user_agent.empty()) user_agent += " ";
    user_agent += kFalkenUserAgentPrefix;
    user_agent += key;
    user_agent += "/";
    user_agent += value;
  };
  append_to_user_agent("cpp", FALKEN_SDK_VERSION_STRING);
  append_to_user_agent("cpp-commit", FALKEN_SDK_COMMIT_STRING);
  append_to_user_agent("cpp-cl", FALKEN_SDK_CHANGELIST_STRING);
  append_to_user_agent("cpp-build", kBuildType);
  append_to_user_agent("cpp-runtime", kCppRuntimeOrStl);
  append_to_user_agent("os", kOperatingSystem);
  append_to_user_agent("cpu", kCpuArchitecture);
  return user_agent;
}

}  // namespace falken
