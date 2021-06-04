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
using System.Collections.Generic;

/// <summary>
/// Reflects Observations to/from the Falken service.
/// </summary>
public class CartPlayerEntity : Falken.EntityBase
{
    public Falken.Number velocity = new Falken.Number(-20.0f, 50.0f);
    public Falken.Number angleToNextTrackSegment =
        new Falken.Number(-180.0f, 180.0f);
    public Falken.Feelers feelers = new Falken.Feelers(
        15.0f, 0.0f, 90.0f, 14, null);
    public Falken.Boolean wrongDirection = new Falken.Boolean();
}

/// <summary>
/// Falken Observations for the game.
/// </summary>
public class CartObservations : Falken.ObservationsBase
{
    public CartObservations()
    {
        player = new CartPlayerEntity();
    }
}

/// <summary>
/// Reflects actions to/from the Falken service.
/// </summary>
public class CartActions : Falken.ActionsBase
{
    public Falken.Number steering = new Falken.Number(-1.0f, 1.0f);
    public Falken.Number throttle = new Falken.Number(-1.0f, 1.0f);
    public Falken.Number handbrake = new Falken.Number(0.0f, 1.0f);
}

public class CartBrainSpec : Falken.BrainSpec<CartObservations, CartActions>
{
}

/// <summary>
/// <c>CartPlayer</c> Transforms player input into lower level physical vehicle controls.
/// </summary>
public class CartPlayer : MonoBehaviour {
    [System.Serializable]
    public class AxleInfo {
        [Tooltip("Reference to the axle's left WheelCollider.")]
        public WheelCollider leftWheel;
        [Tooltip("Reference to the axle's right WheelCollider.")]
        public WheelCollider rightWheel;
        [Tooltip("Determines whether the wheels on this axle are powered.")]
        public bool motor;
        [Tooltip("Determines whether the wheels on this axle steer.")]
        public bool steering;
    }

    [Tooltip("List of axles for this vehicle. Maximum is 12.")]
    public List<AxleInfo> axleInfos;
    [Tooltip("Maximum amount of force for wheels to apply when pressing the gas pedal.")]
    [Range(0, 5000)]
    public float maxMotorTorque;
    [Tooltip("Maximum amount of force for brakes to apply when pressing the handbrake.")]
    [Range(0, 5000)]
    public float maxBrakeTorque;
    [Tooltip("Maximum deflection of any steering-enabled wheels.")]
    [Range(0, 90)]
    public float maxSteeringAngle;

    CartBrainSpec _brainSpec = null;
    private Falken.Episode _episode = null;
    private bool _autopilot = false;
    private bool _stepSucceeded = true;

    /// <summary>
    /// Sets Falken brain spec.
    /// </summary>
    public CartBrainSpec FalkenBrainSpec
    {
        set
        {
            _brainSpec = value;
        }
    }

    /// <summary>
    /// Sets Falken episode.
    /// </summary>
    public Falken.Episode FalkenEpisode
    {
        set
        {
            _episode = value;
        }
    }

    /// <summary>
    /// Gets episode step result.
    /// </summary>
    public bool StepSucceeded
    {
        get
        {
            return _stepSucceeded;
        }
    }

    void OnEnable() {
        foreach (AxleInfo axleInfo in axleInfos) {
            axleInfo.leftWheel.ConfigureVehicleSubsteps(10, 5, 5);
            axleInfo.rightWheel.ConfigureVehicleSubsteps(10, 5, 5);
        }
    }

    void FixedUpdate()
    {
        // Get human actions.
        float playerSteering = Input.GetAxis("Steering");
        float playerThrottle = Input.GetAxis("Gas") - Input.GetAxis("Brake");
        float playerHandbrake = Input.GetAxis("Handbrake");

        if (ConnectedToFalken)
        {
            // TODO(jballoffet): Add autopilot mode (Falken takes over).
            _autopilot = false;

            // Set brain spec.
            SetObservations();
            SetActions(playerSteering, playerThrottle, playerHandbrake);

            // Set actions origin.
            Actions.ActionsSource = _autopilot ?
                    Falken.ActionsBase.Source.BrainAction :
                    Falken.ActionsBase.Source.HumanDemonstration;

            _stepSucceeded = _episode.Step();

            // If the brain is at the wheel, override the actions with the
            // values returned by Step.
            if (Actions.ActionsSource == Falken.ActionsBase.Source.BrainAction)
            {
                playerSteering = Actions.steering.Value;
                playerThrottle = Actions.throttle.Value;
                playerHandbrake = Actions.handbrake.Value;
            }
        }

        Drive(playerSteering, playerThrottle, playerHandbrake);
    }

    /// <summary>
    /// Applies steering, throttle, and brake controls to the vehicle.
    /// <param name="steering">Controls the car direction, from -1 (left) to 1 (right).</param>
    /// <param name="throttle">Controls the car speed, from -1 (backwards) to 1 (forwards).</param>
    /// <param name="handbrake">The strength of the brakes, from 0 (none) to 1 (full).</param>
    /// </summary>
    private void Drive(float steering, float throttle, float handbrake) {
        float steeringAngle = maxSteeringAngle * steering;
        float motorTorque = maxMotorTorque * throttle;
        float brakeTorque = maxBrakeTorque * handbrake;

        foreach (AxleInfo axleInfo in axleInfos) {
            if (axleInfo.steering) {
                axleInfo.leftWheel.steerAngle = steeringAngle;
                axleInfo.rightWheel.steerAngle = steeringAngle;
            }
            if (axleInfo.motor) {
                axleInfo.leftWheel.motorTorque = motorTorque;
                axleInfo.rightWheel.motorTorque = motorTorque;
                axleInfo.leftWheel.brakeTorque = brakeTorque;
                axleInfo.rightWheel.brakeTorque = brakeTorque;
            }

            ApplyLocalPositionToVisuals(axleInfo.leftWheel);
            ApplyLocalPositionToVisuals(axleInfo.rightWheel);
        }
    }

    /// <summary>
    /// Updates wheel visuals to match physics properties.
    /// </summary>
    private void ApplyLocalPositionToVisuals(WheelCollider collider)
    {
        if (collider.transform.childCount > 0) {
            Transform visualWheel = collider.transform.GetChild(0);

            Vector3 position;
            Quaternion rotation;
            collider.GetWorldPose(out position, out rotation);

            visualWheel.transform.position = position;
            visualWheel.transform.rotation = rotation;
        }
    }

    private bool ConnectedToFalken
    {
        get
        {
            return _brainSpec != null && _episode != null;
        }
    }

    private CartObservations Observations
    {
        get
        {
            return _brainSpec.Observations;
        }
    }

    private CartActions Actions
    {
        get
        {
            return _brainSpec.Actions;
        }
    }

    /// <summary>
    /// Sets the observations.
    /// </summary>
    private void SetObservations()
    {
        Observations.player.position = transform.position;
        Observations.player.rotation = transform.rotation;
        // TODO(jballoffet): Compute correct values.
        CartPlayerEntity entity = (CartPlayerEntity)Observations.player;
        entity.velocity.Value = 1.0f;
        entity.angleToNextTrackSegment.Value = 2.0f;
        entity.wrongDirection.Value = false;
    }

    /// <summary>
    /// Sets the actions.
    /// </summary>
    private void SetActions(float steering, float throttle, float handbrake)
    {
        Actions.steering.Value = steering;
        Actions.throttle.Value = throttle;
        Actions.handbrake.Value = handbrake;
    }
}
