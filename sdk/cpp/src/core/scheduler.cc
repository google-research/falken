#include "src/core/scheduler.h"

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

#include <cassert>
#include <chrono>  // NOLINT(build/c++11)
#include <memory>
#include <mutex>  // NOLINT(build/c++11)
#include <utility>

#include "src/core/callback.h"

namespace falken {
namespace core {

bool RequestHandle::Cancel() {
  assert(status_);

  if (!IsValid()) {
    return false;
  }

  std::lock_guard<std::mutex> lock(status_->mutex);
  if (status_->cancelled || (!status_->repeat && status_->triggered)) {
    return false;
  }

  status_->cancelled = true;
  return true;
}

bool RequestHandle::IsCancelled() const {
  assert(status_);
  std::lock_guard<std::mutex> lock(status_->mutex);
  return status_->cancelled;
}

bool RequestHandle::IsTriggered() const {
  assert(status_);
  std::lock_guard<std::mutex> lock(status_->mutex);
  return status_->triggered;
}

Scheduler::RequestData::RequestData(
    RequestId id, std::unique_ptr<Callback>& callback,
    ScheduleTimeMs delay, ScheduleTimeMs repeat)
    : id(id),
      cb(std::move(callback)),
      delay_ms(delay),
      repeat_ms(repeat),
      due_timestamp(std::chrono::system_clock::now()),
      status(new RequestStatusBlock(repeat > std::chrono::milliseconds(0))) {}

Scheduler::Scheduler()
    : thread_(nullptr),
      next_request_id_(0),
      terminating_(false),
      synchronous_stop_(false),
      sleep_sem_(0) {}

Scheduler::~Scheduler() { CancelAllAndShutdownWorkerThread(); }

void Scheduler::CancelAllAndShutdownWorkerThread(bool synchronous_stop) {
  {
    // Notify the worker thread to stop processing anymore requests.
    std::lock_guard<std::mutex> lock(request_mutex_);
    if (terminating_) return;
    terminating_ = true;
    synchronous_stop_ = synchronous_stop;
  }

  // Signal the thread to wake if it is sleeping due to no callbacks in queue
  sleep_sem_.Post();

  if (thread_) {
    thread_->join();
    thread_.reset();
  }
}

RequestHandle Scheduler::Schedule(std::unique_ptr<Callback>& callback,
                                  ScheduleTimeMs delay /* = 0 */,
                                  ScheduleTimeMs repeat /* = 0 */) {
  assert(callback);

  std::lock_guard<std::mutex> lock(request_mutex_);

  if (!thread_ && !terminating_) {
    thread_ =
        std::make_shared<std::thread>(&Scheduler::WorkerThreadRoutine, this);
  }

  RequestDataPtr request = std::make_shared<RequestData>(
      ++next_request_id_, callback, delay, repeat);

  RequestHandle handler(request->status);
  auto current_time = std::chrono::system_clock::now();

  AddToQueue(std::move(request), current_time, delay);

  // Increase semaphore count by one for unfinished request
  sleep_sem_.Post();

  return handler;
}

void Scheduler::WorkerThreadRoutine(void* data) {
  Scheduler* scheduler = static_cast<Scheduler*>(data);
  assert(scheduler);

  while (true) {
    auto current = std::chrono::system_clock::now();

    std::chrono::nanoseconds sleep_time(0);
    RequestDataPtr request;

    // Check if the top request in the queue is due.
    {
      std::lock_guard<std::mutex> lock(scheduler->request_mutex_);
      if (!scheduler->request_queue_.empty()) {
        auto due = scheduler->request_queue_.top()->due_timestamp;
        if (due <= current) {
          request = scheduler->request_queue_.top();
          scheduler->request_queue_.pop();
        } else {
          sleep_time = due - current;
        }
      }

      // On asynchronous stop, stop right now
      // On synchronous stop, stop when there's nothing ready for execution
      if (scheduler->terminating_ &&
          (!scheduler->synchronous_stop_ || !request)) {
        return;
      }
    }

    // If there is no request to process now, there can be 2 cases
    // 1. The queue is empty -> Wait forever
    // 2. The top request in the queue is not due yet.
    if (!request) {
      if (sleep_time > std::chrono::nanoseconds{0}) {
        scheduler->sleep_sem_.TimedWait(sleep_time);
      } else {
        scheduler->sleep_sem_.Wait();
      }

      // Drain the semaphore after wake
      while (scheduler->sleep_sem_.TryWait()) {
      }
    }

    // If the top request is due, trigger the callback.  If the repeat interval
    // is non-zero, move it back to queue.
    if (request && scheduler->TriggerCallback(request)) {
      std::lock_guard<std::mutex> lock(scheduler->request_mutex_);
      ScheduleTimeMs repeat = request->repeat_ms;
      scheduler->AddToQueue(request, current, repeat);
    }
  }
}

void Scheduler::AddToQueue(
    RequestDataPtr request,
    std::chrono::time_point<std::chrono::system_clock> current,
    ScheduleTimeMs after) {
  // Calculate the future timestamp
  request->due_timestamp = current + std::chrono::milliseconds(after);

  // Push the request to the priority queue
  request_queue_.push(request);
}

bool Scheduler::TriggerCallback(const RequestDataPtr& request) {
  std::lock_guard<std::mutex> lock(request->status->mutex);
  if (request->cb && !request->status->cancelled) {
    request->cb->Run();
    request->status->triggered = true;

    // return true if this callback repeats and should be push back to the queue
    if (request->repeat_ms > std::chrono::milliseconds(0)) {
      return true;
    }
  }

  return false;
}

}  // namespace core
}  // namespace falken
