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

package com.google.falken.hellofalken;

import android.os.Bundle;
import android.view.MotionEvent;
import android.view.View;
import org.libsdl.app.SDLActivity;

/**
 * A Falken C++ SDK sample application.
 *
 * <p>This is the main Activity of the sample application. It adds a controller UI on top of the
 * view created by SDLActivity.
 */
public class HFActivity extends SDLActivity {
  /**
   * Gamepad buttons.
   *
   * @note This enum class must be kept in sync with the C++ counterpart (@see
   *     spaas/sdk_cpp/samples/hello_falken/src/gamepad.cc).
   */
  private abstract static class Button {
    private Button() {}

    // Up button.
    public static final int BUTTON_UP = 0;
    // Down button.
    public static final int BUTTON_DOWN = 1;
    // Left button.
    public static final int BUTTON_LEFT = 2;
    // Right button.
    public static final int BUTTON_RIGHT = 3;
    // Reset button.
    public static final int BUTTON_RESET = 4;
    // A button.
    public static final int BUTTON_A = 5;
    // B button.
    public static final int BUTTON_B = 6;
  }

  /**
   * Button states.
   *
   * @note This enum class must be kept in sync with the C++ counterpart (@see
   *     spaas/sdk_cpp/samples/hello_falken/src/gamepad.cc).
   */
  private abstract static class State {
    private State() {}

    // The button is released.
    public static final int RELEASED = 0;
    // The button is pressed.
    public static final int PRESSED = 1;
  }

  @Override
  public void onCreate(Bundle savedInstance) {
    super.onCreate(savedInstance);
    View gamepadView = getLayoutInflater().inflate(R.layout.gamepad, null);
    mLayout.addView(gamepadView);

    findViewById(R.id.button_up)
        .setOnTouchListener(
            (v, event) -> {
              onButtonEvent(event, Button.BUTTON_UP);
              v.performClick();
              return false;
            });
    findViewById(R.id.button_down)
        .setOnTouchListener(
            (v, event) -> {
              onButtonEvent(event, Button.BUTTON_DOWN);
              v.performClick();
              return false;
            });
    findViewById(R.id.button_left)
        .setOnTouchListener(
            (v, event) -> {
              onButtonEvent(event, Button.BUTTON_LEFT);
              v.performClick();
              return false;
            });
    findViewById(R.id.button_right)
        .setOnTouchListener(
            (v, event) -> {
              onButtonEvent(event, Button.BUTTON_RIGHT);
              v.performClick();
              return false;
            });
    findViewById(R.id.button_reset)
        .setOnTouchListener(
            (v, event) -> {
              onButtonEvent(event, Button.BUTTON_RESET);
              v.performClick();
              return false;
            });
    findViewById(R.id.button_a)
        .setOnTouchListener(
            (v, event) -> {
              onButtonEvent(event, Button.BUTTON_A);
              v.performClick();
              return false;
            });
    findViewById(R.id.button_b)
        .setOnTouchListener(
            (v, event) -> {
              onButtonEvent(event, Button.BUTTON_B);
              v.performClick();
              return false;
            });
  }

  private void onButtonEvent(MotionEvent event, int button) {
    switch (event.getAction()) {
      case MotionEvent.ACTION_DOWN:
        nativeOnButtonEvent(button, State.PRESSED);
        break;
      case MotionEvent.ACTION_UP:
        nativeOnButtonEvent(button, State.RELEASED);
        break;
      default:
        break;
    }
  }

  private native void nativeOnButtonEvent(int button, int state);
}
