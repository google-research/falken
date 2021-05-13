# Falken C# SDK

Falken provides developers with a service that allows them to train AI that can
play and test their games. Unlike traditional RL frameworks that learn through
rewards or batches of offline training, Falken is based on training AI via
realtime, human interactions.

Because human time is precious, the system is designed to seamlessly transition
between humans playing the game (training) and the AI playing the game
(inference). This allows us to support a variety of training styles, from
providing a large batch of demonstrations up front to providing “just in time”
demonstrations when the AI encounters a state it does not know how to handle.

Behind the scenes, Falken automatically handles logging of experience, separates
out human demonstrations, trains new models (including hyper parameter search),
serves the best models for on-device inference, and maintains a version history.
