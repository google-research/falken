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

#include "falken/service.h"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <memory>
#include <numeric>
#include <vector>

#include "src/core/active_session.h"
#include "falken/actions.h"
#include "falken/attribute_base.h"
#include "falken/brain.h"
#include "falken/brain_spec.h"
#include "falken/episode.h"
#include "falken/log.h"
#include "falken/observations.h"
#include "falken/session.h"
#include "src/core/stdout_logger.h"
#include "src/core/string_logger.h"
#include "src/core/temp_file.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "absl/status/status.h"
#include "absl/strings/str_format.h"
#include "absl/time/time.h"

ABSL_FLAG(std::string, env, "dev",
          "The environment for running the test.");

ABSL_FLAG(std::string, api_key, "",
          "The API key used to authorize access to the Falken API.");

using ::testing::AllOf;
using ::testing::Eq;
using ::testing::Field;
using ::testing::FloatEq;
using ::testing::Matcher;
using ::testing::MatcherInterface;
using ::testing::MatchResultListener;
using ::testing::Property;
using ::testing::StrEq;
using ::testing::StrNe;

namespace falken {

class ServiceTest {
 public:
  static String GetSessionState(Session& session) { return session.state(); }

  static bool MatchesBrainSpec(const falken::BrainSpecBase& brain_spec,
                               const falken::BrainSpecBase& other_brain_spec) {
    return falken::BrainBase::MatchesBrainSpec(brain_spec, other_brain_spec);
  }

  static std::string GetSessionModelId(Session& session) {
    return session.model_id();
  }

  static std::string GetEpisodeModelId(Episode& episode) {
    return episode.model_id();
  }
};

}  // namespace falken

namespace {

constexpr uint64_t kStepsPerEpisode = 10;
// Threshold to consider actions as equal.
constexpr float kDeltaMaxAverageError = 0.02f;
const char* kProjectId = "Test_Project";
const char* kBrainDisplayName = "test_brain";

std::string GetJSONConfig(const std::string& api_key = "",
                          const std::string& env = "") {
  return absl::StrFormat(
      "{\n"
      "  \"project_id\": \"%s\",\n"
      "  \"api_key\": \"%s\",\n"
      "  \"api_call_timeout_milliseconds\": 120000,\n"
      "  \"service\": { \"environment\": \"%s\" }\n"
      "}\n",
      kProjectId,
      !api_key.empty() ? api_key : absl::GetFlag(FLAGS_api_key).c_str(),
      !env.empty() ? env : absl::GetFlag(FLAGS_env));
}

struct TestObservations : public falken::ObservationsBase {
 public:
  TestObservations()
      : FALKEN_NUMBER(health, 1.0f, 3.0f),
        FALKEN_NUMBER(angle_to_goal, -1.0f, 1.0f),
        FALKEN_NUMBER(distance_to_goal, 0.0f, 5.0f),
        FALKEN_NUMBER(angle_to_enemy, -1.0f, 1.0f),
        FALKEN_NUMBER(distance_to_enemy, 0.0f, 5.0f),
        FALKEN_CATEGORICAL(equipped_item, {"spoon", "cheese", "jam"}),
        FALKEN_FEELERS(feelers, 32, 5.0f, M_PI, 0.0f,
                       {"wall", "fruit_stand", "paper_stand", "enemy"}) {}

  falken::NumberAttribute<float> health;
  falken::NumberAttribute<int> angle_to_goal;
  falken::NumberAttribute<float> distance_to_goal;
  falken::NumberAttribute<int> angle_to_enemy;
  falken::NumberAttribute<float> distance_to_enemy;
  falken::CategoricalAttribute equipped_item;
  falken::FeelersAttribute feelers;
};

struct TestActions : public falken::ActionsBase {
 public:
  TestActions()
      : FALKEN_NUMBER(speed, 5.0f, 10.0f),
        FALKEN_NUMBER(steering, -5, 5),
        FALKEN_CATEGORICAL(select_item, {"spoon", "cheese", "jam"}),
        FALKEN_BOOL(use_item) {}

  falken::NumberAttribute<float> speed;
  falken::NumberAttribute<int> steering;
  falken::CategoricalAttribute select_item;
  falken::BoolAttribute use_item;
};

using TestTemplateBrainSpec = falken::BrainSpec<TestObservations, TestActions>;

struct TestEnemyEntityBase : public falken::EntityBase {
 public:
  TestEnemyEntityBase(falken::EntityContainer& container, const char* name)
      : falken::EntityBase(container, name),
        FALKEN_NUMBER(evilness, 1.0f, 5.0f) {}

  falken::NumberAttribute<float> evilness;
};

struct TestAllyEntityBase : public falken::EntityBase {
 public:
  TestAllyEntityBase(falken::EntityContainer& container, const char* name)
      : falken::EntityBase(container, name),
        FALKEN_CATEGORICAL(spells, {"dark", "ice"}) {}

  falken::CategoricalAttribute spells;
};

struct TestExtendedObservationsBase : public falken::ObservationsBase {
 public:
  TestExtendedObservationsBase()
      : ObservationsBase(),
        FALKEN_NUMBER(health, 1.0f, 3.0f),
        FALKEN_ENTITY(enemy_entity_base),
        FALKEN_ENTITY(ally_entity_base) {}

  falken::NumberAttribute<float> health;
  TestEnemyEntityBase enemy_entity_base;
  TestAllyEntityBase ally_entity_base;
};

using TestExtendedObservationsBrainSpec =
    falken::BrainSpec<TestExtendedObservationsBase, TestActions>;

// Get the range of a number attribute.
template <typename T>
T GetNumberAttributeRange(const falken::NumberAttribute<T>& attribute) {
  return attribute.value_maximum() - attribute.value_minimum();
}

// Get the normalized value of a number attribute.
template <typename T>
float GetNormalizedNumberAttributeValue(
    const falken::NumberAttribute<T>& attribute) {
  return static_cast<float>(attribute.value() - attribute.value_minimum()) /
         GetNumberAttributeRange(attribute);
}

// Calculate a number attribute's value from a linear interpolation of its'
// range given a "t" between 0.0f to 1.0f.
template <typename T>
T LerpNumberAttributeValue(const falken::NumberAttribute<T>& attribute,
                           float t) {
  return attribute.value_minimum() +
         static_cast<T>(GetNumberAttributeRange(attribute) * t);
}

float GenerateSpeedAction(TestActions& actions,
                          const TestObservations& observations,
                          float observation_scale) {
  return LerpNumberAttributeValue(
      actions.speed,
      (1.0f - GetNormalizedNumberAttributeValue(observations.health)) *
          observation_scale);
}

// Populates actions with training data for a step of an episode.
// observation_scale, scales each normalized observation value before
// calculating the action based upon the observations.
void TrainingActions(const TestObservations& observations, int step_index,
                     int number_of_steps_per_episode, TestActions& actions,
                     float observation_scale = 1.0f) {
  ASSERT_TRUE(actions.speed.set_value(
      GenerateSpeedAction(actions, observations, observation_scale)));

  float normalized_distance_to_goal =
      GetNormalizedNumberAttributeValue(observations.distance_to_goal) *
      observation_scale;
  float normalized_distance_to_enemy =
      GetNormalizedNumberAttributeValue(observations.distance_to_enemy);
  // Steering aims at either the goal or the enemy depending upon which
  // is closer.
  ASSERT_TRUE(actions.steering.set_value(LerpNumberAttributeValue(
      actions.steering,
      normalized_distance_to_enemy < normalized_distance_to_goal
          ? normalized_distance_to_enemy
          : normalized_distance_to_goal)));

  // Find the closest feeler ID.
  float closest_feeler_distance = std::numeric_limits<float>::max();
  int closest_feeler_id = -1;
  {
    const auto& feelers_distances = observations.feelers.distances();
    const auto& feelers_ids = observations.feelers.ids();
    for (int i = 0; i < feelers_distances.size(); ++i) {
      if (static_cast<float>(feelers_distances[i]) < closest_feeler_distance) {
        closest_feeler_distance =
            GetNormalizedNumberAttributeValue(feelers_distances[i]) *
            observation_scale;
        closest_feeler_id = feelers_ids[i];
      }
    }
  }

  // Select an item based upon the closest entity or feeler.
  int select_item;
  if (closest_feeler_distance < normalized_distance_to_goal &&
      closest_feeler_distance < normalized_distance_to_enemy &&
      closest_feeler_id == 1 /* fruit_stand */) {
    select_item = 0 /* spoon */;
  } else {
    select_item = (normalized_distance_to_enemy < normalized_distance_to_goal
                       ? /* cheese */ 1
                       : /* jam */ 2);
  }
  ASSERT_TRUE(actions.select_item.set_value(select_item));

  // Use an item when the closest entity is within 10% of the total distance
  // range.
  const float kUseItemRange = 0.1f * observation_scale;
  ASSERT_TRUE(actions.use_item.set_value(
      normalized_distance_to_enemy <= kUseItemRange ||
      normalized_distance_to_goal <= kUseItemRange));
}

// Populates a spec with training data for a step of an episode.
// Returns a normalized "speed" action.
float TrainingData(TestTemplateBrainSpec& spec, int step_index,
                   int number_of_steps_per_episode, bool provide_action = true,
                   float observation_scale = 1.0f) {
  // Linearly map observations to actions across each episode.
  float phase = static_cast<float>(step_index) /
                static_cast<float>(number_of_steps_per_episode);
  float inverse_phase = 1.0f - phase;

  auto& observations = spec.observations;
  EXPECT_TRUE(observations.health.set_value(
      LerpNumberAttributeValue(observations.health, inverse_phase)));
  // Goal is "phase" angle from the player and starts far away from the player
  // and moves closer.
  EXPECT_TRUE(observations.angle_to_goal.set_value(
      LerpNumberAttributeValue(observations.angle_to_goal, phase)));
  EXPECT_TRUE(observations.distance_to_goal.set_value(
      LerpNumberAttributeValue(observations.distance_to_goal, inverse_phase)));

  // Enemy is "inverse_phase" angle from the player and starts close moving
  // further away.
  EXPECT_TRUE(observations.angle_to_enemy.set_value(
      LerpNumberAttributeValue(observations.angle_to_enemy, inverse_phase)));
  EXPECT_TRUE(observations.distance_to_enemy.set_value(
      LerpNumberAttributeValue(observations.distance_to_enemy, phase)));

  // Equipped item depends upon whether the player is close to the goal or
  // enemy.
  EXPECT_TRUE(observations.equipped_item.set_value(
      (float)observations.distance_to_enemy <
              (float)observations.distance_to_goal
          ? /* cheese */ 1
          : /* jam */ 2));

  // Set no position and an identity rotation.
  observations.position.set_value(falken::Position(0.0f, 0.0f, 0.0f));
  observations.rotation.set_value(falken::Rotation(0.0f, 0.0f, 0.0f, 1.0f));

  // Generate some sinusoidal feelers that change based upon the phase.
  // The feeler at each angle is constant regardless of phase.
  auto& feelers_distances = observations.feelers.distances();
  auto& feelers_ids = observations.feelers.ids();
  for (int i = 0; i < feelers_distances.size(); ++i) {
    float offset = phase + (static_cast<float>(i) / feelers_distances.size());
    EXPECT_TRUE(feelers_distances[i].set_value(LerpNumberAttributeValue(
        feelers_distances[i], (sin(offset * 2.0f * M_PI) + 1.0f) * 0.5f)));
    EXPECT_TRUE(
        feelers_ids[i].set_value(i % feelers_ids[i].categories().size()));
  }
  if (provide_action) {
    TrainingActions(observations, step_index, number_of_steps_per_episode,
                    spec.actions, observation_scale);
    return spec.actions.speed;
  }
  return GenerateSpeedAction(spec.actions, observations, observation_scale) /
         GetNumberAttributeRange(spec.actions.speed);
}

enum TrainingMode {
  // Don't wait for training to complete.
  kTrainingModeNoWaiting = 0,
  // Wait until trained to completion.
  kTrainingModeUntilComplete,
  // Wait until a snapshot is available.
  kTrainingModeUntilSnapshot,
};

// Wait for training to advance to a valid state so that when the
// session is closed a snapshot can be generated.
absl::Status WaitForTrainingToComplete(
    std::shared_ptr<falken::Session>& session,
    std::shared_ptr<falken::Brain<TestTemplateBrainSpec>>& brain,
    const falken::String& initial_session_state, int session_state_transitions,
    TrainingMode training_mode, float completion_threshold = 0.0f) {
  if (training_mode == kTrainingModeNoWaiting) {
    std::cerr << "Not waiting for training session " << session->id()
              << " to complete\n";
    return absl::OkStatus();
  }
  falken::String current_session_state(initial_session_state);
  // Wait for training to advance to a valid state so that when the session is
  // closed a snapshot can be generated.
  const int kTrainingPollIntervalMilliseconds = 1000;
  int state_transitions = 0;
  int timeout = 300 * kTrainingPollIntervalMilliseconds;
  float max_training_progress = 0;
  absl::Time start = absl::Now();
  std::cerr << "Waiting for training session " << session->id()
            << " to complete.\n";
  bool ok;
  while (timeout > 0) {
    bool training_complete =
        session->training_state() == falken::Session::kTrainingStateComplete;
    falken::String new_state(falken::ServiceTest::GetSessionState(*session));
    if (new_state != current_session_state) {
      std::cerr << "  ... state transition: " << current_session_state
                << " --> " << new_state << "\n";
      current_session_state = new_state;
      state_transitions++;
    }
    training_complete =
        training_complete || (training_mode == kTrainingModeUntilSnapshot &&
                              state_transitions > session_state_transitions &&
                              max_training_progress >= completion_threshold);

    if (session->training_progress() > max_training_progress) {
      std::cerr << "  ... training progress: " << max_training_progress * 100
                << " % complete.\n";
    }
    max_training_progress = std::max(session->training_progress(),
                                     max_training_progress);
    if (max_training_progress > 1) {
      return absl::InternalError(absl::StrCat(
        "Training progress is over 100%: ", max_training_progress));
    }

    if (training_complete) break;

    // Submit empty episodes with no training data to poll the training state.
    std::shared_ptr<falken::Episode> episode = session->StartEpisode();
    EXPECT_TRUE(episode);
    if (!episode) {
      return absl::InternalError("Could not create episode.");
    }
    // We need to submit at least one step to workaround the service returning
    // an error.
    TrainingData(brain->brain_spec(), 0, 1);
    brain->brain_spec().actions.set_source(falken::ActionsBase::kSourceNone);
    EXPECT_TRUE(ok = episode->Step());
    if (!ok) {
      return absl::InternalError("Could not step episode.");
    }
    EXPECT_TRUE(
        ok = episode->Complete(falken::Episode::kCompletionStateAborted));
    if (!ok) {
      return absl::InternalError("Could not complete episode.");
    }
    absl::SleepFor(absl::Milliseconds(kTrainingPollIntervalMilliseconds));
    timeout -= kTrainingPollIntervalMilliseconds;
    if (timeout <= 0) {
      // This isn't a hard timeout at the moment as need to optimize stopping
      // parameters.
      std::cerr << "Timed out while waiting for training to complete.\n";
    }
  }
  // Training progress can restart as submitted episodes are processed by the
  // service, so just make sure that the service reports that it has made some
  // progress.
  if (completion_threshold > 0.0f) {
    EXPECT_TRUE(ok = max_training_progress > 0.0f);
    EXPECT_TRUE(ok = session->training_progress() > 0.0f);
    if (!ok) {
      return absl::InternalError("No training progress was reported.");
    }
  }
  std::cerr << "Training session " << session->id() << " completed in "
            << absl::ToDoubleSeconds(absl::Now() - start) << "s with "
            << state_transitions << " state transitions.\n";
  return absl::OkStatus();
}

// Simulates a train session by training the data as much as training
// steps are provided.
absl::Status TrainSession(
    std::shared_ptr<falken::Session>& session,
    std::shared_ptr<falken::Brain<TestTemplateBrainSpec>>& brain,
    int number_of_episodes, int number_of_steps_per_episode,
    TrainingMode training_mode, int session_state_transitions = 0,
    float completion_threshold = 0.0f, float observation_scale = 1.0f) {
  auto initial_state = falken::ServiceTest::GetSessionState(*session);

  // Train with some generated data.
  for (int ep = 0; ep < number_of_episodes; ++ep) {
    std::shared_ptr<falken::Episode> episode = session->StartEpisode();
    EXPECT_TRUE(episode);
    if (!episode) {
      return absl::InternalError("Could not create episode.");
    }
    for (int st = 0; st < number_of_steps_per_episode; ++st) {
      TrainingData(brain->brain_spec(), st, number_of_steps_per_episode, true,
                   observation_scale);
      bool ok;
      EXPECT_TRUE(ok = episode->Step());
      if (!ok) {
        return absl::InternalError("Could not step episode.");
      }
    }
    bool ok;
    EXPECT_TRUE(
        ok = episode->Complete(falken::Episode::kCompletionStateSuccess));
    if (!ok) {
      return absl::InternalError("Could not complete episode.");
    }
  }
  RETURN_IF_ERROR(WaitForTrainingToComplete(
      session, brain, initial_state,
      session_state_transitions, training_mode,
      completion_threshold));
  return absl::OkStatus();
}

// Infer actions in an episode, calculating the average normalized error
// inferred speed actions.
absl::Status RunInferenceEpisode(
    std::shared_ptr<falken::Brain<TestTemplateBrainSpec>>& brain,
    std::shared_ptr<falken::Episode>& episode, int number_of_steps_per_episode,
    float& average_episode_error) {
  auto& brain_spec = brain->brain_spec();
  average_episode_error = 0.0f;
  for (int step = 0; step < number_of_steps_per_episode; ++step) {
    // Provide observations
    float expected_normalized_action =
        TrainingData(brain_spec, step, number_of_steps_per_episode, false);
    // Step the episode
    bool step_ok = episode->Step();
    EXPECT_TRUE(step_ok);
    if (!step_ok) {
      return absl::InternalError("Could not step episode.");
    }
    // Store the inferred action.
    float inferred_normalized_action =
        brain_spec.actions.speed /
        GetNumberAttributeRange(brain_spec.actions.speed);
    // Calculate the error.
    average_episode_error += std::fabs(inferred_normalized_action -
                                       expected_normalized_action);
  }
  average_episode_error /= number_of_steps_per_episode;
  return absl::OkStatus();
}

// Runs the inference mode by providing observations to the brain.
absl::Status RunInference(
    std::shared_ptr<falken::Session>& session,
    std::shared_ptr<falken::Brain<TestTemplateBrainSpec>>& brain,
    int number_of_episodes, int number_of_steps_per_episode,
    float* error = nullptr, bool check_minimum_average_error = true) {
  float minimum_average_error = std::numeric_limits<float>::max();

  absl::Duration time_stepping = absl::ZeroDuration();
  for (int ep = 0; ep < number_of_episodes; ++ep) {
    float average_episode_error;
    std::shared_ptr<falken::Episode> episode = session->StartEpisode();
    absl::Time before = absl::Now();

    absl::Status episode_ok = RunInferenceEpisode(
        brain, episode, number_of_steps_per_episode, average_episode_error);
    if (!episode_ok.ok()) return episode_ok;

    absl::Duration episode_step_duration = (absl::Now() - before);
    time_stepping += episode_step_duration;

    if (!episode->Complete(falken::Episode::kCompletionStateSuccess)) {
      return absl::InternalError("Could not close episode.");
    }
    std::cerr << "Performed " << number_of_steps_per_episode
              << " Step calls in "
              << absl::ToDoubleMilliseconds(episode_step_duration) << "ms "
              << "(excluding time spent in Complete calls)." << std::endl;

    // Keep track of the minimum average error.
    minimum_average_error =
        std::min(average_episode_error, minimum_average_error);

    // Check that the inferred actions are below the acceptance error.
    if (check_minimum_average_error) {
      EXPECT_LE(minimum_average_error, kDeltaMaxAverageError);
    }
  }
  // Print the overall speed stepping through episodes.
  int total_steps = number_of_episodes * number_of_steps_per_episode;
  std::cerr << "Overall speed: "
            << std::to_string(total_steps /
                              absl::ToDoubleSeconds(time_stepping))
            << " Steps per second, "
            << absl::ToDoubleMilliseconds(time_stepping / total_steps)
            << "ms per step." << std::endl;
  if (error) {
    *error = minimum_average_error;
  }
  return absl::OkStatus();
}

// Steps the evaluation session until it finishes. It also test that
// the eval session identifies the first model (the snapshot) to be the
// chosen model of the evaluation session.
absl::Status RunEvaluation(
    std::shared_ptr<falken::Session>& session,
    std::shared_ptr<falken::Brain<TestTemplateBrainSpec>>& brain,
    int number_of_episodes, int number_of_steps_per_episode,
    float passing_episode_average_error, float *eval_error) {
  float minimum_average_error = passing_episode_average_error;
  std::map<float, int> error_occurrence;

  for (int ep = 0; ep < number_of_episodes; ++ep) {
    float average_episode_error;
    std::shared_ptr<falken::Episode> episode = session->StartEpisode();
    EXPECT_TRUE(episode);
    EXPECT_NE(falken::Session::TrainingState::kTrainingStateInvalid,
              session->training_state());

    absl::Status episode_ok = RunInferenceEpisode(
        brain, episode, number_of_steps_per_episode, average_episode_error);
    if (!episode_ok.ok()) return episode_ok;

    // Add the error calculated to the occurrence dictionary.
    auto it = error_occurrence.find(average_episode_error);
    if (it != error_occurrence.end()) {
      ++error_occurrence[average_episode_error];
    } else {
      error_occurrence[average_episode_error] = 1;
    }

    // Keep track of the minimum average error.
    minimum_average_error =
        std::min(average_episode_error, minimum_average_error);

    // Check that the inferred actions are below the acceptance error.
    falken::Episode::CompletionState completion_state;
    std::string completion_type;
    if (average_episode_error <= minimum_average_error) {
      completion_state = falken::Episode::kCompletionStateSuccess;
      completion_type = "SUCCESS";
    } else {
      completion_state = falken::Episode::kCompletionStateFailure;
      completion_type = "FAILURE";
    }
    std::cerr << "Completing episode " << std::to_string(ep) << " as "
              << completion_type << ": "
              << "Average error per step "
              << std::to_string(average_episode_error)
              << ", current minimum average error per step "
              << std::to_string(minimum_average_error) << std::endl;
    bool complete_ok;
    EXPECT_TRUE(complete_ok = episode->Complete(completion_state));
    if (!complete_ok) {
      return absl::InternalError("Could not complete episode.");
    }
  }

  // Print out the occurrence of the error
  std::cerr << "Average error occurrence after evaluation: " << std::endl;
  // Verify that a variety of models were served to the client.
  EXPECT_GT(error_occurrence.size(), 1);
  for (auto it : error_occurrence) {
    std::cerr << std::to_string(it.first) << " episode[s] with error "
              << std::to_string(it.second) << std::endl;
  }

  if (eval_error) {
    *eval_error = minimum_average_error;
  }
  return absl::OkStatus();
}

class BrainAttributesEqMatcher
    : public MatcherInterface<const falken::BrainSpecBase&> {
 public:
  explicit BrainAttributesEqMatcher(
      const falken::BrainSpecBase& other_brain_spec)
      : other_brain_spec_(other_brain_spec) {}

  bool MatchAndExplain(const falken::BrainSpecBase& brain_spec,
                       MatchResultListener* listener) const override {
    if (!falken::ServiceTest::MatchesBrainSpec(brain_spec, other_brain_spec_)) {
      *listener << "Brain specs do not match.";
      return false;
    }

    if (!MatchAndExplainEntityContainers(brain_spec.observations_base(),
                                         other_brain_spec_.observations_base(),
                                         listener)) {
      return false;
    }

    if (!MatchAndExplainAttributeContainers(brain_spec.actions_base(),
                                            other_brain_spec_.actions_base(),
                                            listener)) {
      return false;
    }

    return true;
  }

  bool MatchAndExplainEntityContainers(
      const falken::EntityContainer& entity_container,
      const falken::EntityContainer& other_entity_container,
      MatchResultListener* listener) const {
    const auto& entities = entity_container.entities();
    const auto& other_entities = other_entity_container.entities();
    for (int i = 0; i < entities.size(); ++i) {
      if (!MatchAndExplainAttributeContainers(*entities[i], *other_entities[i],
                                              listener)) {
        *listener << "Attributes of entity " << i << " called "
                  << entities[i]->name() << " do not match.";
        return false;
      }
    }
    return true;
  }

  bool MatchAndExplainAttributeContainers(
      const falken::AttributeContainer& attribute_container,
      const falken::AttributeContainer& other_attribute_container,
      MatchResultListener* listener) const {
    const auto& attributes = attribute_container.attributes();
    const auto& other_attributes = other_attribute_container.attributes();
    for (int i = 0; i < attributes.size(); ++i) {
      if (!MatchAndExplainAttributes(*attributes[i], *other_attributes[i],
                                     listener)) {
        return false;
      }
    }
    return true;
  }

  bool MatchAndExplainAttributes(const falken::AttributeBase& attribute,
                                 const falken::AttributeBase& other_attribute,
                                 MatchResultListener* listener) const {
    switch (attribute.type()) {
      case falken::AttributeBase::kTypeUnknown:
        break;
      case falken::AttributeBase::kTypeFloat: {
        Matcher<float> m = FloatEq(attribute.number());
        if (!m.MatchAndExplain(other_attribute.number(), listener)) {
          *listener << "Attribute " << attribute.name() << " value "
                    << attribute.number() << " does not match "
                    << other_attribute.number();
          return false;
        }
        break;
      }
      case falken::AttributeBase::kTypeCategorical: {
        if (attribute.category() != other_attribute.category()) {
          *listener << "Attribute " << attribute.name() << " category "
                    << attribute.category() << " does not match "
                    << other_attribute.category();
          return false;
        }
        break;
      }
      case falken::AttributeBase::kTypeBool:
        if (attribute.boolean() != other_attribute.boolean()) {
          *listener << "Attribute " << attribute.name() << " bool value "
                    << attribute.boolean() << " does not match "
                    << other_attribute.boolean();
          return false;
        }
        break;
      case falken::AttributeBase::kTypePosition: {
        const auto& position = attribute.position();
        Matcher<falken::Position> m =
            AllOf(Field(&falken::Position::x, FloatEq(position.x)),
                  Field(&falken::Position::y, FloatEq(position.y)),
                  Field(&falken::Position::z, FloatEq(position.z)));
        if (!m.MatchAndExplain(other_attribute.position(), listener)) {
          *listener << "Attribute " << attribute.name() << " position "
                    << "does not match";
          return false;
        }
        break;
      }
      case falken::AttributeBase::kTypeRotation: {
        const auto& rotation = attribute.rotation();
        Matcher<falken::Rotation> m =
            AllOf(Field(&falken::Rotation::x, FloatEq(rotation.x)),
                  Field(&falken::Rotation::y, FloatEq(rotation.y)),
                  Field(&falken::Rotation::z, FloatEq(rotation.z)),
                  Field(&falken::Rotation::w, FloatEq(rotation.w)));
        if (!m.MatchAndExplain(other_attribute.rotation(), listener)) {
          *listener << "Attribute " << attribute.name() << " rotation "
                    << "does not match";
          return false;
        }
        break;
      }
      case falken::AttributeBase::kTypeFeelers: {
        for (int i = 0; i < attribute.feelers_distances().size(); ++i) {
          if (!MatchAndExplainAttributes(attribute.feelers_distances()[i],
                                         other_attribute.feelers_distances()[i],
                                         listener)) {
            *listener << "Attribute " << attribute.name() << " feelers "
                      << "distances do not match.";
          }
        }
        for (int i = 0; i < attribute.feelers_ids().size(); ++i) {
          if (!MatchAndExplainAttributes(attribute.feelers_ids()[i],
                                         other_attribute.feelers_ids()[i],
                                         listener)) {
            *listener << "Attribute " << attribute.name() << " feelers IDs "
                      << "do not match.";
          }
        }
        break;
      }
      case falken::AttributeBase::kTypeJoystick: {
        Matcher<falken::AttributeBase> m =
            AllOf(Property(&falken::AttributeBase::joystick_axes_mode,
                           Eq(attribute.joystick_axes_mode())),
                  Property(&falken::AttributeBase::joystick_control_frame,
                           Eq(attribute.joystick_control_frame())),
                  Property(&falken::AttributeBase::joystick_controlled_entity,
                           Eq(attribute.joystick_controlled_entity())),
                  Property(&falken::AttributeBase::joystick_x_axis,
                           FloatEq(attribute.joystick_x_axis())),
                  Property(&falken::AttributeBase::joystick_y_axis,
                           FloatEq(attribute.joystick_y_axis())));
        if (!m.MatchAndExplain(other_attribute, listener)) {
          *listener << "Attribute " << attribute.name() << " joystick "
                    << "does not match";
        }
        break;
      }
    }
    return true;
  }

  void DescribeTo(std::ostream* os) const override {
    *os << "Brain attributes match.";
  }

  void DescribeNegationTo(std::ostream* os) const override {
    *os << "Brain attributes do not match.";
  }

  const falken::BrainSpecBase& other_brain_spec_;
};

Matcher<const falken::BrainSpecBase&> BrainAttributesEq(
    const falken::BrainSpecBase& other_brain_spec) {
  return MakeMatcher(new BrainAttributesEqMatcher(other_brain_spec));
}

class BrainEqMatcher : public MatcherInterface<const falken::BrainBase&> {
 public:
  explicit BrainEqMatcher(const falken::BrainBase& other_brain)
      : other_brain_(other_brain) {}

  bool MatchAndExplain(const falken::BrainBase& brain,
                       MatchResultListener* listener) const override {
    if (strcmp(brain.id(), other_brain_.id()) != 0) {
      *listener << "Brain id: " << brain.id() << " does not match "
                << other_brain_.id();
      return false;
    }
    if (strcmp(brain.display_name(), other_brain_.display_name()) != 0) {
      *listener << "Brain name: " << brain.display_name() << " does not match "
                << other_brain_.display_name();
      return false;
    }
    if (!brain.MatchesBrainSpec(other_brain_.brain_spec_base())) {
      *listener << "Brain specs do not match";
      return false;
    }
    return true;
  }

  void DescribeTo(std::ostream* os) const override {
    *os << "Brains match one another.";
  }

  void DescribeNegationTo(std::ostream* os) const override {
    *os << "Brains do not match one another.";
  }

 private:
  const falken::BrainBase& other_brain_;
};

Matcher<const falken::BrainBase&> BrainEq(
    const falken::BrainBase& other_brain) {
  return MakeMatcher(new BrainEqMatcher(other_brain));
}

class SessionEqMatcher : public MatcherInterface<const falken::Session&> {
 public:
  explicit SessionEqMatcher(const falken::Session& other_session)
      : other_session_(other_session) {}

  bool MatchAndExplain(const falken::Session& session,
                       MatchResultListener* listener) const override {
    if (strcmp(session.id(), other_session_.id()) != 0) {
      *listener << "Session id: " << session.id() << " does not match "
                << other_session_.id();
      return false;
    }
    if (strcmp(session.brain().id(), other_session_.brain().id()) != 0) {
      *listener << "Session brain " << session.brain().id()
                << " does not match " << other_session_.brain().id();
      return false;
    }
    // TODO (b/172470796): Re-enable this once the session creation timestamp
    // bug is fixed.
    /*
    if (session.creation_time() != other_session_.creation_time()) {
      *listener << "Session creation time " << session.creation_time()
                << " does not match " << other_session_.creation_time();
      return false;
    }
    */
    if (session.training_state() != other_session_.training_state()) {
      *listener << "Session training state " << session.training_state()
                << " does not match " << other_session_.training_state();
      return false;
    }
    if (session.type() != other_session_.type()) {
      *listener << "Session type " << session.type() << " does not match "
                << other_session_.type();
      return false;
    }
    if (session.GetEpisodeCount() != other_session_.GetEpisodeCount()) {
      *listener << "Session Episode count " << session.GetEpisodeCount()
                << " does not match " << other_session_.GetEpisodeCount();
      return false;
    }
    return true;
  }

  void DescribeTo(std::ostream* os) const override {
    *os << "Sessions match one another.";
  }

  void DescribeNegationTo(std::ostream* os) const override {
    *os << "Sessions do not match one another.";
  }

 private:
  const falken::Session& other_session_;
};

Matcher<const falken::Session&> SessionEq(
    const falken::Session& other_session) {
  return MakeMatcher(new SessionEqMatcher(other_session));
}

class ServiceTemporaryDirectoryTest : public ::testing::Test {
 protected:
  void SetUp() override {
    // Save current system temporary directory.
    system_temporary_directory_ =
        falken::core::TempFile::GetSystemTemporaryDirectory();
    // Clear system temporary directory.
    EXPECT_TRUE(falken::core::TempFile::SetSystemTemporaryDirectory(
        stdout_logger_, std::string()));
  }

  void TearDown() override {
    // Restore saved system temporary directory.
    if (!system_temporary_directory_.empty()) {
      EXPECT_TRUE(falken::core::TempFile::SetSystemTemporaryDirectory(
          stdout_logger_, system_temporary_directory_));
    }
  }

  falken::StandardOutputErrorLogger stdout_logger_;
  std::string system_temporary_directory_;
  const std::string falken_temporary_dir_ = testing::TempDir();
};

TEST_F(ServiceTemporaryDirectoryTest, SetTemporaryDirectoryUsingApiTest) {
  EXPECT_TRUE(
      falken::Service::SetTemporaryDirectory(falken_temporary_dir_.c_str()));
  EXPECT_STREQ(falken::Service::GetTemporaryDirectory().c_str(),
               falken_temporary_dir_.c_str());
}

TEST_F(ServiceTemporaryDirectoryTest, SetTemporaryDirectoryUsingEnvVarTest) {
  setenv("FALKEN_TMPDIR", falken_temporary_dir_.c_str(), 1);
  // We need to call SetupSystemTemporaryDirectory in order to make the SDK look
  // for FALKEN_TMPDIR value.
  falken::core::TempFile::SetupSystemTemporaryDirectory(stdout_logger_);
  EXPECT_STREQ(falken::Service::GetTemporaryDirectory().c_str(),
               falken_temporary_dir_.c_str());
  unsetenv("FALKEN_TMPDIR");
}

// Basic integration test for the SDK.
class ServiceTest : public ::testing::Test {
 protected:
  // Pre-trained brain to use for test cases.
  struct TrainedBrainInfo {
    TrainedBrainInfo() : training_episodes(0), training_steps_per_episode(0) {}

    // Whether the brain has been trained.
    bool is_trained() const { return !brain_id.empty(); }

    // Connect to the service and get the brain with this ID at the specified
    // snapshot.
    std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> GetBrain() const;

    // Brain ID for the trained brain. Will be empty if the brain isn't trained.
    std::string brain_id;
    // Snapshot ID, will be empty if the brain isn't trained.
    std::string snapshot_id;
    // Number of episodes used to train the brain.
    int training_episodes;
    // Number of training steps in each episode used to train the brain.
    int training_steps_per_episode;
  };

 protected:
  // Allocate the pre-trained brain data structure.
  static void SetUpTestSuite();
  // Clean up pre-trained brain information.
  static void TearDownTestSuite();

  // Get or train a brain that can be used for all tests in the suite.
  static const TrainedBrainInfo& TrainOrGetTrainedBrainInfo();

  // Connect to the service using test credentials.
  static std::shared_ptr<falken::Service> ConnectToService();

 private:
  static TrainedBrainInfo* trained_brain_info_;
};

ServiceTest::TrainedBrainInfo* ServiceTest::trained_brain_info_;

void ServiceTest::SetUpTestSuite() {
  trained_brain_info_ = new TrainedBrainInfo();
}

void ServiceTest::TearDownTestSuite() {
  delete trained_brain_info_;
  trained_brain_info_ = nullptr;
}

const ServiceTest::TrainedBrainInfo& ServiceTest::TrainOrGetTrainedBrainInfo() {
  const int kTrainingEpisodes = 20;
  const int kTrainingStepsPerEpisode = 1000;
  const int kMinimumModelsRequired = 3;
  const float kTrainingFractionComplete = 0.3f;

  if (trained_brain_info_ && !trained_brain_info_->is_trained()) {
    // Connect to the service and create a brain.
    std::shared_ptr<falken::Service> service = ConnectToService();
    EXPECT_TRUE(service);
    if (service) {
      std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> brain =
          service->CreateBrain<TestTemplateBrainSpec>(kBrainDisplayName);
      EXPECT_TRUE(brain);
      if (!brain) {
        return *trained_brain_info_;
      }
      EXPECT_NE("", brain->id());

      if (brain && strlen(brain->id())) {
        // Train the brain.
        std::shared_ptr<falken::Session> session = brain->StartSession(
            falken::Session::Type::kTypeInteractiveTraining,
            kTrainingStepsPerEpisode);
        EXPECT_TRUE(session);
        if (session) {
          EXPECT_TRUE(
              TrainSession(session, brain, kTrainingEpisodes,
                           kTrainingStepsPerEpisode, kTrainingModeUntilSnapshot,
                           kMinimumModelsRequired, kTrainingFractionComplete)
                  .ok());
          const auto snapshot_id = session->Stop();
          EXPECT_NE("", snapshot_id.c_str());

          if (!snapshot_id.empty()) {
            trained_brain_info_->brain_id = brain->id();
            trained_brain_info_->snapshot_id = snapshot_id;
            trained_brain_info_->training_episodes = kTrainingEpisodes;
            trained_brain_info_->training_steps_per_episode =
                kTrainingStepsPerEpisode;
          }
        }
      }
    }
  }
  return *trained_brain_info_;
}

std::shared_ptr<falken::Brain<TestTemplateBrainSpec>>
    ServiceTest::TrainedBrainInfo::GetBrain() const {
  std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> brain;
  if (is_trained()) {
    auto service = ConnectToService();
    if (service) {
      brain = service->GetBrain<TestTemplateBrainSpec>(
          brain_id.c_str(),
          snapshot_id.c_str());
      EXPECT_TRUE(brain);
    }
  }
  return brain;
}

std::shared_ptr<falken::Service> ServiceTest::ConnectToService() {
  std::shared_ptr<falken::Service> service = falken::Service::Connect(
      kProjectId, absl::GetFlag(FLAGS_api_key).c_str(),
      GetJSONConfig().c_str());
  EXPECT_TRUE(service);
  return service;
}

TEST_F(ServiceTest, ConnectTestFails) {
  std::shared_ptr<falken::Service> service =
      falken::Service::Connect(nullptr, nullptr,
                               GetJSONConfig("invalid", "xyz").c_str());
  EXPECT_EQ(service, nullptr);
}

TEST_F(ServiceTest, ConnectTest) {
  std::shared_ptr<falken::Service> service = ConnectToService();
  EXPECT_TRUE(service);
}

TEST_F(ServiceTest, ConnectWithJsonConfig) {
  std::string json_config = GetJSONConfig();
  {
    auto service =
        falken::Service::Connect(nullptr, nullptr, json_config.c_str());
    EXPECT_TRUE(service);
  }
  {
    auto service = falken::Service::Connect("", "", json_config.c_str());
    EXPECT_TRUE(service);
  }
  {
    auto service =
        falken::Service::Connect(kProjectId, nullptr, json_config.c_str());
    EXPECT_TRUE(service);
  }
  {
    auto service = falken::Service::Connect(
        nullptr, absl::GetFlag(FLAGS_api_key).c_str(), json_config.c_str());
    EXPECT_TRUE(service);
  }
}

TEST_F(ServiceTest, CreateBrainBaseTest) {
  std::shared_ptr<falken::Service> service = ConnectToService();
  ASSERT_TRUE(service);
  TestObservations test_observations;
  test_observations.health.set_number(1.0f);
  TestActions test_actions;
  falken::BrainSpecBase brain_spec_base(&test_observations, &test_actions);
  std::shared_ptr<falken::BrainBase> brain_base =
      service->CreateBrain(kBrainDisplayName, brain_spec_base);
  ASSERT_TRUE(brain_base);
  EXPECT_NE(brain_base->id(), "");
  falken::ObservationsBase& brain_observation =
      brain_base->brain_spec_base().observations_base();
  EXPECT_TRUE(brain_observation.attribute("health")->set_number(2.0f));
  // Brain observation should have its own specification.
  EXPECT_NE(brain_observation.attribute("health")->number(),
            test_observations.health.value());
}

TEST_F(ServiceTest, CreateWrongBrainBaseTest) {
  std::shared_ptr<falken::Service> service =
      falken::Service::Connect(kProjectId, "ABC",
                               GetJSONConfig().c_str());
  ASSERT_TRUE(service);
  TestObservations test_observations;
  test_observations.health.set_number(1.0f);
  TestActions test_actions;
  falken::BrainSpecBase brain_spec_base(&test_observations, &test_actions);
  std::shared_ptr<falken::BrainBase> brain_base =
      service->CreateBrain(kBrainDisplayName, brain_spec_base);
  EXPECT_FALSE(brain_base);
}

TEST_F(ServiceTest, CreateTemplateBrainTest) {
  std::shared_ptr<falken::Service> service = ConnectToService();
  ASSERT_TRUE(service);
  std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> brain =
      service->CreateBrain<TestTemplateBrainSpec>(kBrainDisplayName);
  ASSERT_TRUE(brain);
  EXPECT_NE(brain->id(), "");
}

TEST_F(ServiceTest, LoadTemplateBrainTest) {
  std::shared_ptr<falken::Service> service = ConnectToService();
  ASSERT_TRUE(service);
  std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> brain =
      service->CreateBrain<TestTemplateBrainSpec>(kBrainDisplayName);
  ASSERT_TRUE(brain);
  ASSERT_NE(brain->id(), "");

  std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> loaded_brain =
      service->GetBrain<TestTemplateBrainSpec>(brain->id());
  ASSERT_TRUE(loaded_brain);
  EXPECT_THAT(loaded_brain->display_name(), StrEq(kBrainDisplayName));
  EXPECT_THAT(loaded_brain->id(), StrEq(brain->id()));
}

TEST_F(ServiceTest, StartSession) {
  std::shared_ptr<falken::Service> service = ConnectToService();
  ASSERT_TRUE(service);
  std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> brain =
      service->CreateBrain<TestTemplateBrainSpec>(kBrainDisplayName);
  ASSERT_TRUE(brain);
  std::shared_ptr<falken::Session> new_session = brain->StartSession(
      falken::Session::Type::kTypeInteractiveTraining, kStepsPerEpisode);
  ASSERT_TRUE(new_session);
  EXPECT_EQ(new_session->training_state(),
            falken::Session::TrainingState::kTrainingStateTraining);
  EXPECT_EQ(new_session->type(),
            falken::Session::Type::kTypeInteractiveTraining);
  EXPECT_EQ(&new_session->brain(), brain.get());
  EXPECT_NE(new_session->id(), std::string());
}

TEST_F(ServiceTest, StopSession) {
  std::shared_ptr<falken::Service> service = ConnectToService();
  ASSERT_TRUE(service);
  std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> brain =
      service->CreateBrain<TestTemplateBrainSpec>(kBrainDisplayName);
  ASSERT_TRUE(brain);
  std::shared_ptr<falken::Session> new_session = brain->StartSession(
      falken::Session::Type::kTypeInteractiveTraining, kStepsPerEpisode);
  ASSERT_TRUE(new_session);
  EXPECT_EQ(new_session->type(),
            falken::Session::Type::kTypeInteractiveTraining);
  EXPECT_EQ(new_session->Stop(), falken::String());
  EXPECT_TRUE(new_session->stopped());
}

TEST_F(ServiceTest, StopSessionBeforeFirstModelIsReceived) {
  std::shared_ptr<falken::Service> service = ConnectToService();
  ASSERT_TRUE(service);
  std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> brain =
      service->CreateBrain<TestTemplateBrainSpec>(kBrainDisplayName);
  ASSERT_TRUE(brain);
  std::shared_ptr<falken::Session> session = brain->StartSession(
      falken::Session::Type::kTypeInteractiveTraining, kStepsPerEpisode);
  ASSERT_TRUE(session);
  EXPECT_EQ(session->type(), falken::Session::Type::kTypeInteractiveTraining);

  std::shared_ptr<falken::SystemLogger> logger = falken::SystemLogger::Get();
  logger->set_abort_on_fatal_error(false);
  falken::testing::StringLogger sink;
  EXPECT_TRUE(logger->AddLogger(sink));

  EXPECT_EQ(session->Stop(), falken::String());
  EXPECT_NE(
      sink.FindLog(
          falken::kLogLevelWarning,
          absl::StrFormat(
              "Falken has not trained a brain for session %s, this results "
              "in a brain that performs no actions. You need to keep the "
              "session open and submit more episodes to train the brain.",
              session->id())
              .c_str()),
      nullptr);
}

TEST_F(ServiceTest, StopSessionBeforeTrainingFinished) {
  const int kTrainingPollIntervalMilliseconds = 1000;
  std::shared_ptr<falken::Service> service = ConnectToService();
  ASSERT_TRUE(service);
  std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> brain =
      service->CreateBrain<TestTemplateBrainSpec>(kBrainDisplayName);
  ASSERT_TRUE(brain);
  std::shared_ptr<falken::Session> session = brain->StartSession(
      falken::Session::Type::kTypeInteractiveTraining, kStepsPerEpisode);
  ASSERT_TRUE(session);
  EXPECT_EQ(session->type(), falken::Session::Type::kTypeInteractiveTraining);

  // Train with some generated data until the first model is received.
  while (falken::ServiceTest::GetSessionState(*session).empty()) {
    std::shared_ptr<falken::Episode> episode = session->StartEpisode();
    ASSERT_TRUE(episode);

    for (int st = 0; st < kStepsPerEpisode; ++st) {
      TrainingData(brain->brain_spec(), st, kStepsPerEpisode);
      ASSERT_TRUE(episode->Step());
    }
    ASSERT_TRUE(episode->Complete(falken::Episode::kCompletionStateSuccess));
    absl::SleepFor(absl::Milliseconds(kTrainingPollIntervalMilliseconds));
  }

  EXPECT_EQ(session->training_state(),
            falken::Session::TrainingState::kTrainingStateTraining);

  std::shared_ptr<falken::SystemLogger> logger = falken::SystemLogger::Get();
  logger->set_abort_on_fatal_error(false);
  falken::testing::StringLogger sink;
  EXPECT_TRUE(logger->AddLogger(sink));

  session->Stop();
  EXPECT_NE(
      sink.FindLog(
          falken::kLogLevelWarning,
          absl::StrFormat(
              "Falken has not finished training the brain for session %s. This "
              "can result in a brain that is less effective at completing "
              "assigned tasks. You need to keep the session open, submitting "
              "episodes without human demonstrations for training to progress "
              "to completion. You can query the session object to retrieve the "
              "training state.",
              session->id())
              .c_str()),
      nullptr);
}

TEST_F(ServiceTest, StartInvalidSession) {
  std::shared_ptr<falken::Service> service = ConnectToService();
  ASSERT_TRUE(service);
  std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> brain =
      service->CreateBrain<TestTemplateBrainSpec>(kBrainDisplayName);
  ASSERT_TRUE(brain);
  std::shared_ptr<falken::Session> new_session = brain->StartSession(
      falken::Session::Type::kTypeInvalid, kStepsPerEpisode);

  EXPECT_FALSE(new_session);
}

TEST_F(ServiceTest, GetSessionInfo) {
  auto brain = TrainOrGetTrainedBrainInfo().GetBrain();
  ASSERT_TRUE(brain);
  auto session =
      brain->StartSession(falken::Session::Type::kTypeInteractiveTraining, 10);
  ASSERT_TRUE(session);
  EXPECT_EQ(session->training_state(),
            falken::Session::TrainingState::kTrainingStateTraining);
  EXPECT_NE(session->info(), falken::String());
}

TEST_F(ServiceTest, GetBrainTest) {
  std::shared_ptr<falken::Service> service = ConnectToService();
  ASSERT_TRUE(service);
  std::shared_ptr<falken::Brain<TestExtendedObservationsBrainSpec>> brain =
      service->CreateBrain<TestExtendedObservationsBrainSpec>(
          kBrainDisplayName);
  ASSERT_TRUE(brain);
  ASSERT_NE(brain->id(), "");

  std::shared_ptr<falken::BrainBase> ret_brain = service->GetBrain(brain->id());
  ASSERT_TRUE(ret_brain);
  EXPECT_THAT(*(ret_brain.get()), BrainEq(*(brain.get())));
}

TEST_F(ServiceTest, DISABLED_ListBrainsTest) {
  std::shared_ptr<falken::Service> service = ConnectToService();
  ASSERT_TRUE(service);

  const int kNewBrains = 5;
  std::vector<std::shared_ptr<falken::Brain<TestExtendedObservationsBrainSpec>>>
      new_brains;
  for (int i = 0; i < kNewBrains; ++i) {
    new_brains.push_back(
        service->CreateBrain<TestExtendedObservationsBrainSpec>(""));
  }

  auto resp_brains = service->ListBrains();

  int brains_found = 0;
  for (const auto& new_brain : new_brains) {
    for (const auto& resp_brain : resp_brains) {
      if (strcmp(resp_brain->id(), new_brain->id()) == 0) {
        EXPECT_THAT(*(new_brain.get()), BrainEq(*(resp_brain.get())));
        ++brains_found;
        break;
      }
    }
  }
  EXPECT_EQ(brains_found, kNewBrains);
}

TEST_F(ServiceTest, StartEpisodeTest) {
  std::shared_ptr<falken::Service> service = ConnectToService();
  ASSERT_TRUE(service);
  std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> brain =
      service->CreateBrain<TestTemplateBrainSpec>(kBrainDisplayName);
  ASSERT_TRUE(brain);
  ASSERT_THAT(brain->id(), StrNe(""));

  std::shared_ptr<falken::Session> session = brain->StartSession(
      falken::Session::Type::kTypeInteractiveTraining, kStepsPerEpisode);
  ASSERT_TRUE(session);
  EXPECT_EQ(session->type(), falken::Session::Type::kTypeInteractiveTraining);
  std::shared_ptr<falken::Episode> episode = session->StartEpisode();
  ASSERT_TRUE(episode);
  ASSERT_STRNE("", episode->id());
}

TEST_F(ServiceTest, StepEpisodeTestReward) {
  std::shared_ptr<falken::Service> service = ConnectToService();
  ASSERT_TRUE(service);
  std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> brain =
      service->CreateBrain<TestTemplateBrainSpec>(kBrainDisplayName);
  ASSERT_TRUE(brain);
  ASSERT_NE(brain->id(), "");

  std::shared_ptr<falken::Session> session = brain->StartSession(
      falken::Session::Type::kTypeInteractiveTraining, kStepsPerEpisode);
  ASSERT_TRUE(session);
  EXPECT_EQ(session->type(), falken::Session::Type::kTypeInteractiveTraining);
  std::shared_ptr<falken::Episode> episode = session->StartEpisode();
  ASSERT_TRUE(episode);
  TestObservations& observations = brain->brain_spec().observations;
  observations.health.set_value(2.0f);
  TestActions& actions = brain->brain_spec().actions;
  actions.speed.set_value(7.0f);
  falken::core::ActiveSession* active_session =
      falken::core::GetSessionFromMap(session->id());
  EXPECT_TRUE(episode->Step(3.0f));
  EXPECT_TRUE(episode->Step());
  falken::proto::EpisodeChunk chunk =
      active_session->GetEpisode(episode->id())->chunk();
  EXPECT_EQ(chunk.mutable_steps(0)->reward().reward_value(), 3.0f);
  EXPECT_EQ(chunk.mutable_steps(1)->reward().reward_value(), 0.0f);
}

TEST_F(ServiceTest, GaveUpEpisodeTest) {
  std::shared_ptr<falken::Service> service = ConnectToService();
  ASSERT_TRUE(service);
  std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> brain =
      service->CreateBrain<TestTemplateBrainSpec>(kBrainDisplayName);
  ASSERT_TRUE(brain);
  ASSERT_NE(brain->id(), "");

  std::shared_ptr<falken::Session> session = brain->StartSession(
      falken::Session::Type::kTypeInteractiveTraining, kStepsPerEpisode);
  ASSERT_TRUE(session);
  EXPECT_EQ(session->type(), falken::Session::Type::kTypeInteractiveTraining);
  std::shared_ptr<falken::Episode> episode = session->StartEpisode();
  ASSERT_TRUE(episode);
  TestObservations& observations = brain->brain_spec().observations;
  observations.health.set_value(2.0f);
  TestActions& actions = brain->brain_spec().actions;
  actions.speed.set_value(7.0f);
  for (int i = 0; i < kStepsPerEpisode; ++i) {
    EXPECT_TRUE(episode->Step(3.0f));
  }
  // Expect to gave up since we didn't complete the episode.
  EXPECT_FALSE(episode->Step(2.0f));
  EXPECT_TRUE(episode->completed());
}

TEST_F(ServiceTest, CompleteEpisodeTest) {
  std::shared_ptr<falken::Service> service = ConnectToService();
  ASSERT_TRUE(service);
  std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> brain =
      service->CreateBrain<TestTemplateBrainSpec>(kBrainDisplayName);
  ASSERT_TRUE(brain);
  ASSERT_NE(brain->id(), "");


  std::shared_ptr<falken::Session> session = brain->StartSession(
      falken::Session::Type::kTypeInteractiveTraining, kStepsPerEpisode);
  ASSERT_TRUE(session);
  EXPECT_EQ(session->type(), falken::Session::Type::kTypeInteractiveTraining);
  std::shared_ptr<falken::Episode> episode = session->StartEpisode();
  ASSERT_TRUE(episode);
  TestObservations& observations = brain->brain_spec().observations;
  observations.health.set_value(2.0f);
  TestActions& actions = brain->brain_spec().actions;
  actions.speed.set_value(7.0f);
  EXPECT_TRUE(episode->Step(3.0f));
  EXPECT_TRUE(episode->Complete(falken::Episode::kCompletionStateSuccess));
  EXPECT_TRUE(episode->completed());
}

TEST_F(ServiceTest, CompleteEmptyEpisode) {
  std::shared_ptr<falken::Service> service = ConnectToService();
  ASSERT_TRUE(service);
  std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> brain =
      service->CreateBrain<TestTemplateBrainSpec>(kBrainDisplayName);
  ASSERT_TRUE(brain);
  std::shared_ptr<falken::Session> session = brain->StartSession(
      falken::Session::Type::kTypeInteractiveTraining, kStepsPerEpisode);
  ASSERT_TRUE(session);
  std::shared_ptr<falken::Episode> episode = session->StartEpisode();
  ASSERT_TRUE(episode);
  ASSERT_FALSE(episode->Complete(falken::Episode::kCompletionStateAborted));
  ASSERT_TRUE(episode->completed());
}

TEST_F(ServiceTest, DestroyOppositeOrderTest) {
  std::shared_ptr<falken::Service> service = ConnectToService();
  std::weak_ptr<falken::Service> service_weak(service);
  ASSERT_TRUE(service);
  std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> brain =
      service->CreateBrain<TestTemplateBrainSpec>(kBrainDisplayName);
  ASSERT_TRUE(brain);

  std::shared_ptr<falken::Session> session =
      brain->StartSession(falken::Session::Type::kTypeInteractiveTraining, 5);
  ASSERT_TRUE(session);
  EXPECT_EQ(session->type(), falken::Session::Type::kTypeInteractiveTraining);

  std::shared_ptr<falken::Episode> episode = session->StartEpisode();
  ASSERT_TRUE(episode);
  TestObservations& observations = brain->brain_spec().observations;
  observations.health.set_value(2.0f);
  TestActions& actions = brain->brain_spec().actions;
  actions.speed.set_value(7.0f);
  EXPECT_TRUE(episode->Step());
  EXPECT_FALSE(episode->completed());

  service.reset();
  EXPECT_TRUE(episode);
  EXPECT_TRUE(session);
  EXPECT_TRUE(brain);
  EXPECT_FALSE(service_weak.expired());
  EXPECT_TRUE(episode->Step());
  EXPECT_FALSE(episode->completed());

  brain.reset();
  EXPECT_TRUE(episode);
  EXPECT_TRUE(session);
  EXPECT_FALSE(service_weak.expired());
  EXPECT_TRUE(episode->Step());
  EXPECT_FALSE(episode->completed());

  session.reset();
  EXPECT_TRUE(episode);
  EXPECT_FALSE(service_weak.expired());
  EXPECT_TRUE(episode->Step());
  EXPECT_FALSE(episode->completed());

  episode.reset();
  EXPECT_TRUE(service_weak.expired());
}

TEST_F(ServiceTest, AbortEpisodesWhenSessionIsStopped) {
  std::shared_ptr<falken::Service> service = ConnectToService();
  ASSERT_TRUE(service);
  std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> brain =
      service->CreateBrain<TestTemplateBrainSpec>(kBrainDisplayName);
  ASSERT_TRUE(brain);
  ASSERT_NE(brain->id(), "");

  std::shared_ptr<falken::Session> session = brain->StartSession(
      falken::Session::Type::kTypeInteractiveTraining, kStepsPerEpisode);
  ASSERT_TRUE(session);
  EXPECT_EQ(session->type(), falken::Session::Type::kTypeInteractiveTraining);

  TestObservations& observations = brain->brain_spec().observations;
  observations.health.set_value(2.0f);
  TestActions& actions = brain->brain_spec().actions;
  actions.speed.set_value(7.0f);
  actions.set_source(falken::ActionsBase::kSourceHumanDemonstration);
  std::vector<std::shared_ptr<falken::Episode>> episodes;
  episodes.reserve(3);
  for (int i = 0; i < 3; ++i) {
    std::shared_ptr<falken::Episode> episode = session->StartEpisode();
    ASSERT_TRUE(episode);
    EXPECT_TRUE(episode->Step(3.0f));
    EXPECT_FALSE(episode->completed());
    episodes.emplace_back(std::move(episode));
  }
  EXPECT_EQ(session->Stop(), "");
  for (int i = 0; i < 3; ++i) {
    std::shared_ptr<falken::Episode>& episode = episodes[i];
    EXPECT_TRUE(episode->completed());
  }
}

// Enable this test to measure training error stats.
TEST_F(ServiceTest, DISABLED_ReportTrainingErrorStats) {
  const int kTrainingIterations = 50;
  std::vector<float> errors(kTrainingIterations);
  for (int i = 0; i < errors.size(); ++i) {
    std::cerr << "Training iteration " << std::to_string(i) << " of "
              << std::to_string(errors.size()) << "\n";
    // Force retraining.
    TearDownTestSuite();
    SetUpTestSuite();
    const auto& trained_brain_info = TrainOrGetTrainedBrainInfo();
    auto brain = trained_brain_info.GetBrain();
    ASSERT_TRUE(brain);
    auto session =
        brain->StartSession(falken::Session::Type::kTypeInference,
                            trained_brain_info.training_steps_per_episode);
    ASSERT_TRUE(session);
    EXPECT_TRUE(RunInference(session, brain, 1,
                             trained_brain_info.training_steps_per_episode,
                             &errors[i], false)
                    .ok());
    std::cerr << "Iteration " << std::to_string(i) << ", session "
              << session->id() << ", has average error " << errors[i] << "\n";
  }
  float error_min = *std::min_element(errors.begin(), errors.end());
  float error_max = *std::max_element(errors.begin(), errors.end());
  float error_mean =
      std::accumulate(errors.begin(), errors.end(), 0.0f) / errors.size();
  float error_stddev = 0.0f;
  for (auto& error : errors) {
    float distance = error - error_mean;
    error_stddev += distance * distance;
  }
  error_stddev = sqrt(error_stddev / errors.size());

  // Report training error stats.
  std::cerr << "Trained " << errors.size() << " times. "
            << "Error stats, min: " << std::to_string(error_min)
            << ", max: " << std::to_string(error_max)
            << ", mean: " << std::to_string(error_mean)
            << ", stddev: " << std::to_string(error_stddev)
            << ", per inference session...\n";
  for (auto& error : errors) {
    std::cerr << "* " << error << "\n";
  }
}

TEST_F(ServiceTest, ResumeFromSnapshot) {
  const auto& trained_brain_info = TrainOrGetTrainedBrainInfo();
  {
    std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> loaded_brain =
      trained_brain_info.GetBrain();
    ASSERT_TRUE(loaded_brain);
    std::shared_ptr<falken::Session> resume_session =
        loaded_brain->StartSession(
            falken::Session::Type::kTypeInteractiveTraining,
            trained_brain_info.training_steps_per_episode);
    ASSERT_TRUE(resume_session);
    EXPECT_STREQ(loaded_brain->snapshot_id(),
                 trained_brain_info.snapshot_id.c_str());
    std::cerr << "Train Session started" << std::endl;
    ASSERT_TRUE(
        TrainSession(resume_session, loaded_brain, 1,
                     trained_brain_info.training_steps_per_episode,
                     kTrainingModeUntilSnapshot, 1 /* Wait for 1 new model */,
                     0.0f,
                     0.5f /* Scale observations used to determine actions. */)
            .ok());
    std::cerr << "Train Session ended" << std::endl;
    falken::String loaded_snapshot_id = resume_session->Stop();
    EXPECT_STRNE(loaded_snapshot_id.c_str(), "");
    EXPECT_STRNE(loaded_snapshot_id.c_str(),
                 trained_brain_info.snapshot_id.c_str());
  }
  {
    std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> second_loaded_brain =
        trained_brain_info.GetBrain();
    EXPECT_STREQ(second_loaded_brain->snapshot_id(),
                 trained_brain_info.snapshot_id.c_str());
  }
}

// Trains a brain and checks how it behaves in a inference session.
TEST_F(ServiceTest, TestInference) {
  const auto& trained_brain_info = TrainOrGetTrainedBrainInfo();
  std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> brain =
      trained_brain_info.GetBrain();
  ASSERT_TRUE(brain);
  // Start an inference session.
  auto session =
      brain->StartSession(falken::Session::Type::kTypeInference,
                          trained_brain_info.training_steps_per_episode);
  ASSERT_TRUE(session);
  // RunInference internally checks the error between the training data and
  // inferred actions.
  EXPECT_TRUE(RunInference(session, brain, 1,
                           trained_brain_info.training_steps_per_episode)
                  .ok());
}

/*
 * Test if evaluation session is able to improve the model by comparing
 * the minimum average error of an evaluation session before and after
 * evaluation.
 */
TEST_F(ServiceTest, TestEvaluation) {
  // Amount of episodes of the inference session.
  const int kInferenceEpisodes = 1;
  // Amount of episodes of the evaluation session.
  const int kEvaluationEpisodes = 10;

  const auto& trained_brain_info = TrainOrGetTrainedBrainInfo();
  float baseline_error = 0.0f;
  {
    std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> loaded_brain =
        trained_brain_info.GetBrain();
    ASSERT_TRUE(loaded_brain);

    // Start an inference session.
    std::shared_ptr<falken::Session> session = loaded_brain->StartSession(
        falken::Session::Type::kTypeInference,
        trained_brain_info.training_steps_per_episode);
    ASSERT_TRUE(session);
    ASSERT_TRUE(RunInference(session, loaded_brain, kInferenceEpisodes,
                             trained_brain_info.training_steps_per_episode,
                             &baseline_error)
                    .ok());
    std::cerr
        << "Inference session returned baseline average error per step of "
        << std::to_string(baseline_error) << std::endl;
    auto inference_snapshot_id = session->Stop();
    ASSERT_STREQ(trained_brain_info.snapshot_id.c_str(),
                 inference_snapshot_id.c_str());
  }

  float evaluation_average_error;
  falken::String evaluation_snapshot_id;
  {
    std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> loaded_brain =
        trained_brain_info.GetBrain();
    ASSERT_TRUE(loaded_brain);

    // Run an evaluation session using the trained brain and track the best
    // average error per step.
    std::shared_ptr<falken::Session> session = loaded_brain->StartSession(
        falken::Session::Type::kTypeEvaluation,
        trained_brain_info.training_steps_per_episode);
    ASSERT_TRUE(session);
    ASSERT_TRUE(RunEvaluation(session, loaded_brain, kEvaluationEpisodes,
                              trained_brain_info.training_steps_per_episode,
                              baseline_error, &evaluation_average_error)
                    .ok());
    evaluation_snapshot_id = session->Stop();
    ASSERT_TRUE(session->stopped());
    ASSERT_NE("", evaluation_snapshot_id);
    std::cerr << "Evaluation session returned a best average error per step of "
              << std::to_string(evaluation_average_error) << std::endl;
  }

  // The error after evaluation session should be equal or lower than running
  // only inference Session.
  ASSERT_LE(evaluation_average_error, baseline_error);

  {
    auto service = ConnectToService();
    ASSERT_TRUE(service);
    std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> loaded_brain =
        service->GetBrain<TestTemplateBrainSpec>(
            trained_brain_info.brain_id.c_str(),
            evaluation_snapshot_id.c_str());
    ASSERT_TRUE(loaded_brain);

    // Start a new inference session and make sure the average error per step is
    // the same as the best result of the evaluation session.
    std::shared_ptr<falken::Session> session = loaded_brain->StartSession(
        falken::Session::Type::kTypeInference,
        trained_brain_info.training_steps_per_episode);
    ASSERT_TRUE(session);
    float post_evaluation_error;
    ASSERT_TRUE(RunInference(session, loaded_brain, kInferenceEpisodes,
                             trained_brain_info.training_steps_per_episode,
                             &post_evaluation_error)
                    .ok());
    session->Stop();
    EXPECT_TRUE(session->stopped());
    // The error after evaluation session should be equal or lower than running
    // only inference Session.
    ASSERT_LE(post_evaluation_error, baseline_error);
  }
}

TEST_F(ServiceTest, ReadSession) {
  const int kEpisodes = 5;
  const int kStepsPerEpisode = 10;
  auto service = ConnectToService();
  ASSERT_TRUE(service);
  auto brain = service->CreateBrain<TestTemplateBrainSpec>(kBrainDisplayName);
  ASSERT_TRUE(brain);
  auto training_session = brain->StartSession(
      falken::Session::kTypeInteractiveTraining, kStepsPerEpisode);
  ASSERT_TRUE(training_session);
  ASSERT_TRUE(TrainSession(training_session, brain, kEpisodes, kStepsPerEpisode,
                           kTrainingModeNoWaiting)
                  .ok());

  auto training_session_id = training_session->id();
  training_session->Stop();

  auto inspect_session = brain->GetSession(training_session_id);
  ASSERT_TRUE(inspect_session);
  EXPECT_FALSE(inspect_session->StartEpisode());
  EXPECT_TRUE(inspect_session->stopped());
  EXPECT_EQ(inspect_session->Stop(), "");
  EXPECT_THAT(*(inspect_session.get()), SessionEq(*(training_session.get())));

  for (int ep = 0; ep < kEpisodes; ++ep) {
    auto episode = inspect_session->GetEpisode(ep);
    ASSERT_NE(nullptr, episode.get());
    EXPECT_FALSE(episode->Step());
    EXPECT_FALSE(episode->Step(1.0f));
    EXPECT_TRUE(episode->completed());
    EXPECT_FALSE(episode->Complete(falken::Episode::kCompletionStateFailure));
    EXPECT_EQ(episode->GetStepCount(), kStepsPerEpisode);

    for (int st = 0; st < kStepsPerEpisode; ++st) {
      EXPECT_TRUE(episode->ReadStep(st));
      EXPECT_FLOAT_EQ(episode->reward(), 0.0f);
      TestTemplateBrainSpec expected_brain_state;
      TrainingData(expected_brain_state, st, kStepsPerEpisode);
      EXPECT_THAT(brain->brain_spec(), BrainAttributesEq(expected_brain_state));
    }

    // Read out of range steps.
    EXPECT_FALSE(episode->ReadStep(-1));
    EXPECT_FALSE(episode->ReadStep(kStepsPerEpisode));
  }
  // Try getting an out of range episode.
  EXPECT_FALSE(inspect_session->GetEpisode(-1));
  EXPECT_FALSE(inspect_session->GetEpisode(kEpisodes));
}

/*
 * Test warning messages from evaluation session for the following situations:
 * - Developper provides an invalid completion state in episode::Complete().
 * - Developper provides human actions during evaluation.
 * - Brain actions not being generated by brain when actions source is not
 * kSourceNone.
 */
TEST_F(ServiceTest, TestEvaluationEpisodeFailure) {
  // Amount of steps per episode.
  const int kMaxStepsPerEpisode = 1000;

  // Set logger.
  std::shared_ptr<falken::SystemLogger> logger = falken::SystemLogger::Get();
  falken::testing::StringLogger sink;
  EXPECT_TRUE(logger->AddLogger(sink));

  falken::String evaluation_snapshot_id;
  {
    auto loaded_brain = TrainOrGetTrainedBrainInfo().GetBrain();
    ASSERT_TRUE(loaded_brain);

    // Run an evaluation session using the trained brain and track the best
    // average error per step.
    std::shared_ptr<falken::Session> session = loaded_brain->StartSession(
        falken::Session::Type::kTypeEvaluation, kMaxStepsPerEpisode);
    ASSERT_TRUE(session);
    std::string episode_id;

    // Create episode and step only once.
    std::shared_ptr<falken::Episode> episode = session->StartEpisode();
    EXPECT_TRUE(episode);
    EXPECT_NE(falken::Session::TrainingState::kTrainingStateInvalid,
              session->training_state());
    episode_id = episode->id();
    // Step episodes without providing data allowing the session
    // to evaluate all the episodes.
    // Provide observations and step.
    TrainingData(loaded_brain->brain_spec(), 0, kMaxStepsPerEpisode, true);
    EXPECT_TRUE(episode->Step());

    // Complete episode in an invalid state.
    episode->Complete(
        falken::Episode::CompletionState::kCompletionStateInvalid);

    const auto expected_log_1 = absl::StrFormat(
        "Human demostration detected in episode %s, step 0 of evaluation "
        "session %s. For an evaluation session to make progress, it should "
        "entirely consist of brain actions.",
        episode_id, session->id());
    ASSERT_NE(sink.FindLog(falken::kLogLevelWarning, expected_log_1.c_str()),
              nullptr);

    const auto expected_log_2 = absl::StrFormat(
        "No brain action generated in evaluation session %s, episode %s at "
        "step 0. If the error persists, please contact Falken team to report "
        "this as a bug",
        session->id(), episode_id);
    ASSERT_NE(sink.FindLog(falken::kLogLevelError, expected_log_2.c_str()),
              nullptr);

    evaluation_snapshot_id = session->Stop();
    ASSERT_TRUE(session->stopped());
    ASSERT_NE("", evaluation_snapshot_id);

    const auto expected_log_3 = absl::StrFormat(
        "Evaluation session episode %s was completed with state 4 which "
        "results in the episode being ignored. Evaluation session episodes "
        "must be completed with either success or failure for the evaluation "
        "process to progress.",
        episode_id);
    ASSERT_NE(sink.FindLog(falken::kLogLevelWarning, expected_log_3.c_str()),
              nullptr);
  }
}

TEST_F(ServiceTest, ListSessions) {
  const int kSessions = 5;
  const int kEpisodes = 5;
  const int kStepsPerEpisode = 10;
  auto service = ConnectToService();
  ASSERT_TRUE(service);
  auto brain = service->CreateBrain<TestTemplateBrainSpec>(kBrainDisplayName);
  ASSERT_TRUE(brain);

  std::vector<std::shared_ptr<falken::Session>> input_sessions;
  for (int i = 0; i < kSessions; ++i) {
    int steps = kStepsPerEpisode + i;
    auto training_session =
        brain->StartSession(falken::Session::kTypeInteractiveTraining, steps);
    ASSERT_TRUE(training_session);
    ASSERT_TRUE(TrainSession(training_session, brain, kEpisodes, steps,
                             kTrainingModeNoWaiting)
                    .ok());
    training_session->Stop();
    input_sessions.push_back(std::move(training_session));
  }

  auto output_sessions = brain->ListSessions();
  EXPECT_EQ(input_sessions.size(), output_sessions.size());

  for (const auto& input_session : input_sessions) {
    for (const auto& output_session : output_sessions) {
      if (strcmp(input_session->id(), output_session->id()) == 0) {
        EXPECT_THAT(*(input_session.get()), SessionEq(*(output_session.get())));
        for (int i = 0; i < input_session->GetEpisodeCount(); ++i) {
          auto input_episode = input_session->GetEpisode(i);
          auto output_episode = output_session->GetEpisode(i);
          ASSERT_EQ(input_episode->GetStepCount(),
                    output_episode->GetStepCount());
        }
        break;
      }
    }
  }
}

TEST_F(ServiceTest, TrainWithInterleavedEpisodes) {
  const int kEpisodeCompleteInterval = 100;
  const int kEpisodes = 4;
  const int kStepsPerEpisode = 10;
  auto service = ConnectToService();
  ASSERT_TRUE(service);
  auto brain = service->CreateBrain<TestTemplateBrainSpec>(kBrainDisplayName);
  ASSERT_TRUE(brain);

  std::string training_session_id;

  {
    auto training_session = brain->StartSession(
        falken::Session::kTypeInteractiveTraining, kStepsPerEpisode);
    ASSERT_TRUE(training_session);

    // Create episodes.
    std::vector<std::shared_ptr<falken::Episode>> episodes(kEpisodes);
    for (int ep = 0; ep < kEpisodes; ++ep) {
      episodes[ep] = training_session->StartEpisode();
      ASSERT_TRUE(episodes[ep]);
    }
    // Populate episodes by interleaving training data.
    for (int st = 0; st < kStepsPerEpisode; ++st) {
      for (int ep = 0; ep < kEpisodes; ++ep) {
        TrainingData(brain->brain_spec(), st, kStepsPerEpisode);
        episodes[ep]->Step();
      }
    }
    // Complete episodes.
    for (int ep = 0; ep < kEpisodes; ++ep) {
      ASSERT_TRUE(
          episodes[ep]->Complete(falken::Episode::kCompletionStateSuccess));
    }
    absl::SleepFor(absl::Milliseconds(kEpisodeCompleteInterval));
    training_session->Stop();

    training_session_id = training_session->id();
  }

  {
    // Fetch session data and make sure all episodes are populated as expected.
    auto inspect_session = brain->GetSession(training_session_id.c_str());
    ASSERT_TRUE(inspect_session);
    for (int ep = 0; ep < kEpisodes; ++ep) {
      auto episode = inspect_session->GetEpisode(ep);
      for (int st = 0; st < kStepsPerEpisode; ++st) {
        EXPECT_TRUE(episode->ReadStep(st));
        TestTemplateBrainSpec expected_brain_state;
        TrainingData(expected_brain_state, st, kStepsPerEpisode);
        EXPECT_THAT(brain->brain_spec(),
                    BrainAttributesEq(expected_brain_state));
      }
    }
  }
}

TEST_F(ServiceTest, StepWarnsIfObservationsNotSet) {
  std::shared_ptr<falken::SystemLogger> logger = falken::SystemLogger::Get();
  falken::testing::StringLogger sink;
  EXPECT_TRUE(logger->AddLogger(sink));
  std::shared_ptr<falken::Service> service = ConnectToService();
  ASSERT_TRUE(service);
  std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> brain =
      service->CreateBrain<TestTemplateBrainSpec>(kBrainDisplayName);
  ASSERT_TRUE(brain);
  ASSERT_NE(brain->id(), "");
  std::shared_ptr<falken::Session> session = brain->StartSession(
      falken::Session::Type::kTypeInteractiveTraining, kStepsPerEpisode);
  ASSERT_TRUE(session);
  EXPECT_EQ(session->type(), falken::Session::Type::kTypeInteractiveTraining);
  std::shared_ptr<falken::Episode> episode = session->StartEpisode();
  ASSERT_TRUE(episode);
  TestObservations& observations = brain->brain_spec().observations;
  const auto expected_log = absl::StrFormat(
      "Attributes \\[%s, %s\\] of entity %s are not set\\. To fix this issue, "
      "set attributes to a valid value before stepping an episode\\.",
      std::string(observations.feelers.name()) + "/distance_11",
      observations.health.name(), observations.name());
  auto set_all_but_health_and_a_feeler = [](TestObservations& observations) {
    observations.angle_to_goal.set_value(0);
    observations.distance_to_goal.set_value(2.0f);
    observations.angle_to_enemy.set_value(0);
    observations.distance_to_enemy.set_value(2.0f);
    observations.equipped_item.set_value(0);
    observations.position.set_value(falken::Position(0, 0, 0));
    observations.rotation.set_value(falken::Rotation(0, 0, 0, 1));
    int feeler_idx = 0;
    for (auto& distance_ref : observations.feelers.distances()) {
      if (feeler_idx != 11) {
        distance_ref = 0.0;
      }
      ++feeler_idx;
    }
    for (auto& id_ref : observations.feelers.ids()) {
      id_ref = 0;
    }
  };
  // all observations set
  set_all_but_health_and_a_feeler(observations);
  observations.health.set_value(2.0f);
  observations.feelers.distances()[11].set_value(0.0f);
  EXPECT_TRUE(episode->Step());
  EXPECT_EQ(sink.FindLog(falken::kLogLevelWarning, expected_log.c_str()),
            nullptr);
  // health observations not set
  set_all_but_health_and_a_feeler(observations);
  EXPECT_TRUE(episode->Step());
  EXPECT_NE(sink.FindLog(falken::kLogLevelWarning, expected_log.c_str()),
            nullptr);
  EXPECT_TRUE(episode->Complete(falken::Episode::kCompletionStateSuccess));
  EXPECT_TRUE(episode->completed());
}

TEST_F(ServiceTest, StepWarnsIfActionsNotSet) {
  std::shared_ptr<falken::SystemLogger> logger = falken::SystemLogger::Get();
  falken::testing::StringLogger sink;
  EXPECT_TRUE(logger->AddLogger(sink));
  std::shared_ptr<falken::Service> service = ConnectToService();
  ASSERT_TRUE(service);
  std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> brain =
      service->CreateBrain<TestTemplateBrainSpec>(kBrainDisplayName);
  ASSERT_TRUE(brain);
  ASSERT_NE(brain->id(), "");
  std::shared_ptr<falken::Session> session = brain->StartSession(
      falken::Session::Type::kTypeInteractiveTraining, kStepsPerEpisode);
  ASSERT_TRUE(session);
  EXPECT_EQ(session->type(), falken::Session::Type::kTypeInteractiveTraining);
  std::shared_ptr<falken::Episode> episode = session->StartEpisode();
  ASSERT_TRUE(episode);
  TestObservations& observations = brain->brain_spec().observations;
  TestActions& actions = brain->brain_spec().actions;
  const auto expected_log = absl::StrFormat(
      "Action data has been partly provided, but the attributes \\[%s, %s\\] "
      "have "
      "not been set to valid values\\. To fix this issue, when providing "
      "action data set all attributes to valid values before stepping an "
      "episode\\.",
      actions.speed.name(), actions.use_item.name());
  auto set_all_observations = [](TestObservations& observations) {
    observations.angle_to_goal.set_value(0);
    observations.distance_to_goal.set_value(2.0f);
    observations.angle_to_enemy.set_value(0);
    observations.distance_to_enemy.set_value(2.0f);
    observations.equipped_item.set_value(0);
    observations.health.set_value(2.0f);
    observations.position.set_value(falken::Position(0, 0, 0));
    observations.rotation.set_value(falken::Rotation(0, 0, 0, 1));
    for (auto& distance_ref : observations.feelers.distances()) {
      distance_ref = 0.0;
    }
    for (auto& id_ref : observations.feelers.ids()) {
      id_ref = 0;
    }
  };
  auto set_all_actions_but_speed_and_use_item = [](TestActions& actions) {
    actions.steering.set_value(0.0);
    actions.select_item.set_value(0);
  };
  // all observations and actions set
  set_all_observations(observations);
  set_all_actions_but_speed_and_use_item(actions);
  actions.speed.set_value(6.0);
  actions.use_item.set_value(false);
  actions.set_source(falken::ActionsBase::kSourceHumanDemonstration);
  EXPECT_TRUE(episode->Step());
  EXPECT_EQ(sink.FindLog(falken::kLogLevelWarning, expected_log.c_str()),
            nullptr);
  // speed and use_item are not set, all observations set
  set_all_observations(observations);
  set_all_actions_but_speed_and_use_item(actions);
  EXPECT_TRUE(episode->Step());
  EXPECT_NE(sink.FindLog(falken::kLogLevelWarning, expected_log.c_str()),
            nullptr);
  EXPECT_TRUE(episode->Complete(falken::Episode::kCompletionStateSuccess));
  EXPECT_TRUE(episode->completed());
}

class ModelUpdateTests : public ServiceTest {
 protected:
  bool ModelUpdateTrackingLoop(falken::Brain<TestTemplateBrainSpec>* brain,
                               falken::Session* session,
                               int delay_in_seconds_for_each_batch_of_steps,
                               int number_of_episodes, int number_of_steps,
                               bool& session_model_updated_in_episode,
                               bool& episode_model_updated_in_episode) {
    const auto kNumberOfStepsPerBatch = number_of_steps / 10;
    // Delay every N steps (e.g N = 10 - where N >= 2 since we need at least two
    // steps to generate a trajectory for training).

    TestActions& actions = brain->brain_spec().actions;

    session_model_updated_in_episode = false;
    episode_model_updated_in_episode = false;

    for (auto k = 0; k < number_of_episodes; ++k) {
      std::shared_ptr<falken::Episode> episode = session->StartEpisode();
      auto initial_session_model_id =
          falken::ServiceTest::GetSessionModelId(*session);
      auto initial_episode_model_id =
          falken::ServiceTest::GetEpisodeModelId(*episode);
      for (auto i = 0; i < number_of_steps / kNumberOfStepsPerBatch; ++i) {
        for (auto j = 0; j < kNumberOfStepsPerBatch; ++j) {
          TrainingData(brain->brain_spec(), (i * kNumberOfStepsPerBatch) + j,
                       number_of_steps);
          if (session->type() ==
              falken::Session::Type::kTypeInteractiveTraining) {
            actions.set_source(falken::ActionsBase::kSourceHumanDemonstration);
          } else {
            actions.set_source(falken::ActionsBase::kSourceNone);
          }
          EXPECT_TRUE(episode->Step());
        }

        int count = 0;
        std::string latest_session_model_id;
        std::string latest_episode_model_id;
        bool exit_loop = false;
        while (count != delay_in_seconds_for_each_batch_of_steps &&
               !exit_loop) {
          absl::SleepFor(absl::Seconds(1));

          latest_session_model_id =
              falken::ServiceTest::GetSessionModelId(*session);
          latest_episode_model_id =
              falken::ServiceTest::GetEpisodeModelId(*episode);

          if (initial_session_model_id != latest_session_model_id) {
            session_model_updated_in_episode = true;
          }
          if (initial_episode_model_id != latest_episode_model_id) {
            episode_model_updated_in_episode = true;
          }
          if (session_model_updated_in_episode &&
              episode_model_updated_in_episode) {
            return episode->Complete(falken::Episode::kCompletionStateSuccess);
          }
          ++count;
        }
      }
      EXPECT_TRUE(episode->Complete(falken::Episode::kCompletionStateSuccess));
    }
    return true;
  }
};

TEST_F(ModelUpdateTests, TestModelGetsUpdatedDuringTraining) {
  using falken::ServiceTest;
  auto service = ConnectToService();
  ASSERT_TRUE(service);
  auto brain = service->CreateBrain<TestTemplateBrainSpec>(kBrainDisplayName);
  ASSERT_TRUE(brain);

  // Create a session with a small number of steps.
  const auto kNumberOfSteps = 100;
  const auto kNumberOfEpisodes = 3;
  auto session = brain->StartSession(
      falken::Session::Type::kTypeInteractiveTraining, kNumberOfSteps);
  ASSERT_TRUE(session);
  ASSERT_TRUE(
      TrainSession(session, brain, 1, kNumberOfSteps, kTrainingModeNoWaiting)
          .ok());

  bool session_model_updated_in_episode = false;
  bool episode_model_updated_in_episode = false;

  const int kDelayInSecondsForEachBatchOfSteps = 25;
  ASSERT_TRUE(ModelUpdateTrackingLoop(
      brain.get(), session.get(), kDelayInSecondsForEachBatchOfSteps,
      kNumberOfEpisodes, kNumberOfSteps, session_model_updated_in_episode,
      episode_model_updated_in_episode));

  EXPECT_TRUE(session_model_updated_in_episode);
  EXPECT_TRUE(episode_model_updated_in_episode);
}

TEST_F(ModelUpdateTests, TestModelGetsUpdatedDuringEvaluation) {
  using falken::ServiceTest;

  auto trained_brain_info = TrainOrGetTrainedBrainInfo();
  auto brain = trained_brain_info.GetBrain();
  ASSERT_TRUE(brain);
  ASSERT_NE(brain->id(), "");

  // Create a session with a small number of steps.
  const auto kNumberOfSteps = 100;
  const auto kNumberOfEpisodes = 1;
  auto session = brain->StartSession(falken::Session::Type::kTypeEvaluation,
                                     kNumberOfSteps);
  ASSERT_TRUE(session);

  bool session_model_updated_in_episode = false;
  bool episode_model_updated_in_episode = false;

  const int kDelayInSecondsForEachBatchOfSteps = 10;
  ASSERT_TRUE(ModelUpdateTrackingLoop(
      brain.get(), session.get(), kDelayInSecondsForEachBatchOfSteps,
      kNumberOfEpisodes, kNumberOfSteps, session_model_updated_in_episode,
      episode_model_updated_in_episode));

  EXPECT_TRUE(session_model_updated_in_episode);
  EXPECT_FALSE(episode_model_updated_in_episode);
}

}  // namespace
