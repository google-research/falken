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

#ifndef FALKEN_SDK_CORE_ACTION_PROTO_CONVERTER_H_
#define FALKEN_SDK_CORE_ACTION_PROTO_CONVERTER_H_

#include "src/core/protos.h"
#include "falken/actions.h"

namespace falken {

class ActionProtoConverter {
 public:
  static proto::ActionSpec ToActionSpec(const ActionsBase& action_base);
  static proto::ActionData ToActionData(const ActionsBase& action_base);
  // Allocate attributes for a given ActionsBase from an ActionSpec.
  static void FromActionSpec(const proto::ActionSpec& action_spec,
                             ActionsBase& actions_base);
  static bool FromActionData(const proto::ActionData& action_data,
                             ActionsBase& actions_base);
  static bool VerifyActionSpecIntegrity(const proto::ActionSpec& action_spec,
                                        const ActionsBase& actions_base);

 private:
  static proto::ActionType* ToActionType(const AttributeBase& attribute,
                                         proto::ActionSpec& action_spec);
  static void ToCategoryType(const AttributeBase& attribute,
                             proto::ActionSpec& action_spec);
  static void ToCategory(const AttributeBase& attribute,
                         proto::ActionData& action_data);
};

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_ACTION_PROTO_CONVERTER_H_
