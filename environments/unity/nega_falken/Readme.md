# Negafalken Demo

## Table of Contents

- [Negafalken Demo](#negafalken-demo)
  - [Table of Contents](#table-of-contents)
  - [About](#about)
  - [Run the demo](#run-the-demo)
  - [Add more players](#add-more-players)

## About
This shows the learning capabilities of the Falken SDK. The demo has two players
(red and blue arrow) inside an arena. The objective of the game is to win a match by defeating all
other players in the arena by shooting them with bullets. Once you kill the enemy, all players
will respawn and a new match will start.

At first, enemies will stay still and the experience from you playing the game will be used
to train a Falken brain. After a few of matches (between 3 and 5) Falken will start to control your
enemy. If you don't apply any actions to your player, Falken will also control it.

## Run the demo

- Open UnityHub click Add and select env_unity_negafalken folder.
- In Unity, press Run button.
- Move the player with W, A, S, D. Shoot your enemy using Space button.
- Once you kill your enemy, the game will restart. After about 3 matches, the Falken should start
  to control enemies.
- When Falken is controlling enemies, if you don't move your tank, Falken will take control.

## Add more players
It is possible to have multiple enemies in the same arena. To do that:
- Add a prefab player (look for it inside Prefab folder).
- Inside the player prefab, look for Falken Script:
  - Add a reference to the Arena (Grab the arena object and place it into the arena field inside
    Falken script).
  - If you want to control the player, Create a Joystick object and place it into the Joystick
    field.
  - In the bullet field place a bullet prefab (also inside Prefab folder).
  - Optionally, you can create a Health slider to watch player's life.
- In the Arena gameobject, you have a list of current players. Increase the number of players and
  set a reference to the player you created.

Note: You can add NegaFalkenPlayers and Players. The first one will feed the Falken brain while the other will be ignored.
