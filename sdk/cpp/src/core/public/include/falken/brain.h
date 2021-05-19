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

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_BRAIN_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_BRAIN_H_

#include <map>
#include <memory>
#include <string>
#include <utility>
#include <vector>

#include "falken/allocator.h"
#include "falken/brain_spec.h"
#include "falken/config.h"
#include "falken/session.h"
#include "falken/types.h"

namespace falken {

class Service;
class ServiceTest;
class Session;

/// A Brain represents the idea of the thing that observes, learns, and acts.
/// It’s also helpful to think about each Brain as being designed to accomplish
/// a specific kind of task, like completing a lap in a racing game or defeating
/// enemies while moving through a level in an FPS.
class FALKEN_EXPORT BrainBase {
  friend class Session;
  friend class Service;
  friend class ServiceTest;
  class AllocatedBrainSpecBase;

 public:
  /// Remove the brain from the service and destruct.
  virtual ~BrainBase();

  /// Get the service that owns this brain.
  ///
  /// If the service is destroyed before this brain, this method will assert.
  ///
  /// @return Service that owns this brain.
  Service& service() const;
  /// Get brain unique ID in the project.
  ///
  /// @return ID of the brain.
  const char* id() const;
  /// Get brain human readable name.
  ///
  /// @return Human readable name of the brain.
  const char* display_name() const;
  /// Get brain unique ID and human readable name.
  ///
  /// @return ID and human readable name of the brain.
  String info() const;
  /// Get brain unique ID and human readable name.
  ///
  /// @deprecated Use info. This method will be
  /// removed in the future.
  FALKEN_DEPRECATED String BrainInfo() const;
  /// Get brain specification.
  ///
  /// @return Specification of the brain.
  const BrainSpecBase& brain_spec_base() const;
  /// Get brain mutable specification.
  ///
  /// @return Mutable specification of the brain.
  BrainSpecBase& brain_spec_base();
  /// Get the snapshot ID associated with the brain. This is updated when a
  /// session stops.
  ///
  /// @return Snapshot ID of the brain.
  const char* snapshot_id() const;

  /// Start a session.
  ///
  /// @param type Session type.
  /// @param max_steps_per_episode Maximum number of steps per episode.
  /// @return Started session.
  std::shared_ptr<Session> StartSession(falken::Session::Type type,
                                        uint32_t max_steps_per_episode);

  /// Get the number of sessions in the brain.
  ///
  /// @return Number of sessions in the brain.
  int GetSessionCount() const;
  /// Get a session by index in the brain.
  ///
  /// @param index Session index.
  /// @return Session.
  std::shared_ptr<Session> GetSession(int index);
  /// Get a session by ID in the brain.
  ///
  /// @param session_id Session ID.
  /// @return Session.
  std::shared_ptr<Session> GetSession(const char* session_id);
  /// Get a list of Sessions created by this Brain.
  ///
  /// @return A list of Sessions.
  Vector<std::shared_ptr<Session>> ListSessions();
  /// Verify the specification of this brain matches the given brain spec.
  /// @param brain_spec BrainSpec to compare with.
  /// @return True if all attributes and entities match, false otherwise.
  bool MatchesBrainSpec(const BrainSpecBase& brain_spec) const;

  FALKEN_DEFINE_NEW_DELETE

 protected:
  /// Construct a brain.
  ///
  /// @param service Falken service.
  /// @param brain_spec_base Brain specifications.
  /// @param id Brain unique ID.
  /// @param display_name Brain human readable name.
  /// @param snapshot_id Snapshot ID.
  BrainBase(const std::weak_ptr<Service>& service,
            BrainSpecBase* brain_spec_base, const char* id,
            const char* display_name, const char* snapshot_id);
  /// Construct a brain from allocated brain specifications.
  ///
  /// @param service Falken service.
  /// @param allocated_brain_spec Allocated brain specifications.
  /// @param id Brain unique ID.
  /// @param display_name Brain human readable name.
  /// @param snapshot_id Snapshot ID.
  BrainBase(const std::weak_ptr<Service>& service,
            std::unique_ptr<BrainSpecBase> allocated_brain_spec,
            const char* id, const char* display_name,
            const char* snapshot_id);

 private:
  // Update snapshot id. Called only when a session stops and returns a valid
  // snapshot id.
  void UpdateSnapshotId(const char* snapshot_id);
  // Provides a weak_ptr form of this
  std::weak_ptr<BrainBase>& WeakThis();
  // Adds a Session to created_sessions_ list.
  void AddSession(const std::shared_ptr<Session>& session);
  // Retrieves a Session from created_sessions_
  std::shared_ptr<Session> LookupSession(const char* id, bool read_only) const;
  // Generates a key for a Session for use in created_sessions_
  std::string SessionToKey(const char* id, bool read_only) const;

  // Compare two brain specs.
  /// @param brain_spec BrainSpec to compare with.
  /// @return true if all attributes and entities match, false otherwise.
  static bool MatchesBrainSpec(const BrainSpecBase& brain_spec,
                               const BrainSpecBase& other_brain_spec);

  FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_START
  // Private data.
  struct BrainData;
  std::unique_ptr<BrainData> brain_data_;
  FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_END
};

/// Brain with templatized specifications.
template <typename T>
class Brain : public BrainBase {
  friend class Service;

 public:
  ~Brain() override = default;

  /// Get brain specification.
  ///
  /// @return Specification of the brain.
  const T& brain_spec() const { return brain_spec_; }
  /// Get brain mutable specification.
  ///
  /// @return Mutable specification of the brain.
  T& brain_spec() { return brain_spec_; }

  FALKEN_DEFINE_NEW_DELETE

 private:
  Brain(const std::weak_ptr<Service>& service, const char* id,
        const char* display_name, const char* snapshot_id)
      : BrainBase(service, &brain_spec_, id, display_name, snapshot_id) {}
  T brain_spec_;
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_BRAIN_H_
