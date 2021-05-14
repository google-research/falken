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

#ifndef FALKEN_SDK_CORE_SEMAPHORE_H_
#define FALKEN_SDK_CORE_SEMAPHORE_H_

#include <condition_variable>  // NOLINT(build/c++11)
#include <mutex>               // NOLINT(build/c++11)

namespace falken {
namespace core {

class Semaphore {
 public:
  /**
   * @brief Constructor of the class
   * @param [in] count starting count of the semaphore
   */
  explicit Semaphore(int count = 0) : count_{count} {}

  /**
   * @brief Increase the count of notifications of the semaphore
   */
  void Post() {
    std::unique_lock<std::mutex> lock(mutex_);
    ++count_;
    condition_variable_.notify_one();
  }

  /**
   * @brief Blocks the thread waiting for a notification.
   */
  void Wait() {
    std::unique_lock<std::mutex> lock(mutex_);
    condition_variable_.wait(lock, [&](){return count_ != 0;});
    --count_;
  }

  /**
   * @brief Tries to consume a notification without waiting.
   * @return true if it was able to consume a notification.
   */
  bool TryWait() {
    std::unique_lock<std::mutex> lock(mutex_);
    return TryConsume();
  }

  /**
   * @brief Blocks the thread a specific amount of time, waiting
   * for notifications.
   * @param [in] wait_time amount of time to wait for the notification.
   * @return true if it was able to consume a notification.
   */
  template <class Rep, class Period>
  bool TimedWait(std::chrono::duration<Rep, Period> wait_time) {
    std::unique_lock<std::mutex> lck(mutex_);
    if (!TryConsume()) {
      condition_variable_.wait_for(lck, wait_time);
      // Try to claim a notification.
      return TryConsume();
    }
    return true;
  }

 private:
  std::mutex mutex_;
  std::condition_variable condition_variable_;
  int count_;

  // Mutex must be held in order to call this method.
  bool TryConsume() {
    if (count_) {
      --count_;
      return true;
    }
    return false;
  }
};

}  // namespace core
}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_SEMAPHORE_H_
