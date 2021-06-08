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
/// <c>CartGame</c> Creates cars and manages the state of the race.
/// </summary>
public class CartGame : FalkenGame<CartBrainSpec>
{
    [Tooltip("The track upon which to race.")]
    public SplineTrack track;
    [Tooltip("The car prefab to instantiate at the start of the game.")]
    public CartPlayer carPrefab;
    [Tooltip("The chase camera prefab to instantiate at the start of the game.")]
    public CarCamera cameraPrefab;

    private CartPlayer car;
    private CarCamera chaseCamera;
    private int nextCheckpointIndex;
    private Falken.Episode episode = null;

    public void Start()
    {
        if (track && carPrefab && cameraPrefab)
        {
            if (Camera.main)
            {
                Camera.main.gameObject.SetActive(false);
            }
            Transform[] controlPoints = track.GetControlPoints();
            Transform startingPoint = controlPoints[0];
            car = GameObject.Instantiate(carPrefab, startingPoint.position, startingPoint.rotation);
            chaseCamera = GameObject.Instantiate(cameraPrefab, startingPoint.position,
                startingPoint.rotation);
            chaseCamera.target = car.GetComponent<Rigidbody>();
            nextCheckpointIndex = 1;
        }
        else
        {
            Debug.Log("CartGame is not configured properly. Please set a track, car, and camera.");
        }

        // Initialize Falken.
        Init();
        car.FalkenBrainSpec = BrainSpec;

        ResetGame(true);
    }

    public void FixedUpdate()
    {
        if (track && car)
        {
            Transform[] controlPoints = track.GetControlPoints();
            Transform checkpoint = controlPoints[nextCheckpointIndex];
            car.NextCheckpoint = checkpoint;
            Vector3 carToCheckpoint = (car.transform.position - checkpoint.position).normalized;
            if(Vector3.Dot(checkpoint.forward, carToCheckpoint) > 0)
            {
                if (nextCheckpointIndex == 0)
                {
                    Debug.Log("Completed a lap!");
                    ResetGame(true);
                }
                ++nextCheckpointIndex;
                if (nextCheckpointIndex >= controlPoints.Length)
                {
                    nextCheckpointIndex = 0;
                }
            }

            // Checks whether the episode has been completed w/o reaching the goal.
            if (episode != null && episode.Completed)
            {
                Debug.Log("Failed episode " + episode.Id);
                ResetGame(false);
            }
        }
    }

    public void OnDestroy()
    {
        Shutdown();
    }

    /// <summary>
    /// Determines whether Falken or the human player should be in control.
    /// </summary>
    protected override void ControlChanged()
    {
        if (car)
        {
            car.HumanControlled = humanControlled;
        }
    }

    /// <summary>
    /// Restarts the game.
    /// </summary>
    private void ResetGame(bool success)
    {
        episode?.Complete(success ? Falken.Episode.CompletionState.Success :
                Falken.Episode.CompletionState.Failure);

        episode = CreateEpisode();
        car.FalkenEpisode = episode;
    }
}
