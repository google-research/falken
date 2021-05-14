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

#include "keyboard.h"

#include <SDL.h>

namespace hello_falken {

Keyboard::Keyboard() {
  SDL_StartTextInput();
}

Keyboard::~Keyboard() {
  SDL_StopTextInput();
}

bool Keyboard::GetInputState(Input input) const {
  const Uint8* keystates = SDL_GetKeyboardState(nullptr);
  switch (input) {
    case kChangeControl:
      return keystates[SDL_SCANCODE_SPACE];
    case kReset:
      return keystates[SDL_SCANCODE_R];
    case kForceEvaluation:
      return keystates[SDL_SCANCODE_E];
    case kGoUp:
      return keystates[SDL_SCANCODE_W] || keystates[SDL_SCANCODE_UP];
    case kGoDown:
      return keystates[SDL_SCANCODE_S] || keystates[SDL_SCANCODE_DOWN];
    case kGoLeft:
      return keystates[SDL_SCANCODE_A] || keystates[SDL_SCANCODE_LEFT];
    case kGoRight:
      return keystates[SDL_SCANCODE_D] || keystates[SDL_SCANCODE_RIGHT];
    default:
      return false;
  }
  return false;
}

}  // namespace hello_falken
