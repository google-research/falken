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

﻿using UnityEngine;
using System.Collections;

public delegate void NotifyGoalReached();

/// ThirdPersonFalkenGame class is required as a workaround given that Unity cannot
/// serialize an attribute with a generic class type.
[System.Serializable]
public class ThirdPersonFalkenGame : FalkenGame<ThirdPersonBrainSpec>
{
}

/// <summary>
/// <c>GameLogic</c> Manages the lifecycle of the ThirdPerson demo.
/// </summary>
public class GameLogic : MonoBehaviour
{
    [Tooltip("Reference to the player in this game instance.")]
    public ThirdPersonController player;
    [Tooltip("Reference to the goal object the player needs to move towards.")]
    public GameObject goal;
    [Tooltip("Defines the size of the spawn region for player and goal.")]
    public float boardSize = 20f;

    [Tooltip("Falken settings.")]
    public ThirdPersonFalkenGame _falkenGame;

    private float _goalTolerance = 1f;
    private float _startHeight = 0f;

    private Falken.Episode _episode;

    void Start()
    {
        if (goal && player)
        {
            _startHeight = player.transform.position.y;
            player.Goal = goal;
            Vector3 goalPosition = goal.transform.position;
            goalPosition.y = _startHeight;
            goal.transform.position = goalPosition;
            _goalTolerance = goal.GetComponent<Renderer>().bounds.extents.magnitude;
        }
        else
        {
            Debug.LogWarning("ThirdPersonGame requires a player and a controller.");
            return;
        }

        switch (player.controlType)
        {
            case ControlType.Camera:
            {
                _falkenGame.Init<CameraRelativeBrainSpec>();
                break;
            }
            case ControlType.Player:
            {
                _falkenGame.Init<PlayerRelativeBrainSpec>();
                break;
            }
            case ControlType.World:
            {
                _falkenGame.Init<WorldRelativeBrainSpec>();
                break;
            }
            case ControlType.Flight:
            case ControlType.AutoFlight:
            {
                _falkenGame.Init<FlightBrainSpec>();
                break;
            }
            default:
                Debug.Log("Unsupported control type");
                break;
        }
        player.SetActionsAndObservations(
            _falkenGame.BrainSpec.Actions, _falkenGame.BrainSpec.Observations);
        CreateEpisodeAndResetGame(Falken.Episode.CompletionState.Success);
    }

    void OnDestroy()
    {
        _falkenGame.Shutdown();
    }

    void FixedUpdate()
    {
        if (_episode != null && _episode.Completed)
        {
            Debug.Log("Failed to reach goal. Ending episode.");
            CreateEpisodeAndResetGame(Falken.Episode.CompletionState.Failure);
        }
        else if (Vector3.Distance(player.transform.position, goal.transform.position) <
            _goalTolerance)
        {
            Debug.Log("Reached goal. Ending episode with success.");
            CreateEpisodeAndResetGame(Falken.Episode.CompletionState.Success);
        }
    }

    /// <summary>
    /// Completes the current episode if any and creates a new one.
    /// </summary>
    private void CreateEpisodeAndResetGame(Falken.Episode.CompletionState episodeState)
    {
        _episode?.Complete(episodeState);
        _episode = _falkenGame.CreateEpisode();
        player.FalkenEpisode = _episode;

        bool flight = (
            player.controlType == ControlType.Flight ||
            player.controlType == ControlType.AutoFlight);

        if (flight)
        {
            player.transform.rotation = Quaternion.identity;
            SetRandomPosition(player.gameObject, flight);
            SetRandomPosition(goal, flight);
        }
        else
        {
            SetRandomPosition(player.gameObject, flight);
            SetRandomRotation(player.gameObject);
            SetRandomPosition(goal, flight);
        }

        player.Reset();
    }

    private void SetRandomPosition(GameObject obj, bool y = false)
    {
        obj.transform.position = new Vector3(
            Random.Range(-boardSize / 2, boardSize / 2),
            y ? _startHeight + Random.Range(-boardSize / 2, boardSize / 2) : _startHeight,
            Random.Range(-boardSize / 2, boardSize / 2));
    }

    private void SetRandomRotation(GameObject obj)
    {
        obj.transform.rotation = Quaternion.AngleAxis(Random.value * 360, Vector3.up);
    }
}
