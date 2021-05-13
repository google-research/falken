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

#ifndef FALKEN_SDK_CORE_RESOURCE_ID_H_
#define FALKEN_SDK_CORE_RESOURCE_ID_H_

#include <map>
#include <memory>
#include <set>
#include <string>
#include <utility>
#include <vector>

#include <google/protobuf/message_lite.h>
#include "src/core/protos.h"
#include "absl/status/status.h"

namespace falken {

// Container for a Falken resource identifier.
class ResourceId {
 public:
  // Construct an empty ID.
  ResourceId() : key_order_(nullptr) {}

  // Construct from a set of components.
  // This constructs the resource ID with the specified key / value pairs.
  explicit ResourceId(
      const std::vector<std::pair<std::string, std::string>>& components);

  // Construct from a protocol buffer.
  ResourceId(const std::string& key, const google::protobuf::Message& proto)
      : ResourceId() {
    SetComponent(key, proto);
  }

  bool operator==(const ResourceId& other) const {
    return other.components_ == components_;
  }

  // Remove all components from this resource identifier.
  void Clear();

  // Determine whether the ID is empty.
  bool IsEmpty() const;

  // Write the resource ID as a string to the specified stream.
  //
  // For example, given:
  //
  // ResourceId id;
  // id.SetComponent("foo", "bar");
  // id.SetComponent("bish", "bosh");
  //
  // this will generate:
  //
  // bish/bosh/foo/bar
  //
  // When using "\n" and ": " as the component and component name separators
  // this will display:
  //
  // bish: bosh\n
  // foo: bar
  //
  // If no key order is set with SetKeyOrder(), components are sorted by key
  // name.
  template <typename T>
  T& ToStream(T& stream, const char* component_separator = "/",
              const char* component_name_separator = "/") const;

  // Set the value of a component.
  void SetComponent(const std::string& key, const std::string& value);

  // Set from a protocol buffer.
  void SetComponent(const std::string& key, const google::protobuf::Message& proto);

  // Get the value of a component.
  std::string GetComponent(const std::string& key) const;

  // Get an ordered list of non-empty components.
  std::vector<std::pair<std::string, std::string>> GetOrderedComponents(
      bool include_unordered_components = true) const;

  // Get the resource ID as a string.
  std::string ToString(const char* component_separator = "/",
                       const char* component_name_separator = "/") const;

  // Configure key ordering.
  //
  // This array specifies the order keys should be written to a string,
  // the array should be terminated with nullptr.
  // If this is set to nullptr, keys are displayed in the map's sorted order.
  void SetKeyOrder(const char* const* key_order) { key_order_ = key_order; }

  // Parse a resource ID from a string.
  //
  // If key ordering is set, only the keys in the configured array will be
  // parsed from the provided string in the expected order.
  absl::Status Parse(const std::string& id,
                     const char* component_separator = "/",
                     const char* component_name_separator = "/");

 protected:
  // Write a component to a stream.
  template <typename STREAM_TYPE>
  static STREAM_TYPE& ComponentToStream(
      STREAM_TYPE& stream, const std::pair<std::string, std::string>& component,
      const char* component_separator, const char* component_name_separator);

 private:
  std::map<std::string, std::string> components_;
  const char* const* key_order_;
};

template <typename T>
T& ResourceId::ToStream(T& stream, const char* component_separator,
                        const char* component_name_separator) const {
  // Write ordered components.
  bool first_item = true;
  for (auto& component : GetOrderedComponents()) {
    ComponentToStream(stream, component,
                      first_item ? nullptr : component_separator,
                      component_name_separator);
    first_item = false;
  }
  return stream;
}

template <typename STREAM_TYPE>
STREAM_TYPE& ResourceId::ComponentToStream(
    STREAM_TYPE& stream, const std::pair<std::string, std::string>& component,
    const char* component_separator, const char* component_name_separator) {
  if (component_separator) stream << component_separator;
  stream << component.first << component_name_separator << component.second;
  return stream;
}

// Project identifier.
class ProjectId : public ResourceId {
 public:
  ProjectId() { SetKeyOrder(kOrderedKeys); }

  template <typename T>
  explicit ProjectId(const T& proto_or_string)
      : ProjectId(proto_or_string.project_id()) {}

  // Serialize to a proto.
  template <typename T>
  T& ToProto(T& proto) const {
    proto.set_project_id(project_id());
    return proto;
  }

  void set_project_id(const std::string& id) { SetComponent(kProjectKey, id); }
  std::string project_id() const { return GetComponent(kProjectKey); }

  static constexpr const char kProjectKey[] = "projects";

 protected:
  static const char* const kOrderedKeys[];
};

template <>
inline ProjectId::ProjectId(const std::string& proto_or_string) : ProjectId() {
  SetComponent(kProjectKey, proto_or_string);
}

// Brain identifier.
class BrainId : public ProjectId {
 public:
  BrainId() { SetKeyOrder(kOrderedKeys); }

  BrainId(const std::string& project_id, const std::string& brain_id)
      : ProjectId(project_id) {
    SetComponent(kBrainKey, brain_id);
    SetKeyOrder(kOrderedKeys);
  }

  BrainId(const ProjectId& project_id, const std::string& brain_id)
      : BrainId(project_id.project_id(), brain_id) {}

  template <typename T>
  explicit BrainId(const T& proto) : ProjectId(proto.project_id()) {
    SetComponent(kBrainKey, proto.brain_id());
    SetKeyOrder(kOrderedKeys);
  }

  template <typename T>
  T& ToProto(T& proto) const {
    ProjectId::ToProto(proto);
    proto.set_brain_id(brain_id());
    return proto;
  }

  void set_brain_id(std::string id) { SetComponent(kBrainKey, id); }
  std::string brain_id() const { return GetComponent(kBrainKey); }

  static constexpr const char kBrainKey[] = "brains";
  static const char* const kOrderedKeys[];
};

// Session identifier.
class SessionId : public BrainId {
 public:
  SessionId() { SetKeyOrder(kOrderedKeys); }

  SessionId(const std::string& project_id, const std::string& brain_id,
            const std::string& session_id)
      : BrainId(project_id, brain_id) {
    SetComponent(kSessionKey, session_id);
    SetKeyOrder(kOrderedKeys);
  }

  SessionId(const BrainId& brain_id, const std::string& session_id)
      : SessionId(brain_id.project_id(), brain_id.brain_id(), session_id) {}

  template <typename T>
  explicit SessionId(const T& proto)
      : SessionId(proto.project_id(), proto.brain_id(), proto.session_id()) {}

  template <typename T>
  T& ToProto(T& proto) const {
    BrainId::ToProto(proto);
    proto.set_session_id(session_id());
    return proto;
  }

  void set_session_id(const std::string& id) { SetComponent(kSessionKey, id); }
  std::string session_id() const { return GetComponent(kSessionKey); }

  static constexpr const char kSessionKey[] = "sessions";
  static const char* const kOrderedKeys[];
};

template <>
inline SessionId::SessionId(const proto::Session& proto)
    : SessionId(proto.project_id(), proto.brain_id(), proto.name()) {}

template <>
inline proto::Session& SessionId::ToProto(proto::Session& proto) const {
  BrainId::ToProto(proto);
  proto.set_name(session_id());
  return proto;
}

// Snapshot identifier.
class SnapshotId : public BrainId {
 public:
  SnapshotId() { SetKeyOrder(kOrderedKeys); }

  SnapshotId(const std::string& project_id, const std::string& brain_id,
             const std::string& snapshot_id)
      : BrainId(project_id, brain_id) {
    SetComponent(kSnapshotKey, snapshot_id);
    SetKeyOrder(kOrderedKeys);
  }

  SnapshotId(const BrainId& brain_id, const std::string& snapshot_id)
      : SnapshotId(brain_id.project_id(), brain_id.brain_id(), snapshot_id) {}

  template <typename T>
  explicit SnapshotId(const T& proto)
      : SnapshotId(proto.project_id(), proto.brain_id(), proto.snapshot_id()) {}

  template <typename T>
  T& ToProto(T& proto) const {
    BrainId::ToProto(proto);
    proto.set_snapshot_id(snapshot_id());
    return proto;
  }

  void set_snapshot_id(const std::string& id) {
    SetComponent(kSnapshotKey, id);
  }
  std::string snapshot_id() const { return GetComponent(kSnapshotKey); }

  static constexpr const char kSnapshotKey[] = "snapshots";
  static const char* const kOrderedKeys[];
};

// Model identifier.
class ModelId : public BrainId {
 public:
  ModelId() { SetKeyOrder(kOrderedKeys); }

  ModelId(const std::string& project_id, const std::string& brain_id,
          const std::string& model_id)
      : BrainId(project_id, brain_id) {
    SetComponent(kModelKey, model_id);
    SetKeyOrder(kOrderedKeys);
  }

  ModelId(const BrainId& brain_id, const std::string& model_id)
      : ModelId(brain_id.project_id(), brain_id.brain_id(), model_id) {}

  template <typename T>
  explicit ModelId(const T& proto)
      : ModelId(proto.project_id(), proto.brain_id(), proto.model_id()) {}

  template <typename T>
  T& ToProto(T& proto) const {
    BrainId::ToProto(proto);
    proto.set_model_id(model_id());
    return proto;
  }

  void set_model_id(const std::string& id) { SetComponent(kModelKey, id); }
  std::string model_id() const { return GetComponent(kModelKey); }

  static constexpr const char kModelKey[] = "models";
  static const char* const kOrderedKeys[];
};

template <>
inline ModelId::ModelId(const proto::GetModelRequest& proto)
    : ModelId(proto.project_id(), proto.brain_id(), proto.model_id()) {
  SetComponent(SnapshotId::kSnapshotKey, proto.snapshot_id());
}

// Episode identifier.
class EpisodeId : public SessionId {
 public:
  EpisodeId() { SetKeyOrder(kOrderedKeys); }

  EpisodeId(const std::string& project_id, const std::string& brain_id,
            const std::string& session_id, const std::string& episode_id)
      : SessionId(project_id, brain_id, session_id) {
    SetComponent(kEpisodeKey, episode_id);
    SetKeyOrder(kOrderedKeys);
  }

  EpisodeId(const SessionId& session_id, const std::string& episode_id)
      : EpisodeId(session_id.project_id(), session_id.brain_id(),
                  session_id.session_id(), episode_id) {}

  template <typename T>
  explicit EpisodeId(const T& proto)
      : EpisodeId(proto.project_id(), proto.brain_id(), proto.session_id(),
                  proto.episode_id()) {}

  EpisodeId(const SessionId& session_id, const proto::EpisodeChunk& proto)
      : EpisodeId(session_id, proto.episode_id()) {}

  template <typename T>
  T& ToProto(T& proto) const {
    SessionId::ToProto(proto);
    proto.set_episode_id(episode_id());
    return proto;
  }

  void set_episode_id(const std::string& id) { SetComponent(kEpisodeKey, id); }
  std::string episode_id() const { return GetComponent(kEpisodeKey); }

  static constexpr const char kEpisodeKey[] = "episodes";

 protected:
  static const char* const kOrderedKeys[];
};

template <>
inline EpisodeId::EpisodeId(const proto::SubmitEpisodeChunksRequest& proto)
    : EpisodeId(proto.project_id(), proto.brain_id(), proto.session_id(), "") {
  if (proto.chunks_size() > 0) {
    SetComponent(kEpisodeKey, proto.chunks(0).episode_id());
  }
}

// Assignment identifier.
class AssignmentId : public SessionId {
 public:
  AssignmentId() { SetKeyOrder(kOrderedKeys); }

  AssignmentId(const std::string& project_id, const std::string& brain_id,
               const std::string& session_id, const std::string& assignment_id)
      : SessionId(project_id, brain_id, session_id) {
    SetComponent(kAssignmentKey, assignment_id);
    SetKeyOrder(kOrderedKeys);
  }

  AssignmentId(const SessionId& session_id, const std::string& assignment_id)
      : AssignmentId(session_id.project_id(), session_id.brain_id(),
                     session_id.session_id(), assignment_id) {}

  template <typename T>
  explicit AssignmentId(const T& proto)
      : AssignmentId(proto.project_id(), proto.brain_id(), proto.session_id(),
                     proto.assignment_id()) {}

  template <typename T>
  T& ToProto(T& proto) const {
    SessionId::ToProto(proto);
    proto.set_assignment_id(assignment_id());
    return proto;
  }

  void set_assignment_id(const std::string& id) {
    SetComponent(kAssignmentKey, id);
  }
  std::string assignment_id() const { return GetComponent(kAssignmentKey); }

  static constexpr const char kAssignmentKey[] = "assignments";
  static const char* const kOrderedKeys[];
};

class IpAddressId : public ResourceId {
 public:
  explicit IpAddressId(const std::string& ip_address) {
    SetComponent(kIpAddressKey, ip_address);
  }

  static constexpr const char kIpAddressKey[] = "ip_address";
};

class UserAgent : public ResourceId {
 public:
  explicit UserAgent(const std::string& user_agent) {
    SetComponent(kUserAgentKey, user_agent);
  }

  static constexpr const char kUserAgentKey[] = "user_agent";
};

class DatabaseId : public ResourceId {
 public:
  explicit DatabaseId(const std::string& database_path) {
    SetComponent(kDatabasePathKey, database_path);
  }

  static constexpr const char kDatabasePathKey[] = "database_path";
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_RESOURCE_ID_H_
