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

#ifndef HELLO_FALKEN_RENDER_H_
#define HELLO_FALKEN_RENDER_H_

#if !defined(_WIN32)
#define GL_GLEXT_PROTOTYPES
#endif
#include "glplatform.h"
#include "math_utils.h"

struct SDL_Window;
typedef void* SDL_GLContext;

namespace hello_falken {

class Ship;
class Goal;

class Renderer {
 public:
  // Creates a Renderer instance.
  Renderer();

  // Returns a safe distance from zero to the horizontal edge of the screen.
  inline float SafeX(float size) const {
    return half_screen_width_ - size * 0.5f;
  }

  // Returns a safe distance from zero to the vertical edge of the screen.
  inline float SafeY(float size) const {
    return half_screen_height_ - size * 0.5f;
  }

  // Computes an absolute value from a value relative to the smallest screen
  // dimension.
  inline float AbsoluteValue(float relative_value) const {
    return relative_value *
           (screen_width_ < screen_height_ ? screen_width_ : screen_height_);
  }

  // Creates window and sets up OpenGL.
  bool Init(bool vsync_requested);

  // Performs per-frame rendering.
  void Render(const Ship& ship, const Goal& goal);

  // Tears down objects created in InitRender().
  void Shutdown();

 private:
  enum ObjectBuffer {
    kObjectBufferShip = 0,
    kObjectBufferGoal,
    kObjectBufferCount,
  };

  bool GlSetUp();
  void GlTearDown();
  void DrawShip(const Ship& ship);
  void DrawGoal(const Goal& goal);

  SDL_Window* gWindow = nullptr;
  SDL_GLContext gContext = nullptr;
  bool using_vsync = true;

  GLuint program_;
  GLuint vertex_array_[kObjectBufferCount];
  GLuint vertex_buffer_[kObjectBufferCount];
  GLuint modelview_projection_param_;
  Mat4 projection_;

  int screen_width_;
  int half_screen_width_;
  int screen_height_;
  int half_screen_height_;
};

}  // namespace hello_falken

#endif /* HELLO_FALKEN_RENDER_H_ */
