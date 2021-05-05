# Falken

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

This repository provides:
- [A local service](service/) that collects experience, trains and serves
  models.
- [C++](sdk/cpp) and [Unity](sdk/unity) SDKs and to integrate into your game
  to train models.
- [C++](environments/cpp) and [Unity](environments/unity) environments that
  you can use to experiment with Falken.

**NOTE**: This is not an officially supported Google product.
