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
    [Tooltip("Target application framerate.")]
    public int targetFPS = 60;
    [Tooltip("Set to run game faster or slower than realtime.")]
    [Range(0.1f, 10)]
    public float timeScale = 1;
    #endregion

    #region Protected and private attributes
    private NegaFalkenPlayer playerOne;
    private NegaFalkenPlayer playerTwo;
    private float _deltaTime;
    private bool humanControlled = true;
    #endregion

    public NegaFalkenPlayer GetClosestEnemy(NegaFalkenPlayer player)
    {
        return player == playerOne ? playerTwo : playerOne;
    }

    #region Unity Callbacks
    void Start()
    {
        // Try to render at this specified framerate.
        Application.targetFrameRate = targetFPS;

        Init();
        ResetGame();
    }

    void Update()
    {
        // Update simulation time.
        if (Input.GetKeyDown(UnityEngine.KeyCode.Equals))
        {
            timeScale = Mathf.Min(timeScale * 2, 64);
        }
        else if (Input.GetKeyDown(UnityEngine.KeyCode.Minus))
        {
            timeScale = Mathf.Max(timeScale / 2, 0.25f);
        }
        Time.timeScale = timeScale;

        if (playerOne && Input.GetButtonDown("ToggleControl"))
        {
            humanControlled = !humanControlled;
            playerOne.HumanControlled = humanControlled;
        }

        _deltaTime += (Time.unscaledDeltaTime - _deltaTime) * 0.1f;
    }

    void LateUpdate()
    {
        if (playerOne && playerOne.Episode != null && playerOne.Episode.Completed ||
            playerTwo && playerTwo.Episode != null && playerTwo.Episode.Completed)
        {
            ResetGame();
        }
    }

    void OnGUI()
    {
        // Show the current FPS and Timescale
        GUIStyle style = new GUIStyle();
        style.alignment = TextAnchor.UpperCenter;
        style.normal.textColor = new Color(0.0f, 0.0f, 0.0f, 0.8f);

        string content = string.Format("{0:0.} fps", 1f / _deltaTime);
        if (System.Math.Abs(timeScale - 1.0f) > 0.01)
        {
            content += "\nTimescale" + timeScale + "x";
        }

        var trainingState = TrainingState;
        int percentComplete = (int)(TrainingProgress * 100);
        content += "\n" +
            ((trainingState == Falken.Session.TrainingState.Complete) ?
                "training complete" : trainingState.ToString().ToLower()) +
            $" ({percentComplete}%)";
        content += "\n" +
            "1P: " + (humanControlled ? "Human" : "Falken") + "\n" +
            "2P: Falken";

        const int width = 100;
        GUI.Label(new Rect(Screen.width / 2 - width / 2, 10, width, 20), content, style);
    }

    void OnDestroy()
    {
        Shutdown();
    }
    #endregion

    private void ResetGame()
    {
        if (!playerOnePrefab || !playerTwoPrefab || !playerOneSpawn || !playerTwoSpawn)
        {
            Debug.LogError("Cannot start NegaFalken without two players and spawns.");
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
