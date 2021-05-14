/*
 * Copyright 2017 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "src/core/semaphore.h"

#include <chrono>  // NOLINT(build/c++11)
#include <functional>
#include <memory>
#include <mutex>   // NOLINT(build/c++11)
#include <thread>  // NOLINT(build/c++11)

#include "gtest/gtest.h"
#include "absl/time/time.h"

using falken::core::Semaphore;

using ActionFunction = std::function<void()>;

namespace falken {

class SemaphoreTest : public ::testing::Test {
 public:
  void SetUp() override {}
};

// Check creation and destruction of the object.
TEST_F(SemaphoreTest, QueueCreateAndDestruct) {
  auto uut_ = std::make_unique<Semaphore>();
  uut_.reset();
  EXPECT_FALSE(uut_);
}

// Basic test of TryWait, to make sure that its successes and failures
// line up with what we'd expect, based on the initial count.
TEST_F(SemaphoreTest, TryWaitTests) {
  Semaphore sem(2);

  // First time, should be able to get a value just fine.
  EXPECT_TRUE(sem.TryWait());

  // Second time, should still be able to get a value.
  EXPECT_TRUE(sem.TryWait());

  // Third time, we should be unable to acquire a lock.
  EXPECT_FALSE(sem.TryWait());

  sem.Post();

  // Should be able to get a lock now.
  EXPECT_TRUE(sem.TryWait());
}

// Test that semaphores work across threads.
// Blocks, after setting a thread to unlock itself in 1 second.
// If the thread doesn't unblock it, it will wait forever, triggering a test
// failure via timeout after 60 seconds, through the testing framework.
TEST_F(SemaphoreTest, MultithreadedTest) {
  Semaphore sem;
  std::chrono::milliseconds delay_(500);

  std::thread t1([&] {
    std::this_thread::sleep_for(delay_);
    sem.Post();
  });
  t1.detach();

  // This will block, until the thread releases it.
  auto before = std::chrono::system_clock::now();
  sem.Wait();
  auto after = std::chrono::system_clock::now();

  // uut_ must at least wait the same amount of time as the thread.
  EXPECT_LT(delay_.count(), (after - before).count());
}

// Tests that Timed Wait works as intended.
TEST_F(SemaphoreTest, TimedWait) {
  Semaphore sem(0);
  std::chrono::milliseconds delay(500);

  auto start_ms = std::chrono::system_clock::now();
  EXPECT_FALSE(sem.TimedWait(delay));
  auto finish_ms = std::chrono::system_clock::now();
  // uut_ should wait the amount of time requested.
  EXPECT_LT(delay, finish_ms - start_ms);

  sem.Post();
  start_ms = std::chrono::system_clock::now();
  EXPECT_TRUE(sem.TimedWait(delay));
  finish_ms = std::chrono::system_clock::now();
  // uut_ should return inmediatly.
  EXPECT_GT(std::chrono::milliseconds(1), (finish_ms - start_ms));
}

// Executes multiple notifications while waiting for them.
TEST_F(SemaphoreTest, MultithreadedStressTest) {
  Semaphore sem(0);

  for (int i = 0; i < 10000; ++i) {
    std::thread thread([&] { sem.Post(); });
    // This will block, until the thread releases it or it times out.
    EXPECT_TRUE(sem.TimedWait(std::chrono::milliseconds(100)));

    thread.join();
  }
}

}  // namespace falken
