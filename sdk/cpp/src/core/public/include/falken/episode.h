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

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_EPISODE_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_EPISODE_H_

#include <stdint.h>

#include <memory>
#include <string>

#include "falken/actions.h"
#include "falken/allocator.h"
#include "falken/config.h"
#include "falken/observations.h"

namespace falken {

class Session;
class ServiceTest;

/// An Episode represents a sequence of interactions with a clear beginning,
/// middle, and end (like starting a race, driving around the track, and
/// crossing the finish line)
class FALKEN_EXPORT Episode {
 public:
  friend class Session;
  friend class ServiceTest;

  /// Enum to indicate valid episode completion states.
  enum CompletionState {
    /// Invalid state, should never be set.
    kCompletionStateInvalid = 0,
    /// A brain completed the episode successfully.
    kCompletionStateSuccess = 2,
    /// A brain failed to complete the episode.
    kCompletionStateFailure = 3,
    /// The application aborted the episode. For example, if the game player
    /// exits the current level there was no way to complete the episode
    /// successfully so the episode should be completed with the aborted state.
    kCompletionStateAborted = 4,
  };

  /// Abort an episode if it isn't complete.
  ~Episode();

  /// Execute a step of the episode.
  ///
  /// Apply the current observations and actions (if any) of the brain
  /// associated with the episode. The actions are applied only if the source
  /// of them is not HumanProvided. It's not possible to execute a step of an
  /// episode after it is complete.
  ///
  /// @return true if the step was successfully executed, false otherwise.
  bool Step();

  /// Execute a step of the episode, applying a certain reward value.
  ///
  /// Apply the current observations and actions (if any) of the brain
  /// associated with the episode. The actions are applied only if the source
  /// of them is not HumanProvided. It's not possible to execute a step of an
  /// episode after it is complete.
  ///
  /// @param reward Reward value.
  /// @return true if the step was successfully executed, false otherwise.
  bool Step(float reward);

  /// Check if the episode has been completed.
  ///
  /// @return true if the episode has been completed, false otherwise.
  bool completed() const;

  /// Complete the episode.
  ///
  /// @param state Completion state of the episode.
  /// @return true if the completion was successfully executed, false otherwise.
  bool Complete(CompletionState state);

  /// Get the session that owns this episode.
  ///
  /// If the session was destroyed before this episode, this method will assert.
  ///
  /// @return Session that owns this episode.
  Session& session() const;

  /// Get the number of steps submitted in the episode.
  ///
  /// @return Number of steps submitted in the episode.
  int GetStepCount() const;

  /// Read a step from the episode by index storing the results in brain's
  /// observations and actions.
  ///
  /// @param index Step index.
  /// @return true if the reading was successfully executed, false otherwise.
  bool ReadStep(int index);

  /// Get the reward for the current step.
  ///
  /// @return Reward for the current step.
  float reward() const;

  /// Get the episode ID.
  ///
  /// @return ID of the episode.
  const char* id() const;

  FALKEN_DEFINE_NEW_DELETE

 private:
  Episode(const std::weak_ptr<Session>& session, const char* episode_id,
          bool read_only);

  // Overloaded version of the public Step methods that allows reward to be an
  // optional parameter.
  bool Step(float* reward);

  // Check observation attributes, and log warnings for unset values
  void CheckObservationState(const ObservationsBase& observation_base) const;

  // Check if all the attributes in an entity have been set and generate
  // a warning if that's not the case
  void CheckEntityAttributeSetModification(const EntityBase* entity) const;

  // Reset the modification flag in the attributes within action_base
  void ResetActionDataState(ActionsBase& action_base);

  // Checks if all the attributes in the training actions habe been set,
  // logs a warning if not.
  void CheckActionDataState(const ActionsBase& action_base) const;

  // Reset the modification flag in the attributes within the entities in
  // observation base
  void ResetObservationsState(ObservationsBase& observation_base);

  bool Complete(CompletionState state, bool gave_up);

  int FindEpisodeDataIndex() const;

  // Return whether the episode is read-only.
  bool IsReadOnly() const;

  // Provides a weak_ptr form of this
  std::weak_ptr<Episode>& WeakThis();

  // Get the model id used by the episode
  std::string model_id() const;

  FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_START
  // Private data.
  struct EpisodeData;
  std::unique_ptr<EpisodeData> data_;
  FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_END
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_EPISODE_H_
