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

#include "gamepad.h"

#include <jni.h>

#if !defined(__ANDROID__)
#error This gamepad implementation only works on Android.
#endif  // !defined(__ANDROID__)

#define JNI_METHOD(return_type, method_name) \
  JNIEXPORT return_type JNICALL              \
      Java_com_google_falken_hellofalken_HFActivity_##method_name

namespace {

// Gamepad buttons.
// @note This enum must be kept in sync with the Java counterpart (@see
// spaas/sdk_cpp/samples/hello_falken/src/android/java/com/google/falken/hellofalken/HFActivity.java).
enum Button {
  // Up button.
  kButtonUp = 0,
  // Down button.
  kButtonDown,
  // Left button.
  kButtonLeft,
  // Right button.
  kButtonRight,
  // Reset button.
  kButtonReset,
  // A button.
  kButtonA,
  // B button.
  kButtonB,
  // Button count.
  kButtonCount
};

// Button states.
// @note This enum must be kept in sync with the Java counterpart (@see
// spaas/sdk_cpp/samples/hello_falken/src/android/java/com/google/falken/hellofalken/HFActivity.java).
enum State {
  // The button is released.
  kReleased = 0,
  // The button is pressed.
  kPressed,
};

// Saves buttons state. It is asynchronously updated by a JNI call when a change
// in a button state takes place.
uint8_t keystates[kButtonCount] = {kReleased};

}  // namespace

namespace hello_falken {

bool Gamepad::GetInputState(Input input) const {
  switch (input) {
    case kChangeControl:
      return keystates[kButtonA];
    case kReset:
      return keystates[kButtonReset];
    case kForceEvaluation:
      return keystates[kButtonB];
    case kGoUp:
      return keystates[kButtonUp];
    case kGoDown:
      return keystates[kButtonDown];
    case kGoLeft:
      return keystates[kButtonLeft];
    case kGoRight:
      return keystates[kButtonRight];
    default:
      return false;
  }
  return false;
}

}  // namespace hello_falken

extern "C" {

JNI_METHOD(void, nativeOnButtonEvent)
(JNIEnv* env, jobject obj, jint button, jint state) {
  // Updates buttons state.
  keystates[button] = state;
}

}  // extern "C"
