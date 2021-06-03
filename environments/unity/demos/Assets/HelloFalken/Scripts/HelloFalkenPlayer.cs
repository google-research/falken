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

﻿using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Runtime.Serialization;
using UnityEditor;
using UnityEngine;
using UnityEngine.UI;
using Debug = UnityEngine.Debug;

/// <summary>
/// <c>HelloActions</c> Describes the control Actions a HelloFalken player can perform.
/// </summary>
public class HelloActions : Falken.ActionsBase
{
    public Falken.Number throttle = new Falken.Number(-1f, 1f);

    public Falken.Joystick steering = new Falken.Joystick(
        "steering", Falken.AxesMode.DeltaPitchYaw, Falken.ControlledEntity.Player);

    public virtual bool IsNoop()
    {
        const double epsilon = 1e-20;
        return (
            Math.Abs(throttle.Value) <= epsilon &&
            Math.Abs(steering.X) <= epsilon);
    }
}

/// <summary>
/// <c>HelloPlayerEntity</c> Basic observations that sense the environment around the player entity.
/// </summary>
public class HelloPlayerEntity : Falken.EntityBase
{
    public Falken.Feelers feelers = new Falken.Feelers(3f, 0f, 360.0f, 14, null);
}

/// <summary>
/// <c>HelloObservations</c> Final observations with player and goal entities.
/// </summary>
public class HelloObservations : Falken.ObservationsBase
{
    public Falken.EntityBase goal = new Falken.EntityBase("goal");

    public HelloObservations()
    {
        player = new HelloPlayerEntity();
    }
}

/// <summary>
/// <c>HelloBrainSpec</c> Binding of Actions and Observations for this simple player.
/// </summary>
public class HelloBrainSpec : Falken.BrainSpec<HelloObservations, HelloActions> {}


/// <summary>
/// <c>HelloFalkenPlayer</c> Demonstrates how to use Falken in a very simple game.
/// The player can control the steering and thrust of a ship and then attempts to steer the ship
/// to a goal object. Ship and goal transforms are randomized every time.
/// </summary>
[RequireComponent(typeof(Ship))]
public class HelloFalkenPlayer : MonoBehaviour
{
    #region Editor Variables
    [Tooltip("Reference to the goal object that the player needs to move to.")]
    public GameObject goalObject;
    [Tooltip("Reference to the ground plane the player spawns above.")]
    public GameObject groundPlane;

    [Tooltip("Falken ProjectId")]
    public string falkenProjectId = "";
    [Tooltip("Falken API Key")]
    public string falkenApiKey = "";
    [Tooltip("Falken Brain ID. Leave null to create a new brain.")]
    public string brainId = "";
    [Tooltip("Falken Snapshot ID. Leave null to use latest snapshot.")]
    public string snapshotId = "";
    [Tooltip("Display name of the brain.")]
    public string brainLabel = "Hello Falken Brain";
    [Tooltip("Maximum number of FixedUpdates in an Episode.")]
    public uint maxSteps = 300;
    #endregion

    #region Private State
    protected Falken.Service _service = null;
    protected Falken.Brain<HelloBrainSpec> _brain = null;
    protected Falken.Session _session = null;
    private Falken.Episode _episode = null;
    private Falken.Session.Type _sessionType = Falken.Session.Type.InteractiveTraining;
    private int _totalSuccess;
    private int _totalFailure;
    private uint _numSteps;
    private float _lastDistance;
    private float _lastUserInputFixedTime;
    private Ship _ship;
    private float _goalTolerance = 0.3f;
    private bool _autopilot = false;
    #endregion

    #region Unity Callbacks
    void OnEnable()
    {
        _service = Falken.Service.Connect(falkenProjectId, falkenApiKey);
        CreateOrLoadBrain();

        _ship = gameObject.GetComponent<Ship>();

        if (goalObject)
        {
           _goalTolerance = goalObject.GetComponent<Renderer>().bounds.extents.magnitude;
        }

        ResetGameState();
    }

    void OnDisable()
    {
        if(_session != null)
        {
            var endingSnapshotId =  _session.Stop();
            Debug.Log($"Session completed. session_id: {_session.Id}" +
                      $" brain_id: {_brain.Id} snapshot_id: " +
                      $"{endingSnapshotId}");
            _service = null;
            _brain = null;
            _session = null;
            _episode = null;
        }
        _ship = null;
    }

    void OnGUI()
    {
        string message = _autopilot ? "falken enabled" :
                                     "recording demonstrations";
        GUIStyle style = new GUIStyle
        {
            fontSize = 20,
            alignment = TextAnchor.MiddleCenter
        };
        if (_session != null)
        {
            var trainingState = _session.SessionTrainingState;
            int percentComplete = (int)(_session.SessionTrainingProgress * 100);
            message += ": " +
                ((trainingState == Falken.Session.TrainingState.Complete) ?
                 "training complete" : trainingState.ToString().ToLower()) +
                 $" ({percentComplete}%)";
        }
        GUI.Label(new Rect(
            Screen.width/2 - 50, 20,
            100, 20),
            message, style);

    }

    void FixedUpdate()
    {
        ++_numSteps;

        if (Input.GetButtonDown("ToggleControl"))
        {
            _autopilot = !_autopilot;
        }

        CalculateObservations();
        CalculateActions();

        // Calculate Rewards
        float currentDistance = Vector3.Distance(transform.position, goalObject.transform.position);
        bool atGoal = currentDistance <= _goalTolerance;
        _lastDistance = currentDistance;
        if (atGoal)
        {
            Debug.Log("Succeeded episode " + _episode.Id);
            _totalSuccess++;
            CompleteEpisodeAndResetGame(Falken.Episode.CompletionState.Success);
            return;
        }
        else if (_numSteps >= maxSteps)
        {
            Debug.Log("Failed episode " + _episode.Id);
            _totalFailure++;
            CompleteEpisodeAndResetGame(Falken.Episode.CompletionState.Failure);
            return;
        }

        // Backup the throttle and steering values, since the values in Actions will
        // be consumed and replaced by Step
        float throttle = Actions.throttle.Value;
        float steering = Actions.steering.X;

        if (_session != null)
        {
            // Keyboard input overrides brain input.
            _brain.BrainSpec.Actions.ActionsSource = _autopilot ?
                Falken.ActionsBase.Source.BrainAction :
                Falken.ActionsBase.Source.HumanDemonstration;
            _episode.Step();

            // If the brain is at the wheel, override the actions with the
            // values returned by Step.
            if (_brain.BrainSpec.Actions.ActionsSource == Falken.ActionsBase.Source.BrainAction)
            {
                throttle = Actions.throttle.Value;
                steering = Actions.steering.X;
            }
        }

        _ship.ApplyActions(throttle, steering);
    }
    #endregion

    #region Private Methods
    private HelloActions Actions { get { return _brain?.BrainSpec.Actions; } }

    private HelloObservations Observations { get { return _brain?.BrainSpec.Observations; } }

    // Initialize a new brain or load the specified brain from brain ID and
    // snapshot ID.
    private void CreateOrLoadBrain()
    {
        if (_service == null)
        {
            Debug.Log(
                "Failed to connect to Falken's services. Make sure" +
                $"You have a valid api key and project id or your " +
                "json config is properly formated.");
            return;
        }
        try
        {
            if (String.IsNullOrEmpty(brainId))
            {
                _brain = _service.CreateBrain<HelloBrainSpec>(brainLabel);
            }
            else
            {
                _brain = _service.LoadBrain<HelloBrainSpec>(
                    brainId, snapshotId);
            }
            _session = _brain.StartSession(_sessionType, maxSteps);
            _episode = _session.StartEpisode();
        }
        catch (Exception e)
        {
            Debug.LogError(e.ToString());
            _brain = null;
            _session = null;
            _episode = null;
        }
    }

    private void CalculateObservations()
    {
        if (Observations != null)
        {
            Observations.player.position = gameObject.transform.position;
            Observations.player.rotation = gameObject.transform.rotation;
            Observations.goal.position = goalObject.transform.position;
            Observations.goal.rotation = goalObject.transform.rotation;
            HelloPlayerEntity entity = (HelloPlayerEntity)Observations.player;
            entity.feelers.Update(gameObject.transform, new Vector3(0.0f, 0.0f, 0.0f), true);
        }
    }

    private void CalculateActions()
    {
        if (Actions != null)
        {
            Actions.steering.X = Input.GetAxis("Steering");
            Actions.steering.Y = 0f;
            Actions.throttle.Value = Input.GetAxis("Gas") - Input.GetAxis("Brake");

            if (!Actions.IsNoop())
            {
                _lastUserInputFixedTime = Time.fixedTime;
            }
        }
    }

    private void CompleteEpisodeAndResetGame(Falken.Episode.CompletionState episodeState)
    {
        if (_session != null)
        {
            _episode.Complete(episodeState);
            _episode = _session.StartEpisode();
        }
        ResetGameState();
    }

    private void ResetGameState()
    {
        _numSteps = 0;

        Vector3 playerExtents = gameObject.GetComponent<Collider>().bounds.extents;
        float randomAngle = UnityEngine.Random.Range(0f, 360f);
        var randomPos = GenerateRandomGroundPos(randomAngle, playerExtents);
        transform.SetPositionAndRotation(randomPos, Quaternion.AngleAxis(randomAngle, Vector3.up));

        Vector3 goalExtents = goalObject.GetComponent<Renderer>().bounds.extents;
        do {
            goalObject.transform.position = GenerateRandomGroundPos(0f, goalExtents);
            _lastDistance = Vector3.Distance(transform.position, goalObject.transform.position);
        } while (_lastDistance < _goalTolerance);

        _ship.Stop();
    }

    private Vector3 GenerateRandomGroundPos(float angle, Vector3 extents)
    {
        Bounds groundBounds = groundPlane.GetComponent<Renderer>().bounds;
        float wallWidth = 1f;
        Quaternion boxOrientation = Quaternion.AngleAxis(angle, Vector3.up);
        Vector3 position;
        do {
            position = new Vector3(UnityEngine.Random.Range(groundBounds.min.x + wallWidth,
                                                            groundBounds.max.x - wallWidth),
                                   transform.position.y,
                                   UnityEngine.Random.Range(groundBounds.min.z + wallWidth,
                                                            groundBounds.max.z - wallWidth));
        } while (Physics.OverlapBox(position, extents, boxOrientation).Length > 0);
        return position;
    }
    #endregion
}
