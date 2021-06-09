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
    [Tooltip("The location within which to spawn the player.")]
    public PlayerSpawn startSpawn;
    [Tooltip("The final room in the level. Entering this room wins the game.")]
    public Room endRoom;

    private FirstPersonPlayer player;
    private Room currentRoom;
    private Falken.Episode episode;

    void Start() {
        Init();
        ResetGame(false);
    }

    void LateUpdate() {
        if (player && episode != null) {
            if (episode.Completed) {
                Debug.Log("Episode hit max steps.");
                episode = CreateEpisode();
                player.Episode = episode;
            }
            else if (player.CurrentRoom != currentRoom) {
                if (player.CurrentRoom == endRoom) {
                    Debug.Log("Completed level. You win!");
                    ResetGame(true);
                } else {
                    Debug.Log("Completed room.");
                    episode.Complete(Falken.Episode.CompletionState.Success);
                    episode = CreateEpisode();
                    player.Episode = episode;
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

        if (playerPrefab && startSpawn && endRoom) {
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
