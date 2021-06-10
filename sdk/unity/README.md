# Falken Unity SDK

The Unity SDK is one of the two supported Falken SDKs (C++, Unity).
Use the Unity SDK if you are integrating with a game built on Unity.

To use the SDK, you must be running the service, as described in the
[service instructions](../../service/README.md).

Download the Unity SDK on the
[Releases](https://github.com/google-research/falken/releases/) page,
or if you make changes, build it yourself by following the
[Build the Unity SDK instructions](#build-the-unity-sdk).

## Build and Run a Unity Sample

The fastest way to ensure that your setup is working properly is by
building and running one of the Unity samples by following
[these instructions](../../environments/unity/demos/README.md).

## Integrate Falken

Once you verified your setup is working properly with a sample, now it's
time to integrate the Falken SDK with your game.

Make sure you've familiarized yourself with [Falken Concepts](../../README.md#concepts).

### Import the SDK

Simply import falken.unitypackage into your game project.

### Initialize Falken

For the SDK to properly specify the project ID, API key, and the certificate to
connect to the service, the easiest way is to simply copy the
`falken_config.json` that the service launcher generated into the
Assets/StreamingAssets directory of your game and call:

```
Falken.Service.Connect();
```

Alternatively, you can also specify a raw JSON string containing the information
from `falken_config.json` in the third argument of `Connect`:

```
Falken.Service.Connect(null, null, JsonConfigString);
```

### Define Actions

Create a class that derives from ActionBase. Members can be of type float or int
(continuous), bool or enum (discrete) or of type Joystick.

```
public class MyActions : Falken.ActionBase
{
    public Falken.Number throttle = new Falken.Number(-1f, 1f);

    public Falken.Joystick steering = new Falken.Joystick(
        "steering", Falken.AxesMode.DeltaPitchYaw,
        Falken.ControlledEntity.Player);
}
```
Joystick attributes represent a 2-axis input device that either controls pitch
and yaw or indicates a desired direction in the XZ plane of the controlled
object.

When joystick actions are present, entity position and rotation observations
(see next section) are preprocessed to optimize agent learning.
It is therefore important to correctly configure these action types to obtain
good performance.

Below are a few examples of common control schemes modeled as Joystick actions.
Note that if any Joystick action references a camera, a camera entity needs to
be provided as part of the observation (see next section).

#### Third Person Camera-relative controls (e.g., Dark Souls, Mario64 etc.)

```
public class ThirdPersonAvatarControls : Falken.ActionsBase
{
    public Falken.Joystick move = new Falken.Joystick(
        "move",
        Falken.AxesMode.DirectionXZ,
        Falken.ControlledEntity.Player, // Movement on the player XZ plane.
        Falken.ControlFrame.Camera);  // Relative to the camera orientation.

    public Falken.Joystick aim = new Falken.Joystick(
        "aim",
        Falken.AxesMode.DeltaPitchYaw, // Pitch and yaw the camera.
        Falken.ControlledEntity.Camera); // Input moves the camera.
}
```

#### Twin Stick Controls (e.g., Geometry Wars)

```
public class TwinStickControls : Falken.ActionsBase
{
    public Falken.Joystick move = new Falken.Joystick(
        "move",
        Falken.AxesMode.DirectionXZ,
        Falken.ControlledEntity.Player, // Movement on the player XZ plane.
        Falken.ControlFrame.World); // Input is a world-space XZ direction.

    public Falken.Joystick aim = new Falken.Joystick(
        "aim",
        Falken.AxesMode.DirectionXZ,
        Falken.ControlledEntity.Player, // Aiming on the player XZ plane.
        Falken.ControlFrame.World); // Input is a world-space XZ direction.
}
```

#### First-Person Shooter Controls (e.g., Quake)

```
public class FPSControls : Falken.ActionsBase
{
    public Falken.Joystick move = new Falken.Joystick(
        "move",
        Falken.AxesMode.DirectionXZ,
        Falken.ControlledEntity.Player, // Movement on the player XZ plane.
        Falken.ControlFrame.Player);  // Input is relative to the player.

    public Falken.Joystick aim = new Falken.Joystick(
        "aim",
        Falken.AxesMode.DeltaPitchYaw, // Aims the first person camera.
        Falken.ControlledEntity.Camera); // Input moves the camera.
}
```

*Don’t forget to make your fields public and add the [Serializable]
class attribute! Falken uses reflection to automatically transform your
classes into types our backend understands.*

### Define Observations

Create a class that derives from EntityBase.
This will be used to define the attributes of the player.

```
public class MyPlayer : Falken.EntityBase
{
    public Falken.Number my_float = new Falken.Number(-1f, 1f);
}
```

Create a class that derives from ObservationBase and configure it to use your
new EntityBase subclass.

```
public class MyObservations : Falken.ObservationBase
{
    public MyObservations() {
        player = new MyPlayer();
    }
}
```

You can also define other types of Entity (like Enemy or Goal) and add them
to your Observations.

```
public class Enemy : Falken.EntityBase
{
    public Falken.Number my_float = new Falken.Number(-1f, 1f);
}

public class MyObservations : Falken.ObservationBase
{
    public MyObservations() {
        player = new MyPlayer();
    }
    public Enemy my_enemy;
}
```

*Don’t forget to make your fields public!
Falken uses reflection to automatically transform your classes into types our
backend understands.*

Note that if you used Joystick actions that reference a camera,
either by defining a Joystick action that controls the camera or by using a
camera reference frame, you will need to add an entity named *camera* to
your observations, so Falken can know about the position and orientation of
the camera:

```
public class CameraObservations : Falken.ObservationBase
{
    public CameraObservations() {
        player = new MyPlayer();
        camera = new Falken.EntityBase();
    }
    public Falken.EntityBase camera;
}
```

### Create a Brain

Call Falken to create an instance of the Brain, passing in an instance of
your Observation and Action classes.

```
MyObservations observations = new MyObservations();
MyActions actions = new MyActions();
Falken.Brain brain = Falken.Service.CreateBrain(
    "MyBrain", observations, actions);
```

### Start a Session. Start an Episode.

First, start a new Session and then use the Session to start your first
Episode.

```
Falken.Service.ActiveSession session = Falken.Service.StartSession(
    brain.BrainId,
    Falken.SessionType.InteractiveTraining, maxSteps);

session.CreateEpisode();
```

### Step the Episode

```
// Set attributes in MyObservations instance from game state.
if (humanControlled)
{
    // Set attributes in MyActions instance from human player.
}

Falken.ActionData actionData = session.StepEpisode(
                observations,
                reward,
                humanControlled ? null : actions);

if (humanControlled && actionData != null)
{
    actions.FromActionData(actionData);
    // Apply actions to your game.
}
```

### End the Episode. Reset the Game.

```
session.FinishEpisode(Falken.EpisodeState.Success);
// Game specific reset logic.
```

### Ending one Session. Starting a new Session.

```
session.Stop()
```

## Build the Unity SDK

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
   1. MacOS:
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
   cmake --build . --config Release -j 4
   ```
   1. Linux
   ```
   cmake --build . -j
   ```
   The SDK is built to `falken_unity_build/bin`.
