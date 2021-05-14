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

#include "src/core/callback.h"

#include <memory>
#include <string>
#include <utility>

#include "gtest/gtest.h"

using falken::core::callback::AddCallback;
using falken::core::callback::CallbackMoveValue1;
using falken::core::callback::CallbackStdFunction;
using falken::core::callback::CallbackString;
using falken::core::callback::CallbackString2Value1;
using falken::core::callback::CallbackValue1;
using falken::core::callback::CallbackValue1String1;
using falken::core::callback::CallbackValue2;
using falken::core::callback::CallbackValue2String1;
using falken::core::callback::CallbackVoid;
using falken::core::callback::Initialize;
using falken::core::callback::IsInitialized;
using falken::core::callback::PollCallbacks;
using falken::core::callback::RemoveCallback;
using falken::core::callback::Terminate;

namespace firebase {
class CallbackTest : public ::testing::Test {
 protected:
  CallbackTest() {}

  void SetUp() override {
    callback_void_count_ = 0;
    callback1_count_ = 0;
    callback_value1_sum_ = 0;
    callback_value1_ordered_.clear();
    callback_value2_sum_ = 0;
    callback_string_.clear();
    value_and_string_ = std::pair<int, std::string>();
  }

  void TearDown() override { Terminate(true); }

  // Counts callbacks from callback::CallbackVoid.
  static void CountCallbackVoid() { callback_void_count_++; }
  // Counts callbacks from callback::Callback1.
  static void CountCallback1(void* test) {
    CallbackTest* callback_test = *(static_cast<CallbackTest**>(test));
    callback_test->callback1_count_++;
  }
  // Adds the value passed to CallbackValue1 to callback_value1_sum_.
  static void SumCallbackValue1(int value) { callback_value1_sum_ += value; }

  // Add the value passed to CallbackValue1 to callback_value1_ordered_.
  static void OrderedCallbackValue1(int value) {
    callback_value1_ordered_.push_back(value);
  }

  // Multiplies values passed to CallbackValue2 and adds them to
  // callback_value2_sum_.
  static void SumCallbackValue2(char value1, int value2) {
    callback_value2_sum_ += value1 * value2;
  }

  // Appends the string passed to this method to callback_string_.
  static void AggregateCallbackString(const char* str) {
    callback_string_ += str;
  }

  // Stores this function's arguments in value_and_string_.
  static void StoreValueAndString(int value, const char* str) {
    value_and_string_ = std::pair<int, std::string>(value, str);
  }

  // Stores the value argument in value_and_string_.first, then appends the
  // two string arguments and assign to value_and_string_.second,
  static void StoreValueAndString2(const char* str1, const char* str2,
                                   int value) {
    value_and_string_ = std::pair<int, std::string>(
        value, std::string(str1) + std::string(str2));
  }

  // Stores the sum of value1 and value2 in value_and_string_.first and the
  // string argumene in value_and_string_.second.
  static void StoreValue2AndString(char value1, int value2, const char* str) {
    value_and_string_ = std::pair<int, std::string>(value1 + value2, str);
  }

  // Adds the value passed to CallbackMoveValue1 to callback_value1_sum_.
  static void SumCallbackMoveValue1(std::unique_ptr<int>* value) {
    callback_value1_sum_ += **value;
  }

  int callback1_count_;

  static int callback_void_count_;
  static int callback_value1_sum_;
  static std::vector<int> callback_value1_ordered_;
  static int callback_value2_sum_;
  static std::string callback_string_;
  static std::pair<int, std::string> value_and_string_;
};

int CallbackTest::callback_value1_sum_;
std::vector<int> CallbackTest::callback_value1_ordered_;  // NOLINT
int CallbackTest::callback_value2_sum_;
int CallbackTest::callback_void_count_;
std::string CallbackTest::callback_string_;                   // NOLINT
std::pair<int, std::string> CallbackTest::value_and_string_;  // NOLINT

// Verify initialize and terminate setup and tear down correctly.
TEST_F(CallbackTest, TestInitializeAndTerminate) {
  EXPECT_FALSE(IsInitialized());
  Initialize();
  EXPECT_TRUE(IsInitialized());
  Terminate(false);
  EXPECT_FALSE(IsInitialized());
}

// Verify Terminate() is a no-op if the API isn't initialized.
TEST_F(CallbackTest, TestTerminateWithoutInitialization) {
  EXPECT_FALSE(IsInitialized());
  Terminate(false);
  EXPECT_FALSE(IsInitialized());
}

// Add a callback to the queue then terminate the API.
TEST_F(CallbackTest, AddCallbackNoInitialization) {
  EXPECT_FALSE(IsInitialized());
  AddCallback(new CallbackVoid(CountCallbackVoid));
  EXPECT_TRUE(IsInitialized());
  Terminate(false);
  EXPECT_FALSE(IsInitialized());
}

// Flush all callbacks.
TEST_F(CallbackTest, AddCallbacksTerminateAndFlush) {
  EXPECT_FALSE(IsInitialized());
  AddCallback(new CallbackVoid(CountCallbackVoid));
  EXPECT_TRUE(IsInitialized());
  PollCallbacks();
  AddCallback(new CallbackVoid(CountCallbackVoid));
  Terminate(true);
  EXPECT_FALSE(IsInitialized());
  PollCallbacks();
  EXPECT_EQ(1, callback_void_count_);
  EXPECT_FALSE(IsInitialized());
}

// Add a callback to the queue, then remove it.  This should result in
// initializing the callback API then tearing it down when the queue is empty.
TEST_F(CallbackTest, AddRemoveCallback) {
  EXPECT_FALSE(IsInitialized());
  void* callback_reference = AddCallback(new CallbackVoid(CountCallbackVoid));
  EXPECT_TRUE(IsInitialized());
  RemoveCallback(callback_reference);
  PollCallbacks();
  EXPECT_FALSE(IsInitialized());
  EXPECT_EQ(0, callback_void_count_);
}

// Call a void callback.
TEST_F(CallbackTest, CallVoidCallback) {
  AddCallback(new CallbackVoid(CountCallbackVoid));
  PollCallbacks();
  EXPECT_EQ(1, callback_void_count_);
  EXPECT_FALSE(IsInitialized());
}

// Call two void callbacks.
TEST_F(CallbackTest, CallTwoVoidCallbacks) {
  AddCallback(new CallbackVoid(CountCallbackVoid));
  AddCallback(new CallbackVoid(CountCallbackVoid));
  PollCallbacks();
  EXPECT_EQ(2, callback_void_count_);
  EXPECT_FALSE(IsInitialized());
}

// Call three void callbacks with a poll between them.
TEST_F(CallbackTest, CallOneVoidCallbackPollTwo) {
  AddCallback(new CallbackVoid(CountCallbackVoid));
  PollCallbacks();
  EXPECT_EQ(1, callback_void_count_);
  AddCallback(new CallbackVoid(CountCallbackVoid));
  AddCallback(new CallbackVoid(CountCallbackVoid));
  PollCallbacks();
  EXPECT_EQ(3, callback_void_count_);
  EXPECT_FALSE(IsInitialized());
}

// Call 2, 1 argument callbacks.
TEST_F(CallbackTest, TestCallCallback1) {
  AddCallback(new falken::core::callback::Callback1<CallbackTest*>(
      this, CountCallback1));
  AddCallback(new falken::core::callback::Callback1<CallbackTest*>(
      this, CountCallback1));
  PollCallbacks();
  EXPECT_EQ(2, callback1_count_);
  EXPECT_FALSE(falken::core::callback::IsInitialized());
}

// Call a callback passing the argument by value.
TEST_F(CallbackTest, CallCallbackValue1) {
  AddCallback(new CallbackValue1<int>(10, SumCallbackValue1));
  AddCallback(new CallbackValue1<int>(5, SumCallbackValue1));
  PollCallbacks();
  EXPECT_EQ(15, callback_value1_sum_);
  EXPECT_FALSE(IsInitialized());
}

// Ensure callbacks are executed in the order they're added to the queue.
TEST_F(CallbackTest, CallCallbackValue1Ordered) {
  AddCallback(new CallbackValue1<int>(10, OrderedCallbackValue1));
  AddCallback(new CallbackValue1<int>(5, OrderedCallbackValue1));
  PollCallbacks();
  std::vector<int> expected;
  expected.push_back(10);
  expected.push_back(5);
  EXPECT_EQ(expected, callback_value1_ordered_);
}

// Schedule 3 callbacks, removing the middle one from the queue.
TEST_F(CallbackTest, ScheduleThreeCallbacksRemoveOne) {
  AddCallback(new CallbackValue1<int>(1, SumCallbackValue1));
  void* reference = AddCallback(new CallbackValue1<int>(2, SumCallbackValue1));
  AddCallback(new CallbackValue1<int>(4, SumCallbackValue1));
  RemoveCallback(reference);
  PollCallbacks();
  EXPECT_EQ(5, callback_value1_sum_);
  EXPECT_FALSE(IsInitialized());
}

// Call a callback passing two arguments by value.
TEST_F(CallbackTest, CallCallbackValue2) {
  AddCallback(new CallbackValue2<char, int>(10, 4, SumCallbackValue2));
  AddCallback(new CallbackValue2<char, int>(20, 3, SumCallbackValue2));
  PollCallbacks();
  EXPECT_EQ(100, callback_value2_sum_);
  EXPECT_FALSE(IsInitialized());
}

// Call a callback passing a string by value.
TEST_F(CallbackTest, CallCallbackString) {
  AddCallback(new CallbackString("testing", AggregateCallbackString));
  AddCallback(new CallbackString("123", AggregateCallbackString));
  PollCallbacks();
  EXPECT_EQ("testing123", callback_string_);
  EXPECT_FALSE(IsInitialized());
}
// Call a callback passing a value and string by value.
TEST_F(CallbackTest, CallCallbackValue1String1) {
  AddCallback(new CallbackValue1String1<int>(10, "ten", StoreValueAndString));
  PollCallbacks();
  EXPECT_EQ(10, value_and_string_.first);
  EXPECT_EQ("ten", value_and_string_.second);
}

// Call a callback passing a value and two strings by value.
TEST_F(CallbackTest, CallCallbackString2Value1) {
  AddCallback(new CallbackString2Value1<int>("evening", "all", 11,
                                             StoreValueAndString2));
  PollCallbacks();
  EXPECT_EQ(11, value_and_string_.first);
  EXPECT_EQ("eveningall", value_and_string_.second);
}

// Call a callback passing two values and a string by value.
TEST_F(CallbackTest, CallCallbackValue2String1) {
  AddCallback(new CallbackValue2String1<char, int>(11, 31, "meaning",
                                                   StoreValue2AndString));
  PollCallbacks();
  EXPECT_EQ(42, value_and_string_.first);
  EXPECT_EQ("meaning", value_and_string_.second);
}

// Call a callback passing the UniquePtr
TEST_F(CallbackTest, CallCallbackMoveValue1) {
  AddCallback(new CallbackMoveValue1<std::unique_ptr<int>>(
      std::make_unique<int>(10), SumCallbackMoveValue1));
  std::unique_ptr<int> ptr(new int(5));
  AddCallback(new CallbackMoveValue1<std::unique_ptr<int>>(
      std::move(ptr), SumCallbackMoveValue1));
  PollCallbacks();
  EXPECT_EQ(15, callback_value1_sum_);
  EXPECT_FALSE(IsInitialized());
}

// Call a callback which wraps std::function
TEST_F(CallbackTest, CallCallbackStdFunction) {
  int count = 0;
  std::function<void()> callback = [&count]() { count++; };

  AddCallback(new CallbackStdFunction(callback));
  PollCallbacks();
  EXPECT_EQ(1, count);
  AddCallback(new CallbackStdFunction(callback));
  AddCallback(new CallbackStdFunction(callback));
  PollCallbacks();
  EXPECT_EQ(3, count);
  EXPECT_FALSE(IsInitialized());
}

// Ensure callbacks are executed in the order they're added to the queue with
// callbacks added to a different thread to the dispatching thread.
// Also, make sure it's possible to remove a callback from the queue while
// executing a callback.
TEST_F(CallbackTest, ThreadedCallbackValue1Ordered) {
  bool running = true;
  void* callback_entry_to_remove = nullptr;
  std::thread pollingThread(
      [](void* arg) -> void {
        volatile bool* running_ptr = static_cast<bool*>(arg);
        while (*running_ptr) {
          PollCallbacks();
          // Wait 20ms.
          std::this_thread::sleep_for(std::chrono::milliseconds(20));
        }
      },
      &running);
  std::thread addCallbacksThread(
      [](void* arg) -> void {
        void** callback_entry_to_remove_ptr = static_cast<void**>(arg);
        AddCallback(new CallbackValue1<int>(1, OrderedCallbackValue1));
        AddCallback(new CallbackValue1<int>(2, OrderedCallbackValue1));
        // Adds a callback which removes the entry referenced by
        // callback_entry_to_remove.
        AddCallback(new CallbackValue1<void**>(
            callback_entry_to_remove_ptr, [](void** callback_entry) -> void {
              RemoveCallback(*callback_entry);
            }));
        *callback_entry_to_remove_ptr =
            AddCallback(new CallbackValue1<int>(4, OrderedCallbackValue1));
        AddCallback(new CallbackValue1<int>(5, OrderedCallbackValue1));
      },
      &callback_entry_to_remove);
  addCallbacksThread.join();
  AddCallback(new CallbackValue1<volatile bool*>(
      &running, [](volatile bool* running_ptr) { *running_ptr = false; }));
  pollingThread.join();
  std::vector<int> expected;
  expected.push_back(1);
  expected.push_back(2);
  expected.push_back(5);
  EXPECT_EQ(expected, callback_value1_ordered_);
}

TEST_F(CallbackTest, NewCallbackTest) {
  AddCallback(falken::core::callback::NewCallback(SumCallbackValue1, 1));
  AddCallback(falken::core::callback::NewCallback(SumCallbackValue1, 2));
  AddCallback(falken::core::callback::NewCallback(SumCallbackValue2,
                                                  static_cast<char>(1), 10));
  AddCallback(falken::core::callback::NewCallback(SumCallbackValue2,
                                                  static_cast<char>(2), 100));
  AddCallback(
      falken::core::callback::NewCallback(AggregateCallbackString, "Hello, "));
  AddCallback(
      falken::core::callback::NewCallback(AggregateCallbackString, "World!"));
  PollCallbacks();
  EXPECT_EQ(3, callback_value1_sum_);
  EXPECT_EQ(210, callback_value2_sum_);
  EXPECT_EQ("Hello, World!", callback_string_);
  EXPECT_FALSE(IsInitialized());
}

TEST_F(CallbackTest, AddCallbackWithThreadCheckTest) {
  // When PollCallbacks() is called in previous test, g_callback_thread_id
  // would be set to current thread which runs the tests.  We want it to be
  // set to a different thread id in the beginning of this test.
  std::thread changeThreadIdThread([]() {
    AddCallback(new CallbackVoid([]() {}));
    PollCallbacks();
  });
  changeThreadIdThread.join();
  EXPECT_FALSE(IsInitialized());

  void* entry_non_null =
      AddCallbackWithThreadCheck(new CallbackVoid(CountCallbackVoid));
  EXPECT_TRUE(entry_non_null != nullptr);
  EXPECT_EQ(0, callback_void_count_);
  EXPECT_TRUE(IsInitialized());

  PollCallbacks();
  EXPECT_EQ(1, callback_void_count_);
  EXPECT_FALSE(IsInitialized());

  // Once PollCallbacks() is called on this thread,
  // AddCallbackWithThreadCheck() should run the callback immediately and
  // return nullptr.
  void* entry_null =
      AddCallbackWithThreadCheck(new CallbackVoid(CountCallbackVoid));
  EXPECT_EQ(nullptr, entry_null);
  EXPECT_EQ(2, callback_void_count_);
  EXPECT_FALSE(IsInitialized());

  PollCallbacks();
  EXPECT_EQ(2, callback_void_count_);
  EXPECT_FALSE(IsInitialized());
}

TEST_F(CallbackTest, CallbackDeadlockTest) {
  // This is to test the deadlock scenario when CallbackEntry::Execute() and
  // CallbackEntry::DisableCallback() are called at the same time.
  // Ex. given a user mutex "user_mutex"
  // GC thread: lock(user_mutex) -> lock(CallbackEntry::mutex_)
  // Polling thread: lock(CallbackEntry::mutex_) -> lock(user_mutex)
  // If both threads successfully obtain the first lock, a deadlock could
  // occur. CallbackEntry::mutex_ should be released while running the
  // callback.

  struct DeadlockData {
    std::mutex user_mutex;
    void* handle;
  };

  for (int i = 0; i < 1000; ++i) {
    DeadlockData data;

    data.handle = AddCallback(
        new CallbackValue1<DeadlockData*>(&data, [](DeadlockData* data) {
          std::lock_guard<std::mutex> lock(data->user_mutex);
          data->handle = nullptr;
        }));

    std::thread pollingThread([]() { PollCallbacks(); });

    std::thread gcThread(
        [](void* arg) {
          DeadlockData* data = static_cast<DeadlockData*>(arg);
          std::lock_guard<std::mutex> lock(data->user_mutex);
          if (data->handle) {
            RemoveCallback(data->handle);
          }
        },
        &data);

    pollingThread.join();
    gcThread.join();
    EXPECT_FALSE(IsInitialized());
  }
}

}  // namespace firebase
