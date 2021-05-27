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
/// <c>FalkenPlayer</c> AI player that can be trained to play and test games.
/// </summary>
[Serializable]
public class FalkenPlayer<BrainSpec>
  where BrainSpec : Falken.BrainSpecBase, new()
{
    [Tooltip("The Falken service project ID.")]
    public string falkenProjectId = "";
    [Tooltip("The Falken service API Key.")]
    public string falkenApiKey = "";
    [Tooltip("The Falken brain human readable name.")]
    public string brainDisplayName = "Cart Brain";
    [Tooltip("[Optional] The Falken session snapshot ID.")]
    public string snapshotId = null;
    [Tooltip("The Falken brain ID.")]
    public string brainId = null;

    private Falken.Service _service = null;
    private Falken.Brain<BrainSpec> _brain = null;

    /// <summary>
    /// Connects to Falken service and creates or loads a brain.
    /// </summary>
    public void Init()
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
            _brain = _service.CreateBrain<BrainSpec>(brainDisplayName);
        }
        else
        {
            _brain = _service.LoadBrain<BrainSpec>(brainId, snapshotId);
        }
        brainId = _brain.Id;
    }

    /// <summary>
    /// Deletes the brain and disconnects from the Falken service.
    /// </summary>
    public void Shutdown()
    {
        Debug.Log("Shutting down brain: " + brainId);
        _brain = null;
        _service = null;
    }
}
