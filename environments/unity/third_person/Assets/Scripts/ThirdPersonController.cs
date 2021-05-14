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


public class ThirdPersonController : MonoBehaviour
{
    public GameObject player;
    public GameObject thirdPersonCamera;
    public ControlType controlType;

    public InputController inputController;

    public float cameraYawPitchSpeed = 0.5f;
    public float playerRotateSpeed = 2f;
    public float playerForwardSpeed = 0.05f;

    public float rayLength = 20f;
    // Whether the camera is locked to have no roll
    public bool lockedCamera = true;

    private float _cameraDistanceFromTarget;
    private Vector2 _cameraYawPitch = new Vector2(0, 0);

    private const float angleEpsilon = 1e-2f;
    private readonly Vector2 _yAxis = new Vector2(0, 1);

    private const float magnitudeEpsilon = 1e-3f;

    #region Input handling
    // Returns numpad / WASD direction as a vector.
    Vector2 GetMovementInput()
    {
        return inputController.GetAxis1();
    }

    // Returns keyboard yaw / pitch input (QEXZ).
    Vector2 GetYawPitchInput()
    {
        return inputController.GetAxis2();
    }
    #endregion Input

    float GetDegreesRotation(Vector2 dir)
    {
        return Vector2.SignedAngle(dir, _yAxis);
    }

    #region Update player based on input
    void UpdateTargetWorldRelative(Vector2 dir)
    {
        if (dir.magnitude <= magnitudeEpsilon)
            return;
        float yawInDegrees = GetDegreesRotation(dir);
        player.transform.rotation = Quaternion.Euler(
            new Vector3(0, yawInDegrees, 0));
        player.transform.position +=
            player.transform.forward * playerForwardSpeed * dir.magnitude;
    }

    void UpdateTargetPlayerRelative(Vector2 dir)
    {
        if (dir.magnitude <= magnitudeEpsilon)
            return;
        player.transform.rotation *= Quaternion.Euler(
            0, playerRotateSpeed * dir.x, 0);
        player.transform.position +=
            player.transform.forward * playerForwardSpeed * dir.y;
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
        player.transform.position +=
            player.transform.forward * playerForwardSpeed * dir.magnitude;
    }

    void UpdateTargetCameraRelativeAutoFlight()
    {
        RotateTowardsTargetDir(thirdPersonCamera.transform.forward,
            thirdPersonCamera.transform.up);
        player.transform.position +=
            player.transform.forward * playerForwardSpeed;
    }


    void UpdateTargetCameraRelative(Vector2 dir)
    {
        // Note that the pitch of the camera is being ignored.

        // Draw debug planes.
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
                player.transform.position + new Vector3(0, 0.1f, 0) +
                i * 0.1f * player.transform.right -
                player.transform.forward * rayLength / 2,
                player.transform.forward * rayLength,
                Color.green);
        }

        Vector3 cameraYZIntersectPlayerXZ = Vector3.Cross(
            thirdPersonCamera.transform.right,
            player.transform.up).normalized;

        float cameraRelativeHeading = GetDegreesRotation(dir);

        Vector3 target =
            Quaternion.AngleAxis(cameraRelativeHeading, player.transform.up) *
            cameraYZIntersectPlayerXZ;

        Vector3 cameraTarget =
            Quaternion.AngleAxis(
                -cameraRelativeHeading,
                thirdPersonCamera.transform.forward) *
            thirdPersonCamera.transform.up;

        Debug.DrawRay(
            player.transform.position, target * rayLength,
            Color.red);

        Debug.DrawRay(
            thirdPersonCamera.transform.position, cameraTarget * rayLength,
            Color.red);

        if (dir.magnitude == 0)
            return;

        RotateTowardsTargetDir(target, player.transform.up);

        player.transform.position +=
           player.transform.forward * playerForwardSpeed * dir.magnitude;
    }

    void RotateTowardsTargetDir(Vector3 target, Vector3 up)
    {
        Quaternion lookAt = Quaternion.LookRotation(
        target, up);

        float angleToTarget = Quaternion.Angle(
            lookAt, player.transform.rotation);

        float amountToTurn = playerRotateSpeed / angleToTarget;

        player.transform.rotation = Quaternion.Lerp(
            player.transform.rotation, lookAt, amountToTurn);
    }

    void UpdateTarget()
    {
        Vector2 dir = GetMovementInput();
        switch (controlType)
        {
            case ControlType.World:
                UpdateTargetWorldRelative(dir);
                break;
            case ControlType.Player:
                UpdateTargetPlayerRelative(dir);
                break;
            case ControlType.Camera:
                UpdateTargetCameraRelative(dir);
                break;
            case ControlType.Flight:
                UpdateTargetCameraRelativeFlight(dir);
                break;
            case ControlType.AutoFlight:
                UpdateTargetCameraRelativeAutoFlight();
                break;
            default:
                throw new UnityException("Illegal value.");
        }
    }
    #endregion
    // Update the camera location.
    void UpdateCamera()
    {
        Vector2 delta = GetYawPitchInput() * cameraYawPitchSpeed;
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
        playerToCamera = Quaternion.Euler(
            _cameraYawPitch.y, _cameraYawPitch.x, 0) * playerToCamera;

        Vector3 offset = playerToCamera * _cameraDistanceFromTarget;

        thirdPersonCamera.transform.position =
            player.transform.position + offset;

        if (lockedCamera)
        {
            thirdPersonCamera.transform.LookAt(
                player.transform.position);
        }
        else
        {
            thirdPersonCamera.transform.LookAt(
                player.transform,
                thirdPersonCamera.transform.up);
        }
    }

    #region Unity functions
    // Start is called before the first frame update
    public void Reset()
    {
  
        _cameraYawPitch.x = 0;
        if (controlType == ControlType.Flight ||
            controlType == ControlType.AutoFlight)
        {
            _cameraYawPitch.y = 0;
        } else
        {
            _cameraYawPitch.y = 45;
        }
        
        PositionCamera();
    }

    void Start()
    {
        _cameraDistanceFromTarget = Vector3.Distance(
            thirdPersonCamera.transform.position,
            player.transform.position);
        Reset();
    }

    // Update is called once per frame
    void Update()
    {
        UpdateTarget();
        UpdateCamera();
    }

    void OnGUI()
    {
        GUI.Label(new Rect(10, 10, 300, 50),
            "WASD to move, QEXZ camera controls\ncontrol_type: " +
            controlType.ToString());

        // Intersect camera YZ plane with target movement plane.
        Vector3 cameraInTargetPlane = Vector3.Cross(
            thirdPersonCamera.transform.right,
            player.transform.up);

        float angle = Vector3.SignedAngle(
            cameraInTargetPlane,
            player.transform.forward,
            player.transform.up);

        GUIStyle style = new GUIStyle(GUI.skin.label);
        style.normal.textColor = Color.red;
        style.fontSize = 50;
        style.alignment = TextAnchor.MiddleCenter;
        Rect indicatorRect = new Rect(30, 60, 50, 50);

        GUIUtility.RotateAroundPivot(angle, indicatorRect.center);
        GUI.Label(indicatorRect, "\u2191", style);  // arrow up
    }
    #endregion
}
