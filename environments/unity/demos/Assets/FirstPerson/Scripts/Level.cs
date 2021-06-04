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
/// <c>Level</c> Procedurally generates a first person level.
/// </summary>
[ExecuteInEditMode]
public class Level : MonoBehaviour
{
    [Tooltip("Room prefab to use when creating the start of the level.")]
    public Room startPrefab;
    [Tooltip("Room prefab to use when creating the end of the level.")]
    public Room endPrefab;
    [Tooltip("List of room prefabs to use when creating the interior of the level.")]
    public Room[] interiorPrefabs;
    [Tooltip("The shortest number of rooms required to traverse the level.")]
    [Range(3, 100)]
    public int criticalPathLength = 3;
    [Tooltip("Optional cityscape to update on level generation.")]
    public Cityscape cityscape;

    [SerializeField]
    private List<Room> rooms = new List<Room>();

    /// <summary>
    /// Creates a random new level based on the above parameters.
    /// </summary>
    public void CreateLevel() {
        if (!startPrefab || !endPrefab || interiorPrefabs.Length == 0) {
            Debug.LogError("Cannot create a level without start, end, and interior.");
            return;
        }

        for (int i = 0; i < rooms.Count; ++i) {
            if (rooms[i]) {
                GameObject.DestroyImmediate(rooms[i].gameObject);
            }
        }
        rooms.Clear();

        Room currentRoom = TryAppendRoom(null, startPrefab);
        if (!currentRoom) {
            Debug.LogWarning("Unable to create start room. Aborting generation.");
            return;
        }
        int attempts = 0;
        while (rooms.Count < criticalPathLength - 1 && attempts < criticalPathLength * 10) {
            Room randomRoom = interiorPrefabs[Random.Range(0, interiorPrefabs.Length)];
            if (randomRoom.name != currentRoom.name) {
                Room newRoom = TryAppendRoom(currentRoom, randomRoom);
                if (newRoom) {
                    currentRoom = newRoom;
                }
            }
            ++attempts;
        }
        if (rooms.Count < criticalPathLength - 1) {
            Debug.LogWarning("Unable to place enough critical path rooms.");
        }
        currentRoom = TryAppendRoom(currentRoom, endPrefab);
        if (!currentRoom) {
            Debug.LogWarning("Unable to place end room.");
        }

        if (cityscape) {
            Vector3 center = Vector3.zero;
            foreach (Room room in rooms) {
                center += room.Bounds.center;
            }
            center /= rooms.Count;
            center.y = 0f;
            cityscape.transform.position = center;
            cityscape.CreateCityscape();
        }
    }

    /// <summary>
    /// Attempts to append a new room to the level.
    /// </summary>
    private Room TryAppendRoom(Room currentRoom, Room prefab) {
        Vector3 position = Vector3.zero;
        Quaternion rotation = Quaternion.identity;
        Door exit = null;
        if (currentRoom) {
            exit = currentRoom.GetRandomExit();
            if (exit == null) {
                Debug.LogWarning("No valid exits found for " + currentRoom.name);
                return null;
            }
            position = exit.transform.position;
            rotation = exit.transform.rotation;
        }
        Room newRoom = GameObject.Instantiate(prefab, position, rotation);
        for (int i = 0; i < Room.Rooms.Count; ++i) {
            Room room = Room.Rooms[i];
            if (room != newRoom && room != currentRoom && newRoom.Bounds.Intersects(room.Bounds)) {
                GameObject.DestroyImmediate(newRoom.gameObject);
                return null;
            }
        }
        newRoom.name = prefab.name;
        newRoom.transform.parent = transform;
        if (newRoom.entrance) {
            newRoom.entrance.from = currentRoom;
            newRoom.entrance.to = newRoom;
        }
        if (exit) {
            exit.from = currentRoom;
            exit.to = newRoom;
        }
        rooms.Add(newRoom);
        return newRoom;
    }
}
