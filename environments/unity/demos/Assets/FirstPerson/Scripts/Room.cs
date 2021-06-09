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
/// <c>Room</c> Represents a playabale space, including an entrance <c>Door</c> and one or more <c>Door</c> exits.
/// </summary>
[ExecuteInEditMode]
public class Room : MonoBehaviour
{
    [Tooltip("The door that leads into this room.")]
    public Door entrance;
    [Tooltip("The doors that lead out of this room.")]
    public Door[] exits;
    [Tooltip("The region within which to spawn a player in this room.")]
    public PlayerSpawn playerSpawn;

    [SerializeField] [HideInInspector]
    private Bounds bounds;

    private List<Enemy> enemies = new List<Enemy>();

    private static List<Room> rooms = new List<Room>();

    /// <summary>
    /// Returns a list of all active rooms in the scene.
    /// </summary>
    public static List<Room> Rooms { get { return rooms; } }

    /// <summary>
    /// Returns the Bounds of this room.
    /// </summary>
    public Bounds Bounds { get { return bounds; } }

    /// <summary>
    /// Returns true if there are no enemies in this room.
    /// </summary>
    public bool Cleared { get { return enemies.Count == 0; } }

    /// <summary>
    /// Returns the first valid exit (if one exists).
    /// </summary>
    public Door Exit { get { return exits.Length > 0 ? exits[0] : null; } }

    /// <summary>
    /// Returns a random, open exit door.
    /// </summary>
    public Door GetRandomExit() {
        List<Door> validExits = new List<Door>(exits.Length);
        for (int i = 0; i < exits.Length; ++i) {
            if (exits[i].open) {
                validExits.Add(exits[i]);
            }
        }
        return validExits.Count > 0 ? validExits[Random.Range(0, validExits.Count)] : null;
    }

    /// <summary>
    /// Adds an enemy to this room.
    /// </summary>
    public void AddEnemy(Enemy enemy) {
        enemies.Add(enemy);
    }

    /// <summary>
    /// Removes an enemy from this room.
    /// </summary>
    public void RemoveEnemy(Enemy enemy) {
        enemies.Remove(enemy);
    }

    void OnEnable() {
        rooms.Add(this);
        ComputeBounds();
    }

    void OnDisable() {
        rooms.Remove(this);
    }

#if UNITY_EDITOR
    void Update() {
        ComputeBounds();
    }

    /// <summary>
    /// Computes the world space bounding box for this room (based on child renderables).
    /// </summary>
    private void ComputeBounds() {
        bounds = new Bounds();
        bool boundsInit = false;
        foreach(Transform child in transform) {
            if (!child.GetComponent<Door>()) {
                MeshRenderer childRenderer = child.GetComponent<MeshRenderer>();
                if (childRenderer) {
                    if (boundsInit) {
                        bounds.Encapsulate(childRenderer.bounds);
                    } else {
                        bounds = childRenderer.bounds;
                        boundsInit = true;
                    }
                }
            }
        }
    }
#endif // UNITY_EDITOR
}
