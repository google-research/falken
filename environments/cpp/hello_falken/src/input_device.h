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

#ifndef HELLO_FALKEN_INPUT_DEVICE_H_
#define HELLO_FALKEN_INPUT_DEVICE_H_

namespace hello_falken {

// @brief Interface describing a generic input device.
class InputDevice {
 public:
  // Input actions.
  enum Input {
    // Toggles between human and Falken control.
    kChangeControl = 0,
    // Resets the board.
    kReset,
    // Forces the start of an evaluation session w/o waiting for the training
    // to be completed.
    kForceEvaluation,
    // Moves the ship forward.
    kGoUp,
    // Moves the ship backward.
    kGoDown,
    // Steers the ship to the left.
    kGoLeft,
    // Steers the ship to the right.
    kGoRight
  };

  virtual ~InputDevice() = default;

  /*
   * Returns input state.
   */
  virtual bool GetInputState(Input input) const = 0;
};

}  // namespace hello_falken

#endif  // HELLO_FALKEN_INPUT_DEVICE_H_
