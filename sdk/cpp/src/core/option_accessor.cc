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

#include "src/core/option_accessor.h"

namespace falken {
namespace core {

// Build a string from a flexbuffers reference to a string or string list.
std::string FlexbuffersStringListToString(
    const flexbuffers::Reference& value) {
  std::string return_value;
  if (value.IsString()) {
    return_value = value.As<std::string>();
  } else if (value.IsVector()) {
    auto v = value.AsVector();
    for (size_t i = 0; i < v.size(); ++i) {
      return_value += v[i].As<std::string>() + "\n";
    }
  }
  return return_value;
}

}  // namespace core
}  // namespace falken
