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

#include "render.h"

#include <SDL.h>
#include <assert.h>

#include <cstdio>

#if !defined(_WIN32)
#define GL_GLEXT_PROTOTYPES
#endif
#include "glplatform.h"
#include "math_utils.h"
#include "ship.h"

#if defined(_WIN32)
// Loads OpenGL function symbols. This is required to load OpenGL 3
// function symbols on Windows machines. 
#define LOOKUP_GL_FUNCTION(type, name, required, lookup_fn)        \
  union {                                                          \
    void *data;                                                    \
    type function;                                                 \
  } data_function_union_##name;                                    \
  data_function_union_##name.data = (void *)lookup_fn(#name);      \
  if (required && !data_function_union_##name.data) {              \
    return false;                                                  \
  }                                                                \
  name = data_function_union_##name.function;

// Initializes OpenGL function pointers to null.
#define GLEXT(type, name, required) type name = nullptr;
GLBASEEXTS GLEXTS
#undef GLEXT
#endif

#define CHECKGLERROR(label) CheckGlError(__FILE__, __LINE__, label)

namespace hello_falken {
namespace {

#pragma pack(push, 1)
struct Vector3 {
  GLfloat x;
  GLfloat y;
  GLfloat z;
};
#pragma pack(pop)

#pragma pack(push, 1)
struct Color3 {
  GLfloat r;
  GLfloat g;
  GLfloat b;
};
#pragma pack(pop)

#pragma pack(push, 1)
struct ColoredVertex {
  Vector3 vertex;
  Color3 color;
};
#pragma pack(pop)

const ColoredVertex ship_vertices[] = {
    // Position            // Color
    {{ 0.5f,  0.0f, 0.0f}, {0.0f, 0.0f, 1.0f}},
    {{-0.5f,  0.5f, 0.0f}, {0.0f, 0.6f, 1.0f}},
    {{-0.5f, -0.5f, 0.0f}, {0.0f, 0.6f, 1.0f}}};

const ColoredVertex goal_vertices[] = {
    // Position            // Color
    {{ 0.0f,  0.5f, 0.0f}, {1.0f, 0.0f, 0.0f}},
    {{-0.5f,  0.0f, 0.0f}, {1.0f, 0.0f, 0.0f}},
    {{ 0.0f, -0.5f, 0.0f}, {1.0f, 0.0f, 0.0f}},
    {{ 0.0f, -0.5f, 0.0f}, {1.0f, 0.0f, 0.0f}},
    {{ 0.5f,  0.0f, 0.0f}, {1.0f, 0.0f, 0.0f}},
    {{ 0.0f,  0.5f, 0.0f}, {1.0f, 0.0f, 0.0f}}};

#if defined(__ANDROID__)
#define GL_SHADER_VERSION "#version 300 es\n"
#else
#define GL_SHADER_VERSION "#version 330 core\n"
#endif  // defined(__ANDROID__)

constexpr const char* kVertexShader =
    GL_SHADER_VERSION
    R"glsl(uniform mat4 u_MVP;
    layout (location = 0) in vec3 a_Position;
    layout (location = 1) in vec3 a_Color;
    out vec3 v_Color;

    void main() {
      gl_Position = u_MVP * vec4(a_Position, 1.0f);
      v_Color = a_Color;
    })glsl";

constexpr const char* kFragmentShader =
    GL_SHADER_VERSION
    R"glsl(precision mediump float;

    in vec3 v_Color;
    out vec4 o_FragColor;

    void main() {
      o_FragColor = vec4(v_Color, 1.0f);
    })glsl";

void CheckGlError(const char* file, int line, const char* label) {
  int gl_error = glGetError();
  if (gl_error != GL_NO_ERROR) {
    SDL_Log("%s : %d > GL error @ %s: %d", file, line, label, gl_error);
    // Crash immediately to make OpenGL errors obvious.
    abort();
  }
}

GLuint LoadGLShader(GLenum type, const char* shader_source) {
  GLuint shader = glCreateShader(type);
  glShaderSource(shader, 1, &shader_source, nullptr);
  glCompileShader(shader);

  // Get the compilation status.
  GLint compile_status;
  glGetShaderiv(shader, GL_COMPILE_STATUS, &compile_status);

  // If the compilation failed, delete the shader and show an error.
  if (compile_status == 0) {
    GLint info_len = 0;
    glGetShaderiv(shader, GL_INFO_LOG_LENGTH, &info_len);
    if (info_len == 0) {
      return 0;
    }

    std::vector<char> info_string(info_len);
    glGetShaderInfoLog(shader, info_string.size(), nullptr, info_string.data());
    SDL_Log("Could not compile shader of type %d: %s", type,
            info_string.data());
    glDeleteShader(shader);
    return 0;
  } else {
    return shader;
  }
}

}  // namespace

Renderer::Renderer() {
#if defined(__ANDROID__)
  // Window size is fullscreen on Android platforms.
  SDL_DisplayMode display_mode;
  if (SDL_GetCurrentDisplayMode(0, &display_mode) == 0) {
    screen_width_ = display_mode.w;
    screen_height_ = display_mode.h;
  } else {
    screen_width_ = 0;
    screen_height_ = 0;
  }
#else
  // Window size is fixed on desktop platforms.
  screen_width_ = 640;
  screen_height_ = 480;
#endif
  half_screen_width_ = screen_width_ / 2;
  half_screen_height_ = screen_height_ / 2;
}

bool Renderer::Init(bool vsync_requested) {
  assert(gWindow == nullptr && gContext == nullptr);

  // Use OpenGL 3.2.
  SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 3);
  SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 2);
#if defined(__ANDROID__)
  SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_ES);
#else
  SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_CORE);
#endif

  // Create window.
  Uint32 window_flags = SDL_WINDOW_OPENGL | SDL_WINDOW_SHOWN;
#if defined(__ANDROID__)
  window_flags |= SDL_WINDOW_FULLSCREEN;
#endif
  gWindow = SDL_CreateWindow(
      "Hello Falken", SDL_WINDOWPOS_UNDEFINED, SDL_WINDOWPOS_UNDEFINED,
      screen_width_, screen_height_, window_flags);
  if (gWindow == nullptr) {
    SDL_Log("Window could not be created! SDL Error: %s\n", SDL_GetError());
    return false;
  }

  // Create context.
  gContext = SDL_GL_CreateContext(gWindow);
  if (gContext == nullptr) {
    SDL_Log("OpenGL context could not be created! SDL Error: %s\n",
            SDL_GetError());
    return false;
  }

  // Set up OpenGL.
  GlSetUp();

  // Compute orthogonal projection matrix.
  projection_ = Mat4::Ortho(-half_screen_width_, half_screen_width_,
                            -half_screen_height_, half_screen_height_, -1, 1);

  // Try to use Vsync
  if (vsync_requested) {
    if (SDL_GL_SetSwapInterval(1) < 0) {
      SDL_Log("Warning: Unable to set VSync! SDL Error: %s\n", SDL_GetError());
      using_vsync = false;
    } else {
      using_vsync = true;
    }
  } else {
    using_vsync = false;
  }

  if (!using_vsync) {
    SDL_Log("Not using vsync.");
  }

  return true;
}

void Renderer::Render(const Ship& ship, const Goal& goal) {
  assert(gWindow && gContext);

  // Clear color buffer.
  glClearColor(1.f, 1.f, 1.f, 1.f);
  glClear(GL_COLOR_BUFFER_BIT);

  DrawShip(ship);
  DrawGoal(goal);

  // Update screen.
  SDL_GL_SwapWindow(gWindow);

  // If vsync is disabled, enforce 60fps via SDL_Delay.
  if (!using_vsync) {
    SDL_Delay(16);  // 60 fps
  }
}

void Renderer::Shutdown() {
  assert(gWindow && gContext);
  GlTearDown();
  SDL_GL_DeleteContext(gContext);
  SDL_DestroyWindow(gWindow);
  gWindow = nullptr;
  gContext = nullptr;
}

bool Renderer::GlSetUp() {
#if defined(_WIN32)
// Loads OpenGL symbols and sets OpenGL function pointers.
#define GLEXT(type, name, required) \
  LOOKUP_GL_FUNCTION(type, name, required, SDL_GL_GetProcAddress)
GLBASEEXTS GLEXTS
#undef GLEXT
#endif

  // Load shaders.
  const GLuint vertex_shader = LoadGLShader(GL_VERTEX_SHADER, kVertexShader);
  const GLuint fragment_shader =
      LoadGLShader(GL_FRAGMENT_SHADER, kFragmentShader);

  // Create program.
  program_ = glCreateProgram();
  glAttachShader(program_, vertex_shader);
  glAttachShader(program_, fragment_shader);
  glLinkProgram(program_);
  glDeleteShader(vertex_shader);
  glDeleteShader(fragment_shader);
  CHECKGLERROR("Create program");

  // Get shader params.
  const GLuint position_param = glGetAttribLocation(program_, "a_Position");
  const GLuint color_param = glGetAttribLocation(program_, "a_Color");
  modelview_projection_param_ = glGetUniformLocation(program_, "u_MVP");
  CHECKGLERROR("Get shader params");

  // Create vertex arrays and vertex buffers.
  glGenVertexArrays(kObjectBufferCount, vertex_array_);
  glGenBuffers(kObjectBufferCount, vertex_buffer_);

  // Set ship vertex buffer.
  glBindVertexArray(vertex_array_[kObjectBufferShip]);
  glBindBuffer(GL_ARRAY_BUFFER, vertex_buffer_[kObjectBufferShip]);
  glBufferData(GL_ARRAY_BUFFER, sizeof(ship_vertices), ship_vertices,
               GL_STATIC_DRAW);
  glVertexAttribPointer(position_param, sizeof(Vector3) / sizeof(GLfloat),
                        GL_FLOAT, GL_FALSE, sizeof(ColoredVertex), nullptr);
  glEnableVertexAttribArray(position_param);
  glVertexAttribPointer(color_param, sizeof(Color3) / sizeof(GLfloat), GL_FLOAT,
                        GL_FALSE, sizeof(ColoredVertex),
                        (void*)offsetof(ColoredVertex, color));
  glEnableVertexAttribArray(color_param);

  // Set goal vertex buffer.
  glBindVertexArray(vertex_array_[kObjectBufferGoal]);
  glBindBuffer(GL_ARRAY_BUFFER, vertex_buffer_[kObjectBufferGoal]);
  glBufferData(GL_ARRAY_BUFFER, sizeof(goal_vertices), goal_vertices,
               GL_STATIC_DRAW);
  glVertexAttribPointer(position_param, sizeof(Vector3) / sizeof(GLfloat),
                        GL_FLOAT, GL_FALSE, sizeof(ColoredVertex), nullptr);
  glEnableVertexAttribArray(position_param);
  glVertexAttribPointer(color_param, sizeof(Color3) / sizeof(GLfloat), GL_FLOAT,
                        GL_FALSE, sizeof(ColoredVertex),
                        (void*)offsetof(ColoredVertex, color));
  glEnableVertexAttribArray(color_param);
  glBindVertexArray(0);

  CHECKGLERROR("GlSetUp");
  return true;
}

void Renderer::GlTearDown() {
  glUseProgram(program_);

  glDeleteVertexArrays(kObjectBufferCount, vertex_array_);
  vertex_array_[kObjectBufferShip] = 0;
  vertex_array_[kObjectBufferGoal] = 0;
  glDeleteBuffers(kObjectBufferCount, vertex_buffer_);
  vertex_buffer_[kObjectBufferShip] = 0;
  vertex_buffer_[kObjectBufferGoal] = 0;
  CHECKGLERROR("GlTearDown");
}

void Renderer::DrawShip(const Ship& ship) {
  glUseProgram(program_);

  Mat4 translation =
      Mat4::FromTranslationVector({ship.position.x, ship.position.y, 0.f});
  Mat4 rotation = Mat4::FromRotationZ(DegreesToRadians(ship.rotation));
  Mat4 scale = Mat4::FromScaleVector({AbsoluteValue(ship.kSize),
                                      AbsoluteValue(ship.kSize),
                                      AbsoluteValue(ship.kSize)});
  Mat4 model_view = translation * rotation * scale;
  Mat4 modelview_projection = projection_ * model_view;
  glUniformMatrix4fv(modelview_projection_param_, 1, GL_FALSE,
                     modelview_projection.ToArray().data());

  glBindVertexArray(vertex_array_[kObjectBufferShip]);
  glDrawArrays(GL_TRIANGLES, 0, 3);
  CHECKGLERROR("DrawShip");
}

void Renderer::DrawGoal(const Goal& goal) {
  glUseProgram(program_);

  Mat4 translation =
      Mat4::FromTranslationVector({goal.position.x, goal.position.y, 0.f});
  Mat4 scale = Mat4::FromScaleVector({AbsoluteValue(goal.kSize),
                                      AbsoluteValue(goal.kSize),
                                      AbsoluteValue(goal.kSize)});
  Mat4 model_view = translation * scale;
  Mat4 modelview_projection = projection_ * model_view;
  glUniformMatrix4fv(modelview_projection_param_, 1, GL_FALSE,
                     modelview_projection.ToArray().data());

  glBindVertexArray(vertex_array_[kObjectBufferGoal]);
  glDrawArrays(GL_TRIANGLES, 0, 6);
  CHECKGLERROR("DrawGoal");
}

}  // namespace hello_falken
