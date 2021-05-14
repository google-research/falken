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

#ifndef FALKEN_SDK_CORE_UUID4_H_
#define FALKEN_SDK_CORE_UUID4_H_

#include <cstdint>
#include <random>
#include <string>

namespace falken {
namespace core {

class UUIDGen {
 public:
  // Seeds using a combination of seed helepr, current time and number of rng
  // in existence.
  explicit UUIDGen(const std::string& seed_helper);

  // Returns a random UUID v4.
  std::string RandUUID4();

  // Exposed for testing.
  static uint64_t GetFreshSeed(const std::string& seed_str, uint64_t time = 0);
 private:
  std::default_random_engine rng_;
  std::uniform_int_distribution<int> random_int_;

  void GenerateRandomHexNibbles(std::stringstream& out,
                                int number_of_nibbles,
                                int override_mask = 0,
                                int override = 0);
};

std::string RandUUID4(const std::string& seed_helper);
}  // namespace core
}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_UUID4_H_
