// Copyright 2021 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

using System.Collections;
using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// <c>FirstPersonGame</c> A FirstPerson game where the goal is to make it to the final room in the level.
/// </summary>
public class FirstPersonGame : FalkenGame<FirstPersonBrainSpec>
{
    [Tooltip("The player prefab to spawn at the start of the game.")]
    public FirstPersonPlayer playerPrefab;
    [Tooltip("The level for this game to play.")]
    public Level level;
    [Tooltip("When true the game picks a single room and ends when you clear it.")]
    public bool singleRoomMode;

    private FirstPersonPlayer player;
    private Room currentRoom;
    private Falken.Episode episode;

    void Start() {
        Init();
        ResetGame(false);
    }

    void LateUpdate() {
        if (player && episode != null) {
            if (EpisodeCompleted) {
                ResetGame(false);
                Debug.Log("Episode hit max steps.");
            }
            else if (singleRoomMode) {
                if (currentRoom.Cleared) {
                    Debug.Log("Room cleared. You win!");
                    ResetGame(true);
                }
            }
            else if (player.CurrentRoom != currentRoom) {
                if (player.CurrentRoom == level.EndRoom) {
                    if (Enemy.Enemies.Count > 0)
                    {
                        Debug.Log("Reached end, but enemies remain. You lose!");
                        ResetGame(false);
                    } else
                    {
                        Debug.Log("Completed level. You win!");
                        ResetGame(true);
                    }
                } else {
                    Debug.Log("Completed room.");
                    currentRoom = player.CurrentRoom;
                }
            }
        }
    }

    void OnDestroy() {
        Shutdown();
    }

    protected override void ControlChanged() {
        if (player) {
            player.HumanControlled = humanControlled;
        }
    }

    /// <summary>
    /// Restarts the game without reloading the level.
    /// </summary>
    private void ResetGame(bool success) {
        if (episode != null) {
            episode.Complete(success ? Falken.Episode.CompletionState.Success :
                Falken.Episode.CompletionState.Failure);
        }

        if (player) {
            GameObject.Destroy(player.gameObject);
        }

        while (Enemy.Enemies.Count > 0) {
            GameObject.Destroy(Enemy.Enemies[0].gameObject);
        }

        for (int i = 0; i < EnemySpawn.EnemySpawns.Count; ++i) {
            EnemySpawn.EnemySpawns[i].Activate();
        }

        if (playerPrefab && level) {
            PlayerSpawn startSpawn = null;
            if (singleRoomMode) {
                while (startSpawn == null) {
                    startSpawn = level.RandomInteriorRoom.playerSpawn;
                }
            } else {
                startSpawn = level.StartRoom.playerSpawn;
            }

            player = GameObject.Instantiate(playerPrefab,
                startSpawn.GetSpawnPoint(), startSpawn.transform.rotation);

            episode = CreateEpisode();
            player.Episode = episode;
            player.BrainSpec = BrainSpec;
            player.HumanControlled = humanControlled;
            currentRoom = player.CurrentRoom;

            Health playerHealth = player.GetComponent<Health>();
            if (playerHealth) {
                playerHealth.OnKilled += PlayerKilled;
            }
        } else {
            Debug.LogWarning("LevelGame is misconfigured. Unable to start.");
        }
    }

    private void PlayerKilled(Health killed) {
        Debug.Log("You lose!");
        ResetGame(false);
    }
}
