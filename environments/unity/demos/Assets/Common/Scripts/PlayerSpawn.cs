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
/// <c>PlayerSpawn</c> Represents a region within which the player can spawn.
/// </summary>
public class PlayerSpawn : MonoBehaviour
{
    [Tooltip("The size of the spawn region in X.")]
    [Range(0, 10)]
    public float width = 1;
    [Tooltip("The size of the spawn region in Y.")]
    [Range(0, 10)]
    public float length = 1;

    /// <summary>
    /// Returns a random point within the defined spawn region.
    /// </summary>
    public Vector3 GetSpawnPoint() {
        float x = Random.Range(width * -0.5f, width * 0.5f);
        float z = Random.Range(length * -0.5f, length * 0.5f);
        return transform.TransformPoint(new Vector3(x, 0, z));
    }

    void OnDrawGizmos() {
        Gizmos.color = Color.blue;
        Gizmos.DrawWireCube(transform.position,
            transform.rotation * new Vector3(width, 0f, length));
    }
}
