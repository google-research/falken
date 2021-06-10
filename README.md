# Falken

![Main branch](https://github.com/google-research/falken/actions/workflows/build_on_push.yaml/badge.svg)
![Latest release](https://github.com/google-research/falken/actions/workflows/build_release.yaml/badge.svg)

**NOTE**: This is not an officially supported Google product.

Falken provides developers with a service that allows them to train AI that can
play their games. Unlike traditional RL frameworks that learn through rewards
or batches of offline training, Falken is based on training AI via realtime,
human interactions.

Because human time is precious, the system is designed to seamlessly transition
between humans playing the game (training) and the AI playing the game
(inference). This allows us to support a variety of training styles, from
providing a large batch of demonstrations up front to providing “just in time”
demonstrations when the AI encounters a state it does not know how to handle.

Behind the scenes, Falken automatically handles logging of experience,
separates out human demonstrations, trains new models, serves the best models
for on-device inference, and maintains a version history.

## Components

This project consists of:

 * [A local service](service/README.md) that collects experience, trains and
   serves models.
 * A [C++](sdk/cpp/README.md) SDK that can be integrated into C++ games to use
   the service and an example environment,
   [Hello Falken](environments/cpp/hello_falken/README.md) that demonstrates
   use of the C++ SDK.
 * A [Unity](sdk/unity/README.md) SDK that can be integrated into Unity games to
   use the service and
   [example environments](environments/unity/demos/README.md) with
   [Hello Falken](environments/unity/demos/Assets/HelloFalken) being the most
   simple to get started.
 * A [simple web dashboard](dashboard/README.md) that connects to the service to
   provides a way to visualize traces from sessions for debugging purposes.

## Getting started

The fastest way to ensure that everything is working properly is to
launch a local service then build and run Hello Falken environment.

In C++:
 * [Launch the service](service/README.md#launch-the-service)
 * [Build and run the environment](environments/cpp/hello_falken/README.md)

In Unity:
 * [Launch the service](service/README.md#launch-the-service)
 * [Configure and run the environment](environments/unity/demos/Assets/HelloFalken/README.md)

## Concepts

### Stand up and Initialize Falken

The first step in using Falken is to
[launch the service](service/README.md#launch-the-service) and connect to the
service from the client SDK (e.g C++ or Unity) using your JSON configuration.
All subsequent API calls from the client will automatically use this
information.

### Define Actions
Actions allow you to define how Falken’s AI interacts with your game and how it
learns from humans who play it. In Falken, Actions can be either continuous or
discrete.

 * **Continuous Actions** are used to represent analog controls like a joystick
   that controls aiming or an analog trigger that controls the gas pedal in a
   car. All continuous actions are required to include a developer defined min
   and max value.
 * **Discrete Actions** can be used to represent simple buttons (like whether
  the fire button is pressed) or discrete selections (like which weapon to
  equip). We generally recommend developers create Actions which represent
  logical interactions (jump, shoot, move, etc) rather than physical inputs (A
  button, left stick). As such, you may have more Actions in Falken than there
  are physical inputs for your game.

### Define Observations

Observations allow you to define how Falken’s AI perceives your game both while
it is playing and while it is “watching” a human play. Falken’s Observations are
based on the Entity/Attribute model, where an Entity is simply a container for
attributes, each of which have a corresponding name, type, and value.

 * **Position:** All Entities include an optional, pre-defined 3D position
   attribute (vector). If used, this position should generally be in world
   space.
 * **Rotation:** All Entities include an optional, pre-defined 3D rotation
   attribute (quaternion). If used, this rotation should generally be in world
   space.
 * **Number:** Number attributes represent quantities in the world that can be
   counted, either as whole numbers (ints) or real numbers (floats). All Number
   attributes are required to have a developer-defined minimum and maximum
   value.
 * **Category:** Categorical attributes represent values with discrete states,
   like a simple bool or the entries in an enum.
 * **Feelers:** Feelers represent a set of evenly spaced samples reaching out
   from an entity. They are commonly used to sense the 3D environment around an
   entity (usually the player).

Defining the best Observations for your game can be tricky and can impact
Falken's performance, so we recommend starting with the bare minimum a human
would require to play a game and slowly refining the set of Observations to
improve efficacy. In practice we've found that simple observations can yield
much better performance.

### Create a Brain

In Falken, a Brain represents the idea of the thing that observes, learns, and
acts. It’s also helpful to think about each Brain as being designed to
accomplish a specific kind of task, like completing a lap in a racing game or
defeating enemies while moving through a level in an FPS.

When creating a Brain, you provide a specific set of Actions and a specific set
of Observations that define how the brain perceives the world and what actions
it can take.

### Start a Session. Start an Episode.

In Falken, a Session represents a period of time during which Falken was
learning how to play your game, playing your game, or both. Sessions are
composed of one or more Episodes, which represent a sequence of interactions
with a clear beginning, middle, and end (like starting a race, driving around
the track, and crossing the finish line).

Falken supports a number of different Session types, including:

 * **Interactive Training:** In this mode, Falken learns by watching a human
   play the game. Players can teach Falken by playing entire Episodes from
   beginning to end or they can let Falken play and only take over to suggest
   a correction in behavior whenever Falken makes a mistake.
 * **Evaluation:** In this mode, Falken plays the game autonomously in order to
   determine the best model that can be produced for your game given the data
   provided in earlier Interactive Training mode.
 * **Inference:** In this mode, Falken simply plays your game as much as you
   like and intentionally disables all learning features. This guarantees that
   you get consistent results, and is ideal for testing your game at scale.

All Sessions also require you to define a maximum number of Steps per Episode.
You’ll want to set this number to be a comfortable amount more than one a human
would require. For example, if you call `Episode::Step()` every frame, your game
runs at 30fps, and a human would take 300 seconds to complete an episode, then
you should set a max steps to about 9000 or 12000 to ensure the AI has enough
time to complete the task. If the number of steps is too high then Falken will
take longer to detect when an agent is stuck when using an evaluation session.

### Step the Episode

Every time you want Falken to learn from a human or interact with your game,
you need to need to call Step(). Step() always operates on a set of
Observations from your game. If a human is playing, then you also provide the
Actions that the human performed, and Falken will learn from them. If you want
Falken to play your game, don’t pass in any Actions to Step() but instead use
the Actions returned by Step() and apply them to your game as if a human had
performed them.

For most games, you’ll call Falken’s Step() every time you update your game
simulation. However, some games might want to call Step() less often, like when
the player takes a turn or performs an important action.

### End the Episode. Reset the Game.

Episodes in Falken end when the player succeeds, fails, or the maximum number
of steps has been exceeded. You provide this context when you end the Episode.

 * **Success:** The player (human or AI) has successfully accomplished the goal
   (e.g. completed a lap or finished the level).
 * **Failure:** The player (human or AI) failed to accomplish the goal
   (e.g. car crashed or player was killed by an enemy).
 * **Gave Up:** The episode reached its max steps without succeeding or failing.
 * **Aborted:** The episode was unexpectedly terminated in the middle.

Most Sessions involve many Episodes (either for training Falken or testing your
game), so when an Episode completes, you’ll need to reset your game state before
you bring the next Episode. Falken leaves the definition of this reset up to you
and does not require that every Episode in a Session start with identical state.
In general, you want each episode to start with similar but not identical state
(similar to what many games do for human players) as this helps Falken most
effectively learn from and test your game.

### Ending one Session. Starting a new Session.

Once you are done with a Session, you simply Stop it. If an Episode is still
active when a Session is stopped, the Episode will be Aborted.

When you Stop a learning-type session (InteractiveTraining or Evaluation), the
Brain makes a record of what it has learned and *"gets smarter"*. Additional
Sessions created with this brain will start from this more intelligent state and
use that as the basis for additional learning or playing.


