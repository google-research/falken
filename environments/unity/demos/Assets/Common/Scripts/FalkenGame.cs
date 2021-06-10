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
using UnityEngine;

/// <summary>
/// <c>FalkenGame</c> AI player that can be trained to play and test games.
/// </summary>
[Serializable]
public abstract class FalkenGame<PlayerBrainSpec> : MonoBehaviour
  where PlayerBrainSpec : Falken.BrainSpecBase, new()
{
    [Tooltip("The Falken service project ID.")]
    public string falkenProjectId = "";
    [Tooltip("The Falken service API Key.")]
    public string falkenApiKey = "";
    [Tooltip("The Falken brain human readable name.")]
    public string brainDisplayName = "A Brain";
    [Tooltip("The Falken brain ID.")]
    public string brainId = null;
    [Tooltip("[Optional] The Falken session snapshot ID.")]
    public string snapshotId = null;
    [Tooltip("The maximum number of steps per episode.")]
    public uint falkenMaxSteps = 300;
    [Tooltip("The type of session to create.")]
    public Falken.Session.Type sessionType = Falken.Session.Type.InteractiveTraining;
    [Tooltip("Determines whether Falken or the Player should be in control.")]
    public bool humanControlled = true;
    [Tooltip("Set to false to disable the rendering of control and training status.")]
    public bool renderGameHUD = true;

    private Falken.Service _service = null;
    private Falken.BrainBase _brain = null;
    private Falken.Session _session = null;

    /// <summary>
    /// Getter for brain spec.
    /// </summary>
    protected PlayerBrainSpec BrainSpec
    {
        get
        {
            return (PlayerBrainSpec)(_brain?.BrainSpecBase);
        }
    }

    /// <summary>
    /// Getter for training state.
    /// </summary>
    protected Falken.Session.TrainingState TrainingState
    {
        get
        {
            return _session != null ? _session.SessionTrainingState :
                Falken.Session.TrainingState.Invalid;
        }
    }

    /// <summary>
    /// Getter for training progress.
    /// </summary>
    protected float TrainingProgress
    {
        get
        {
            return _session != null ? _session.SessionTrainingProgress : 0f;
        }
    }

    /// <summary>
    /// Connects to Falken service and creates or loads a brain.
    /// </summary>
    protected void Init()
    {
        Init<PlayerBrainSpec>();
    }

    /// <summary>
    /// Connects to Falken service and creates or loads a brain spec subclass.
    /// </summary>
    protected void Init<BrainSpec>() where BrainSpec : PlayerBrainSpec, new()
    {
        // Connect to Falken service.
        _service = Falken.Service.Connect(falkenProjectId, falkenApiKey);
        if (_service == null)
        {
            Debug.LogWarning(
                "Failed to connect to Falken's services. Make sure" +
                "You have a valid api key and project id or your " +
                "json config is properly formated.");
            return;
        }

        // If there is no brainId, create a new one. Othewise, load an existing
        // brain.
        if (String.IsNullOrEmpty(brainId))
        {
            _brain = _service.CreateBrain<BrainSpec>(brainDisplayName);
        }
        else
        {
            _brain = _service.LoadBrain<BrainSpec>(brainId, snapshotId);
        }
        if (_brain == null)
        {
            return;
        }
        brainId = _brain.Id;

        // Create session.
        _session = _brain.StartSession(sessionType, falkenMaxSteps);

        if (humanControlled && sessionType != Falken.Session.Type.InteractiveTraining) {
            humanControlled = false;
            ControlChanged();
        }
    }

    /// <summary>
    /// Starts a new episode.
    /// </summary>
    protected Falken.Episode CreateEpisode()
    {
        return _session?.StartEpisode();
    }

    /// <summary>
    /// Stops a session.
    /// </summary>
    protected void StopSession()
    {
        if (_session != null)
        {
            snapshotId = _session.Stop();
            Debug.Log($"Stopped session with snapshot ID: {snapshotId}");
            _session = null;
        }
    }

    /// <summary>
    /// Deletes the brain and disconnects from the Falken service.
    /// </summary>
    protected void Shutdown()
    {
        StopSession();

        Debug.Log($"Shutting down brain {brainId}");
        _brain = null;
        _service = null;
    }

    protected abstract void ControlChanged();

    void Update()
    {
        if (Input.GetButtonDown("ToggleControl") &&
            sessionType == Falken.Session.Type.InteractiveTraining)
        {
            humanControlled = !humanControlled;
            ControlChanged();
        }
    }

    void OnGUI()
    {
        if (!renderGameHUD)
        {
            return;
        }

        // Show the current FPS and Timescale
        GUIStyle style = new GUIStyle();
        style.alignment = TextAnchor.UpperCenter;
        style.normal.textColor = new Color(0.0f, 0.0f, 0.0f, 0.8f);

        string content = "Control: " + (humanControlled ? "Human" : "Falken");

        var trainingState = TrainingState;
        int percentComplete = (int)(TrainingProgress * 100);
        content += "\n" +
            ((trainingState == Falken.Session.TrainingState.Complete) ?
                "Training Complete" : trainingState.ToString().ToLower()) +
            $" ({percentComplete}%)";

        const int width = 100;
        GUI.Label(new Rect(Screen.width / 2 - width / 2, 10, width, 20), content, style);
    }
}
