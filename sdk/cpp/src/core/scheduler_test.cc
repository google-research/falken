/*
 * Copyright 2018 Google LLC
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

#include "src/core/scheduler.h"

#include <atomic>
#include <chrono>  // NOLINT(build/c++11)
#include <functional>
#include <future>  // NOLINT(build/c++11)
#include <iostream>
#include <list>
#include <memory>
#include <mutex>  // NOLINT(build/c++11)

#include "src/core/callback.h"
#include "src/core/semaphore.h"
#include "gtest/gtest.h"
#include "absl/time/time.h"

using falken::core::RequestHandle;
using falken::core::callback::Callback;
using falken::core::callback::CallbackValue1;
using falken::core::callback::CallbackVoid;

using falken::core::Scheduler;
using falken::core::Semaphore;

using ActionFunction = std::function<void()>;

namespace falken {

class SchedulerTest : public ::testing::Test {
 protected:
  SchedulerTest() {}

  void SetUp() override {
    atomic_count_.store(0);
    while (callback_sem1_.TryWait()) {
    }
    while (callback_sem2_.TryWait()) {
    }
    ordered_value_.clear();
    repeat_period_ms_ = std::chrono::milliseconds(0);
    repeat_countdown_ = std::chrono::milliseconds(0);
  }

  static void SemaphorePost1() { callback_sem1_.Post(); }

  static void AddCount() {
    atomic_count_.fetch_add(1);
    callback_sem1_.Post();
  }

  static void AddValueInOrder(int v) {
    ordered_value_.push_back(v);
    callback_sem1_.Post();
  }

  static void RecursiveCallback(Scheduler* scheduler) {
    callback_sem1_.Post();
    --repeat_countdown_;

    std::unique_ptr<Callback> cb = std::make_unique<CallbackValue1<Scheduler*>>(
        scheduler, RecursiveCallback);

    if (repeat_countdown_ > std::chrono::milliseconds(0)) {
      scheduler->Schedule(cb, repeat_period_ms_);
    }
  }

  static std::atomic_int atomic_count_;
  static Semaphore callback_sem1_;
  static Semaphore callback_sem2_;
  static std::vector<int> ordered_value_;
  static std::chrono::milliseconds repeat_period_ms_;
  static std::chrono::milliseconds repeat_countdown_;

  Scheduler scheduler_;
};

std::atomic_int SchedulerTest::atomic_count_(0);
Semaphore SchedulerTest::callback_sem1_(0);      // NOLINT
Semaphore SchedulerTest::callback_sem2_(0);      // NOLINT
std::vector<int> SchedulerTest::ordered_value_;  // NOLINT
std::chrono::milliseconds SchedulerTest::repeat_period_ms_ =
    std::chrono::milliseconds(0);
std::chrono::milliseconds SchedulerTest::repeat_countdown_ =
    std::chrono::milliseconds(0);

// 10000 seems to be a good number to surface racing condition.
const int kThreadTestIteration = 10000;

TEST_F(SchedulerTest, Basic) {
  std::unique_ptr<Callback> cb1 =
      std::make_unique<CallbackVoid>(SemaphorePost1);
  scheduler_.Schedule(cb1);
  EXPECT_TRUE(callback_sem1_.TimedWait(std::chrono::seconds(1)));

  std::unique_ptr<Callback> cb2 =
      std::make_unique<CallbackVoid>(SemaphorePost1);
  scheduler_.Schedule(cb2, std::chrono::milliseconds(1));
  EXPECT_TRUE(callback_sem1_.TimedWait(std::chrono::seconds(1)));
}

TEST_F(SchedulerTest, TriggerOrderNoDelay) {
  std::vector<int> expected;
  for (int i = 0; i < kThreadTestIteration; ++i) {
    std::unique_ptr<Callback> cb =
        std::make_unique<CallbackValue1<int>>(i, AddValueInOrder);
    scheduler_.Schedule(cb);
    expected.push_back(i);
  }

  for (int i = 0; i < kThreadTestIteration; ++i) {
    EXPECT_TRUE(callback_sem1_.TimedWait(std::chrono::milliseconds(1000)));
  }
  EXPECT_EQ(expected, ordered_value_);
}

TEST_F(SchedulerTest, TriggerOrderSameDelay) {
  std::vector<int> expected;
  for (int i = 0; i < kThreadTestIteration; ++i) {
    std::unique_ptr<Callback> cb =
        std::make_unique<CallbackValue1<int>>(i, AddValueInOrder);
    scheduler_.Schedule(cb, std::chrono::milliseconds(1));
    expected.push_back(i);
  }

  for (int i = 0; i < kThreadTestIteration; ++i) {
    EXPECT_TRUE(callback_sem1_.TimedWait(std::chrono::milliseconds(1000)));
  }
  EXPECT_EQ(expected, ordered_value_);
}

TEST_F(SchedulerTest, TriggerOrderDifferentDelay) {
  std::vector<int> expected;
  for (int i = 0; i < 1000; ++i) {
    std::unique_ptr<Callback> cb =
        std::make_unique<CallbackValue1<int>>(i, AddValueInOrder);
    scheduler_.Schedule(cb, std::chrono::milliseconds(i));
    expected.push_back(i);
  }

  for (int i = 0; i < 1000; ++i) {
    EXPECT_TRUE(callback_sem1_.TimedWait(std::chrono::milliseconds(2000)));
  }

  EXPECT_EQ(expected, ordered_value_);
}

TEST_F(SchedulerTest, ExecuteDuringCallback) {
  std::unique_ptr<Callback> cb = std::make_unique<CallbackValue1<Scheduler*>>(
      &scheduler_, [](Scheduler* scheduler) {
        callback_sem1_.Post();
        std::unique_ptr<Callback> inner_cb =
            std::make_unique<CallbackValue1<Scheduler*>>(
                scheduler, [](Scheduler* scheduler) { callback_sem2_.Post(); });
        scheduler->Schedule(inner_cb);
      });

  scheduler_.Schedule(cb);

  EXPECT_TRUE(callback_sem1_.TimedWait(std::chrono::milliseconds(1000)));
  EXPECT_TRUE(callback_sem2_.TimedWait(std::chrono::milliseconds(1000)));
}

TEST_F(SchedulerTest, ScheduleDuringCallback1) {
  std::unique_ptr<Callback> cb = std::make_unique<CallbackValue1<Scheduler*>>(
      &scheduler_, [](Scheduler* scheduler) {
        callback_sem1_.Post();
        std::unique_ptr<Callback> inner_cb =
            std::make_unique<CallbackValue1<Scheduler*>>(
                scheduler, [](Scheduler* scheduler) { callback_sem2_.Post(); });
        scheduler->Schedule(inner_cb, std::chrono::milliseconds(1));
      });

  scheduler_.Schedule(cb, std::chrono::milliseconds(1));

  EXPECT_TRUE(callback_sem1_.TimedWait(std::chrono::milliseconds(1000)));
  EXPECT_TRUE(callback_sem2_.TimedWait(std::chrono::milliseconds(1000)));
}

TEST_F(SchedulerTest, ScheduleDuringCallback100) {
  std::unique_ptr<Callback> cb = std::make_unique<CallbackValue1<Scheduler*>>(
      &scheduler_, [](Scheduler* scheduler) {
        callback_sem1_.Post();
        std::unique_ptr<Callback> inner_cb =
            std::make_unique<CallbackValue1<Scheduler*>>(
                scheduler, [](Scheduler* scheduler) { callback_sem2_.Post(); });
        scheduler->Schedule(inner_cb, std::chrono::milliseconds(100));
      });

  scheduler_.Schedule(cb, std::chrono::milliseconds(100));

  EXPECT_TRUE(callback_sem1_.TimedWait(std::chrono::milliseconds(1000)));
  EXPECT_TRUE(callback_sem2_.TimedWait(std::chrono::milliseconds(1000)));
}

TEST_F(SchedulerTest, RecursiveCallbackNoInterval) {
  repeat_period_ms_ = std::chrono::milliseconds(0);
  repeat_countdown_ = std::chrono::milliseconds(1000);

  std::unique_ptr<Callback> cb = std::make_unique<CallbackValue1<Scheduler*>>(
      &scheduler_, RecursiveCallback);

  scheduler_.Schedule(cb, repeat_period_ms_);

  for (int i = 0; i < 1000; ++i) {
    EXPECT_TRUE(callback_sem1_.TimedWait(std::chrono::milliseconds(1000)));
  }
}

TEST_F(SchedulerTest, RecursiveCallbackWithInterval) {
  repeat_period_ms_ = std::chrono::milliseconds(10);
  repeat_countdown_ = std::chrono::milliseconds(5);

  std::unique_ptr<Callback> cb = std::make_unique<CallbackValue1<Scheduler*>>(
      &scheduler_, RecursiveCallback);

  scheduler_.Schedule(cb, repeat_period_ms_);

  for (int i = 0; i < 5; ++i) {
    EXPECT_TRUE(callback_sem1_.TimedWait(std::chrono::milliseconds(1000)));
  }
}

TEST_F(SchedulerTest, RepeatCallbackNoDelay) {
  std::unique_ptr<Callback> cb = std::make_unique<CallbackVoid>(SemaphorePost1);

  scheduler_.Schedule(cb, std::chrono::milliseconds(0),
                      std::chrono::milliseconds(1));

  // Wait for it to repeat 100 times
  for (int i = 0; i < 100; ++i) {
    EXPECT_TRUE(callback_sem1_.TimedWait(std::chrono::milliseconds(1000)));
  }
}

TEST_F(SchedulerTest, RepeatCallbackWithDelay) {
  std::chrono::milliseconds delay(100);
  std::unique_ptr<Callback> cb = std::make_unique<CallbackVoid>(SemaphorePost1);
  scheduler_.Schedule(cb, delay, std::chrono::milliseconds(1));

  auto start = std::chrono::system_clock::now();
  EXPECT_TRUE(callback_sem1_.TimedWait(std::chrono::milliseconds(1000)));
  auto end = std::chrono::system_clock::now();

  // Test if the first delay actually works.
  auto actual_delay = end - start;
  auto error = actual_delay - delay;
  std::cerr << "Delay: " << delay.count()
            << "ms. Actual delay: " << actual_delay.count()
            << " ms. Error: " << error.count() << " ms." << std::endl;
  EXPECT_TRUE(error < std::chrono::milliseconds(100));

  // Wait for it to repeat 100 times
  for (int i = 0; i < 100; ++i) {
    EXPECT_TRUE(callback_sem1_.TimedWait(std::chrono::milliseconds(1000)));
  }
}

TEST_F(SchedulerTest, CancelImmediateCallback) {
  auto test_func = [](int delay) {
    // Use standalone scheduler and counter
    Scheduler scheduler;
    std::atomic_int count(0);
    int success_cancel = 0;
    for (int i = 0; i < kThreadTestIteration; ++i) {
      std::unique_ptr<Callback> cb =
          std::make_unique<CallbackValue1<std::atomic_int*>>(
              &count, [](std::atomic_int* count) { count->fetch_add(1); });

      bool cancelled =
          scheduler.Schedule(cb, std::chrono::milliseconds(0)).Cancel();
      if (cancelled) {
        ++success_cancel;
      }
    }

    std::this_thread::sleep_for(std::chrono::milliseconds(10));

    // Does not guarantee 100% successful cancellation
    float success_rate = success_cancel * 100.0f / kThreadTestIteration;
    std::cerr << "[Delay " << delay
              << "ms] Cancel success rate: " << success_rate
              << " (And it is ok if not 100%%)" << std::endl;
    EXPECT_EQ(kThreadTestIteration, success_cancel + count.load());
  };

  // Test without delay
  test_func(0);

  // Test with delay
  test_func(1);
}

// This test can take around 5s ~ 30s depending on the platform
TEST_F(SchedulerTest, CancelRepeatCallback) {
  auto test_func = [](int delay, int repeat, int wait_repeat) {
    // Use standalone scheduler and counter for iterations
    Scheduler scheduler;
    std::atomic_int count(0);
    while (callback_sem1_.TryWait()) {
    }

    std::unique_ptr<Callback> cb =
        std::make_unique<CallbackValue1<std::atomic_int*>>(
            &count, [](std::atomic_int* count) {
              count->fetch_add(1);
              callback_sem1_.Post();
            });

    std::chrono::milliseconds delay_ms(delay);
    std::chrono::milliseconds repeat_ms(repeat);
    RequestHandle handler = scheduler.Schedule(cb, delay_ms, repeat_ms);
    EXPECT_FALSE(handler.IsCancelled());

    for (int i = 0; i < wait_repeat; ++i) {
      EXPECT_TRUE(callback_sem1_.TimedWait(std::chrono::milliseconds(1000)));
      EXPECT_TRUE(handler.IsTriggered());
    }

    // Cancellation of a repeat cb should always be successful, as long as
    // it is not cancelled yet
    EXPECT_TRUE(handler.Cancel());
    EXPECT_TRUE(handler.IsCancelled());
    EXPECT_FALSE(handler.Cancel());

    // Should have no more cb triggered after the cancellation
    int saved_count = count.load();

    std::this_thread::sleep_for(std::chrono::milliseconds(1));
    EXPECT_EQ(saved_count, count.load());
  };

  for (int i = 0; i < 1000; ++i) {
    // No delay and do not wait for the first trigger to cancel it
    test_func(0, 1, 0);
    // No delay and wait for the first trigger, then cancel it
    test_func(0, 1, 1);
    // 1ms delay and do not wait for the first trigger to cancel it
    test_func(1, 1, 0);
    // 1ms delay and wait for the first trigger, then cancel it
    test_func(1, 1, 1);
  }
}

TEST_F(SchedulerTest, CancelAll) {
  Scheduler scheduler;

  for (int i = 0; i < kThreadTestIteration; ++i) {
    std::unique_ptr<Callback> cb = std::make_unique<CallbackVoid>(AddCount);
    scheduler.Schedule(cb);
  }
  scheduler.CancelAllAndShutdownWorkerThread();
  // Does not guarantee 0% trigger rate
  float trigger_rate = atomic_count_.load() * 100.0f / kThreadTestIteration;
  std::cerr << "Callback trigger rate: " << trigger_rate
            << "(And it is ok if not 0%%)" << std::endl;
}

TEST_F(SchedulerTest, DeleteScheduler) {
  for (int i = 0; i < kThreadTestIteration; ++i) {
    Scheduler scheduler;
    std::unique_ptr<Callback> cb = std::make_unique<CallbackVoid>(AddCount);
    scheduler.Schedule(cb);
  }

  // Does not guarantee 0% trigger rate
  float trigger_rate = atomic_count_.load() * 100.0f / kThreadTestIteration;
  std::cerr << "Callback trigger rate: " << trigger_rate
            << "(And it is ok if not 0%%)" << std::endl;
}

TEST_F(SchedulerTest, SyncCancelAll) {
  Scheduler scheduler;

  auto first_task = []() {
    callback_sem1_.Post();
    callback_sem2_.Wait();
  };

  // schedule the synchronization task that makes sure the scheduler worker
  // tread is active when we call CancelAllAndShutdownWorkerThread
  {
    std::unique_ptr<Callback> cb = std::make_unique<CallbackVoid>(first_task);
    scheduler.Schedule(cb);
  }

  // add a repeat task to the mix, which should never get to be executed
  {
    std::unique_ptr<Callback> cb = std::make_unique<CallbackVoid>(AddCount);
    scheduler.Schedule(cb, std::chrono::seconds(10), std::chrono::seconds(1));
  }

  // add the rest of the tasks for immediate execution
  for (int i = 0; i < kThreadTestIteration; ++i) {
    std::unique_ptr<Callback> cb = std::make_unique<CallbackVoid>(AddCount);
    scheduler.Schedule(cb);
  }

  // wait for the sync task to activate
  callback_sem1_.Wait();

  // cancel all tasks in a separate thread (because
  // CancelAllAndShutdownWorkerThread is blocking)
  auto cancel_future = std::async(std::launch::async, [&scheduler]() {
    scheduler.CancelAllAndShutdownWorkerThread(true);
  });

  // need to wait for the cancel thread to call CancelAllAndShutdownWorkerThread
  std::this_thread::sleep_for(std::chrono::seconds(1));

  // signal sync task to continue
  callback_sem2_.Post();

  // Join with the cancel thread
  cancel_future.wait();

  // All of the non-repeat tasks should have been activated before cancelling
  ASSERT_EQ(kThreadTestIteration, atomic_count_.load());
}

TEST_F(SchedulerTest, AsyncCancelAll) {
  Scheduler scheduler;

  auto first_task = []() {
    callback_sem1_.Post();
    callback_sem2_.Wait();
  };

  // schedule the synchronization task that makes sure the scheduler worker
  // tread is active when we call CancelAllAndShutdownWorkerThread
  {
    std::unique_ptr<Callback> cb = std::make_unique<CallbackVoid>(first_task);
    scheduler.Schedule(cb);
  }

  // add a repeat task to the mix, which should never get to be executed
  {
    std::unique_ptr<Callback> cb = std::make_unique<CallbackVoid>(AddCount);
    scheduler.Schedule(cb, std::chrono::seconds(10), std::chrono::seconds(1));
  }

  // add the rest of the tasks for immediate execution
  for (int i = 0; i < kThreadTestIteration; ++i) {
    std::unique_ptr<Callback> cb = std::make_unique<CallbackVoid>(AddCount);
    scheduler.Schedule(cb);
  }

  // wait for the sync task to activate
  callback_sem1_.Wait();

  // cancel all tasks in a separate thread (because
  // CancelAllAndShutdownWorkerThread is blocking)
  auto cancel_future = std::async(std::launch::async, [&scheduler]() {
    scheduler.CancelAllAndShutdownWorkerThread(false);
  });

  // need to wait for the cancel thread to call CancelAllAndShutdownWorkerThread
  std::this_thread::sleep_for(std::chrono::seconds(1));

  // signal sync task to continue
  callback_sem2_.Post();

  // Join with the cancel thread
  cancel_future.wait();

  // None of the tasks should have been activated before cancelling
  ASSERT_EQ(0, atomic_count_.load());
}

}  // namespace falken
