# Third Person Game Sample

The goal of this sample is to demonstrate what a Falken integration might look like in a game with a third person camera view.

You must be running the service, as described in the
[service instructions](../../../../../service/README.md)
before building and running the Unity demos.

## Prerequisites

- Use Unity 2018.4.17f1 or above.
- If you're using an older version of Unity make sure the project is configured
to use .NET 4.x or above.

## Set Up Third Person Game Sample

1. For the Unity demo to properly connect to the service, copy the
   `falken_config.json` generated from launching the service to the
   `environments/demos/Assets/StreamingAssets` directory.
   1. Windows:
   ```
   copy service\tools\falken_config.json environments\unity\demos\Assets\StreamingAssets\falken_config.json
   ```
   1. macOS:
   ```
   cp service/tools/falken_config.json environments/unity/demos/Assets/ StreamingAssets/falken_config.json
   ```
   1. Linux:
   ```
   cp service/tools/falken_config.json environments/unity/demos/Assets/ StreamingAssets/falken_config.json
   ```
1. Add the environments/demos/ directory as a project in Unity Hub.
1. Open the Unity project.
1. Go to the Menu, Assets --> Import Package --> Custom Package and import the
falken.unitypackage downloaded from the
[Releases](https://github.com/googleresearch/falken/releases) page or
[built](../../../../../sdk/unity/README.md).
1. Open `environments/unity/demos/Assets/ThirdPerson/Scenes/ThirdPerson.unity`.
1. Press the Play button

## Play the Third Person Game Sample

The goal of this game is to steer the blue player to the green goal using arrow
or WASD keys and the mouse for camera control.

Play the game for a few rounds, and press the
`t` key for Falken to take over.

If Falken is running into trouble playing the game, you can simply take over,
play correctly, then press the `t` key again for Falken to take over.
