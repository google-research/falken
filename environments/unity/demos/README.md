# Unity Demos

This directory contains Unity scenes to demonstrate the training flow for Falken.

You must be running the service, as described in the
[service instructions](../../../service/README.md)
before building and running the Unity demos.

## Prerequisites

- Use Unity 2018.4.17f1 or above.
- If you're using an older version of Unity make sure the project is configured
to use .NET 4.x or above.

## Set Up Unity Demos

1. For the Unity demo to properly connect to the service, copy the
   `falken_config.json` generated from launching the service to the
   `environments/demos/Assets/StreamingAssets` directory.
   1. Windows:
   ```
   copy service\tools\falken_config.json environments\unity\demos\Assets\StreamingAssets\falken_config.json
   ```
   1. macOS:
   ```
   cp service/tools/falken_config.json environments/unity/demos/Assets/StreamingAssets/falken_config.json
   ```
   1. Linux:
   ```
   cp service/tools/falken_config.json environments/unity/demos/Assets/StreamingAssets/falken_config.json
   ```
1. Add the environments/demos/ directory as a project in Unity Hub.
1. Open the Unity project.
1. Go to the Menu, Assets --> Import Package --> Custom Package and import the
falken.unitypackage downloaded from the
[Releases](https://github.com/google-research/falken/releases) page or
[built](../../../sdk/unity/README.md).
1. Open the scene file for the demo that you're interested in playing.
   Options for scenes to load are:

   - [environments/unity/demos/Assets/NegaFalken/Scenes/NegaFalken.unity](./Assets/NegaFalken/Scenes/)
   - [environments/unity/demos/Assets/HelloFalken/Scenes/HelloFalkenWithObstacles.unity](./Assets/HelloFalken/Scenes/)
   - [environments/unity/demos/Assets/HelloFalken/Scenes/HelloFalken.unity](./Assets/NegaFalken/Scenes/)
   - [environments/unity/demos/Assets/FirstPerson/Scenes/FirstPerson.unity](./Assets/FirstPerson/Scenes/)
   - [environments/unity/demos/Assets/ThirdPerson/Scenes/ThirdPerson.unity](./Assets/ThirdPerson/Scenes)
   - [environments/unity/demos/Assets/Cart/Scenes/Cart.unity](./Assets/Cart/Scenes/)

1. Press the Play button

## Overview of the Demos

All of these games require you to play the game for a few rounds, and press the
`t` key for Falken to take over.

If Falken is running into trouble playing the game, you can simply take over,
play correctly, then press the `t` key again for Falken to take over.

### Cart

The goal of this game is to drive the cart along the track using arrow or WASD
keys to control the cart.

### First Person

The goal of this game is to navigate the player various rooms using arrow or
WASD keys, aim using the mouse, and destroy all enemies using left mouse click.

### Hello Falken

The goal of this game is to steer the blue ship into the green goal using arrow
or WASD keys.

To play the game with obstacles, you can load the
`HelloFalkenWithObstacles.unity` scene.

### NegaFalken

The goal of this game is to steer the blue player using arrow or WASD keys, and
shoot the yellow "NegaFalken" player using the space key while being mindful of
the blue player's HP (on the left side).

The yellow "NegaFalken" player will learn to play the game from your
demonstrations. You can also press `t` to let Falken also take over the blue
player, and see two Falken players play against each other.

### Third Person

The goal of this game is to steer the blue player to the green goal using arrow
or WASD keys and the mouse for camera control.
