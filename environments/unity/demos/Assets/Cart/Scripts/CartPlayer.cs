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
    public Falken.Number velocity1D = new Falken.Number(-20.0f, 50.0f);
    public Falken.Feelers feelers = new Falken.Feelers(
        15.0f, 0.0f, 360.0f, 14, null);
}

/// <summary>
/// Falken Observations for the game.
/// </summary>
public class CartObservations : Falken.ObservationsBase
{
    public Falken.EntityBase nextTrackSegment = new Falken.EntityBase();

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
[RequireComponent(typeof(Rigidbody))]
public class CartPlayer : MonoBehaviour
{
    [System.Serializable]
    public class AxleInfo
    {
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
    private bool _humanControlled = true;
    private Transform _nextCheckpoint = null;
    private Rigidbody _rigidBody;

    /// <summary>
    /// Sets Falken brain spec.
    /// </summary>
    public CartBrainSpec FalkenBrainSpec { set { _brainSpec = value; } }

    /// <summary>
    /// Sets Falken episode.
    /// </summary>
    public Falken.Episode FalkenEpisode { set { _episode = value; } }

    /// <summary>
    /// Sets human vs Falken control.
    /// </summary>
    public bool HumanControlled { set { _humanControlled = value; } }

    /// <summary>
    /// Sets next checkpoint transform.
    /// </summary>
    public Transform NextCheckpoint { set { _nextCheckpoint = value; } }

    public void OnEnable()
    {
        _rigidBody = GetComponent<Rigidbody>();

        foreach (AxleInfo axleInfo in axleInfos)
        {
            axleInfo.leftWheel.ConfigureVehicleSubsteps(10, 5, 5);
            axleInfo.rightWheel.ConfigureVehicleSubsteps(10, 5, 5);
        }
    }

    public void FixedUpdate()
    {
        // Get human actions.
        float playerSteering = Input.GetAxis("Steering");
        float playerThrottle = Input.GetAxis("Gas") - Input.GetAxis("Brake");
        float playerHandbrake = Input.GetAxis("Handbrake");

        if (_brainSpec != null && _episode != null && !_episode.Completed)
        {
            // Set brain spec.
            SetObservations();
            SetActions(playerSteering, playerThrottle, playerHandbrake);

            _episode.Step();

            // If the brain is at the wheel, override the actions with the values returned by Step.
            if (!_humanControlled)
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
    private void Drive(float steering, float throttle, float handbrake)
    {
        float steeringAngle = maxSteeringAngle * steering;
        float motorTorque = maxMotorTorque * throttle;
        float brakeTorque = maxBrakeTorque * handbrake;

        foreach (AxleInfo axleInfo in axleInfos)
        {
            if (axleInfo.steering)
            {
                axleInfo.leftWheel.steerAngle = steeringAngle;
                axleInfo.rightWheel.steerAngle = steeringAngle;
            }
            if (axleInfo.motor)
            {
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
    /// <param name="collider">Wheel to update.</param>
    private void ApplyLocalPositionToVisuals(WheelCollider collider)
    {
        if (collider.transform.childCount > 0)
        {
            Transform visualWheel = collider.transform.GetChild(0);

            Vector3 position;
            Quaternion rotation;
            collider.GetWorldPose(out position, out rotation);

            visualWheel.transform.position = position;
            visualWheel.transform.rotation = rotation;
        }
    }

    /// <summary>
    /// Gets the brain observations.
    /// </summary>
    private CartObservations Observations { get { return _brainSpec.Observations; } }

    /// <summary>
    /// Gets the brain actions.
    /// </summary>
    private CartActions Actions { get { return _brainSpec.Actions; } }

    /// <summary>
    /// Sets the brain observations.
    /// </summary>
    private void SetObservations()
    {
        Observations.player.position = transform.position;
        Observations.player.rotation = transform.rotation;
        if (_nextCheckpoint != null)
        {
            Observations.nextTrackSegment.position = _nextCheckpoint.position;
            Observations.nextTrackSegment.rotation = _nextCheckpoint.rotation;
        }

        CartPlayerEntity entity = (CartPlayerEntity)Observations.player;
        float velocitySign = Mathf.Sign(
            Vector3.Dot(transform.forward, _rigidBody.velocity));
        entity.velocity1D.Value = _rigidBody.velocity.magnitude * velocitySign;

        entity.feelers.Update(transform, Vector3.zero, true);
    }

    /// <summary>
    /// Sets the brain actions.
    /// </summary>
    /// <param name="steering">Action that controls the car direction.</param>
    /// <param name="throttle">Action that controls the car speed.</param>
    /// <param name="handbrake">Action that controls the strength of the brakes.</param>
    private void SetActions(float steering, float throttle, float handbrake)
    {
        if (_humanControlled)
        {
            Actions.steering.Value = steering;
            Actions.throttle.Value = throttle;
            Actions.handbrake.Value = handbrake;
            Actions.ActionsSource = Falken.ActionsBase.Source.HumanDemonstration;
        }
        else
        {
            Actions.steering.Value = 0.0f;
            Actions.throttle.Value = 0.0f;
            Actions.handbrake.Value = 0.0f;
            Actions.ActionsSource = Falken.ActionsBase.Source.BrainAction;
        }
    }
}
