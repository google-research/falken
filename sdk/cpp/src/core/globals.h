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

#ifndef FALKEN_SDK_CORE_GLOBALS_H_
#define FALKEN_SDK_CORE_GLOBALS_H_

#ifdef FALKEN_SYNC_DESTRUCTION
#include <mutex>  // NOLINT

#define FALKEN_LOCK_GLOBAL_MUTEX() \
  std::lock_guard<std::recursive_mutex> _lock(falken::kDestructionLock);
#else  // FALKEN_SYNC_DESTRUCTION
#define FALKEN_LOCK_GLOBAL_MUTEX()
#endif  // FALKEN_SYNC_DESTRUCTION

namespace falken {

#ifdef FALKEN_SYNC_DESTRUCTION
// Lock used to synchronize destruction in GC languages like C#.
extern std::recursive_mutex kDestructionLock;
#endif  // FALKEN_SYNC_DESTRUCTION

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_GLOBALS_H_
