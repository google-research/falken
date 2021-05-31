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
/// <c>SessionController</c> Manages the NegaFalken game state and related Falken state.
/// </summary>
public class SessionController : MonoBehaviour
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

    [Tooltip("Falken ProjectId")]
    public string falkenProjectId = "";
    [Tooltip("Falken API Key")]
    public string falkenApiKey = "";
    [Tooltip("Falken Brain ID. Leave null to use latest snapshot.")]
    public string brainId = null;
    [Tooltip("Falken Snapshot ID. Leave null to use latest snapshot.")]
    public string snapshotId = null;
    [Tooltip("Display name of the brain.")]
    public string brainDisplayName = "NegaFalken Brain";
    [Tooltip("Maximum number of FixedUpdates in an Episode.")]
    public uint falkenMaxSteps = 300;
    #endregion

    #region Protected and private attributes
    private Falken.Service _service = null;
    private Falken.Brain<NegaPlayerBrainSpec> _brain = null;
    private Falken.Session _session = null;
    private NegaFalkenPlayer playerOne;
    private NegaFalkenPlayer playerTwo;
    private float _deltaTime;
    #endregion

    public NegaFalkenPlayer GetClosestEnemy(NegaFalkenPlayer player)
    {
        return player == playerOne ? playerTwo : playerOne;
    }

    #region Unity Callbacks
    void OnEnable()
    {
        // Connect to Falken service.
        _service = Falken.Service.Connect(falkenProjectId, falkenApiKey);
        if (_service == null)
        {
            Debug.Log(
                "Failed to connect to Falken's services. Make sure" +
                "You have a valid api key and project id or your " +
                "json config is properly formated.");
            brainId = null;
            return;
        }
        // If there is no brainId, create a new one. Othewise, load an existing brain.
        if (String.IsNullOrEmpty(brainId))
        {
            _brain = _service.CreateBrain<NegaPlayerBrainSpec>(brainDisplayName);
        }
        else
        {
            _brain = _service.LoadBrain<NegaPlayerBrainSpec>(brainId, snapshotId);
        }
        brainId = _brain.Id;
    }

    void Start()
    {
        // Try to render at this specified framerate.
        Application.targetFrameRate = targetFPS;

        if (_brain != null)
        {
            _session = _brain.StartSession(Falken.Session.Type.InteractiveTraining,
                falkenMaxSteps);
        }

        if (_session == null)
        {
            Debug.LogError("Error while trying to start a session.");
        }

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
            playerOne.HumanControlled = !playerOne.HumanControlled;
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
        if (_session != null)
        {
            var trainingState = _session.SessionTrainingState;
            int percentComplete = (int)(_session.SessionTrainingProgress * 100);
            content += "\n" +
                ((trainingState == Falken.Session.TrainingState.Complete) ?
                 "training complete" : trainingState.ToString().ToLower()) +
                $" ({percentComplete}%)";
        }

        const int width = 100;
        GUI.Label(
            new Rect(Screen.width / 2 - width / 2, 10, width, 20), content, style);
    }

    void OnDestroy()
    {
        // Stop the current session if it was running.
        if (_session != null)
        {
            _session.Stop();
            _session = null;
        }
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
        playerOne.HumanControlled = true;
        playerTwo = CreatePlayer(playerTwoPrefab, playerTwoSpawn, playerTwoSlider);
        playerTwo.HumanControlled = false;
    }

    private NegaFalkenPlayer CreatePlayer(NegaFalkenPlayer prefab, PlayerSpawn spawn, Slider slider)
    {
        Vector3 randomPos = spawn.GetSpawnPoint();
        Quaternion randomRot = Quaternion.AngleAxis(UnityEngine.Random.Range(0f, 360f), Vector3.up);
        NegaFalkenPlayer player = GameObject.Instantiate(prefab, randomPos, randomRot);
        player.SessionController = this;
        player.HealthSlider = slider;
        player.BrainSpec = _brain.BrainSpec;
        player.Episode = _session.StartEpisode();
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
