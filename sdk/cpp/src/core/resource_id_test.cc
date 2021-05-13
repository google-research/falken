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

#include "src/core/protos.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"

namespace falken {

TEST(ResourceId, SetGetComponent) {
  ResourceId id;
  EXPECT_EQ(id.GetComponent("foo"), "");
  id.SetComponent("foo", "bar");
  id.SetComponent("bish", "bosh");
  EXPECT_EQ(id.GetComponent("foo"), "bar");
  EXPECT_EQ(id.GetComponent("bish"), "bosh");
}

TEST(ResourceId, ConstructWithComponents) {
  ResourceId id({{"foo", "bar"}, {"bish", "bosh"}});
  EXPECT_EQ(id.GetComponent("foo"), "bar");
  EXPECT_EQ(id.GetComponent("bish"), "bosh");
}

TEST(ResourceId, ConstructFromProto) {
  falken::proto::Brain proto;
  proto.set_project_id("foo");
  proto.set_brain_id("bar");
  ResourceId id("brain", proto);
  EXPECT_EQ(id.GetComponent("brain"),
            "{ project_id: \"foo\" brain_id: \"bar\" }");
}

TEST(ResourceId, SetComponentFromProto) {
  falken::proto::Brain proto;
  proto.set_project_id("foo");
  proto.set_brain_id("bar");
  ResourceId id;
  id.SetComponent("brain", proto);
  EXPECT_EQ(id.GetComponent("brain"),
            "{ project_id: \"foo\" brain_id: \"bar\" }");
}

TEST(ResourceId, SetEmptyComponent) {
  ResourceId id({{"foo", "bar"}, {"bish", ""}});
  EXPECT_EQ(id.GetComponent("foo"), "bar");
  EXPECT_EQ(id.GetComponent("bish"), "");
  auto expected =
      std::vector<std::pair<std::string, std::string>>({{"foo", "bar"}});
  EXPECT_EQ(id.GetOrderedComponents(), expected);
}

TEST(ResourceId, Clear) {
  ResourceId id;
  id.SetComponent("foo", "bar");
  id.SetComponent("bish", "bosh");
  id.Clear();
  EXPECT_EQ(id.GetComponent("foo"), "");
  EXPECT_EQ(id.GetComponent("bish"), "");
}

TEST(ResourceId, IsEmpty) {
  ResourceId id;
  EXPECT_TRUE(id.IsEmpty());
  id.SetComponent("foo", "bar");
  EXPECT_FALSE(id.IsEmpty());
}

TEST(ResourceId, Equality) {
  ResourceId id1;
  id1.SetComponent("foo", "bar");
  ResourceId id2;
  id2.SetComponent("foo", "bar");
  EXPECT_EQ(id1, id2);
}

TEST(ResourceId, ToString) {
  ResourceId id;
  id.SetComponent("foo", "bar");
  id.SetComponent("bish", "bosh");
  EXPECT_EQ(id.ToString(), "bish/bosh/foo/bar");
  EXPECT_EQ(id.ToString("\n"), "bish/bosh\nfoo/bar");
  EXPECT_EQ(id.ToString("\n", ":"), "bish:bosh\nfoo:bar");
}

TEST(ResourceId, OrderKeys) {
  ResourceId id;
  id.SetComponent("zazzle", "fizzle");
  id.SetComponent("foo", "bar");
  id.SetComponent("bish", "bosh");
  const std::vector<std::pair<std::string, std::string>> kExpectedUnordered(
      {{"bish", "bosh"}, {"foo", "bar"}, {"zazzle", "fizzle"}});
  EXPECT_EQ(id.GetOrderedComponents(), kExpectedUnordered);
  EXPECT_EQ(id.ToString(), "bish/bosh/foo/bar/zazzle/fizzle");
  static const char* kOrder[] = {"bish", "zazzle", nullptr};
  id.SetKeyOrder(kOrder);
  const std::vector<std::pair<std::string, std::string>> kExpectedOrdered(
      {{"bish", "bosh"}, {"zazzle", "fizzle"}, {"foo", "bar"}});
  EXPECT_EQ(id.GetOrderedComponents(), kExpectedOrdered);
  EXPECT_EQ(id.ToString(), "bish/bosh/zazzle/fizzle/foo/bar");
}

TEST(ResourceId, OrderAndFilterEmptyComponents) {
  ResourceId id;
  id.SetComponent("zazzle", "fizzle");
  id.SetComponent("blamo", "");
  id.SetComponent("foo", "bar");
  id.SetComponent("bish", "");
  static const char* kOrder[] = {"blamo", "bish", "zazzle", nullptr};
  id.SetKeyOrder(kOrder);
  const std::vector<std::pair<std::string, std::string>> kExpected(
      {{"zazzle", "fizzle"}, {"foo", "bar"}});
  EXPECT_EQ(id.GetOrderedComponents(), kExpected);
  EXPECT_EQ(id.ToString(), "zazzle/fizzle/foo/bar");
}

TEST(ResourceId, OrderAndFilterUnorderedComponents) {
  ResourceId id({{"bish", "bosh"}, {"foo", "bar"}, {"vroom", "vroom"}});
  static const char* kOrder[] = {"foo", "bish", nullptr};
  id.SetKeyOrder(kOrder);
  const std::vector<std::pair<std::string, std::string>> kExpected(
      {{"foo", "bar"}, {"bish", "bosh"}});
  EXPECT_EQ(id.GetOrderedComponents(false), kExpected);
}

TEST(ResourceId, Parse) {
  ResourceId id;
  EXPECT_TRUE(id.Parse("foo/bar/bish/bosh").ok());
  EXPECT_EQ(id.GetComponent("foo"), "bar");
  EXPECT_EQ(id.GetComponent("bish"), "bosh");
}

TEST(ResourceId, ParseCustomSeparators) {
  ResourceId id;
  EXPECT_TRUE(id.Parse("foo: bar\nbish: bosh", ": ", "\n").ok());
  EXPECT_EQ(id.GetComponent("foo"), "bar");
  EXPECT_EQ(id.GetComponent("bish"), "bosh");
}

TEST(ResourceId, ParseCustomSeparatorsWithInvalidOrder) {
  ResourceId id;
  EXPECT_FALSE(id.Parse("foo\n bar:bish: bosh", ": ", "\n").ok());
  EXPECT_TRUE(id.IsEmpty());
}

TEST(ResourceId, ParseInvalidNumberOfComponents) {
  ResourceId id;
  EXPECT_FALSE(id.Parse("foo/bar/bish").ok());
  EXPECT_TRUE(id.IsEmpty());
}

TEST(ResourceId, ParseOrderedComponents) {
  ResourceId id;
  static const char* kOrder[] = {"bish", "zazzle", nullptr};
  id.SetKeyOrder(kOrder);
  EXPECT_TRUE(id.Parse("bish/bosh/zazzle/fizzle").ok());
  EXPECT_EQ(id.GetComponent("bish"), "bosh");
  EXPECT_EQ(id.GetComponent("zazzle"), "fizzle");
}

TEST(ResourceId, ParseOutOfOrderComponents) {
  ResourceId id;
  static const char* kOrder[] = {"bish", "zazzle", nullptr};
  id.SetKeyOrder(kOrder);
  EXPECT_FALSE(id.Parse("zazzle/fizzle/bish/bosh").ok());
  EXPECT_TRUE(id.IsEmpty());
}

TEST(ResourceId, ParseTooManyComponents) {
  ResourceId id;
  static const char* kOrder[] = {"bish", "zazzle", nullptr};
  id.SetKeyOrder(kOrder);
  EXPECT_FALSE(id.Parse("bish/bosh/zazzle/fizzle/foo/bar").ok());
  EXPECT_TRUE(id.IsEmpty());
}

TEST(ProjectId, ConstructFromString) {
  ProjectId id(std::string("foo"));
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.ToString(), "projects/foo");
}

TEST(ProjectId, SetProjectId) {
  ProjectId id(std::string(""));
  EXPECT_EQ(id.project_id(), "");
  id.set_project_id("foo");
  EXPECT_EQ(id.project_id(), "foo");
}

TEST(ProjectId, ConstructFromProto) {
  falken::proto::Brain proto;
  proto.set_project_id("foo");
  proto.set_brain_id("bar");
  ProjectId id(proto);
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.ToString(), "projects/foo");
}

TEST(ProjectId, Parse) {
  ProjectId id;
  EXPECT_TRUE(id.Parse("projects/foo").ok());
  EXPECT_EQ(id.project_id(), "foo");
}

TEST(ProjectId, ToProto) {
  ProjectId id(std::string("foo"));
  falken::proto::Brain proto;
  EXPECT_EQ(&id.ToProto(proto), &proto);
  EXPECT_EQ(proto.project_id(), "foo");
}

TEST(BrainId, ConstructFromString) {
  BrainId id("foo", "bar");
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
  EXPECT_EQ(id.ToString(), "projects/foo/brains/bar");
}

TEST(BrainId, SetBrainId) {
  BrainId id("foo", "");
  EXPECT_EQ(id.brain_id(), "");
  id.set_brain_id("bar");
  EXPECT_EQ(id.brain_id(), "bar");
}

TEST(BrainId, Parse) {
  BrainId id;
  EXPECT_TRUE(id.Parse("projects/foo/brains/bar").ok());
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
}

TEST(BrainId, ConstructFromProject) {
  BrainId id(ProjectId(std::string("foo")), "bar");
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
}

TEST(BrainId, ConstructFromCommonProto) {
  falken::proto::Brain proto;
  proto.set_project_id("foo");
  proto.set_brain_id("bar");
  BrainId id(proto);
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
}

TEST(BrainId, ConstructFromStorageProto) {
  falken::proto::Brain proto;
  proto.set_project_id("foo");
  proto.set_brain_id("bar");
  BrainId id(proto);
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
}

TEST(BrainId, ToProto) {
  BrainId id("foo", "bar");
  falken::proto::Brain proto;
  EXPECT_EQ(&id.ToProto(proto), &proto);
  EXPECT_EQ(proto.project_id(), "foo");
  EXPECT_EQ(proto.brain_id(), "bar");
}

TEST(SessionId, ConstructFromString) {
  SessionId id("foo", "bar", "baz");
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
  EXPECT_EQ(id.session_id(), "baz");
  EXPECT_EQ(id.ToString(), "projects/foo/brains/bar/sessions/baz");
}

TEST(SessionId, SetSessionId) {
  SessionId id("foo", "bar", "");
  EXPECT_EQ(id.session_id(), "");
  id.set_session_id("baz");
  EXPECT_EQ(id.session_id(), "baz");
}

TEST(SessionId, Parse) {
  SessionId id;
  EXPECT_TRUE(id.Parse("projects/foo/brains/bar/sessions/baz").ok());
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
  EXPECT_EQ(id.session_id(), "baz");
}

TEST(SessionId, ConstructFromBrain) {
  SessionId id(BrainId("foo", "bar"), "baz");
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
  EXPECT_EQ(id.session_id(), "baz");
}

TEST(SessionId, ConstructFromCommonProto) {
  falken::proto::Session proto;
  proto.set_project_id("foo");
  proto.set_brain_id("bar");
  proto.set_name("baz");
  SessionId id(proto);
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
  EXPECT_EQ(id.session_id(), "baz");
}

TEST(SessionId, ToCommonProto) {
  SessionId id("foo", "bar", "baz");
  falken::proto::Session proto;
  EXPECT_EQ(&id.ToProto(proto), &proto);
  EXPECT_EQ(proto.project_id(), "foo");
  EXPECT_EQ(proto.brain_id(), "bar");
  EXPECT_EQ(proto.name(), "baz");
}

TEST(SnapshotId, ConstructFromString) {
  SnapshotId id("foo", "bar", "baz");
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
  EXPECT_EQ(id.snapshot_id(), "baz");
  EXPECT_EQ(id.ToString(), "projects/foo/brains/bar/snapshots/baz");
}

TEST(SnapshotId, SetSnapshotId) {
  SnapshotId id("foo", "bar", "");
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
  EXPECT_EQ(id.snapshot_id(), "");
  id.set_snapshot_id("baz");
  EXPECT_EQ(id.snapshot_id(), "baz");
}

TEST(SnapshotId, Parse) {
  SnapshotId id;
  EXPECT_TRUE(id.Parse("projects/foo/brains/bar/snapshots/baz").ok());
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
  EXPECT_EQ(id.snapshot_id(), "baz");
}

TEST(SnapshotId, ConstructFromBrain) {
  SnapshotId id(BrainId("foo", "bar"), "baz");
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
  EXPECT_EQ(id.snapshot_id(), "baz");
}

TEST(SnapshotId, ConstructFromCommonProto) {
  falken::proto::Snapshot proto;
  proto.set_project_id("foo");
  proto.set_brain_id("bar");
  proto.set_snapshot_id("baz");
  SnapshotId id(proto);
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
  EXPECT_EQ(id.snapshot_id(), "baz");
}

TEST(SnapshotId, ToProto) {
  SnapshotId id("foo", "bar", "baz");
  falken::proto::Snapshot proto;
  EXPECT_EQ(&id.ToProto(proto), &proto);
  EXPECT_EQ(proto.project_id(), "foo");
  EXPECT_EQ(proto.brain_id(), "bar");
  EXPECT_EQ(proto.snapshot_id(), "baz");
}

TEST(ModelId, ConstructFromString) {
  ModelId id("foo", "bar", "baz");
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
  EXPECT_EQ(id.model_id(), "baz");
  EXPECT_EQ(id.ToString(), "projects/foo/brains/bar/models/baz");
}

TEST(ModelId, SetModelId) {
  ModelId id("foo", "bar", "");
  EXPECT_EQ(id.model_id(), "");
  id.set_model_id("baz");
  EXPECT_EQ(id.model_id(), "baz");
}

TEST(ModelId, Parse) {
  ModelId id;
  EXPECT_TRUE(id.Parse("projects/foo/brains/bar/models/bish").ok());
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
  EXPECT_EQ(id.model_id(), "bish");
}

TEST(ModelId, ConstructFromBrain) {
  ModelId id(BrainId("foo", "bar"), "baz");
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
  EXPECT_EQ(id.model_id(), "baz");
}

TEST(ModelId, ConstructFromCommonProto) {
  falken::proto::GetModelRequest proto;
  proto.set_project_id("foo");
  proto.set_brain_id("bar");
  proto.set_snapshot_id("baz");
  proto.set_model_id("bish");
  ModelId id(proto);
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
  EXPECT_EQ(id.GetComponent(SnapshotId::kSnapshotKey), "baz");
  EXPECT_EQ(id.model_id(), "bish");
}

TEST(ModelId, ToProto) {
  ModelId id("foo", "bar", "baz");
  falken::proto::GetModelRequest proto;
  EXPECT_EQ(&id.ToProto(proto), &proto);
  EXPECT_EQ(proto.project_id(), "foo");
  EXPECT_EQ(proto.brain_id(), "bar");
  EXPECT_EQ(proto.model_id(), "baz");
}

TEST(EpisodeId, ConstructFromString) {
  EpisodeId id("foo", "bar", "baz", "bish");
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
  EXPECT_EQ(id.session_id(), "baz");
  EXPECT_EQ(id.episode_id(), "bish");
}

TEST(EpisodeId, SetEpisodeId) {
  EpisodeId id("foo", "bar", "baz", "");
  EXPECT_EQ(id.episode_id(), "");
  id.set_episode_id("bish");
  EXPECT_EQ(id.episode_id(), "bish");
}

TEST(EpisodeId, Parse) {
  EpisodeId id;
  EXPECT_TRUE(
      id.Parse("projects/foo/brains/bar/sessions/bish/episodes/baz").ok());
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
  EXPECT_EQ(id.session_id(), "bish");
  EXPECT_EQ(id.episode_id(), "baz");
}

TEST(EpisodeId, ConstructFromSession) {
  EpisodeId id(SessionId("foo", "bar", "baz"), "bish");
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
  EXPECT_EQ(id.session_id(), "baz");
  EXPECT_EQ(id.episode_id(), "bish");
  EXPECT_EQ(id.ToString(),
            "projects/foo/brains/bar/sessions/baz/episodes/bish");
}

TEST(EpisodeId, ConstructFromRequestProto) {
  falken::proto::SubmitEpisodeChunksRequest proto;
  proto.set_project_id("foo");
  proto.set_brain_id("bar");
  proto.set_session_id("baz");
  proto.add_chunks()->set_episode_id("bish");
  EpisodeId id(proto);
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
  EXPECT_EQ(id.session_id(), "baz");
  EXPECT_EQ(id.episode_id(), "bish");
}

TEST(EpisodeId, ConstructFromChunkProto) {
  falken::proto::EpisodeChunk proto;
  proto.set_episode_id("bish");
  EpisodeId id(SessionId("foo", "bar", "baz"), proto);
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
  EXPECT_EQ(id.session_id(), "baz");
  EXPECT_EQ(id.episode_id(), "bish");
}

TEST(AssignmentId, ConstructFromString) {
  AssignmentId id("foo", "bar", "baz", "bish");
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
  EXPECT_EQ(id.session_id(), "baz");
  EXPECT_EQ(id.assignment_id(), "bish");
  EXPECT_EQ(id.ToString(),
            "projects/foo/brains/bar/sessions/baz/assignments/bish");
}

TEST(AssignmentId, SetAssignmentId) {
  AssignmentId id("foo", "bar", "baz", "");
  EXPECT_EQ(id.assignment_id(), "");
  id.set_assignment_id("bish");
  EXPECT_EQ(id.assignment_id(), "bish");
}

TEST(AssignmentId, Parse) {
  AssignmentId id;
  EXPECT_TRUE(
      id.Parse("projects/foo/brains/bar/sessions/baz/assignments/bish").ok());
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
  EXPECT_EQ(id.session_id(), "baz");
  EXPECT_EQ(id.assignment_id(), "bish");
}

TEST(AssignmentId, ConstructFromSession) {
  AssignmentId id(SessionId("foo", "bar", "baz"), "bish");
  EXPECT_EQ(id.project_id(), "foo");
  EXPECT_EQ(id.brain_id(), "bar");
  EXPECT_EQ(id.session_id(), "baz");
  EXPECT_EQ(id.assignment_id(), "bish");
}

TEST(IpAddressId, Construct) {
  EXPECT_EQ(IpAddressId("127.0.0.1").ToString(), "ip_address/127.0.0.1");
}

TEST(DatabaseId, Construct) {
  EXPECT_EQ(DatabaseId("mydb").ToString(), "database_path/mydb");
}

TEST(UserAgent, Construct) {
  EXPECT_EQ(UserAgent("foo-bar/1.2.3").ToString(), "user_agent/foo-bar/1.2.3");
}

}  // namespace falken
