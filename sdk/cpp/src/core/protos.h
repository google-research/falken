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

#ifndef FALKEN_SDK_CORE_PROTOS_H_
#define FALKEN_SDK_CORE_PROTOS_H_

// Bridging header to include the appropriate protos depending upon the build
// environment.

// TODO(b/185930119): Remove FALKEN_INTERNAL section when forking for OSS.
#if FALKEN_INTERNAL

// NOLINTBEGIN
#include "service/proto/falken_service.grpc.pb.h"
#include "service/proto/falken_service.pb.h"
#include "service/proto/action.pb.h"
#include "service/proto/brain.pb.h"
#include "service/proto/episode.pb.h"
#include "service/proto/observation.pb.h"
#include "service/proto/primitives.pb.h"
#include "service/proto/serialized_model.pb.h"
#include "service/proto/session.pb.h"
#include "service/proto/snapshot.pb.h"  // NOLINT
// NOLINTEND

// Move internal protos into the OSS namespace.
namespace falken {
namespace proto {

using ActionData = research::kernel::falken::common::proto::ActionData;
using Action = research::kernel::falken::common::proto::Action;
using ActionSpec = research::kernel::falken::common::proto::ActionSpec;
using ActionType = research::kernel::falken::common::proto::ActionType;
using Brain = research::kernel::falken::common::proto::Brain;
using BrainSpec = research::kernel::falken::common::proto::BrainSpec;
using Category = research::kernel::falken::common::proto::Category;
using CategoryType = research::kernel::falken::common::proto::CategoryType;
using EntityField = research::kernel::falken::common::proto::EntityField;
using EntityFieldType =
    research::kernel::falken::common::proto::EntityFieldType;
using Entity = research::kernel::falken::common::proto::Entity;
using EntityType = research::kernel::falken::common::proto::EntityType;
using Episode = research::kernel::falken::common::proto::Episode;
using EpisodeChunk = research::kernel::falken::common::proto::EpisodeChunk;
using EpisodeState = research::kernel::falken::common::proto::EpisodeState;
using Feeler = research::kernel::falken::common::proto::Feeler;
using FeelerType = research::kernel::falken::common::proto::FeelerType;
using Joystick = research::kernel::falken::common::proto::Joystick;
using JoystickAxesMode =
    research::kernel::falken::common::proto::JoystickAxesMode;
using JoystickType = research::kernel::falken::common::proto::JoystickType;
using Number = research::kernel::falken::common::proto::Number;
using NumberType = research::kernel::falken::common::proto::NumberType;
using ObservationData =
    research::kernel::falken::common::proto::ObservationData;
using ObservationSpec =
    research::kernel::falken::common::proto::ObservationSpec;
using Position = research::kernel::falken::common::proto::Position;
using PositionType = research::kernel::falken::common::proto::PositionType;
using Rotation = research::kernel::falken::common::proto::Rotation;
using RotationType = research::kernel::falken::common::proto::RotationType;
using SerializedModel =
    research::kernel::falken::common::proto::SerializedModel;
using SessionInfo = research::kernel::falken::common::proto::SessionInfo;
using Session = research::kernel::falken::common::proto::Session;
using SessionSpec = research::kernel::falken::common::proto::SessionSpec;
using SessionType = research::kernel::falken::common::proto::SessionType;
using Snapshot = research::kernel::falken::common::proto::Snapshot;
using Step = research::kernel::falken::common::proto::Step;

namespace grpc_gen {
using FalkenService =
    google::internal::falken::v1eap::falken::grpc_gen::FalkenPrivateService;
}  // namespace grpc_gen
using CreateBrainRequest =
    google::internal::falken::v1eap::falken::CreateBrainRequest;
using CreateSessionRequest =
    google::internal::falken::v1eap::falken::CreateSessionRequest;
using GetBrainRequest =
    google::internal::falken::v1eap::falken::GetBrainRequest;
using GetModelRequest =
    google::internal::falken::v1eap::falken::GetModelRequest;
using GetSessionByIndexRequest =
    google::internal::falken::v1eap::falken::GetSessionByIndexRequest;
using GetSessionCountRequest =
    google::internal::falken::v1eap::falken::GetSessionCountRequest;
using GetSessionCountResponse =
    google::internal::falken::v1eap::falken::GetSessionCountResponse;
using GetSessionRequest =
    google::internal::falken::v1eap::falken::GetSessionRequest;
using ListBrainsRequest =
    google::internal::falken::v1eap::falken::ListBrainsRequest;
using ListBrainsResponse =
    google::internal::falken::v1eap::falken::ListBrainsResponse;
using ListEpisodeChunksRequest =
    google::internal::falken::v1eap::falken::ListEpisodeChunksRequest;
using ListEpisodeChunksResponse =
    google::internal::falken::v1eap::falken::ListEpisodeChunksResponse;
using ListSessionsRequest =
    google::internal::falken::v1eap::falken::ListSessionsRequest;
using ListSessionsResponse =
    google::internal::falken::v1eap::falken::ListSessionsResponse;
using Model = google::internal::falken::v1eap::falken::Model;
using StopSessionRequest =
    google::internal::falken::v1eap::falken::StopSessionRequest;
using StopSessionResponse =
    google::internal::falken::v1eap::falken::StopSessionResponse;
using SubmitEpisodeChunksRequest =
    google::internal::falken::v1eap::falken::SubmitEpisodeChunksRequest;
using SubmitEpisodeChunksResponse =
    google::internal::falken::v1eap::falken::SubmitEpisodeChunksResponse;

}  // namespace proto
}  // namespace falken

#else

// NOLINTBEGIN
#include "service/proto/action.pb.h"
#include "service/proto/brain.pb.h"
#include "service/proto/episode.pb.h"
#include "service/proto/falken_service.grpc.pb.h"
#include "service/proto/falken_service.pb.h"
#include "service/proto/observation.pb.h"
#include "service/proto/primitives.pb.h"
#include "service/proto/serialized_model.pb.h"
#include "service/proto/session.pb.h"
#include "service/proto/snapshot.pb.h"
// NOLINTEND

#endif  // FALKEN_INTERNAL

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PROTOS_H_
