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
/// <c>EnemySpawn</c> Handles spawning enemies, including support for easy resets.
/// </summary>
public class EnemySpawn : MonoBehaviour
{
    [Tooltip("The enemy prefab to spawn at this location.")]
    public Enemy enemyPrefab;
    [Tooltip("The probability of spawning an enemy from this location.")]
    [Range(0, 1)]
    public float spawnProbability = 1f;
    [Tooltip("Activate when GameObject is created. Primarily for testing.")]
    public bool autoActivate;

    private GameObject enemy;
    private static List<EnemySpawn> enemySpawns = new List<EnemySpawn>();

    /// <summary>
    /// Returns a list of all enabled EnemySpawns in the world.
    /// </summary>
    public static List<EnemySpawn> EnemySpawns { get { return enemySpawns; } }

    /// <summary>
    /// Attempts to spawn a new Enemy. Will also cleanup previously created enemies.
    /// </summary>
    public void Activate() {
        if (enemy) {
            GameObject.Destroy(enemy);
        }
        if (Random.value <= spawnProbability) {
            enemy = GameObject.Instantiate(enemyPrefab.gameObject, transform.position,
                transform.rotation);
        }
    }

    void OnEnable() {
        enemySpawns.Add(this);
    }

    void OnDisable() {
        enemySpawns.Remove(this);
    }

    void Start() {
        if (autoActivate) {
            Activate();
        }
    }

    void OnDrawGizmos() {
        if (enemyPrefab) {
            Gizmos.color = Color.red;
            Gizmos.DrawWireMesh(enemyPrefab.GetComponent<MeshFilter>().sharedMesh,
                transform.position, transform.rotation, enemyPrefab.transform.localScale);
        }
    }
}
