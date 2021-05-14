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

#include "falken/session.h"

#include <algorithm>
#include <memory>
#include <vector>

#include "src/core/active_session.h"
#include "src/core/assert.h"
#include "src/core/falken_core.h"
#include "src/core/globals.h"
#include "src/core/log.h"
#include "src/core/protos.h"
#include "falken/episode.h"
#include "falken/service.h"
#include "src/core/session_internal.h"

namespace falken {
namespace {

const char* SessionTypeToString(falken::Session::Type type) {
  switch (type) {
    case falken::Session::Type::kTypeInvalid:
      return "Invalid";
    case falken::Session::Type::kTypeInteractiveTraining:
      return "\"Interactive Training\"";
    case falken::Session::Type::kTypeInference:
      return "\"Inference\"";
    case falken::Session::Type::kTypeEvaluation:
      return "\"Evaluation\"";
    default:
      return "Type does not exist";
  }
}

const char* SessionTrainingStateToString(
    falken::Session::TrainingState training_state) {
  switch (training_state) {
    case falken::Session::TrainingState::kTrainingStateInvalid:
      return "Invalid";
    case falken::Session::TrainingState::kTrainingStateTraining:
      return "\"Training\"";
    case falken::Session::TrainingState::kTrainingStateComplete:
      return "\"Complete\"";
    case falken::Session::TrainingState::kTrainingStateEvaluating:
      return "\"Evaluating\"";
    default:
      return "Training state does not exist";
  }
}

}  // namespace

Session::Session(const std::weak_ptr<BrainBase>& brain,
                 uint32_t total_steps_per_episode, const char* id, Type type,
                 uint64_t time)
    : data_(new SessionData(brain, total_steps_per_episode, id, type, time)) {}

Session::~Session() {
  FALKEN_LOCK_GLOBAL_MUTEX();
  if (!stopped()) {
    // if we are destroying a session that has not been properly stopped,
    // then do an async stop (one that does not wait for tasks that are still
    // queued to complete)
    Stop(false);
  }
}

std::shared_ptr<Episode> Session::StartEpisode() {
  if (!data_->brain) {
    LogError(
        "StartEpisode failed for session %s: cannot start an episode as "
        "the associated brain has been destroyed.",
        id());
    return std::shared_ptr<Episode>();
  }
  if (IsReadOnly()) {
    LogError(
        "Unable to start an episode for read-only session %s. Create a "
        "new session to add experience to the brain.",
        id());
    return std::shared_ptr<Episode>();
  }
  auto& brain = this->brain();
  auto& core = core::FalkenCore::Get();
  common::StatusOr<std::string> episode_or =
      core.CreateEpisode(core.ToSession(id(), brain.id(), brain.snapshot_id()));
  if (!episode_or.ok()) {
    LogError("Failed to start episode for session %s: %s. %s.", id(),
             episode_or.ToString().c_str(), kContactFalkenTeam);
    return std::shared_ptr<Episode>();
  }
  std::shared_ptr<Episode> episode(
      new Episode(data_->weak_this, episode_or.ValueOrDie().c_str(), false));
  AddEpisode(episode);
  return episode;
}

String Session::Stop() {
  // Stopping the session from the public interface causes a sync
  // stop which blocks until all previously queued tasks have been
  // executed by the background thread
  return Stop(true);
}

String Session::Stop(bool synchronous_stop) {
  if (!data_->brain) {
    LogError(
        "Stop failed for session %s: cannot stop the session as the associated "
        "brain has been destroyed.",
        id());
    return String();
  }
  if (IsReadOnly()) {
    LogError(
        "Unable to stop read-only session %s. Create a new session to "
        "add more experience to the brain.",
        id());
    return String();
  }
  if (state().empty()) {
    LogWarning(
        "Falken has not trained a brain for session %s, this results in a "
        "brain that performs no actions. You need to keep the session open and "
        "submit more episodes to train the brain.",
        id());
  } else if (training_state() == kTrainingStateTraining) {
    LogWarning(
        "Falken has not finished training the brain for session %s. This can "
        "result in a brain that is less effective at completing assigned "
        "tasks. You need to keep the session open, submitting episodes without "
        "human demonstrations for training to progress to completion. You can "
        "query the session object to retrieve the training state.",
        id());
  }
  BrainBase& brain = this->brain();
  if (stopped()) {
    LogWarning("Session %s for brain %s has already been stopped.", id(),
               brain.info().c_str());
    return String();
  }
  // We have to abort episodes before destroying the session. Otherwise an
  // error will rise stating that the episode could not be completed.
  for (const auto& episode : data_->created_episodes.GetChildren()) {
    if (!episode->completed()) {
      // We don't have to log anything here since that it's done in the
      // Complete method.
      episode->Complete(Episode::kCompletionStateAborted);
    }
  }
  auto& core = core::FalkenCore::Get();
  falken::common::StatusOr<std::string> snapshot_or = core.StopSession(
      core.ToSession(id(), brain.id(), brain.snapshot_id()), synchronous_stop);
  if (!snapshot_or.ok()) {
    LogError("Failed to stop session %s for brain %s: %s. %s.", id(),
             brain.info().c_str(), snapshot_or.ToString().c_str(),
             kContactFalkenTeam);
    return String();
  }
  data_->active_session = false;
  String snapshot_id(snapshot_or.ValueOrDie().c_str());
  if (!snapshot_id.empty()) {
    LogVerbose("Updating snapshot id of brain %s to %s.", brain.info().c_str(),
               snapshot_or.ToString().c_str());
    brain.UpdateSnapshotId(snapshot_id.c_str());
  }
  return snapshot_id;
}

BrainBase& Session::brain() const {
  FALKEN_ASSERT_MESSAGE(data_->brain,
                        "Associated brain has been destroyed for session %s.",
                        id());
  return *data_->brain;
}

int Session::GetEpisodeCount() const {
  if (!LoadSessionData()) {
    return 0;
  }
  return data_->episodes.size();
}

std::shared_ptr<falken::Episode> Session::GetEpisode(int index) {
  if (!LoadSessionData()) {
    return std::shared_ptr<Episode>();
  }

  // Check range.
  int number_of_episodes = data_->episodes.size();
  if (index < 0 || index >= number_of_episodes) {
    LogError(
        "Requested episode %d of session %s is not available. Select an "
        "episode at index < %d.",
        index, id(), number_of_episodes);
    return std::shared_ptr<Episode>();
  }

  std::shared_ptr<Episode> episode =
      LookupEpisode(data_->episodes[index].episode_id().c_str());
  if (episode) {
    return episode;
  }

  // Return a read-only episode.
  episode = std::shared_ptr<Episode>(new Episode(
      data_->weak_this, data_->episodes[index].episode_id().c_str(), true));
  AddEpisode(episode);
  return episode;
}

String Session::info() const {
  String session_info =
      "brain: " + data_->brain->info() + ", session: " + String(id()) +
      ", session_type: " + String(SessionTypeToString(type())) +
      ", session_training_state: " +
      String(SessionTrainingStateToString(training_state())) +
      ", session_training_progress: " +
      String(std::to_string(training_progress()).c_str()) +
      ", model: " + state();
  return session_info;
}

bool Session::LoadSessionData() const {
  if (!data_->brain) {
    LogError(
        "LoadSessionData failed for session %s: cannot load data for the "
        "session as the associated brain has been destroyed.",
        id());
    return false;
  }
  if (!data_->episodes.empty()) {
    return true;
  }

  BrainBase& brain = this->brain();
  auto episodes_or =
      core::FalkenCore::Get().GetSessionEpisodes(brain.id(), id());
  if (!episodes_or.ok()) {
    LogError("Failed to load session data for session %s: %s. %s.", id(),
             episodes_or.ToString().c_str(), kContactFalkenTeam);
    return false;
  }

  // Save loaded data.
  data_->episodes = episodes_or.ValueOrDie();
  return true;
}

bool Session::IsReadOnly() const { return data_->total_steps_per_episode == 0; }

String Session::state() const {
  auto* internal =
      !IsReadOnly() ? falken::core::GetSessionFromMap(id()) : nullptr;
  return internal ? internal->GetModelId().c_str() : String();
}

// Gets a weak_ptr form of this
std::weak_ptr<Session>& Session::WeakThis() { return data_->weak_this; }

void Session::AddEpisode(const std::shared_ptr<Episode>& episode) {
  data_->created_episodes.AddChild(episode, episode->WeakThis(), episode->id());
}

std::shared_ptr<Episode> Session::LookupEpisode(const char* id) const {
  return data_->created_episodes.LookupChild(id);
}

const char* Session::id() const { return data_->id.c_str(); }

Session::TrainingState Session::training_state() const {
  return data_->training_state;
}

void Session::set_training_state(Session::TrainingState state) {
  data_->training_state = state;
}

float Session::training_progress() const {
  return data_->training_progress;
}

void Session::set_training_progress(float training_progress) {
  data_->training_progress = training_progress;
}

Session::Type Session::type() const { return data_->type; }

int64_t Session::creation_time() const { return data_->creation_time; }

bool Session::stopped() const { return !data_->active_session; }

uint32_t Session::total_steps_per_episode() const {
  return data_->total_steps_per_episode;
}

std::string Session::model_id() const {
  auto* internal = falken::core::GetSessionFromMap(id());
  return internal->GetModelId();
}

}  // namespace falken
