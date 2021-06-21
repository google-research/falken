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

using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

/// <summary>
/// <c>NegaFalkenGame</c> Manages the NegaFalken game state and related Falken state.
/// </summary>
public class NegaFalkenGame : FalkenGame<NegaBrainSpec>
{
    #region Editor variables
    [Tooltip("Prefab that defines player one.")]
    public NegaFalkenPlayer playerOnePrefab;
    [Tooltip("Prefab that defines player two.")]
    public NegaFalkenPlayer playerTwoPrefab;
    [Tooltip("Region within which to spawn player one.")]
    public PlayerSpawn playerOneSpawn;
    [Tooltip("Region within which to spawn player two.")]
    public PlayerSpawn playerTwoSpawn;
    [Tooltip("Reference to Canvas element for player one health.")]
    public Slider playerOneSlider;
    [Tooltip("Reference to Canvas element for player two health.")]
    public Slider playerTwoSlider;
    #endregion

    #region Protected and private attributes
    private NegaFalkenPlayer playerOne;
    private NegaFalkenPlayer playerTwo;
    #endregion

    public NegaFalkenPlayer GetClosestEnemy(NegaFalkenPlayer player)
    {
        return player == playerOne ? playerTwo : playerOne;
    }

    #region Unity Callbacks
    void Start()
    {
        Init();
        ResetGame();
    }

    void LateUpdate()
    {
        if (playerOne && playerOne.Episode != null && EpisodeCompleted ||
            playerTwo && playerTwo.Episode != null && EpisodeCompleted)
        {
            ResetGame();
        }
    }

    void OnDestroy()
    {
        Shutdown();
    }
    #endregion

    protected override void ControlChanged()
    {
        if (playerOne)
        {
            playerOne.HumanControlled = humanControlled;
        }
    }

    private void ResetGame()
    {
        bool timedOut = false;
        if (playerOne != null && playerOne.Episode != null && !playerOne.Episode.Completed)
        {
            playerOne.Episode.Complete(Falken.Episode.CompletionState.Failure);
            timedOut = true;
        }

        if (playerTwo != null && playerTwo.Episode != null && playerTwo.Episode.Completed)
        {
            playerTwo.Episode.Complete(Falken.Episode.CompletionState.Failure);
            timedOut = true;
        }

        if (timedOut)
        {
            Debug.Log("Episode timed out. Resetting as failure.");
        }

        if(playerOne)
        {
            GameObject.Destroy(playerOne.gameObject);
        }

        if(playerTwo)
        {
            GameObject.Destroy(playerTwo.gameObject);
        }

        playerOne = CreatePlayer(playerOnePrefab, playerOneSpawn, playerOneSlider);
        playerOne.HumanControlled = humanControlled;
        playerTwo = CreatePlayer(playerTwoPrefab, playerTwoSpawn, playerTwoSlider);
        playerTwo.HumanControlled = false;
    }

    private NegaFalkenPlayer CreatePlayer(NegaFalkenPlayer prefab, PlayerSpawn spawn, Slider slider)
    {
        Vector3 randomPos = spawn.GetSpawnPoint();
        Quaternion randomRot = Quaternion.AngleAxis(UnityEngine.Random.Range(0f, 360f), Vector3.up);
        NegaFalkenPlayer player = GameObject.Instantiate(prefab, randomPos, randomRot);
        player.Game = this;
        player.HealthSlider = slider;
        player.BrainSpec = BrainSpec;
        player.Episode = CreateEpisode();
        player.GetComponent<Health>().OnKilled += PlayerKilled;
        return player;
    }

    private void PlayerKilled(Health killed)
    {
        bool playerOneWins = killed.gameObject == playerTwo.gameObject;
        Debug.Log(playerOneWins ? "Player one wins!" : "Player two wins!");

        if (playerOne.Episode != null)
        {
            playerOne.Episode.Complete(playerOneWins ?
                Falken.Episode.CompletionState.Success : Falken.Episode.CompletionState.Failure);
        }

        if (playerTwo.Episode != null)
        {
            playerTwo.Episode.Complete(!playerOneWins ?
                Falken.Episode.CompletionState.Success : Falken.Episode.CompletionState.Failure);
        }

        ResetGame();
    }
}
