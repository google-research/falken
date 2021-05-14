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

#ifndef HELLO_FALKEN_KEYBOARD_H_
#define HELLO_FALKEN_KEYBOARD_H_

#include "input_device.h"

namespace hello_falken {

// @brief Keyboard concrete implementation of InputDevice.
class Keyboard : public InputDevice {
 public:
  // Creates a Keyboard instance.
  Keyboard();

  // Destroys a Keyboard instance.
  ~Keyboard();

  // Returns input state.
  bool GetInputState(Input input) const override;
};

}  // namespace hello_falken

#endif  // HELLO_FALKEN_KEYBOARD_H_
