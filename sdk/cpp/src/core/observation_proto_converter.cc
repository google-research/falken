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

#include "src/core/observation_proto_converter.h"

#include <string.h>

#include "src/core/entity_proto_converter.h"
#include "src/core/log.h"
#include "src/core/protos.h"
#include "falken/entity.h"

namespace falken {

proto::ObservationSpec ObservationProtoConverter::ToObservationSpec(
    const ObservationsBase& observation_base) {
  proto::ObservationSpec observation_spec;
  *observation_spec.mutable_player() =
      EntityProtoConverter::ToEntityType(observation_base);
  for (const EntityBase* entity_base : observation_base.entities()) {
    if (strcmp(entity_base->name(), "player") == 0) {
      continue;  // Ignore player entity since it's already parsed.
    } else if (strcmp(entity_base->name(), "camera") == 0) {
      *observation_spec.mutable_camera() =
          EntityProtoConverter::ToEntityType(*entity_base);
    } else {
      proto::EntityType* entity_type = observation_spec.add_global_entities();
      *entity_type = EntityProtoConverter::ToEntityType(*entity_base);
    }
  }
  return observation_spec;
}

proto::ObservationData ObservationProtoConverter::ToObservationData(
    const ObservationsBase& observation_base) {
  proto::ObservationData observation_data;
  *observation_data.mutable_player() =
      EntityProtoConverter::ToEntity(observation_base);
  for (const EntityBase* entity_base : observation_base.entities()) {
    if (strcmp(entity_base->name(), "player") == 0) {
      continue;  // Ignore player entity since it's already parsed.
    } else if (strcmp(entity_base->name(), "camera") == 0) {
      *observation_data.mutable_camera() =
          EntityProtoConverter::ToEntity(*entity_base);
    } else {
      proto::Entity* entity = observation_data.add_global_entities();
      *entity = EntityProtoConverter::ToEntity(*entity_base);
    }
  }
  return observation_data;
}

void ObservationProtoConverter::FromObservationSpec(
    const proto::ObservationSpec& observation_spec,
    ObservationsBase& observation_base) {
  const std::string entity_base_name = "entity_";
  EntityProtoConverter::FromEntityType(observation_spec.player(),
                                       observation_base);
  if (observation_spec.has_camera()) {
      EntityProtoConverter::FromEntityType(observation_spec.camera(),
                                           "camera",
                                           observation_base);
  }
  size_t entity_index = 0;
  for (const proto::EntityType& entity_type :
       observation_spec.global_entities()) {
    const std::string entity_actual_name =
        entity_base_name + std::to_string(entity_index);
    EntityProtoConverter::FromEntityType(entity_type, entity_actual_name,
                                         observation_base);
    ++entity_index;
  }
}

bool ObservationProtoConverter::FromObservationData(
    const proto::ObservationData& observation_data,
    ObservationsBase& observations_base) {
  if (!VerifyObservationDataIntegrity(observation_data, observations_base)) {
    LogError("Failed to parse the observations returned by the service. %s.",
             kContactFalkenTeamBug);
    return false;
  }

  bool parsed = true;
  // Convert entities.
  size_t entity_index = 0;
  for (EntityBase* entity_base : observations_base.entities()) {
    // Player entity it's not part of the global entities message in the proto.
    if (strcmp(entity_base->name(), "player") == 0) {
      parsed = EntityProtoConverter::FromEntity(observation_data.player(),
                                                *entity_base) &&
               parsed;
    } else if (strcmp(entity_base->name(), "camera") == 0) {
      parsed = EntityProtoConverter::FromEntity(observation_data.camera(),
                                                *entity_base) &&
               parsed;
    } else {
      const proto::Entity& entity =
          observation_data.global_entities()[entity_index];
      // Keep parsing even if we find a wrong entity to fully log every error
      // found.
      parsed = EntityProtoConverter::FromEntity(entity, *entity_base) && parsed;
      ++entity_index;
    }
  }

  return parsed;
}

bool ObservationProtoConverter::VerifyObservationSpecIntegrity(
    const proto::ObservationSpec& observation_spec,
    const ObservationsBase& observations_base) {
  bool success = true;
  size_t global_entity_index = 0;
  bool has_player = false;
  bool has_camera = false;

  for (const EntityBase* entity_base : observations_base.entities()) {
    if (strcmp(entity_base->name(), "player") == 0) {
      has_player = true;
      if (!EntityProtoConverter::VerifyEntityTypeIntegrity(
              observation_spec.player(), *entity_base)) {
        LogWarning(
            "Player entity differs from the service specifications."
            "Please check that is was properly defined in your code.");
        success = false;
      }
    } else if (strcmp(entity_base->name(), "camera") == 0) {
      has_camera = true;
      if (!EntityProtoConverter::VerifyEntityTypeIntegrity(
              observation_spec.camera(), *entity_base)) {
        LogWarning(
            "Camera entity differs from the service specifications."
            "Please check that is was properly defined in your code.");
        success = false;
      }
    } else {
      if (global_entity_index < observation_spec.global_entities_size()) {
        const auto& entity_spec =
            observation_spec.global_entities(global_entity_index);
        if (!EntityProtoConverter::VerifyEntityTypeIntegrity(
                entity_spec, *entity_base)) {
          LogWarning(
              "Observations specifications in '%s' are different from the ones "
              "in the service. Please check that the specifications for this "
              "entity were properly defined in your code.",
              entity_base->name());
          success = false;
        }
      }
      global_entity_index++;
    }
  }

  if (observation_spec.has_player() != has_player) {
    LogWarning(
        "The service a expected a \"player\" entity, but the application did "
        "not define one. Please create a brain with a \"player\" entity.");
    success = false;
  }

  if (observation_spec.has_camera() != has_camera) {
    LogWarning(
        "The service a expected a \"camera\" entity, but the application did "
        "not define one. Please create a brain with a \"camera\" entity.");
    success = false;
  }

  if (global_entity_index != observation_spec.global_entities_size()) {
    LogWarning(
        "Observations specification size mismatch. The service expected '%d' "
        "custom entities and the application defined '%d' entities. Please "
        "create a new brain with the new observation specifications.",
        global_entity_index, observation_spec.global_entities_size());
    success = false;
  }

  return success;
}

bool ObservationProtoConverter::VerifyObservationDataIntegrity(
    const proto::ObservationData& observation_data,
    const ObservationsBase& observations_base) {
  bool success = true;
  size_t global_entity_index = 0;
  bool has_player = false;
  bool has_camera = false;

  for (const EntityBase* entity_base : observations_base.entities()) {
    if (strcmp(entity_base->name(), "player") == 0) {
      has_player = true;
      if (!EntityProtoConverter::VerifyEntityIntegrity(
              observation_data.player(), *entity_base)) {
        LogWarning(
            "Player entity differs from the service specifications."
            "Please check that is was properly defined in your code.");
        success = false;
      }
    } else if (strcmp(entity_base->name(), "camera") == 0) {
      has_camera = true;
      if (!EntityProtoConverter::VerifyEntityIntegrity(
              observation_data.camera(), *entity_base)) {
        LogWarning(
            "Camera entity differs from the service specifications."
            "Please check that is was properly defined in your code.");
        success = false;
      }
    } else {
      if (global_entity_index < observation_data.global_entities_size()) {
        const auto& entity =
            observation_data.global_entities(global_entity_index);
        if (!EntityProtoConverter::VerifyEntityIntegrity(
                entity, *entity_base)) {
          LogWarning(
              "Observations specifications in '%s' are different from the ones "
              "in the service. Please check that the specifications for this "
              "entity were properly defined in your code.",
              entity_base->name());
          success = false;
        }
      }
      global_entity_index++;
    }
  }

  if (observation_data.has_player() != has_player) {
    LogWarning(
        "The service expected a \"player\" entity, but the "
        "application did not define one. Please create a brain with a "
        "\"player\" entity.");
    success = false;
  }

  if (observation_data.has_camera() != has_camera) {
    LogWarning(
        "The service expected a expected a \"camera\" entity, but the "
        "application did not define one. Please create a brain with a "
        "\"camera\" entity.");
    success = false;
  }

  if (global_entity_index != observation_data.global_entities_size()) {
    LogWarning(
        "Observations specification size mismatch. The service expected '%d' "
        "custom entities and the application defined '%d' entities. Please "
        "create a new brain with the new observation specifications.",
        global_entity_index, observation_data.global_entities_size());
    success = false;
  }

  return success;
}

}  // namespace falken
