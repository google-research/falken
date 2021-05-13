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

#include <SDL.h>
#include <stdio.h>
#include <string.h>

#include <string>

#include "game.h"

using namespace hello_falken;

const char* get_arg(int argc, char* args[], const char* opt_name) {
  // Return nullptr if option is not set, otherwise return succeeding string.
  for (int i = 1; i < argc; ++i) {
    if (strcmp(opt_name, args[i]) == 0) {
      if (i + 1 == argc) {
        return "";
      }
      return args[i + 1];
    }
  }
  return nullptr;
}

int main(int argc, char* args[]) {
  const char* brain_id = get_arg(argc, args, "-brain_id");
  const char* snapshot_id = get_arg(argc, args, "-snapshot_id");
  bool vsync = (get_arg(argc, args, "-novsync") == nullptr);

  if (SDL_Init(SDL_INIT_VIDEO) < 0) {
    SDL_Log("SDL could not initialize! SDL Error: %s\n", SDL_GetError());
    return 1;
  }

  Game game;
  SDL_Log("Starting game with brain_id %s and snapshot_id %s\n",
          (brain_id == nullptr ? "<new>" : brain_id),
          (snapshot_id == nullptr ? "<new>" : snapshot_id));
  if (!game.Init(brain_id, snapshot_id, vsync)) {
    return 1;
  }

  Uint64 current_time = SDL_GetPerformanceCounter();
  Uint64 last_time = 0;
  bool quit = false;
  while (!quit) {
    // Compute a delta_time (in milliseconds) for each frame
    last_time = current_time;
    current_time = SDL_GetPerformanceCounter();
    static const float kMillisecondsPerSecond = 1000.0f;
    float delta_time = ((current_time - last_time) * kMillisecondsPerSecond /
                        SDL_GetPerformanceFrequency()) /
                       kMillisecondsPerSecond;

    game.Update(delta_time);

    // Check for any events from "outside" the game.
    SDL_Event e;
    while (SDL_PollEvent(&e) != 0) {
      if (e.type == SDL_QUIT) {
        quit = true;
      }
    }
  }

  game.Shutdown();
  SDL_Quit();

  return 0;
}
