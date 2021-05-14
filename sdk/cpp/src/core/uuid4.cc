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

#include "src/core/uuid4.h"

#include <ctime>
#include <random>
#include <sstream>

namespace falken {
namespace core {

namespace {
// UUIDGens are seeded by system time. In case system time-resolution is too
// low there could be collisions when UUIDGens are created close together. We
// therefore factor the number of counters into the seed.
int rng_counter = 0;
}

void UUIDGen::GenerateRandomHexNibbles(std::stringstream& out,
                                       int number_of_nibbles,
                                       int override_mask,
                                       int override) {
  for (int i = 0; i < number_of_nibbles; ++i) {
    int nibble = ((random_int_(rng_) & 0xF) & ~override_mask);
    nibble |= (override_mask & override);
    out << std::hex << nibble;
  }
}

// Returns a random UUID v4.
// See spec at:
// https://en.wikipedia.org/wiki/Universally_unique_identifier#Version_4_(random)
std::string UUIDGen::RandUUID4() {
  std::stringstream ss;

  GenerateRandomHexNibbles(ss, 8);
  ss << "-";
  GenerateRandomHexNibbles(ss, 4);
  ss << "-" << "4";  // 13th digit is always 4.
  GenerateRandomHexNibbles(ss, 3);
  ss << "-";
  // 17th digit is either 8, 9, a or b
  GenerateRandomHexNibbles(ss, 1, (1 << 3) | (1 << 2), (1 << 3));
  GenerateRandomHexNibbles(ss, 3);
  ss << "-";
  GenerateRandomHexNibbles(ss, 12);
  return ss.str();
}

// Create seed by combining current time, number of rngs, and input str.
uint64_t UUIDGen::GetFreshSeed(const std::string& seed_str, uint64_t time) {
  if (!time) {
    time = std::time(nullptr);
  }
  std::string full_seed_str = (
      seed_str + std::to_string(time) + std::to_string(rng_counter++));
  std::seed_seq seed_seq(full_seed_str.begin(), full_seed_str.end());
  uint64_t seed;
  seed_seq.generate(&seed, &seed+ 1);
  return seed;
}

UUIDGen::UUIDGen(const std::string& seed_helper) :
  rng_(GetFreshSeed(seed_helper)) {}

std::string RandUUID4(const std::string& seed_helper) {
  return UUIDGen(seed_helper).RandUUID4();
}

}  // namespace core
}  // namespace falken
