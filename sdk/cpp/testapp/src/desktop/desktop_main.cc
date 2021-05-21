// Copyright 2016 Google Inc. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <signal.h>
#include <stdarg.h>
#include <stdio.h>

#ifdef _WIN32
#include <direct.h>
#define chdir _chdir
#else
#include <unistd.h>
#endif  // _WIN32

#ifdef _WIN32
#include <windows.h>
#endif  // _WIN32

#include <algorithm>
#include <string>

#include "main.h"

// The TO_STRING macro is useful for command line defined strings as the quotes
// get stripped.
#define TO_STRING_EXPAND(X) #X
#define TO_STRING(X) TO_STRING_EXPAND(X)

// Path to the app framework config file to load.
#ifdef APP_FRAMEWORK_CONFIG
#define APP_FRAMEWORK_CONFIG_STRING TO_STRING(APP_FRAMEWORK_CONFIG)
#else
#define APP_FRAMEWORK_CONFIG_STRING ""
#endif  // APP_FRAMEWORK_CONFIG

extern "C" int common_main(int argc, const char* argv[]);

static bool quit = false;

#ifdef _WIN32
static BOOL WINAPI SignalHandler(DWORD event) {
  if (!(event == CTRL_C_EVENT || event == CTRL_BREAK_EVENT)) {
    return FALSE;
  }
  quit = true;
  return TRUE;
}
#else
static void SignalHandler(int /* ignored */) { quit = true; }
#endif  // _WIN32

bool ProcessEvents(int msec) {
#ifdef _WIN32
  Sleep(msec);
#else
  usleep(msec * 1000);
#endif  // _WIN32
  return quit;
}

std::string PathForResource() {
  return std::string();
}

void LogPrintV(FILE* stream, const char* format, va_list list) {
  vfprintf(stream, format, list);
  fprintf(stream, "\n");
  fflush(stream);
}

void LogMessage(const char* format, ...) {
  va_list list;
  va_start(list, format);
  LogPrintV(stdout, format, list);
  va_end(list);
}

void LogError(const char* format, ...) {
  va_list list;
  va_start(list, format);
  LogPrintV(stderr, format, list);
  va_end(list);
}

WindowContext GetWindowContext() { return nullptr; }

// Returns the temporary directory path.
// TODO(b/182802651): Add implementation for Windows, macOS and Linux.
const char* GetTemporaryDirectoryPath() { return ""; }

// Change the current working directory to the directory containing the
// specified file.
void ChangeToFileDirectory(const char* file_path) {
  std::string path(file_path);
  std::replace(path.begin(), path.end(), '\\', '/');
  auto slash = path.rfind('/');
  if (slash != std::string::npos) {
    std::string directory = path.substr(0, slash);
    if (!directory.empty()) {
      // this is to get the compiler to ignore the return
      // value even though chdir() is marked as warn_unused_result
      auto retval = chdir(directory.c_str());
      (void)retval;
    }
  }
}

int main(int argc, const char* argv[]) {
  ChangeToFileDirectory(APP_FRAMEWORK_CONFIG_STRING[0] != '\0'
                            ? APP_FRAMEWORK_CONFIG_STRING
                            : argv[0]);  // NOLINT
#ifdef _WIN32
  SetConsoleCtrlHandler((PHANDLER_ROUTINE)SignalHandler, TRUE);
#else
  signal(SIGINT, SignalHandler);
#endif  // _WIN32
  return common_main(argc, argv);
}

#if defined(_WIN32)
// Returns the number of microseconds since the epoch.
int64_t WinGetCurrentTimeInMicroseconds() {
  FILETIME file_time;
  GetSystemTimeAsFileTime(&file_time);

  ULARGE_INTEGER now;
  now.LowPart = file_time.dwLowDateTime;
  now.HighPart = file_time.dwHighDateTime;

  // Windows file time is expressed in 100s of nanoseconds.
  // To convert to microseconds, multiply x10.
  return now.QuadPart * 10LL;
}
#endif
