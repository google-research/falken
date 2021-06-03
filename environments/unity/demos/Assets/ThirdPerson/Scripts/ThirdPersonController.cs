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
using UnityEngine;

public enum ControlType
{
    // Move the player directionally in the world XZ plane.
    World = 1,
    // Tank controls, turn left/right, go forward back.
    Player = 2,
    // Move the player directionally relative to the camera along the XZ plane.
    Camera = 3,
    // Move the player directionally relative to the camera, but match player
    // yaw to camera yaw.
    Flight = 4,
    // Fly but constantly move forward. Only camera control works.
    AutoFlight = 5,
}

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

public class ThirdPersonBrainSpec : Falken.BrainSpecBase
{
    public ThirdPersonBrainSpec() :
        base(new ThirdPersonActions(ControlType.Player), new ThirdPersonObservations()) {}

    public ThirdPersonBrainSpec(ControlType controlType) :
        base(new ThirdPersonActions(controlType), new ThirdPersonObservations()) {}

    public ThirdPersonActions Actions
    {
        get
        {
            return (ThirdPersonActions)ActionsBase;
        }
    }

    public ThirdPersonObservations Observations
    {
        get
        {
            return (ThirdPersonObservations)ObservationsBase;
        }
    }
}

public class CameraRelativeBrainSpec : ThirdPersonBrainSpec
{
    public CameraRelativeBrainSpec() : base(ControlType.Camera) {}
}

public class PlayerRelativeBrainSpec : ThirdPersonBrainSpec
{
    public PlayerRelativeBrainSpec() : base(ControlType.Player) {}
}

public class WorldRelativeBrainSpec : ThirdPersonBrainSpec
{
    public WorldRelativeBrainSpec() : base(ControlType.World) {}
}

public class FlightBrainSpec : ThirdPersonBrainSpec
{
    public FlightBrainSpec() : base(ControlType.Flight) {}
}


/// <summary>
/// <c>ThirdPersonController</c> Provides 3P input handling, player physics, and camera control.
/// </summary>
public class ThirdPersonController : MonoBehaviour
{
    [Tooltip("The camera object to control.")]
    public Camera thirdPersonCamera;
    [Tooltip("Determines the control scheme used by this player.")]
    public ControlType controlType;

    [Tooltip("Speed at which the player moves.")]
    public float playerForwardSpeed = 0.05f;
    [Tooltip("Speed at which the player rotates.")]
    public float playerRotateSpeed = 2f;
    [Tooltip("Speed at which the camera orbits.")]
    public float cameraYawPitchSpeed = 0.5f;
    [Tooltip("Offset from player object that the camera looks at.")]
    public Vector3 cameraLookOffset = Vector3.zero;
    [Tooltip("Whether the camera is locked to have no roll.")]
    public bool lockedCamera = true;

    private bool _falkenControlled;
    private GameObject _goal;
    private float _cameraDistanceFromTarget;
    private Vector2 _cameraYawPitch = new Vector2(0, 0);

    private const float angleEpsilon = 1e-2f;
    private readonly Vector2 _yAxis = new Vector2(0, 1);

    private const float magnitudeEpsilon = 1e-3f;

    private Falken.Episode _episode;
    private ThirdPersonActions _actions;
    private ThirdPersonObservations _observations;

    public GameObject Goal { set { _goal = value; } }

    public void SetActionsAndObservations(
        ThirdPersonActions actions, ThirdPersonObservations observations)
    {
        _actions = actions;
        _observations = observations;
    }

    public Falken.Episode FalkenEpisode { set { _episode = value; } }

    // Start is called before the first frame update
    public void Reset()
    {
        _cameraYawPitch.x = 0;
        if (controlType == ControlType.Flight || controlType == ControlType.AutoFlight)
        {
            _cameraYawPitch.y = 0;
        }
        else
        {
            _cameraYawPitch.y = 45;
        }

        PositionCamera();
    }

    #region Update player and camera based on input
    float GetDegreesRotation(Vector2 dir)
    {
        return Vector2.SignedAngle(dir, _yAxis);
    }

    void UpdateTargetWorldRelative(Vector2 dir)
    {
        if (dir.magnitude <= magnitudeEpsilon)
        {
            return;
        }
        float yawInDegrees = GetDegreesRotation(dir);
        transform.rotation = Quaternion.Euler(new Vector3(0, yawInDegrees, 0));
        transform.position += transform.forward * playerForwardSpeed * dir.magnitude;
    }

    void UpdateTargetPlayerRelative(Vector2 dir)
    {
        if (dir.magnitude <= magnitudeEpsilon)
        {
            return;
        }
        transform.rotation *= Quaternion.Euler(0, playerRotateSpeed * dir.x, 0);
        transform.position += transform.forward * playerForwardSpeed * dir.y;
    }

    void UpdateTargetCameraRelativeFlight(Vector2 dir)
    {
        if (dir.magnitude <= magnitudeEpsilon)
        {
            return;
        }
        Vector3 dir3d = new Vector3(dir.x, 0, dir.y);
        Vector3 target = thirdPersonCamera.transform.TransformDirection(dir3d);
        RotateTowardsTargetDir(target, thirdPersonCamera.transform.up);
        transform.position += transform.forward * playerForwardSpeed * dir.magnitude;
    }

    void UpdateTargetCameraRelativeAutoFlight()
    {
        RotateTowardsTargetDir(thirdPersonCamera.transform.forward, thirdPersonCamera.transform.up);
        transform.position += transform.forward * playerForwardSpeed;
    }

    void UpdateTargetCameraRelative(Vector2 dir)
    {
        // Note that the pitch of the camera is being ignored.

        // Draw debug planes.
        const float rayLength = 20f;
        for (int i = -20; i < 20; i++)
        {
            // Hint at camera YZ plane.
            Debug.DrawRay(
                thirdPersonCamera.transform.position +
                i * 0.1f * thirdPersonCamera.transform.up -
                thirdPersonCamera.transform.forward * rayLength / 2,
                thirdPersonCamera.transform.forward * rayLength,
                Color.white);

            // Hint at player XZ plane.
            Debug.DrawRay(
                transform.position + new Vector3(0, 0.1f, 0) +
                i * 0.1f * transform.right -
                transform.forward * rayLength / 2,
                transform.forward * rayLength,
                Color.green);
        }

        Vector3 cameraYZIntersectPlayerXZ = Vector3.Cross(
            thirdPersonCamera.transform.right,
            transform.up).normalized;

        float cameraRelativeHeading = GetDegreesRotation(dir);

        Vector3 target =
            Quaternion.AngleAxis(cameraRelativeHeading, transform.up) *
            cameraYZIntersectPlayerXZ;

        Vector3 cameraTarget =
            Quaternion.AngleAxis(
                -cameraRelativeHeading,
                thirdPersonCamera.transform.forward) *
            thirdPersonCamera.transform.up;

        Debug.DrawRay(
            transform.position, target * rayLength,
            Color.red);

        Debug.DrawRay(
            thirdPersonCamera.transform.position, cameraTarget * rayLength,
            Color.red);

        if (dir.magnitude == 0)
            return;

        RotateTowardsTargetDir(target, transform.up);
        transform.position += transform.forward * playerForwardSpeed * dir.magnitude;
    }

    void RotateTowardsTargetDir(Vector3 target, Vector3 up)
    {
        Quaternion lookAt = Quaternion.LookRotation(target, up);
        float angleToTarget = Quaternion.Angle(lookAt, transform.rotation);
        float amountToTurn = playerRotateSpeed / angleToTarget;
        transform.rotation = Quaternion.Lerp(transform.rotation, lookAt, amountToTurn);
    }

    void UpdateTarget(Vector2 moveInput)
    {
        switch (controlType)
        {
            case ControlType.World:
                UpdateTargetWorldRelative(moveInput);
                break;
            case ControlType.Player:
                UpdateTargetPlayerRelative(moveInput);
                break;
            case ControlType.Camera:
                UpdateTargetCameraRelative(moveInput);
                break;
            case ControlType.Flight:
                UpdateTargetCameraRelativeFlight(moveInput);
                break;
            case ControlType.AutoFlight:
                UpdateTargetCameraRelativeAutoFlight();
                break;
            default:
                throw new UnityException("Illegal value.");
        }
    }

    // Update the camera location.
    void UpdateCamera(Vector2 yawPitchInput)
    {
        Vector2 delta = yawPitchInput * cameraYawPitchSpeed;
        _cameraYawPitch += delta;

        _cameraYawPitch.x %= 360;
        if (lockedCamera)
        {
            // Clamp pitch to a half-space.
            _cameraYawPitch.y = Mathf.Clamp(
                _cameraYawPitch.y,
                -90f + angleEpsilon, 90f - angleEpsilon);
        }
        PositionCamera();
    }

    // Position the camerate to a given yaw and pitch around the target.
    void PositionCamera()
    {
        Vector3 playerToCamera = Vector3.back;
        playerToCamera = Quaternion.Euler(_cameraYawPitch.y, _cameraYawPitch.x, 0) * playerToCamera;

        Vector3 offset = playerToCamera * _cameraDistanceFromTarget;

        thirdPersonCamera.transform.position = transform.position + offset;

        if (lockedCamera)
        {
            thirdPersonCamera.transform.LookAt(
                transform.position + transform.rotation * cameraLookOffset);
        }
        else
        {
            thirdPersonCamera.transform.LookAt(transform, thirdPersonCamera.transform.up);
        }
    }
    #endregion

    #region Unity functions
    void OnEnable() {
        _cameraDistanceFromTarget = Vector3.Distance(
            thirdPersonCamera.transform.position,
            transform.position);
    }

    // Update is called once per frame
    void FixedUpdate()
    {
        if (Input.GetButtonDown("ToggleControl"))
        {
            _falkenControlled = !_falkenControlled;
        }

        Vector2 moveInput = new Vector2(Input.GetAxis("MoveX"), Input.GetAxis("MoveY")).normalized;
        Vector2 lookInput = new Vector2(Input.GetAxis("LookX"), Input.GetAxis("LookY")).normalized;

        if (_episode != null && !_episode.Completed)
        {
            _observations.UpdateFrom(gameObject, thirdPersonCamera.gameObject, _goal);

            if (!_falkenControlled)
            {
                _actions.joy_axis1.X = moveInput.x;
                _actions.joy_axis1.Y = moveInput.y;
                _actions.joy_axis2.X = lookInput.x;
                _actions.joy_axis2.Y = lookInput.y;
                _actions.ActionsSource = Falken.ActionsBase.Source.HumanDemonstration;
            }
            else
            {
                _actions.ActionsSource = Falken.ActionsBase.Source.BrainAction;
            }

            _episode.Step();

            if (_falkenControlled)
            {
                moveInput.x = _actions.joy_axis1.X;
                moveInput.y = _actions.joy_axis1.Y;
                lookInput.x = _actions.joy_axis2.X;
                lookInput.y = _actions.joy_axis2.Y;
            }
        }

        UpdateTarget(moveInput);
        UpdateCamera(lookInput);
    }

    void OnGUI()
    {
        GUI.Label(new Rect(10, 10, 300, 50), "Control_type: " + controlType.ToString());

        // Intersect camera YZ plane with target movement plane.
        Vector3 cameraInTargetPlane = Vector3.Cross(
            thirdPersonCamera.transform.right,
            transform.up);

        float angle = Vector3.SignedAngle(cameraInTargetPlane, transform.forward, transform.up);

        GUIStyle style = new GUIStyle(GUI.skin.label);
        style.normal.textColor = Color.red;
        style.fontSize = 50;
        style.alignment = TextAnchor.MiddleCenter;
        Rect indicatorRect = new Rect(30, 60, 50, 50);

        GUIUtility.RotateAroundPivot(angle, indicatorRect.center);
        GUI.Label(indicatorRect, "\u2191", style);  // arrow up

         GUI.Label(new Rect(10, 60, 300, 50), "Falken controlled: " + _falkenControlled);
    }
    #endregion
}
