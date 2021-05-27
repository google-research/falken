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

public class SessionController : MonoBehaviour
{
    #region Editor variables
    public string brainDisplayName = "NegaFalken Brain";
    public float timeScale = 1;
    public int xCopies = 1;
    public int zCopies = 1;
    public Arena arena;
    public int targetFPS = 60;
    public uint falkenMaxSteps = 300;
    public string falkenProjectId = "";
    public string falkenApiKey = "";
    // Optional snapshot ID used to start the session.
    public string snapshotId = null;
    public string brainId = null;
    #endregion

    #region Protected and private attributes
    private Falken.Service _service = null;
    private Falken.Brain<PlayerBrainSpec> _brain = null;
    private Falken.Session _session = null;
    private float _deltaTime;
    private readonly float _separation = 0.1f;
    #endregion

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
            _brain = _service.CreateBrain<PlayerBrainSpec>(brainDisplayName);
            Debug.Log($"Created brain {_brain.Id}");
        }
        else
        {
            _brain = _service.LoadBrain<PlayerBrainSpec>(brainId, snapshotId);
        }
        brainId = _brain.Id;
    }

    void Start()
    {
        // Try to render at this specified framerate.
        Application.targetFrameRate = targetFPS;
        // Start a new training session.
        CreateSession();

        Vector3 offset = new Vector3(
            arena.BoardSize + _separation / 2, 0,
            arena.BoardSize + _separation / 2);

        // Copy scene in a grid.
        for (int x = 0; x < xCopies; x++)
        {
            for (int z = 0; z < zCopies; z++)
            {
                Arena cur;
                if (x == 0 && z == 0)
                {
                    cur = this.arena;
                }
                else
                {
                    cur = Instantiate(arena);
                }

                foreach (Player p in cur.players)
                {
                    // Cast if possible and provide references to the running session.
                    var negaFalkenPlayer = p as NegaFalkenPlayer;
                    if (negaFalkenPlayer != null)
                    {
                        negaFalkenPlayer.Session = _session;
                        negaFalkenPlayer.BrainSpec = _brain.BrainSpec;
                    }
                }

                Vector3 total_offset = new Vector3(
                    offset.x * x, 0,
                    offset.z * z);
                cur.transform.position += total_offset;
            }
        }
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

        _deltaTime += (Time.unscaledDeltaTime - _deltaTime) * 0.1f;

        if (arena.GameReadyToStart)
        {
            arena.StartGame();
        }
    }

    void OnGUI()
    {
        // Show the current FPS and Timescale
        GUIStyle style = new GUIStyle();
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

        GUI.Label(
            new Rect(10, 10, 100, 20), content, style);
    }

    private void OnDestroy()
    {
        // Stop the current session if it was running.
        if (_session != null)
        {
            _session.Stop();
            _session = null;
        }
    }
    #endregion

    #region Auxiliary methods
    private void CreateSession()
    {
        if (_brain != null)
        {
            _session = _brain.StartSession(Falken.Session.Type.InteractiveTraining,
                falkenMaxSteps);
            Debug.Log($"Created session {_session.Id}");
        }

        if (_session == null)
        {
            Debug.LogError("Error while trying to start a session.");
        }
    }
    #endregion
}
