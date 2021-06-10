# NegaFalken Game Sample

The goal of this sample is to demonstrate what a Falken vs. Falken game
integration may look like.

You must be running the service, as described in the
[service instructions](../../../../../service/README.md)
before building and running the Unity demos.

## Prerequisites

- Use Unity 2018.4.17f1 or above.
- If you're using an older version of Unity make sure the project is configured
to use .NET 4.x or above.

## Set Up NegaFalken Game Sample

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
[Releases](https://github.com/google-research/falken/releases) page or
 [built](../../../../../sdk/unity/README.md).
1. Open `environments/unity/demos/Assets/NegaFalken/Scenes/NegaFalken.unity`.
1. Press the Play button

## Play the NegaFalken game

The goal of this game is to steer the blue player using arrow or WASD keys, and
shoot the yellow "NegaFalken" player using the space key while being mindful of
the blue player's HP (on the left side).

The yellow "NegaFalken" player will learn to play the game from your
demonstrations. You can also press `t` to let Falken also take over the blue
player, and see two Falken players play against each other.

If Falken is running into trouble playing the game, you can simply take over,
play correctly, then press the `t` key again for Falken to take over.
