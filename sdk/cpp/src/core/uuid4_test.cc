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

#include <set>

#include "gmock/gmock.h"
#include "gtest/gtest.h"


namespace {

TEST(UUID4Test, TestUUIDs) {
  const int kNumUUIDs = 10000;

  std::set<std::string> uuids;

  for (int i = 0; i < kNumUUIDs; ++i) {
    std::string uuid = falken::core::RandUUID4("");

    ASSERT_EQ(uuid.size(), 32 + 4);  // 32 digits, 4 dashes
    for (char c : uuid) {
      ASSERT_TRUE((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') ||
                  c == '-') << "Unexpected character: " << c;
    }

    // 4 dashes
    ASSERT_EQ(std::count(&uuid[0], &uuid[0] + uuid.size(), '-'), 4);

    // At indices 8, 13, 18 and 23
    ASSERT_EQ(uuid[8], '-');
    ASSERT_EQ(uuid[13], '-');
    ASSERT_EQ(uuid[18], '-');
    ASSERT_EQ(uuid[23], '-');

    // A '4' at index 14
    ASSERT_EQ(uuid[14], '4');

    // A '8', '9', 'A' or 'B' at index 19
    ASSERT_TRUE(uuid[19] == '8' || uuid[19] == '9' ||
                uuid[19] == 'a' || uuid[19] == 'b')
        << "Unexpected character: " << uuid[19] << ", wanted 8, 9, a or b";

    uuids.insert(uuid);
  }

  EXPECT_EQ(uuids.size(), kNumUUIDs)
      << "Detected UUID collision.";
}

TEST(UUID4Test, TestSeedsDifferent) {
  // Check seeds are different when called at different times.
  EXPECT_NE(falken::core::UUIDGen::GetFreshSeed("seed"),
            falken::core::UUIDGen::GetFreshSeed("seed"));
  // Check seeds are different when called at the same time.
  EXPECT_NE(falken::core::UUIDGen::GetFreshSeed("seed", 10),
            falken::core::UUIDGen::GetFreshSeed("seed", 10));
}

}  // namespace
