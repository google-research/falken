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

#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>

#include <cstddef>
#include <cstdlib>
#include <fstream>
#include <map>
#include <memory>
#include <string>
#include <vector>

#include "main.h"  // OS abstraction layer.
#include "falken/falken.h"
#include "absl/flags/flag.h"
#include "absl/flags/parse.h"
#include "absl/strings/str_format.h"
#include "absl/time/time.h"

ABSL_FLAG(std::string, env, "local",
          "Flag to indicate which environment the SDK should try to connect "
          "to. Choices are 'local', 'dev', 'prod' or 'sandbox'.");

ABSL_FLAG(std::string, api_key, "",
          "The API key used to authorize access to the Falken API. If not "
          "specified, the environment variable FALKEN_API_KEY is used.");

ABSL_FLAG(std::string, project_id, "",
          "The project_id used to authorize access to the Falken API.");

ABSL_FLAG(bool, force_error_check_failure, false,
          "If true, will learn constant output and fail average error check.");

ABSL_FLAG(int, milliseconds_between_steps, 100,
          "Number of milliseconds to wait between each simulation step.");

ABSL_FLAG(int, number_of_episodes, 10, "Number of episodes in a session.");

ABSL_FLAG(int, number_of_steps_per_episode, 300, "Number of steps per episode");

ABSL_FLAG(int, training_timeout_in_milliseconds, 60000,
          "Milliseconds to wait for training to complete.");

ABSL_FLAG(std::string, service_address, "",
          "Address to connect to the Falken service.");

ABSL_FLAG(bool, error_on_training_timeout, false,
          "Whether to fail if training "
          "times out");

ABSL_FLAG(int, rpc_timeout_in_milliseconds, 30000,
          "Milliseconds to wait "
          "before aborting an RPC.");

ABSL_FLAG(std::string, log_level, "info",
          "Log verbosity can be one of "
          "[debug, verbose, info, warning, error, fatal]");

ABSL_FLAG(std::string, json_config_file, "",
          "JSON configuration file used to configure the SDK. "
          "If this is specified, env, api_key, project_id, service_address, "
          "and rpc_timeout_in_milliseconds flags are ignored.");

namespace {

// The environment variable to look for the API key.
const char kFalkenApiKeyEnvironmentVariable[] = "FALKEN_API_KEY";

const char* kBrainDisplayName = "test_brain";
constexpr const char* kJsonConfigSchema =
    R"({
      "api_key": "%s",
      "project_id": "%s",
      "api_call_timeout_milliseconds": %d,
      "service": {
        "environment": "%s",
        %s
      }
    })";

// Acceptable average error.
const float kAverageErrorLimit = 0.05;

// Time to wait between polling the service to determine whether training is
// complete.
const int kTrainingPollIntervalMilliseconds = 1000;

const struct LogLevelNameToEnum {
  const char* name;
  falken::LogLevel log_level;
} kLogLevelNameToEnum[] = {
    {"debug", falken::kLogLevelDebug}, {"verbose", falken::kLogLevelVerbose},
    {"info", falken::kLogLevelInfo},   {"warning", falken::kLogLevelWarning},
    {"error", falken::kLogLevelError}, {"fatal", falken::kLogLevelFatal},
};

}  // namespace

struct TestEntity : public falken::EntityBase {
  explicit TestEntity(falken::EntityContainer& entity_container,
                      const char* name)
      : falken::EntityBase(entity_container, "Evil_guy"),
        FALKEN_NUMBER(health, 0.0f, 100.0f),
        FALKEN_NUMBER(evilness, 1.0f, 25.0f) {}
  falken::NumberAttribute<float> health;
  falken::NumberAttribute<float> evilness;
};

struct TestAction : public falken::ActionsBase {
  TestAction()
      : falken::ActionsBase(),
        FALKEN_NUMBER(number, -1.0f, 1.0f),
        FALKEN_CATEGORICAL(category, {"Off", "On"}),
        FALKEN_BOOL(boolean) {}

  falken::NumberAttribute<float> number;
  falken::CategoricalAttribute category;
  falken::BoolAttribute boolean;
};

struct TestObservation : public falken::ObservationsBase {
  TestObservation()
      : FALKEN_NUMBER(number, -1.0f, 1.0f),
        FALKEN_CATEGORICAL(category, {"Off", "On"}),
        FALKEN_BOOL(boolean),
        FALKEN_FEELERS(feelers, 3, 100.0f, 180.0f, 0.2f,
                       {"table", "glass", "dish"}),
        FALKEN_ENTITY(evil_guy) {}

  falken::NumberAttribute<float> number;
  falken::CategoricalAttribute category;
  falken::BoolAttribute boolean;
  falken::FeelersAttribute feelers;
  TestEntity evil_guy;
};

using TestTemplateBrainSpec = falken::BrainSpec<TestObservation, TestAction>;

void GetObservation(TestTemplateBrainSpec& brain_spec, int step_count,
                    int number_of_steps_per_episode) {
  auto& observations = brain_spec.observations;

  float observation_value =
      static_cast<float>(step_count) / number_of_steps_per_episode;
  observations.position = {static_cast<float>(step_count + 1),
                           static_cast<float>(step_count + 2),
                           static_cast<float>(step_count + 3)};
  observations.number = -1 + 2 * observation_value;
  bool first_half = step_count < number_of_steps_per_episode / 2;
  observations.category = static_cast<int>(first_half);
  observations.boolean = !first_half;
  auto& feelers_distances = brain_spec.observations.feelers.feelers_distances();
  auto& feelers_ids = brain_spec.observations.feelers.feelers_ids();
  float feelers_maximum_length = brain_spec.observations.feelers.length();
  feelers_distances[0] = feelers_maximum_length * observation_value;
  feelers_distances[1] = feelers_maximum_length * (1 - observation_value);
  feelers_distances[2] = feelers_maximum_length * observation_value / 2.0f;
  feelers_ids[0] = first_half ? 2.0f : 1.0f;
  feelers_ids[1] = first_half ? 1.0f : 0.0f;
  feelers_ids[2] = first_half ? 0.0f : 2.0f;
  float health_range = (observations.evil_guy.health.number_maximum() -
                        observations.evil_guy.health.number_minimum());
  observations.evil_guy.health = health_range * observation_value +
                                 observations.evil_guy.health.number_minimum();
  float evilness_range = (observations.evil_guy.evilness.number_maximum() -
                          observations.evil_guy.evilness.number_minimum());
  observations.evil_guy.evilness =
      evilness_range * (1 - observation_value) +
      observations.evil_guy.evilness.number_minimum();

  observations.rotation.set_value(falken::Rotation({0.0f, 0.0f, 0.0f, 1.0f}));
  observations.position.set_value(falken::Position({0.0f, 0.0f, 0.0f}));
  observations.evil_guy.rotation.set_value(
      falken::Rotation({0.0f, 0.0f, 0.0f, 1.0f}));
  observations.evil_guy.position.set_value(
      falken::Position({0.0f, 0.0f, 0.0f}));
}

// Expert to imitate: Reverses input category and negates number.
void ExpertPolicy(const TestObservation& observations, TestAction& actions) {
  actions.number = -1 * static_cast<float>(observations.number);
  actions.category = static_cast<int>(observations.category) ? 0 : 1;
  actions.boolean = (observations.number < 0);
}

void ConstantPolicy(TestAction& actions) {
  actions.number = 0.0f;
  actions.category = 0;
  actions.boolean = false;
}

struct TestStepData {
  TestAction action;
  TestObservation observation;
};

struct TestEpisodeData {
  std::vector<TestStepData> steps;
};

bool AreEqualFloat(float a, float b) {
  const float kFloatErrorLimit = 0.1;
  if (std::fabs(a - b) < kFloatErrorLimit) {
    return true;
  }
  LogError("Float values are not equal. Value1: %f - Value2: %f - Error: %f.",
           a, b, std::fabs(a - b));
  return false;
}

bool AreEqualInt(int a, int b) {
  if (a == b) {
    return true;
  }
  LogError("Integer values are not equal. Value1: %d - Value2: %d - Error: %d.",
           a, b, std::fabs(a - b));
  return false;
}

bool CheckFeelers(const falken::FeelersAttribute& submitted,
                  const falken::FeelersAttribute& received) {
  if (submitted.feelers_distances().size() !=
      received.feelers_distances().size()) {
    return false;
  }
  if (submitted.feelers_ids().size() != received.feelers_ids().size()) {
    return false;
  }
  for (int i = 0; i < submitted.feelers_distances().size(); ++i) {
    if (!AreEqualFloat(submitted.feelers_distances()[i],
                       received.feelers_distances()[i])) {
      return false;
    }
  }
  for (int i = 0; i < submitted.feelers_ids().size(); ++i) {
    if (!AreEqualInt(submitted.feelers_ids()[i], received.feelers_ids()[i])) {
      return false;
    }
  }
  return true;
}

bool CheckEntities(const TestEntity& submitted, const TestEntity& received) {
  return AreEqualFloat(submitted.health, received.health) &&
         AreEqualFloat(submitted.evilness, received.evilness);
}

bool CheckObservations(const TestObservation& submitted,
                       const TestObservation& received) {
  return AreEqualInt(submitted.category, received.category) &&
         AreEqualFloat(submitted.number, received.number);
}

bool CheckActions(const TestAction& submitted, const TestAction& received) {
  return AreEqualInt(submitted.category, received.category) &&
         AreEqualFloat(submitted.number, received.number);
}

void FillStep(const falken::BrainSpec<TestObservation, TestAction>& spec,
              TestStepData& step) {
  step.action.number = static_cast<float>(spec.actions.number);
  step.action.category = static_cast<int>(spec.actions.category);
  step.action.boolean = static_cast<bool>(spec.actions.boolean);
  step.observation.number = static_cast<float>(spec.observations.number);
  step.observation.category = static_cast<int>(spec.observations.category);
  step.observation.boolean = static_cast<bool>(spec.observations.boolean);
  step.observation.evil_guy.health =
      static_cast<float>(spec.observations.evil_guy.health);
  step.observation.evil_guy.evilness =
      static_cast<float>(spec.observations.evil_guy.evilness);
  for (int i = 0; i < spec.observations.feelers.feelers_distances().size();
       ++i) {
    step.observation.feelers.feelers_distances()[i] =
        static_cast<float>(spec.observations.feelers.feelers_distances()[i]);
    step.observation.feelers.feelers_ids()[i] =
        static_cast<int>(spec.observations.feelers.feelers_ids()[i]);
  }
}

int TestInteractiveTraining(falken::Service& service) {
  const int milliseconds_between_steps =
      absl::GetFlag(FLAGS_milliseconds_between_steps);
  const int number_of_episodes = absl::GetFlag(FLAGS_number_of_episodes);
  const int number_of_steps_per_episode =
      absl::GetFlag(FLAGS_number_of_steps_per_episode);

  std::string brain_id;
  std::vector<TestEpisodeData> submitted_episodes;
  {
    // Create brain.
    std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> brain =
        service.CreateBrain<TestTemplateBrainSpec>(kBrainDisplayName);
    // Get reference to brain spec.
    if (!brain) {
      LogError("Create brain failed.");
      return 1;
    }
    LogMessage("Created brain successfully with id: %s.", brain->id());
    brain_id = brain->id();

    auto& brain_spec = brain->brain_spec();

    // Start session.
    std::shared_ptr<falken::Session> session =
        brain->StartSession(falken::Session::Type::kTypeInteractiveTraining,
                            number_of_steps_per_episode);
    if (!session) {
      LogError("Start session failed.");
      return 1;
    }
    LogMessage("Started session %s successfully.", session->id());

    // Used to calculate inference performance when training is complete.
    absl::Duration time_stepping = absl::ZeroDuration();

    // Create episodes.
    float total_error = 0;
    int eval_frames = 0;
    int brain_action_counter = 0;
    int episodes_index = 0;
    for (int ep = 0; ep < number_of_episodes; ++ep) {
      // Start episode.
      std::shared_ptr<falken::Episode> episode = session->StartEpisode();
      if (!episode) {
        LogError("Create Episode failed for episode no. %d.", ep);
        return 1;
      }
      LogMessage("Created episode no. %d successfully.", ep);
      submitted_episodes.resize(episodes_index + 1);

      bool last_episode = ep == number_of_episodes - 1;
      if (last_episode) {
        // The service currently only returns the training state on completion
        // of an episode, so submit empty episodes until the service returns a
        // result.
        const int training_timeout_in_milliseconds =
            absl::GetFlag(FLAGS_training_timeout_in_milliseconds);
        int timeout = training_timeout_in_milliseconds;
        LogMessage("Waiting for training to complete...");
        while (session->training_state() !=
                   falken::Session::kTrainingStateComplete &&
               timeout-- > 0) {
          absl::SleepFor(absl::Milliseconds(kTrainingPollIntervalMilliseconds));
          timeout -= kTrainingPollIntervalMilliseconds;
          brain_spec.actions.set_source(falken::ActionsBase::kSourceNone);

          // Set attributes to avoid unset attribute warnings.
          ConstantPolicy(brain_spec.actions);
          GetObservation(brain_spec, ep, number_of_steps_per_episode);

          // Submit an empty step per episode.
          if (!(episode->Step(0.0f) &&
                episode->Complete(falken::Episode::kCompletionStateAborted))) {
            LogError(
                "Failed to step and complete the episode while waiting for "
                "training to complete.");
            return 1;
          }

          // Add empty episode to submitted episodes.
          auto& submitted_steps = submitted_episodes[episodes_index].steps;
          submitted_steps.resize(1);
          auto& submitted_step = submitted_steps[0];
          FillStep(brain_spec, submitted_step);
          ++episodes_index;

          // Start new episode.
          episode = session->StartEpisode();
          if (!episode) {
            LogError("Create Episode failed for empty episode no. %d.",
                     episodes_index);
            return 1;
          }
          submitted_episodes.resize(episodes_index + 1);
        }
        LogMessage(
            "Training complete, starting evaluation (session info: %s)...",
            session->info().c_str());
        if (timeout <= 0) {
          // This isn't a hard timeout at the moment as need to optimize
          // stopping parameters.
          LogError("Timed out while waiting %d for training to complete.",
                   training_timeout_in_milliseconds);
          if (absl::GetFlag(FLAGS_error_on_training_timeout)) return 1;
        }
      }

      // Create steps.
      auto& submitted_steps = submitted_episodes[episodes_index].steps;
      submitted_steps.resize(number_of_steps_per_episode);
      for (int step_count = 0; step_count < number_of_steps_per_episode;
           ++step_count) {
        absl::Time before = absl::Now();

        // Set observation data.
        GetObservation(brain_spec, step_count, number_of_steps_per_episode);

        if (absl::GetFlag(FLAGS_force_error_check_failure)) {
          // Feed incorrect data to learn the wrong function.
          ConstantPolicy(brain_spec.actions);
        } else {
          ExpertPolicy(brain_spec.observations, brain_spec.actions);
        }
        if (!last_episode && step_count % 2) {
          // Provide human demos in odd steps.
          brain_spec.actions.set_source(
              falken::ActionsBase::kSourceHumanDemonstration);
        } else {
          brain_spec.actions.set_source(falken::ActionsBase::kSourceNone);
        }

        TestAction expert_policy_actions;  // Get expert policy output
        ExpertPolicy(brain_spec.observations, expert_policy_actions);

        // Step episode.
        if (!episode->Step(step_count * 5.0f)) {
          LogError("Step Episode failed for episode no. %d at step %d.", ep,
                   step_count);
          return 1;
        }

        // Compute step result error.
        const TestAction& output_actions = brain_spec.actions;

        if (output_actions.source() ==
            falken::ActionsBase::Source::kSourceBrainAction) {
          ++brain_action_counter;
          if (last_episode) {
            // Calculate time spent generating the brain action.
            absl::Duration episode_step_duration = (absl::Now() - before);
            time_stepping += episode_step_duration;

            LogMessage("Last episode: Evaluating trained brain.");
            float number_error =
                (std::fabs(static_cast<float>(output_actions.number) -
                           static_cast<float>(expert_policy_actions.number))) /
                (output_actions.number.value_maximum() -
                 output_actions.number.value_minimum());
            float category_error =
                (std::fabs(static_cast<int>(output_actions.category) -
                           static_cast<int>(expert_policy_actions.category))) /
                static_cast<float>(output_actions.category.categories().size());
            float bool_error =
                static_cast<bool>(output_actions.boolean) !=
                        static_cast<bool>(expert_policy_actions.boolean)
                    ? 0.5f
                    : 0.0f;
            LogMessage(
                "Step %d: number_error: %f, category_error: %f, bool_error %f.",
                step_count, number_error, category_error, bool_error);
            total_error += number_error + category_error + bool_error;
            ++eval_frames;
          }
        }

        const char* action_source_string = nullptr;
        switch (output_actions.source()) {
          case falken::ActionsBase::kSourceInvalid:
            action_source_string = "Invalid";
            break;
          case falken::ActionsBase::kSourceNone:
            action_source_string = "None";
            break;
          case falken::ActionsBase::kSourceHumanDemonstration:
            action_source_string = "Human Demonstration";
            break;
          case falken::ActionsBase::kSourceBrainAction:
            action_source_string = "Brain Action";
            break;
        }

        LogMessage("Stepped episode %d, step %d (action source %s).", ep,
                   step_count, action_source_string);
        absl::SleepFor(absl::Milliseconds(milliseconds_between_steps));

        // Add step data to submitted steps list.
        auto& submitted_step = submitted_steps[step_count];
        FillStep(brain_spec, submitted_step);
      }
      // Complete episode.
      if (!episode->Complete(falken::Episode::kCompletionStateSuccess)) {
        LogError("Complete episode failed for episode no. %d.", ep);
        return 1;
      }
      LogMessage("Completed episode no. %d successfully.", ep);
      ++episodes_index;
    }

    if (!brain_action_counter) {
      LogError("Inference failed: No brain actions recorded.");
      return 1;
    }

    // Check average error.
    float average_error = total_error / eval_frames;
    LogMessage("Average eval error is %f.", average_error);
    if (average_error > kAverageErrorLimit) {
      LogError("Average error higher than allowed threshold of %f.",
               kAverageErrorLimit);
      return 1;
    }

    LogMessage("Evaluation performed %d Step calls in %.4fms\n"
               "Overall speed: %.2f Steps per second, %.4fms per step.",
               number_of_steps_per_episode,
               static_cast<float>(absl::ToDoubleMilliseconds(time_stepping)),
               static_cast<float>(static_cast<float>(eval_frames) /
                                  absl::ToDoubleSeconds(time_stepping)),
               static_cast<float>(absl::ToDoubleMilliseconds(time_stepping) /
                                  static_cast<float>(eval_frames)));
    // Stop session.
    auto snapshot_id = session->Stop();
    if (!session->stopped()) {
      LogError("Stop session failed.");
      return 1;
    }
    LogMessage("Stopped session successfully.");
  }

  // Compare retrieved and submitted session.
  // Load brain.
  std::shared_ptr<falken::Brain<TestTemplateBrainSpec>> loaded_brain =
      service.GetBrain<TestTemplateBrainSpec>(brain_id.c_str());
  if (!loaded_brain) {
    LogError("Load brain with id '%s' failed.", brain_id.c_str());
    return 1;
  }

  // Load session count.
  std::vector<std::shared_ptr<falken::Session>> sessions =
      loaded_brain->ListSessions();
  if (sessions.empty()) {
    LogError("Loaded brain's session count equal to zero.");
    return 1;
  }

  // Load episode count.
  auto& loaded_session = sessions[0];
  int loaded_episode_count = loaded_session->GetEpisodeCount();
  int submitted_episode_count = submitted_episodes.size();
  if (loaded_episode_count != submitted_episode_count) {
    LogError(
        "Loaded session %s of brain %s reports a different number of episodes "
        "(%d) than submitted (%d).",
        loaded_session->id(), loaded_brain->id(), loaded_episode_count,
        submitted_episode_count);
    return 1;
  }

  // Compare episodes.
  bool received_matches = true;
  for (int ep = 0; ep < submitted_episode_count; ++ep) {
    // Load episode.
    auto loaded_episode = loaded_session->GetEpisode(ep);
    if (!loaded_episode) {
      LogError("Load episode no. %d failed.", ep);
      return 1;
    }

    // Load step count.
    int loaded_step_count = loaded_episode->GetStepCount();
    int submitted_step_count = submitted_episodes[ep].steps.size();
    if (loaded_step_count != submitted_step_count) {
      LogError(
          "Loaded episode %d of session %s reports a different number of steps "
          "(%d) than submitted (%d).",
          ep, loaded_session->id(), loaded_step_count, submitted_step_count);
      return 1;
    }

    // Compare steps.
    for (int step = 0; step < loaded_step_count; ++step) {
      if (!loaded_episode->ReadStep(step)) {
        LogError("Reading step %d of episode %d of session %s failed.", step,
                 ep, loaded_session->id());
        return 1;
      }
      auto& loaded_step_data = loaded_brain->brain_spec();
      const TestStepData& submitted_step_data =
          submitted_episodes[ep].steps[step];

      // Compare feelers.
      if (!CheckFeelers(submitted_step_data.observation.feelers,
                        loaded_step_data.observations.feelers)) {
        LogError(
            "Loaded feelers of step %d of episode %d reports a different value "
            "than submitted.",
            step, ep);
        received_matches = false;
      }

      // Compare entities.
      if (!CheckEntities(submitted_step_data.observation.evil_guy,
                         loaded_step_data.observations.evil_guy)) {
        LogError(
            "Loaded entities of step %d of episode %d reports a different "
            "value than submitted.",
            step, ep);
        received_matches = false;
      }

      // Compare observations.
      if (!CheckObservations(submitted_step_data.observation,
                             loaded_step_data.observations)) {
        LogError(
            "Loaded observations of step %d of episode %d reports a different "
            "value than submitted.",
            step, ep);
        received_matches = false;
      }

      // Compare actions.
      if (!CheckActions(submitted_step_data.action, loaded_step_data.actions)) {
        LogError(
            "Loaded actions of step %d of episode %d reports a different value "
            "than submitted.",
            step, ep);
        received_matches = false;
      }
    }
  }

  if (!received_matches) {
    LogError("Retrieved episodes do not match submitted episodes.");
    return 1;
  }
  LogMessage("Retrieved episodes matched submitted episodes.");

  return 0;
}

namespace falken {
// Get the private state from a session.
class ServiceTest {
 public:
  static String GetSessionState(Session& session) { return session.state(); }
};
}  // namespace falken

static void* CustomAllocate(size_t size, void* context) { return malloc(size); }
static void CustomFree(void* ptr, void* context) { free(ptr); }

// Test app entry point.
extern "C" int common_main(int argc, const char* argv[]) {
#if defined(__ANDROID__)
  falken::Service::SetTemporaryDirectory(GetTemporaryDirectoryPath());
#endif
  falken::AllocatorCallbacks custom_callbacks(CustomAllocate, CustomFree,
                                              nullptr);
  falken::AllocatorCallbacks::Set(custom_callbacks);
  absl::ParseCommandLine(argc, const_cast<char**>(argv));

  // Configure the log verbosity.
  std::string log_level = absl::GetFlag(FLAGS_log_level);
  auto system_logger = falken::SystemLogger::Get();
  for (int i = 0;
       i < sizeof(kLogLevelNameToEnum) / sizeof(kLogLevelNameToEnum[0]); ++i) {
    if (log_level == kLogLevelNameToEnum[i].name) {
      system_logger->set_log_level(kLogLevelNameToEnum[i].log_level);
      break;
    }
  }

  std::string json_config;
  // Try reading configuration from the file.
  std::string json_config_file = absl::GetFlag(FLAGS_json_config_file);
  if (!json_config_file.empty()) {
    std::ifstream stream(json_config_file, std::ifstream::in);
    if (!stream.is_open()) {
      LogError("Failed to read JSON config %s", json_config_file.c_str());
      return 1;
    }
    stream.seekg(0, stream.end);
    auto size = stream.tellg();
    stream.seekg(0, stream.beg);
    json_config.resize(size, '\0');
    stream.read(&json_config[0], size);
    stream.close();
  }
  if (json_config.empty()) {
    const std::string project_id = absl::GetFlag(FLAGS_project_id);
    if (project_id.empty()) {
      LogError("You need to provide a valid project id.");
      return 1;
    }
    // If the API key flag is set, use it, otherwise check the environment
    // variable.
    std::string api_key = absl::GetFlag(FLAGS_api_key);
    const char* api_key_from_env = std::getenv(
        kFalkenApiKeyEnvironmentVariable);
    if (api_key.empty() && api_key_from_env != nullptr) {
      api_key = api_key_from_env;
    }
    // If the env flag is set, use it, otherwise the default is local.
    std::string environment = absl::GetFlag(FLAGS_env);
    // Build json config.
    std::string service_address = absl::GetFlag(FLAGS_service_address);
    std::string grpc_address_setting =
        service_address.empty()
        ? ""
        : absl::StrFormat("\"connection\": {  \"address\": \"%s\" }",
                          service_address.c_str());
    json_config =
        absl::StrFormat(kJsonConfigSchema, api_key.c_str(), project_id.c_str(),
                        absl::GetFlag(FLAGS_rpc_timeout_in_milliseconds),
                        environment.c_str(), grpc_address_setting);
  }

  // Connect to the service.
  std::shared_ptr<falken::Service> service = falken::Service::Connect(
      nullptr, nullptr, json_config.c_str());
  if (!service) {
    LogError("Connection to service failed.");
    return 1;
  }
  LogMessage("Connection to service successful.");

  int status = TestInteractiveTraining(*service);
  if (status != 0) {
    LogError("Interactive training test failed.");
    return status;
  }
  LogMessage("Interactive training test succeeded.");
  LogMessage("Test app succeeded.");
  return 0;
}
