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
public class FirstPersonGame : MonoBehaviour
{
    [Tooltip("The player prefab to spawn at the start of the game.")]
    public FirstPersonPlayer playerPrefab;
    [Tooltip("The location within which to spawn the player.")]
    public PlayerSpawn startSpawn;
    [Tooltip("The final room in the level. Entering this room wins the game.")]
    public Room endRoom;

    private GameObject player;

    void Start() {
        ResetGame();
    }

    void LateUpdate() {
        if (player && endRoom && endRoom.Bounds.Contains(player.transform.position)) {
            Debug.Log("You win!");
            ResetGame();
        }
    }

    /// <summary>
    /// Restarts the game without reloading the level.
    /// </summary>
    private void ResetGame() {
        if (player) {
            GameObject.Destroy(player);
        }

        while (Enemy.Enemies.Count > 0) {
            GameObject.Destroy(Enemy.Enemies[0].gameObject);
        }

        for (int i = 0; i < EnemySpawn.EnemySpawns.Count; ++i) {
            EnemySpawn.EnemySpawns[i].Activate();
        }

        if (playerPrefab && startSpawn && endRoom) {
            player = GameObject.Instantiate(playerPrefab.gameObject,
                startSpawn.GetSpawnPoint(), startSpawn.transform.rotation);
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
        ResetGame();
    }
}
