#ifndef FALKEN_SDK_CORE_SCHEDULER_H_
#define FALKEN_SDK_CORE_SCHEDULER_H_

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

#include <functional>
#include <memory>
#include <mutex>  // NOLINT(build/c++11)
#include <queue>
#include <thread>  // NOLINT(build/c++11)

#include "src/core/callback.h"
#include "src/core/semaphore.h"


namespace falken {
namespace core {

using falken::core::callback::Callback;

typedef std::chrono::milliseconds ScheduleTimeMs;

// RequestStatusBlock contains the status of a request.  References to this
// block are shared by the queued request and the request handle.  The contents
// of this structure are potentially modified from different thread, hence
// guarded by mutex.
struct RequestStatusBlock {
  explicit RequestStatusBlock(bool repeat)
      : cancelled(false), triggered(false), repeat(repeat) {}

  // Guard both "cancelled" and "triggered"
  std::mutex mutex;

  // Whether the callback is properly cancelled
  bool cancelled;

  // Whether the callback has been triggered.
  bool triggered;

  // Whether this callback will repeat itself again after first trigger.
  const bool repeat;
};

// The handle used to check the status of a scheduled task or to cancel it.
// This handle is safe to be copied or be moved.  However, it is NOT safe to
// modify or reference the same handle from different threads since SharedPtr
// is not thread-safe.
class RequestHandle {
 public:
  RequestHandle() : status_() {}
  explicit RequestHandle(const std::shared_ptr<RequestStatusBlock>& status)
      : status_(status) {}

  // Attempt to cancel the scheduled task.  return true if success or false if
  // it is cancelled or complete already.
  bool Cancel();

  // Return true if the handler is pointing to a request
  bool IsValid() const {
    if (status_) {
      return true;
    }
    return false;
  }

  // Thread-safe call to check if the scheduled callback has been cancelled.
  bool IsCancelled() const;

  // Thread-safe call to check if the scheduled callback has been triggered
  bool IsTriggered() const;

 private:
  std::shared_ptr<RequestStatusBlock> status_;
};

// Scheduler can be used to trigger a callback from the same worker thread.
// Currently it supports to trigger a callback ASAP using Execute() or with
// a delay using Schedule().
// All the public functions are safe to be called from different thread
class Scheduler {
 public:
  Scheduler();

  // When a scheduler is deleted, all the future callback will be discarded.
  // The scheduler does not guarantee to trigger any callback scheduled before
  // the deletion or any the potentially due callback
  ~Scheduler();

  // Scheduler is neither copyable nor movable.
  Scheduler(const Scheduler&) = delete;
  Scheduler(Scheduler&&) = delete;
  Scheduler& operator=(const Scheduler&) = delete;
  Scheduler& operator=(Scheduler&&) = delete;

  // Schedule a callback to be triggered with a delay and optional
  // repeat interval.
  // A handler is returned for caller to check status or cancel the callback.
  // If delay is 0, the first trigger will happen as soon as possible.
  // If repeat is non-zero, after the first trigger, the callback will be push
  // back to the queue again using repeat interval and trigger timestamp
  // Note that multiple callback with the same due time theoretically will be
  // triggered in order.  The only edge case is when request id reaches 2^64 - 1
  // and some of the requests of the same due time are using the wrapped id. Ex.
  // [2^64 - 2, 2^64 - 1, 0, 1, 2].  This should be really rare.
  RequestHandle Schedule(std::unique_ptr<Callback>& callback,
                         ScheduleTimeMs delay = std::chrono::milliseconds(0),
                         ScheduleTimeMs repeat = std::chrono::milliseconds(0));

  // Cancel all scheduled callbacks and shut down the worker thread.
  void CancelAllAndShutdownWorkerThread(bool synchronous_stop = false);

 private:
  typedef uint64_t RequestId;
  // The request data for all scheduled callback.
  struct RequestData {
    explicit RequestData(RequestId id,
                         std::unique_ptr<callback::Callback>& callback,
                         ScheduleTimeMs delay, ScheduleTimeMs repeat);

    // Unique id per scheduler.
    RequestId id;

    // The callback to be triggered.
    std::unique_ptr<Callback> cb;

    // Delay to trigger in milliseconds
    ScheduleTimeMs delay_ms;

    // Repeat interval after first trigger.  Will not repeat if value is 0
    ScheduleTimeMs repeat_ms;

    // The timestamp after the delay in milliseconds.  Used for priority_queue
    std::chrono::time_point<std::chrono::system_clock> due_timestamp;

    // Status block shared with handlers
    std::shared_ptr<RequestStatusBlock> status;
  };

  // SharedPtr of request data.  Ideally this should be UniquePtr and there
  // should only have one copy of it in request_queue_ .  However, STLPort queue
  // uses copy instead of move() while reordering heap element, and UniquePtr is
  // not copyable.  Therefore, use SharedPtr here.
  typedef std::shared_ptr<RequestData> RequestDataPtr;

  // Comparer struct for priority_queue.  If the operator return true, lhs will
  // output later than rhs, due to the implementation of std::priority_queue.
  // http://en.cppreference.com/w/cpp/container/priority_queue
  // That is, the request with lowest timestamp is on the top of the queue.
  // If multiple requests have the same due timestamp, it would be sorted based
  // on request id, i.e. creation time.
  struct RequestDataPtrComparer {
    bool operator()(const RequestDataPtr& lhs,
                    const RequestDataPtr& rhs) const {
      return lhs->due_timestamp > rhs->due_timestamp ||
             (lhs->due_timestamp == rhs->due_timestamp && lhs->id > rhs->id);
    }
  };

  // The worker thread to process scheduled callback.
  std::shared_ptr<std::thread> thread_;

  // Generate next available request id.
  RequestId next_request_id_;

  // Whether the scheduler is terminating.  Only be changed in destructor and
  // referenced in worker thread.
  bool terminating_;

  // If true, the worker thread will process the queue completely before exiting
  bool synchronous_stop_;

  // Priority queue for all scheduled callback, ordered by due timestamp and
  // request id
  std::priority_queue<RequestDataPtr, std::vector<RequestDataPtr>,
                      RequestDataPtrComparer>
      request_queue_;

  // Mutex to guard next_request_id_, terminating_ and request_queue_
  std::mutex request_mutex_;

  // A semaphore with its count equivalent to the number of unfinished
  // requests.  Used to sleep the thread when there are no more unfinished
  // requests.  Also, it's used to wake the thread when new requests is added
  // or when the scheduler is terminating.
  Semaphore sleep_sem_;

  // Everything below runs on worker thread
  // The main worker thread routine
  static void WorkerThreadRoutine(void* data);

  // Move the request to the priority queue that will be triggered in given
  // milliseconds since now
  void AddToQueue(RequestDataPtr request,
                  std::chrono::time_point<std::chrono::system_clock> current,
                  ScheduleTimeMs after);

  // Trigger the callback.  Return true if this callback repeats and is not
  // cancelled yet.
  bool TriggerCallback(const RequestDataPtr& request);
};

}  // namespace core
}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_SCHEDULER_H_
