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

﻿using UnityEngine;
using System.Collections;
using System;

public class ThirdPersonEntity : Falken.EntityBase
{
    public void UpdateFrom(GameObject gameObject)
    {
        position = gameObject.transform.position;
        rotation = gameObject.transform.rotation;
    }
}

public class ThirdPersonObservations : Falken.ObservationsBase
{
    public ThirdPersonEntity camera;
    public ThirdPersonEntity goal;
    public ThirdPersonObservations()
    {
        camera = new ThirdPersonEntity();
        player = new ThirdPersonEntity();
        goal = new ThirdPersonEntity();
    }

    public void UpdateFrom(GameObject player, GameObject camera, GameObject goal)
    {
        ((ThirdPersonEntity)this.player).UpdateFrom(player);
        this.camera.UpdateFrom(camera);
        this.goal.UpdateFrom(goal);
    }
}

public class ThirdPersonActions : Falken.ActionsBase
{
    public Falken.Joystick joy_axis1;
    public Falken.Joystick joy_axis2;

    public ThirdPersonActions(ControlType controlType)
    {
        switch (controlType)
        {
            case ControlType.Camera:
            case ControlType.Flight:
            case ControlType.AutoFlight:
                joy_axis1 = new Falken.Joystick(
                    "joy_axis1", Falken.AxesMode.DirectionXZ,
                    Falken.ControlledEntity.Player, Falken.ControlFrame.Camera);
                break;

            case ControlType.Player:
                joy_axis1 = new Falken.Joystick(
                    "joy_axis1", Falken.AxesMode.DeltaPitchYaw,
                    Falken.ControlledEntity.Player, Falken.ControlFrame.World);
                break;
            case ControlType.World:
                joy_axis1 = new Falken.Joystick(
                    "joy_axis1", Falken.AxesMode.DirectionXZ,
                    Falken.ControlledEntity.Player, Falken.ControlFrame.World);
                break;
            default:
                Debug.Log("Unsupported action type");
                break;
        }
        joy_axis2 = new Falken.Joystick(
             "joy_axis2", Falken.AxesMode.DeltaPitchYaw,
              Falken.ControlledEntity.Camera, Falken.ControlFrame.World);
    }
}

public class CameraRelativeActions : ThirdPersonActions
{
    public CameraRelativeActions() : base(ControlType.Camera) { }
}

public class PlayerRelativeActions : ThirdPersonActions
{
    public PlayerRelativeActions() : base(ControlType.Player) { }
}

public class WorldRelativeActions : ThirdPersonActions
{
    public WorldRelativeActions() : base(ControlType.World) { }
}

// Handles Flight and Autoflight mode.
public class FlightActions : ThirdPersonActions
{
    public FlightActions() : base(ControlType.Flight) { }
}

public class CameraRelativeBrainSpec :
    Falken.BrainSpec<ThirdPersonObservations, CameraRelativeActions> { }

public class PlayerRelativeBrainSpec :
    Falken.BrainSpec<ThirdPersonObservations, PlayerRelativeActions> { }

public class WorldRelativeBrainSpec :
    Falken.BrainSpec<ThirdPersonObservations, WorldRelativeActions> { }

public class FlightBrainSpec :
    Falken.BrainSpec<ThirdPersonObservations, FlightActions> { }

public class ThirdPersonPlayer : InputController
{
    public InputController playerInput;
    public GameLogic gameLogic;
    public bool falkenControlled = false;
    public uint maxNumSteps = 500;
    public ThirdPersonController thirdPersonController;

    public GameObject thirdPersonCamera;

    public const string BrainDisplayName = "ThirdPersonBrain";

    Falken.Service _service;
    Falken.BrainBase _brain;
    Falken.Session _session;
    Falken.Episode _episode;


    ThirdPersonActions _actions;
    ThirdPersonObservations _observations;

    private uint _steps = 0;

    // Use this for initialization
    void Start()
    {
        if (_service == null)
        {
            _service = Falken.Service.Connect();
            if (_service == null)
            {
                throw new System.Exception(
                    "Failed to connect to falken service.");
            }
            Debug.Log("Connected to falken service.");
        }

        switch (thirdPersonController.controlType)
        {
            case ControlType.Camera:
                {
                    var b = _service.CreateBrain<CameraRelativeBrainSpec>(BrainDisplayName);
                    _actions = b.BrainSpec.Actions;
                    _observations = b.BrainSpec.Observations;
                    _brain = b;
                    break;
                }
            case ControlType.Player:
                {
                    var b = _service.CreateBrain<PlayerRelativeBrainSpec>(BrainDisplayName);
                    _actions = b.BrainSpec.Actions;
                    _observations = b.BrainSpec.Observations;
                    _brain = b;
                    break;
                }
            case ControlType.World:
                {
                    var b = _service.CreateBrain<WorldRelativeBrainSpec>(BrainDisplayName);
                    _actions = b.BrainSpec.Actions;
                    _observations = b.BrainSpec.Observations;
                    _brain = b;
                    break;
                }
            case ControlType.Flight:
            case ControlType.AutoFlight:
                {
                    var b = _service.CreateBrain<FlightBrainSpec>(BrainDisplayName);
                    _actions = b.BrainSpec.Actions;
                    _observations = b.BrainSpec.Observations;
                    _brain = b;
                    break;
                }
            default:
                Debug.Log("Unsupported control type");
                break;
        }
        _session = _brain.StartSession(
            Falken.Session.Type.InteractiveTraining, maxNumSteps);

        gameLogic.notifyGoalReached += HandleGoalReachedEvent;
    }

    public void HandleGoalReachedEvent()
    {
        if(_episode != null)
        {
            Debug.Log("Reached goal. Ending episode with success.");
            _episode.Complete(Falken.Episode.CompletionState.Success);
        }
    }

    public void FixedUpdate()
    {
        if (_session == null)
        {
            return;
        }

        if (_episode != null && _steps + 1 == maxNumSteps)
        {
            Debug.Log("Failed to reach goal. Ending episode.");
            _episode.Complete(Falken.Episode.CompletionState.Failure);
            _steps = 0;
        }

        if(_episode == null|| _episode.Completed)
        {
            Debug.Log("Starting new episode");
            _episode = _session.StartEpisode();
            gameLogic.Reset();
            thirdPersonController.Reset();
            _steps = 0;
        }

        _observations.UpdateFrom(
            gameLogic.player.gameObject,
            thirdPersonCamera, gameLogic.goal);

        if (falkenControlled)
        {
            // Trigger falken action inference.
            _actions.ActionsSource = Falken.ActionsBase.Source.None;
        }

        SampleInput();
        _steps++;
        _episode.Step();
    }

    // Update is called once per frame.
    void Update()
    {
        if (Input.GetKeyDown(KeyCode.T))
        {
            falkenControlled = !falkenControlled;
        }
    }

    // Sample player input.
    public void SampleInput()
    {
        if (!falkenControlled)
        {

            Vector2 axis1 = playerInput.GetAxis1();
            _actions.joy_axis1.X = axis1.x;
            _actions.joy_axis1.Y = axis1.y;

            Vector2 axis2 = playerInput.GetAxis2();
            _actions.joy_axis2.X = axis2.x;
            _actions.joy_axis2.Y = axis2.y;
        }
    }

    public override Vector2 GetAxis1() {
        if (_actions == null)
        {
            return playerInput.GetAxis1();
        }


        return new Vector2(
            _actions.joy_axis1.X,
            _actions.joy_axis1.Y);
    }

    public override Vector2 GetAxis2() {
        if (_actions == null)
        {
            return playerInput.GetAxis2();
        }

        return new Vector2(
            _actions.joy_axis2.X,
            _actions.joy_axis2.Y);
    }

    void OnGUI()
    {
        GUI.Label(
            new Rect(10, 60, 300, 50),
            "Falken controlled: " + falkenControlled);
    }
}
