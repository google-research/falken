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

#include "src/core/resource_id.h"

#include <sstream>
#include <utility>

#include "absl/status/status.h"
#include "absl/strings/str_cat.h"
#include "absl/strings/str_replace.h"
#include "absl/strings/str_split.h"
#include "absl/strings/strip.h"

namespace falken {

constexpr const char ProjectId::kProjectKey[];
const char* const ProjectId::kOrderedKeys[] = {kProjectKey, nullptr};
constexpr const char BrainId::kBrainKey[];
const char* const BrainId::kOrderedKeys[] = {kProjectKey, kBrainKey, nullptr};
constexpr const char SessionId::kSessionKey[];
const char* const SessionId::kOrderedKeys[] = {kProjectKey, kBrainKey,
                                               kSessionKey, nullptr};
constexpr const char SnapshotId::kSnapshotKey[];
const char* const SnapshotId::kOrderedKeys[] = {kProjectKey, kBrainKey,
                                                kSnapshotKey, nullptr};
constexpr const char ModelId::kModelKey[];
const char* const ModelId::kOrderedKeys[] = {kProjectKey, kBrainKey, kModelKey,
                                             nullptr};
constexpr const char EpisodeId::kEpisodeKey[];
const char* const EpisodeId::kOrderedKeys[] = {
    kProjectKey, kBrainKey, kSessionKey, kEpisodeKey, nullptr};
constexpr const char AssignmentId::kAssignmentKey[];
const char* const AssignmentId::kOrderedKeys[] = {
    kProjectKey, kBrainKey, kSessionKey, kAssignmentKey, nullptr};
constexpr const char IpAddressId::kIpAddressKey[];
constexpr const char UserAgent::kUserAgentKey[];
constexpr const char DatabaseId::kDatabasePathKey[];

ResourceId::ResourceId(
    const std::vector<std::pair<std::string, std::string>>& components)
    : ResourceId() {
  for (auto& component : components) {
    SetComponent(component.first, component.second);
  }
}

void ResourceId::Clear() { components_.clear(); }

bool ResourceId::IsEmpty() const {
  for (auto& it : components_) {
    if (!it.second.empty()) return false;
  }
  return true;
}

void ResourceId::SetComponent(const std::string& key,
                              const std::string& value) {
  if (!value.empty()) {
    components_[key] = value;
  } else {
    components_.erase(key);
  }
}

// Set from a protocol buffer.
void ResourceId::SetComponent(const std::string& key,
                              const google::protobuf::Message& proto) {
  std::string proto_string =
      absl::StrReplaceAll(proto.ShortDebugString(), {{"\n", " "}});
  absl::string_view proto_string_view(proto_string);
  absl::ConsumeSuffix(&proto_string_view, " ");
  SetComponent(key, absl::StrCat("{ ", proto_string_view, " }"));
}

std::string ResourceId::GetComponent(const std::string& key) const {
  auto it = components_.find(key);
  return it == components_.end() ? std::string() : it->second;
}

std::vector<std::pair<std::string, std::string>>
ResourceId::GetOrderedComponents(bool include_unordered_components) const {
  std::vector<std::pair<std::string, std::string>> ordered_components;
  std::set<std::string> output_keys;
  if (key_order_ != nullptr) {
    for (const char* const* it = key_order_; *it; it++) {
      auto component = components_.find(*it);
      if (component != components_.end() && !component->second.empty()) {
        output_keys.insert(component->first);
        ordered_components.push_back(*component);
      }
    }
  }
  // Unordered components.
  if (include_unordered_components) {
    for (const auto& component : components_) {
      if (!component.second.empty() &&
          output_keys.find(component.first) == output_keys.end()) {
        ordered_components.push_back(component);
      }
    }
  }
  return ordered_components;
}

// Used to split a string using a set of delimiter strings cycling through
// each delimiter for each new position.
class AlternatingMultiStringSplitter {
 public:
  explicit AlternatingMultiStringSplitter(
      const std::vector<absl::string_view>& delimiters)
      : delimiters_(delimiters), delimiter_index_(0), last_pos_(0) {}

  // Search "text", starting at offset "pos" for the first instance of
  // delimiter_[delimiter_index_]. If "pos" is ahead of the last call to Find()
  // this moves to the next delimiter in the delimiters_ vector cycling back to
  // the start.
  //
  // The returned value is either a string view of the substring following a
  // delimiter or the end of the string if a delimiter isn't found.
  // For example, given the delimiter "," and the string "foo,bar" with pos 0
  // this will return "bar". When provided the position 4 ("b") this will return
  // a reference to the end of the string.
  absl::string_view Find(absl::string_view text, size_t pos) {
    if (pos > last_pos_) {
      // If the search position has moved, move to the next delimiter.
      delimiter_index_ = (delimiter_index_ + 1) % delimiters_.size();
      last_pos_ = pos;
    }
    const auto& delimiter = delimiters_[delimiter_index_];
    auto next_pos = text.find(delimiter, pos);
    // If other delimiters are found before the current delimiter,
    // stop searching.
    for (int i = 0; i < delimiters_.size(); ++i) {
      const auto& other_delimiter =
          delimiters_[(delimiter_index_ + 1 + i) % delimiters_.size()];
      auto other_delimiter_pos = text.find(other_delimiter, pos);
      if (other_delimiter_pos < next_pos) {
        return text.substr(text.size());
      }
    }
    return next_pos == absl::string_view::npos
               ? text.substr(text.size())
               : text.substr(next_pos, delimiter.length());
  }

 private:
  std::vector<absl::string_view> delimiters_;
  int delimiter_index_;
  size_t last_pos_;
};

absl::Status ResourceId::Parse(const std::string& id,
                               const char* component_separator,
                               const char* component_name_separator) {
  Clear();
  const AlternatingMultiStringSplitter splitter(
      {component_separator, component_name_separator});
  std::vector<std::string> components =
      absl::StrSplit(id, splitter, absl::AllowEmpty());
  // Should end up with pairs of components split by
  // name0{component_name_separator}value1{component_separator}name1...
  if ((components.size() % 2) != 0) {
    return absl::InvalidArgumentError(
        absl::StrCat("Resource ID string '", id,
                     "'does not contain a set of key / value pairs, found ",
                     components.size(), " components."));
  }

  const char* const* expected_key = key_order_;
  for (int i = 0; i < components.size(); i += 2) {
    const auto& key = components[i];
    const auto& value = components[i + 1];
    if (expected_key != nullptr) {
      if (*expected_key == nullptr || key != *expected_key) {
        Clear();
        return absl::InvalidArgumentError(absl::StrCat(
            "Key '", key, " in an unexpected order, expected key '",
            std::string(*expected_key ? *expected_key : "<none>"),
            "' in resource ID string '", id, "'."));
      }
      expected_key++;
    }
    if (!value.empty()) SetComponent(key, value);
  }
  return absl::OkStatus();
}

std::string ResourceId::ToString(const char* component_separator,
                                 const char* component_name_separator) const {
  std::stringstream ss;
  return ToStream(ss, component_separator, component_name_separator).str();
}

}  // namespace falken
