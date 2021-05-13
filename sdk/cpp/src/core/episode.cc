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

#include "falken/episode.h"

#include <string.h>

#include <memory>
#include <utility>
#include <vector>

#include "src/core/statusor.h"
#include "src/core/action_proto_converter.h"
#include "src/core/active_session.h"
#include "src/core/assert.h"
#include "src/core/child_resource_map.h"
#include "src/core/episode_internal.h"
#include "src/core/falken_core.h"
#include "src/core/globals.h"
#include "src/core/observation_proto_converter.h"
#include "src/core/protos.h"
#include "falken/brain.h"
#include "falken/service.h"
#include "falken/session.h"
#include "src/core/session_internal.h"
#include "absl/strings/str_cat.h"
#include "absl/strings/str_join.h"
#include "absl/time/clock.h"
#include "absl/time/time.h"

namespace falken {

using EpisodeCompletionCallback =
    std::function<void(const falken::common::StatusOr<proto::SessionInfo>&)>;

proto::EpisodeState ToEpisodeState(Episode::CompletionState state,
                                   bool gave_up) {
  if (gave_up) {
    return proto::EpisodeState::GAVE_UP;
  }
  switch (state) {
    case Episode::kCompletionStateInvalid:
      return proto::EpisodeState::UNSPECIFIED;
    case Episode::kCompletionStateSuccess:
      return proto::EpisodeState::SUCCESS;
    case Episode::kCompletionStateFailure:
      return proto::EpisodeState::FAILURE;
    case Episode::kCompletionStateAborted:
      return proto::EpisodeState::ABORTED;
  }
  return proto::EpisodeState::UNSPECIFIED;
}

Episode::~Episode() {
  FALKEN_LOCK_GLOBAL_MUTEX();
  if (!completed()) {
    Complete(Episode::CompletionState::kCompletionStateAborted);
  }
}

bool Episode::Step() { return Step(nullptr); }

bool Episode::Step(float reward) { return Step(&reward); }

bool Episode::Step(float* reward) {
  if (IsReadOnly()) {
    LogError("It's not possible to step episode %s as it's read-only. To add "
             "more experience to the brain, create a new session.", id());
    return false;
  }
  if (data_->completed) {
    LogError("It's not possible to step episode %s as it's already complete. "
             "To add more experience to the brain, create a new episode.",
             id());
    return false;
  } else if (!data_->session) {
    LogError("It's not possible to step episode %s as the associated session "
             "has been destroyed. To add experience to the brain, create a "
             "new session.", id());
    return false;
  }

  Session& session = this->session();
  if (session.total_steps_per_episode() == data_->current_step) {
    LogWarning("Reach the maximum number of steps '%d' for an episode in this "
               "session, aborting the episode. To add more experience to "
               "the brain create a new episode.",
               session.total_steps_per_episode());
    // The completion state in this case is ignored since
    // we gave up trying to complete the task. Also we ignore
    // the return value since the step could not be made.
    Complete(Episode::kCompletionStateAborted, true);
    return false;
  }

  BrainSpecBase& brain_spec_base = session.brain().brain_spec_base();
  ObservationsBase& observations_base = brain_spec_base.observations_base();
  CheckObservationState(observations_base);
  ActionsBase& actions_base = brain_spec_base.actions_base();
  proto::Step step;
  *step.mutable_observation() =
      ObservationProtoConverter::ToObservationData(observations_base);
  ResetObservationsState(observations_base);
  if (actions_base.source() == ActionsBase::kSourceHumanDemonstration &&
      data_->session->type() == Session::Type::kTypeEvaluation) {
    LogWarning(
        "Human demostration detected in episode %s, step %d of evaluation "
        "session %s."
        " For an evaluation session to make progress, it should entirely "
        "consist of brain actions.",
        id(), data_->current_step, data_->session->id());
  }
  CheckActionDataState(actions_base);
  *step.mutable_action() = ActionProtoConverter::ToActionData(actions_base);
  ResetActionDataState(actions_base);
  if (reward) {
    step.mutable_reward()->set_reward_value(*reward);
  }
  step.set_timestamp_millis(absl::ToUnixMillis(absl::Now()));
  auto& core = core::FalkenCore::Get();
  proto::Session session_proto = core.ToSession(
      session.id(), session.brain().id(), session.brain().snapshot_id());

  auto status = core.StepEpisode(brain_spec_base, session_proto,
                                 data_->episode_id.c_str(), std::move(step),
                                 &session);

  if (status.ok() &&
      (actions_base.source() == ActionsBase::kSourceHumanDemonstration) &&
      (session.training_state() ==
       Session::TrainingState::kTrainingStateComplete)) {
    if (data_->session->type() == Session::Type::kTypeEvaluation) {
      session.set_training_state(
          Session::TrainingState::kTrainingStateEvaluating);
    } else {
      session.set_training_state(
          Session::TrainingState::kTrainingStateTraining);
    }
    session.set_training_progress(0);
  }

  if (data_->session->type() == Session::Type::kTypeEvaluation &&
      actions_base.source() != ActionsBase::kSourceBrainAction) {
    LogError(
        "No brain action generated in evaluation session %s, episode %s at "
        "step %d. %s",
        data_->session->id(), id(), data_->current_step, kContactFalkenTeamBug);
  }

  if (!status.ok()) {
    LogError("Step failed. %s", status.ToString().c_str());
    return false;
  }
  ++data_->current_step;
  return true;
}

bool Episode::completed() const { return data_->completed; }

bool Episode::Complete(Episode::CompletionState state) {
  return Complete(state, false);
}

Session& Episode::session() const {
  FALKEN_ASSERT_MESSAGE(data_->session,
                        "Session was destroyed before episode %s", id());
  return *data_->session;
}

bool Episode::Complete(CompletionState state, bool gave_up) {
  if (IsReadOnly()) {
    LogError("Episode %s is read-only so can not be completed. To "
             "add more experience to the brain, create a new session.", id());
    return false;
  }
  if (state == Episode::kCompletionStateInvalid) {
    LogError("It is not possible to complete episode %s with the 'Invalid' "
             "completion state. To complete the episode use a valid "
             "completion state.", id());
    return false;
  }
  if (completed()) {
    LogWarning("Episode %s is already complete. To add more experience to "
               "the brain, create a new episode.", id());
    return true;
  }
  if (!data_->session) {
    LogError("Unable to complete episode %s as the associated session has been "
             "destroyed. To add more experience to the brain, create a new "
             "session.", id());
    return false;
  }
  if (data_->session->type() == Session::Type::kTypeEvaluation &&
      state != Episode::CompletionState::kCompletionStateSuccess &&
      state != Episode::CompletionState::kCompletionStateFailure) {
    LogWarning(
        "Evaluation session episode %s was completed with state %d which "
        "results in the episode being ignored. Evaluation session episodes "
        "must be completed with either success or failure for the evaluation "
        "process to progress.",
        id(), state);
  }
  Session& session = this->session();
  auto& core = core::FalkenCore::Get();
  proto::Session session_proto = core.ToSession(
      session.id(), session.brain().id(), session.brain().snapshot_id());

  falken::common::StatusOr<proto::SessionInfo> session_info_or =
      core.FinishEpisode(session_proto, id(), ToEpisodeState(state, gave_up),
                         &session);
  // in ga_mode this will be the only call to UpdateSessionState. In non ga_mode
  // will get called with TRAINING mode and progress 0, and later the callback
  // will be called again with the actual value returned by the service.
  core::ActiveEpisode::UpdateSessionState(session_info_or, id(), &session,
                                          true);
  data_->completed = true;
  return session_info_or.ok();
}

int Episode::GetStepCount() const {
  if (!IsReadOnly()) {
    return static_cast<int>(data_->current_step);
  }
  if (!data_->session) {
    LogError("The session associated with episode %s has been destroyed. "
             "To read the number of episode steps, fetch a new session and "
             "refetch this episode.", id());
    return 0;
  }
  int ep = FindEpisodeDataIndex();
  if (ep < 0) {
    return 0;
  }
  return session().data_->episodes[ep].steps().size();
}

bool Episode::ReadStep(int index) {
  if (!data_->session) {
    LogError("The session associated with episode %s has been destroyed. "
             "To read episode data, fetch a new session and refetch this "
             "episode.", id());
    return false;
  }
  int ep = FindEpisodeDataIndex();
  if (ep < 0) {
    return false;
  }

  const Session& session = this->session();
  const proto::Episode& episode = session.data_->episodes[ep];

  // Check step index is valid.
  int number_of_steps = episode.steps().size();
  if (index < 0 || index >= number_of_steps) {
    LogError("Episode %s has %d steps, the requested step %d is out of range. "
             "Specify a step index less than %d.", id(), number_of_steps,
             index, number_of_steps);
    return false;
  }
  const proto::Step& step = episode.steps(index);

  // Load reward value.
  data_->reward = step.reward().reward_value();

  // Load brain with retrieved data.
  BrainSpecBase& brain_spec_base = session.brain().brain_spec_base();
  bool status = ObservationProtoConverter::FromObservationData(
      step.observation(), brain_spec_base.observations_base());
  if (step.action().actions_size() > 0) {
    status = ActionProtoConverter::FromActionData(
        step.action(), brain_spec_base.actions_base()) && status;
  }
  return status;
}

int Episode::FindEpisodeDataIndex() const {
  // Check session data is available.
  const Session& session = this->session();
  const auto& session_data = session.data_;
  if (!session_data || session_data->episodes.empty()) {
    LogError("Session %s has no data, unable to fetch data for episode %s. "
             "Try fetching the session again.", session.id(), id());
    return -1;
  }

  // Locate episode in session data.
  int index = 0;
  const std::vector<proto::Episode>& episodes = session_data->episodes;
  for (const auto& episode : episodes) {
    if (strcmp(id(), episode.episode_id().c_str()) == 0) {
      return index;
    }
    index++;
  }

  LogError("Episode %s not found in session %s. Try fetching the session again."
           , id(), session.id());
  return -1;
}

Episode::Episode(const std::weak_ptr<Session>& session, const char* episode_id,
                 bool read_only)
    : data_(new EpisodeData(session, episode_id, read_only)) {}

bool Episode::IsReadOnly() const { return data_->read_only; }

float Episode::reward() const { return data_->reward; }

const char* Episode::id() const { return data_->episode_id.c_str(); }

std::weak_ptr<Episode>& Episode::WeakThis() { return data_->weak_this; }

void Episode::CheckEntityAttributeSetModification(
    const EntityBase* entity) const {
  std::vector<std::string> unmodified_attribute_names;
  if (entity->HasUnmodifiedAttributes(unmodified_attribute_names)) {
    LogWarning(
        absl::StrCat("Attributes [",
                     absl::StrJoin(unmodified_attribute_names, ", "),
                     "] of entity %s are not set. To fix this issue, set "
                     "attributes to a valid value before stepping an episode.")
            .c_str(),
        entity->name());
  }
}

void Episode::CheckObservationState(
    const ObservationsBase& observation_base) const {
  for (const EntityBase* entity_base : observation_base.entities()) {
    CheckEntityAttributeSetModification(entity_base);
  }
}

void Episode::ResetObservationsState(ObservationsBase& observation_base) {
  EntityBase* player_entity = &observation_base;
  player_entity->reset_attributes_dirty_flags();
  for (EntityBase* entity_base : observation_base.entities()) {
    entity_base->reset_attributes_dirty_flags();
  }
}

void Episode::CheckActionDataState(const ActionsBase& action_base) const {
  std::vector<std::string> unmodified_attribute_names;
  if (action_base.HasUnmodifiedAttributes(unmodified_attribute_names)) {
    LogWarning(absl::StrCat(
                   "Action data has been partly provided, but the attributes [",
                   absl::StrJoin(unmodified_attribute_names, ", "),
                   "] have not been set to valid values. To fix this issue, "
                   "when providing action data set all attributes to valid "
                   "values before stepping an episode.")
                   .c_str());
  }
}

void Episode::ResetActionDataState(ActionsBase& action_base) {
  AttributeContainer& action_attributes = action_base;
  action_attributes.reset_attributes_dirty_flags();
}

std::string Episode::model_id() const {
  Session& session = this->session();
  auto& core = core::FalkenCore::Get();
  auto session_proto = core.ToSession(session.id(), session.brain().id(),
                                      session.brain().snapshot_id());
  auto episode_model_id =
      core.GetEpisodeModelId(session_proto, data_->episode_id);
  return episode_model_id;
}

}  // namespace falken
