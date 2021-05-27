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

public class HF_Actions : Falken.ActionsBase
{
    protected const double _epsilon = 1e-20;

    [Range(-1f, 1f)]
    public float throttle;

    public Falken.Joystick steering = new Falken.Joystick(
        "steering", Falken.AxesMode.DeltaPitchYaw, Falken.ControlledEntity.Player);

    public virtual bool IsNoop()
    {
        return (
            Math.Abs(throttle) <= _epsilon &&
            Math.Abs(steering.X) <= _epsilon);
    }
}

public class HF_Entity : Falken.EntityBase
{
    public Falken.Feelers feelers = new Falken.Feelers(0.8f, 0.15f, 90.0f, 14, null);
}

public class HF_Observations : Falken.ObservationsBase
{
    public Falken.EntityBase goal = new Falken.EntityBase("goal");

    public HF_Observations()
    {
        player = new HF_Entity();
    }
}

public class HF_BrainSpec : Falken.BrainSpec<HF_Observations, HF_Actions> {}


[RequireComponent(typeof(Rigidbody))]
public class HF_Player : MonoBehaviour
{
    #region Editor Variables
    public float movementRate = 10f;
    public float steeringRate = 10f;
    public float linearDrag = 2f;
    public float angularDrag = 5f;
    public float maxSpeed = 5f;
    public float maxTurn = 5f;
    public bool useGamepad = false;
    public uint maxSteps = 300;
    public float autopilotSeconds = 2;
    // Distance to the goal object that is required to complete the episode.
    public const float goalDistance = 0.3f;
    public GameObject goalObject;
    public GameObject groundPlane;
    public string falkenApiKey = "";
    public string falkenProjectId = "";
    public string brainId = "";
    public string snapshotId = "";
    public string brainLabel = "Hello Falken Brain";
    #endregion

    #region Private State

    protected Falken.Service _service = null;
    protected Falken.Brain<HF_BrainSpec> _brain = null;
    protected Falken.Session _session = null;
    private Falken.Episode _episode = null;
    private Falken.Session.Type _sessionType = Falken.Session.Type.InteractiveTraining;
    private int _numEpisodesRequested;
    private int _numEpisodesRemaining;
    private int _totalSuccess;
    private int _totalFailure;
    private uint _numSteps;
    private float _lastDistance;
    private float _lastUserInputFixedTime;
    private Rigidbody _playerRigidBody;
    private bool _autopilot = false;
    #endregion

    // Optionally load arguments from Unity command line and the public string
    // commandLineArguments.
    public string commandLineArguments = null;
    private CommandLineParser _commandLineParser = null;

    #region Unity Callbacks

    public HF_Actions Actions
    {
        get
        {
            return _brain?.BrainSpec.Actions;
        }
    }

    public HF_Observations Observations
    {
        get
        {
            return _brain?.BrainSpec.Observations;
        }
    }

    public void OnEnable()
    {
        _service = Falken.Service.Connect(falkenProjectId, falkenApiKey);
        _commandLineParser = new CommandLineParser(commandLineArguments);
        CreateOrLoadBrain();
        _playerRigidBody = gameObject.GetComponent<Rigidbody>();

        if (!goalObject || !groundPlane)
        {
            Debug.LogError(
                "HF_Player requires both Goal and a Ground objects.");
        }

        ResetGameState();
    }

    public void OnDisable()
    {
        if(_session != null)
        {
            var endingSnapshotId =  _session.Stop();
            Debug.Log($"Session completed. session_id: {_session.Id}" +
                      $" brain_id: {_brain.Id} snapshot_id: " +
                      $"{endingSnapshotId}");
            Debug.Log($"[Test Runner] Completed {_numEpisodesRequested} episodes: " +
                      $"{_totalSuccess} succeeded, " +
                      $"{_totalFailure} failed, " +
                      $"0 aborted.");
            _service = null;
            _brain = null;
            _session = null;
            _episode = null;
        }
        _playerRigidBody = null;
    }

    public void OnGUI()
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

    // Initialize a new brain or load the specified brain from brain ID and
    // snapshot ID.
    private void CreateOrLoadBrain()
    {
        if (!String.IsNullOrEmpty(_commandLineParser.BrainId)) {
            brainId = _commandLineParser.BrainId;
            snapshotId = _commandLineParser.SnapshotId;
        }
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
                _brain = _service.CreateBrain<HF_BrainSpec>(brainLabel);
            }
            else
            {
                _brain = _service.LoadBrain<HF_BrainSpec>(
                    brainId, snapshotId);
            }
            _sessionType = _commandLineParser.SessionType;
            _numEpisodesRequested = _commandLineParser.EpisodesRequested;
            _numEpisodesRemaining = _numEpisodesRequested;
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

    public void FixedUpdate()
    {
        ++_numSteps;

        CalculateObservations();
        CalculateActions();

        // Calculate Rewards
        float currentDistance = Vector3.Distance(transform.position, goalObject.transform.position);
        bool atGoal = currentDistance <= goalDistance;
        float reward = atGoal ? 10f : _lastDistance - currentDistance;
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
        float throttle = Actions.throttle;
        float steering = Actions.steering.X;

        if (_session != null)
        {
            // Keyboard input overrides brain input.
            _autopilot = Time.fixedTime - _lastUserInputFixedTime > autopilotSeconds;
            _brain.BrainSpec.Actions.ActionsSource = _autopilot ?
                Falken.ActionsBase.Source.BrainAction :
                Falken.ActionsBase.Source.HumanDemonstration;
            _episode.Step();

            // If the brain is at the wheel, override the actions with the
            // values returned by Step.
            if (_brain.BrainSpec.Actions.ActionsSource == Falken.ActionsBase.Source.BrainAction)
            {
                throttle = Actions.throttle;
                steering = Actions.steering.X;
            }
        }

        ApplyActions(throttle, steering);
    }
    #endregion

    private void CalculateObservations()
    {
        if (Observations == null)
        {
            return;
        }

        Observations.player.position = gameObject.transform.position;
        Observations.player.rotation = gameObject.transform.rotation;
        Observations.goal.position = goalObject.transform.position;
        Observations.goal.rotation = goalObject.transform.rotation;
        HF_Entity entity = (HF_Entity)Observations.player;
        entity.feelers.Update(gameObject.transform, new Vector3(0.0f, 0.0f, 0.0f), true);
    }

    private void CalculateActions()
    {
        if (Actions == null)
        {
            return;
        }

        Actions.throttle = 0f;
        if (Input.GetKey(KeyCode.W))
        {
            Actions.throttle += 1f;
        }
        if (Input.GetKey(KeyCode.S))
        {
            Actions.throttle -= 1f;
        }

        Actions.steering.X = 0f;
        Actions.steering.Y = 0f;

        if (Input.GetKey(KeyCode.A))
        {
            Actions.steering.X -= 1f;
        }
        if (Input.GetKey(KeyCode.D))
        {
            Actions.steering.X += 1f;
        }

        if (useGamepad)
        {
            Actions.steering.X = Input.GetAxis("Turn");
            // Pressing up on the axis is -1.
            Actions.throttle = -Input.GetAxis("Accelerate");
            Actions.throttle = Mathf.Clamp(Actions.throttle, -1f, 1f);
        }

        if (!Actions.IsNoop())
        {
            _lastUserInputFixedTime = Time.fixedTime;
        }
    }

    public void ApplyActions(float throttle, float steering)
    {
        if (Actions == null)
        {
            return;
        }

        _playerRigidBody.maxAngularVelocity = maxTurn;
        _playerRigidBody.angularDrag = angularDrag;
        _playerRigidBody.drag = linearDrag;

        if (_playerRigidBody.velocity.magnitude < maxSpeed)
        {
            _playerRigidBody.AddForce(throttle * transform.forward * movementRate);
        }

        if (_playerRigidBody.angularVelocity.magnitude < maxTurn)
        {
            _playerRigidBody.AddTorque(new Vector3(0, steering * steeringRate, 0f));
        }
    }

    private void CompleteEpisodeAndResetGame(
        Falken.Episode.CompletionState episodeState)
    {
        if (_session != null)
        {
            _episode.Complete(episodeState);
            if (_numEpisodesRequested != 0)
            {
                _numEpisodesRemaining--;
                // Stop the game if a certain number of episodes were requested
                // through command line and we have fulfilled them.
                if (_numEpisodesRemaining <= 0)
                {
                    OnDisable();
#if UNITY_EDITOR
                    UnityEditor.EditorApplication.isPlaying = false;
#else
                    Application.Quit();
#endif
                    return;
                }
            }
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
        } while (_lastDistance < goalDistance);

        if (_playerRigidBody)
        {
            _playerRigidBody.velocity = new Vector3(0, 0, 0);
            _playerRigidBody.angularVelocity = new Vector3(0, 0, 0);
        }
    }

    public Vector3 GenerateRandomGroundPos(float angle, Vector3 extents)
    {
        Bounds groundBounds = groundPlane.GetComponent<Renderer>().bounds;
        float wallWidth = 0.4f;
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
}
