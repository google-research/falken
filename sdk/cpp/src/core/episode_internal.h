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

#ifndef FALKEN_SDK_CORE_EPISODE_INTERNAL_H_
#define FALKEN_SDK_CORE_EPISODE_INTERNAL_H_

#include <memory>
#include <string>

#include "falken/episode.h"
#include "falken/session.h"

namespace falken {

class Episode;
class Session;

// Private data for the Episode class.
struct Episode::EpisodeData {
  EpisodeData(const std::weak_ptr<Session>& session_,
              const char* episode_id_,
              bool read_only_) :
      session(session_),
      episode_id(episode_id_),
      read_only(read_only_),
      current_step(0),
      completed(read_only_),
      reward(0.0f) {}

  // Session this Episode belongs to.
  std::shared_ptr<Session> session;
  // Weak reference to the episode instance.
  std::weak_ptr<Episode> weak_this;
  // ID of the episode.
  const std::string episode_id;
  // Whether this episode is read-only.
  const bool read_only;
  // Current step of this episode.
  uint64_t current_step;
  // Whether the episode is complete.
  bool completed;
  // Last reward provided to Episode::Step().
  float reward;
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_EPISODE_INTERNAL_H_
