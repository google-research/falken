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

using UnityEngine;

public class Arena : MonoBehaviour
{
    public GameObject groundPlane;
    public Player[] players;
    public GameObject[] obstacles;

    public bool enableObstacles = true;
    public KeyCode toggleObstaclesKey = KeyCode.Return;

    #region Getters and Setters
    /// <summary>
    /// Size of the playable arena.
    /// </summary>
    public float BoardSize
    {
        get
        {
            return groundPlane.transform.localScale.x / 0.1f;
        }

        set
        {
            groundPlane.transform.localScale = new Vector3(
                value * 0.1f,
                groundPlane.transform.localScale.y,
                value * 0.1f);
        }
    }

    /// <summary>
    /// Limits of the current arena.
    /// </summary>
    public Bounds Bounds
    {
        get
        {
            return groundPlane.GetComponent<Renderer>().bounds;
        }
    }

    /// <summary>
    /// Width of the biggest obstacle in the arena.
    /// </summary>
    public float BiggestObstacleWidth
    {
        get
        {
            float width = float.MinValue;
            foreach (GameObject obj in obstacles)
            {
                width = Mathf.Max(width, obj.GetComponent<Collider>().bounds.size.y);
            }
            return width;
        }
    }

    /// <summary>
    /// Returns True if there is more than one player in the current arena.
    /// </summary>
    public bool EnemiesAlive
    {
        get
        {
            int playersAlive = 0;
            foreach (var p in players)
            {
                if (p.Alive)
                {
                    playersAlive++;
                    if (playersAlive > 1)
                    {
                        return true;
                    }
                }
            }
            return false;
        }
    }

    /// <summary>
    /// Returns true if all the players have finished its episodes.
    /// </summary>
    public bool GameReadyToStart
    {
        get
        {
            foreach (FalkenPlayer p in players)
            {
                if (p.EpisodeStarted)
                {
                    return false;
                }
            }
            return true;
        }
    }

    #endregion

    #region Unity Callbacks
    public virtual void Update()
    {
        if (Input.GetKeyDown(toggleObstaclesKey))
        {
            enableObstacles = !enableObstacles;
        }
    }

    public virtual void FixedUpdate()
    {
        foreach (GameObject o in obstacles)
        {
            if (o != null)
            {
                o.SetActive(enableObstacles);
            }
        }

    }
    #endregion

    #region Helper Objects
    /// <summary>
    /// Gets the position of the closest enemy related to player enemy.
    /// </summary>
    /// <param name="player"> Reference to player </param>
    /// <returns> Position of the enemy </returns>
    public Player GetClosestEnemy(Player player)
    {
        var playerPosition = player.transform.position;
        float closestDistance = float.MaxValue;
        var closestEnemy = player;

        foreach (var enemy in players)
        {
            var renderer = enemy.GetComponentInChildren<MeshRenderer>();
            if (!Object.ReferenceEquals(player, enemy) && renderer.enabled)
            {
                var currentEnemyDistance =
                    Vector3.Distance(playerPosition, enemy.transform.position);
                if (closestDistance > currentEnemyDistance)
                {
                    closestEnemy = enemy;
                    closestDistance = currentEnemyDistance;
                }
            }
        }
        return closestEnemy;
    }

    /// <summary>
    /// Starts episodes on each of the FalkenPlayers.
    /// </summary>
    public void StartGame()
    {
        foreach (var gamePlayer in players)
        {
            if (gamePlayer is FalkenPlayer falkenPlayer)
            {
                falkenPlayer.StartEpisode();
            }
        }
    }

    /// <summary>
    /// Generate a random position to spawn a player.
    /// </summary>
    /// <param name="angle">Orientation of the object.</param>
    /// <param name="extents">Area taken up by the object.</param>
    /// <returns></returns>
    public Vector3 GenerateRandomGroundPos(MonoBehaviour monoObject, float angle)
    {
        // Get the bounds of the arena.
        Bounds groundBounds = Bounds;
        // Extents of the object.
        Vector3 extents = monoObject.GetComponent<Collider>().bounds.extents;
        // Get the width of the walls in the arena.
        Quaternion boxOrientation = Quaternion.AngleAxis(angle, Vector3.up);

        var boundsArenaSize = groundBounds.size.magnitude;
        var boundsMonoObjectSize = monoObject.GetComponent<Collider>().bounds.size.magnitude;

        // Check if object fits inside arena.
        if (boundsArenaSize < boundsMonoObjectSize)
        {
            throw new System.InvalidOperationException(
                "Cannot generate position. The object is bigger than the arena");
        }

        Vector3 position;
        do
        {
            position = new Vector3(UnityEngine.Random.Range(groundBounds.min.x,
                                                            groundBounds.max.x),
                                   monoObject.transform.position.y,
                                   UnityEngine.Random.Range(groundBounds.min.z,
                                                            groundBounds.max.z));
        } while (Physics.OverlapBox(position, extents, boxOrientation).Length > 0);
        return position;
    }
    #endregion
}
