# Falken C++ SDK

The C++ SDK is one of the two supported Falken SDKs (C++, Unity).
Use the C++ SDK if you are integrating with a C++ game or a game built on a C++
game engine.

To use the SDK, you must be running the service, as described in the
[service instructions](../../service/README.md).

Download the C++ SDK on the
[Releases](https://github.com/google-research/falken/releases/) page, or if you
make changes, build it yourself by following the
[Build the C++ SDK instructions](#build-the-c-sdk).

## Build and Run the Hello Falken Sample

The fastest way to ensure that your setup is working properly is by building and
running the Hello Falken sample by following
[these instructions](../../environments/cpp/hello_falken/README.md).

## Integrate Falken

Once you verified your setup is working properly with Hello Falken, now it's
time to integrate the Falken SDK with your game.

Make sure you've familiarized yourself with
[Falken Concepts](../../README.md#concepts).

### Import the SDK

There are two options when importing the SDK: [manually](#import-manually) or by
using [cmake](#import-using-cmake).

#### Import Manually

1. Add falken_cpp_sdk/include to the include path
1. Add falken_cpp_sdk library to the linker command line:
  1. Windows:
  ```
  falken_sdk/libs/CONFIG/falken_cpp_sdk.dll
  falken_sdk/libs/CONFIG/falken_cpp_sdk.lib (import library)
  ```
  1. macOS:
  ```
  falken_sdk/libs/falken_cpp_sdk.dylib
  ```
  1. Linux:
  ```
  falken_sdk/libs/falken_cpp_sdk.so
  ```

##### Import into Visual Studio project

1. Add `falken_cpp_sdk/include` to the include path;
[example here](https://docs.microsoft.com/en-us/cpp/build/walkthrough-creating-and-using-a-dynamic-link-library-cpp?view=msvc-160&viewFallbackFrom=vs-2019#to-add-the-dll-header-to-your-include-path).
1. Add DLL import library `falken_sdk/libs/CONFIG/falken_cpp_sdk.lib`;
[example here](https://docs.microsoft.com/en-us/cpp/build/walkthrough-creating-and-using-a-dynamic-link-library-cpp?view=msvc-160#to-add-the-dll-import-library-to-your-project).
1. Copy the DLL `falken_sdk/libs/CONFIG/falken_cpp_sdk.dll` to the
executable directory;
[example here](https://docs.microsoft.com/en-us/cpp/build/walkthrough-creating-and-using-a-dynamic-link-library-cpp?view=msvc-160&viewFallbackFrom=vs-2019#to-copy-the-dll-in-a-post-build-event).

##### Import into Xcode project

1. Add `falken_cpp_sdk/include` to the include path;
[example here](https://stackoverflow.com/questions/14134064/how-to-set-include-path-in-xcode-project).
1. Add `falken_sdk/libs/falken_cpp_sdk.dylib` to the link step;
[example here](https://stackoverflow.com/questions/445815/linking-libraries-in-xcode).

#### Import Using cmake

1. Add the falken_sdk directory to `CMAKE_MODULE_PATH` then find the package using:
  ```
  find_package(falken REQUIRED)
  ```
1. Link the falken library using:
  ```
  target_link_libraries(YOUR_TARGET falken_cpp_sdk)
  ```

### Initialize Falken

For the SDK to properly specify the project ID, API key, and the certificate to
connect to the service, the easiest way is to simply copy the
`falken_config.json` that the service launcher generated into the directory
where your game binary is located and call:

```
std::shared_ptr<falken::Service> service = falken::Service::Connect(
  nullptr, nullptr, nullptr);
```

You can also specify a raw JSON string containing the information from
`falken_config.json` in the third argument of `Connect`:

```
std::shared_ptr<falken::Service> service = falken::Service::Connect(
  nullptr, nullptr, kJsonConfig);
```

*Make sure to retain this pointer to the service. If the returned shared_ptr is
deallocated or assigned to null, the Falken service will shutdown and
destroy all active Sessions, Brains, etc.*

### Define Actions

Create a class that derives from falken::ActionBase. Members can be of type
NumberAttribute, CategoryAttribute or JoystickAttribute.

```
struct MyActions : public falken::ActionsBase {
    MyActions()
        : FALKEN_NUMBER(throttle, -1.0f, 1.0f),
          FALKEN_JOYSTICK_DELTA_PITCH_YAW(joystick,
                                          falken::kControlledEntityPlayer) {}

    falken::NumberAttribute<float> throttle;
    falken::JoystickAttribute joystick;
};
```

Joystick attributes represent a 2-axis input device that either controls pitch
and yaw or indicates a desired direction in the XZ plane of the controlled
object. When joystick actions are present, entity position and rotation
observations (see next section) are preprocessed to optimize agent learning.
It is therefore important to correctly configure these action types to obtain
good performance. Below are a few examples of common control schemes modeled
as Joystick actions. Note that if any Joystick action references a camera,
a camera entity needs to be provided as part of the observation;
see [next section](#third-person-camera-relative-controls-eg-dark-souls-mario64-etc).

#### Third Person Camera-relative controls (e.g., Dark Souls, Mario64 etc.)

```
// Tomb-raider style controls: left stick controls movement, right stick camera.
struct ThirdPersonAvatarControls : public falken::ActionsBase {
  ThirdPersonAvatarControls()
      : FALKEN_JOYSTICK_DIRECTION_XZ( // Controls player movement in XZ plane.
            move,
            falken::kControlledEntityPlayer,  // Controls player-XZ movement.
            falken::kControlFrameCamera),     // Input is relative to the camera.
        FALKEN_JOYSTICK_DELTA_PITCH_YAW( // Controls camera pitch and yaw.
            aim,
            falken::kControlledEntityCamera) // Input controls the camera.
   {}


  falken::JoystickAttribute move;
  falken::JoystickAttribute aim;
};
```

#### Twin Stick Controls (e.g., Geometry Wars)

```
struct TwinStickControls : public falken::ActionsBase {
  TwinStickControls()
      : FALKEN_JOYSTICK_DIRECTION_XZ( // Controls player movement in XZ plane.
            move,
            falken::kControlledEntityPlayer, // Controls player-XZ movement.
            falken::kControlFrameWorld),     // Input is world-relative.
        FALKEN_JOYSTICK_DIRECTION_XZ( // Controls XZ aim direction.
            aim,
            falken::kControlledEntityPlayer, // Controls player-XZ aim.
            falken::kControlFrameWorld)      // Input is world-relative.
  {}

  falken::JoystickAttribute move;
  falken::JoystickAttribute aim;
};
```

#### First-Person Shooter Controls (e.g., Quake)

```
struct FPSControls : public falken::ActionsBase {
  FPSControls()
      : FALKEN_JOYSTICK_DIRECTION_XZ( // Controls player-XZ movement.
            move,
            falken::kControlledEntityPlayer, // Controls player-XZ movement.
            falken::kControlFramePlayer),    // Input is relative to the player.
        FALKEN_JOYSTICK_DELTA_PITCH_YAW(
            aim,
            falken::kControlledEntityCamera) // Aims the first-person camera.
  {}

  falken::JoystickAttribute move;
  falken::JoystickAttribute aim;
};
```
### Define Observations

Create a struct that derives from falken::ObservationBase. You can add members
of type NumberAttribute, CategoryAttribute, and FeelersAttribute and they will
be treated as part of the default Player entity. ObservationBase has fields for
position and rotation, which indicate the position and rotation of the player.
Falken expects a left-handed coordinate system in which the y axis points up,
the x-axis points towards the right, and the z-axis is aligned with the forward
direction of entities.

```
struct MyObservations : public falken::ObservationsBase {
    MyObservations()
      : FALKEN_NUMBER(my_float, -1.0f, 1.0f) {}

    falken::NumberAttribute<float> my_float;
};
```

You can also define new types of Entity (like Enemy or Goal) by creating classes
that derive from falken::EntityBase. Note that entities have default attributes
for position and rotation.

```
struct Enemy : public falken::EntityBase {
    Enemy(falken::EntityContainer& container, const char* name)
      : falken::EntityBase(container, name),
        FALKEN_NUMBER(my_float, -1.0f, 1.0f) {}

    falken::NumberAttribute<float> my_float;
};
```

And add instances of them as attributes for your observations.

```
struct MyObservations : public falken::ObservationsBase {
    MyObservations()
      : FALKEN_NUMBER(my_float, -1.0f, 1.0f),
        FALKEN_ENTITY(my_enemy) {}

    falken::NumberAttribute<float> my_float;
    Enemy my_enemy;
};
```

Note that if you used Joystick actions that reference a camera, either by
defining a Joystick action that controls the camera or by using a camera
reference frame, you will need to add an entity named camera to your
observations, so Falken can know about the position and orientation of the
camera as well as the player (note that position and rotation of the player are
set using the position and orientation members of ObservationsBase):

```
struct MyObservations : public falken::ObservationsBase {
    MyObservations()
      : FALKEN_NUMBER(unrelated_observation, -1.0f, 1.0f),
        FALKEN_ENTITY(camera) {}

    falken::NumberAttribute<float> unrelated_observation;
    falken::EntityBase camera;
};
```
### Create a Brain

Define a BrainSpec type that binds your Actions and Observations.

```
using MyBrainSpec = falken::BrainSpec<MyObservations, MyActions>;
```

Call Falken to create an instance of the Brain.

```
std::unique_ptr<falken::Brain<MyBrainSpec>> brain =
    service->CreateBrain<BrainSpec>("MyBrain");
```
*Make sure to retain this pointer to the brain. If the returned unique_ptr is
deallocated or assigned to null, the Brain will be unloaded.*

### Start a Session. Start an Episode.

Start a new Session using the Brain instance you created above and then use the
Session to start your first Episode.

```
std::unique_ptr<falken::Session> session =
    brain->StartSession(falken::Session::kTypeInteractiveTraining, kMaxSteps);

std::unique_ptr<falken::Episode> episode = session->StartEpisode();
```

### Step the Episode

```
auto& brain_spec = brain->brain_spec();
// Set attributes in brain_spec.observations from game state.
if (human_control) {
  // Set attributes in brain_spec.actions.
}

episode->Step();

if (episode->completed()) {
  episode = nullptr;
  // Reset your game as we've hit the maximum number of steps.
} else if (!human_control) {
  // Apply brain_spec.actions to your game.
}
```

### End the Episode. Reset the Game.
```
episode->Complete(falken::Episode::kCompletionStateSuccess);
// Game specific reset logic.
```

### Ending one Session.

```
session->Stop();
```

## Build the C++ SDK

1. Make a new subdirectory called build in the sdk/cpp directory and go into
that directory:
   ```
   cd sdk/cpp
   mkdir build
   cd build
   ```
1. Configure cmake:
   1. Windows
   ```
   cmake -A x64 ..
   ```
   1. macOS:
   ```
   cmake -GXcode ..
   ```
   1. Linux:
   ```
   cmake ..
   ```
1. Build the SDK:
   *Note* the number of parallel build tasks `4` is required on macOS when
   building with Xcode other platforms this can be omitted.

   This can be changed to a number that matches the number of CPUs in your
   system to speed up builds.
   1. Windows
   ```
   cmake --build . --config Release -j
   ```
   1. macOS
   ```
   cmake --build . --config Release -j
   ```
   1. Linux
   ```
   cmake --build . -j
   ```
 1. Package the SDK

   Package the SDK to generate a zip file that contains build artifacts to use
   in your projects.
   1. Windows
   ```
   cpack -G ZIP -C Release
   ```
   1. macOS (Xcode)
   ```
   cpack -G ZIP -C Release
   ```
   1. Linux
   ```
   cpack -G ZIP
   ```

Build artifacts are stored under `build/lib` (Linux / macOS) and `build/bin`
(Windows DLL)

On macOS and Windows it's also possible to open the generated Xcode or Visual
Studio project and build from the IDE by selecting the falken_cpp_sdk build
target.
