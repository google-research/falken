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

#include "src/core/stdout_logger.h"

#include <stdio.h>

#if _MSC_VER
#include <windows.h>
#elif defined(__ANDROID__)
#include <android/log.h>
#endif

#include "falken/log.h"

namespace falken {

void StandardOutputErrorLogger::Log(LogLevel log_level, const char* message) {
  if (ShouldLog(log_level)) {
    FILE* output_stream = log_level == kLogLevelWarning ||
                          log_level == kLogLevelError ||
                          log_level == kLogLevelFatal
                          ? stderr
                          : stdout;
    fprintf(output_stream, "%s\n", message);
#if _MSC_VER  // On Windows log to Visual Studio's console.
    OutputDebugString(message);
#elif defined(__ANDROID__)  // On Android log to Android log.
    __android_log_print(ANDROID_LOG_INFO, "Falken", "%s\n", message);
#endif
  }
}

}  // namespace falken
