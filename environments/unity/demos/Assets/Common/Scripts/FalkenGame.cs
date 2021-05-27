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
public class FalkenGame<PlayerBrainSpec>
  where PlayerBrainSpec : Falken.BrainSpecBase, new()
{
    [Tooltip("The Falken service project ID.")]
    public string falkenProjectId = "";
    [Tooltip("The Falken service API Key.")]
    public string falkenApiKey = "";
    [Tooltip("The Falken brain human readable name.")]
    public string brainDisplayName = "Cart Brain";
    [Tooltip("The Falken brain ID.")]
    public string brainId = null;
    [Tooltip("[Optional] The Falken session snapshot ID.")]
    public string snapshotId = null;
    [Tooltip("The maximum number of steps per episode.")]
    public uint falkenMaxSteps = 300;

    private Falken.Service _service = null;
    private Falken.Brain<PlayerBrainSpec> _brain = null;
    private Falken.Session _session = null;

    /// <summary>
    /// Getter for brain spec.
    /// </summary>
    public PlayerBrainSpec BrainSpec
    {
        get
        {
            return _brain?.BrainSpec;
        }
    }

    /// <summary>
    /// Connects to Falken service and creates or loads a brain.
    /// </summary>
    public void Init()
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
            _brain = _service.CreateBrain<PlayerBrainSpec>(brainDisplayName);
        }
        else
        {
            _brain = _service.LoadBrain<PlayerBrainSpec>(brainId, snapshotId);
        }
        if (_brain == null)
        {
            return;
        }
        brainId = _brain.Id;

        // Create session.
        _session = _brain.StartSession(Falken.Session.Type.InteractiveTraining,
                                       falkenMaxSteps);
    }

    /// <summary>
    /// Starts a new episode.
    /// </summary>
    public Falken.Episode CreateEpisode()
    {
        return _session?.StartEpisode();
    }

    /// <summary>
    /// Stops a session.
    /// </summary>
    public void StopSession()
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
    public void Shutdown()
    {
        StopSession();

        Debug.Log($"Shutting down brain {brainId}");
        _brain = null;
        _service = null;
    }
}
