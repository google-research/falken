Install CMake (version 3.17 or higher is required)
 * Linux: sudo apt install cmake g++
 * MacOS: brew install cmake
 * Windows: https://cmake.org/install/

Build and Run Hello Falken (desktop version)
1. Make a new subdirectory called build and go into that directory:
 * mkdir build
 * cd build
2. Create build files:
  a. Windows:
   * cmake -DCMAKE_MODULE_PATH="<FALKEN_SDK_DIR>" -A x64 ..
  b. MacOS:
   * cmake -DCMAKE_MODULE_PATH="<FALKEN_SDK_DIR>" ..
  c. Linux:
   * cmake -DCMAKE_MODULE_PATH="<FALKEN_SDK_DIR>" ..
3. Set the Project ID and API key in `hello_falken/src/falken_player.cc` and
   `hello_falken/src/falken_player_dynamic.cc`.
4. Build project:
 * cmake --build .
5. Run executable:
 * ./HelloFalken

Build and Run Hello Falken (Android version)
1. Open the `hello_falken` folder with Android Studio.
2. Set `systemProp.falken_cpp_sdk.dir` with the Falken C++ SDK path in
   `hello_falken/gradle.properties`.
3. Set `FALKEN_CMAKE_VERSION` with the semantic version number of the installed
   CMake in `hello_falken/gradle.properties`.
4. Set the Project ID and API key in `hello_falken/src/falken_player.cc`.
5. Sync project.
6. Build project.
7. Install the app on an Android phone.
8. Launch app.

Playing The Game (desktop version)
 * The goal is to steer the blue triangle ship into the red diamond goal, using
   WASD or arrow keys to control the steering and throttle of the ship.
 * After successfully getting to the goal a few times, press the spacebar to
   have Falken take over and automatically steer the ship to the goal.
 * If Falken runs into trouble, you can press spacebar to take control, correct
   the problem, and then press spacebar again to return control to Falken.
   Falken will learn from these “corrections” which you should see in ~30
   seconds.
 * Press R to reset the board.
 * Press E to force the start of an evaluation session w/o waiting for the
   training to be completed.

Playing The Game (Android version)
 * The goal is to steer the blue triangle ship into the red diamond goal, using
   the arrow buttons to control the steering and throttle of the ship.
 * After successfully getting to the goal a few times, press A to
   have Falken take over and automatically steer the ship to the goal.
 * If Falken runs into trouble, you can press A to take control, correct
   the problem, and then press A again to return control to Falken.
   Falken will learn from these “corrections” which you should see in ~30
   seconds.
 * Press RESET to reset the board.
 * Press B to force the start of an evaluation session w/o waiting for the
   training to be completed.
