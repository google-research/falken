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

using System.Collections;
using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// <c>CarCamera</c> Chase camera controller designed to follow a moving vehicle.
/// </summary>
[RequireComponent(typeof(Camera))]
public class CarCamera : MonoBehaviour {
    [Tooltip("The RigidBody of the vehicle that this camera should follow.")]
    public Rigidbody target;
    [Tooltip("The position the camera should look at, relative to the target's position.")]
    public Vector3 targetOffset;

    [Tooltip("Ideal distance at which to follow the target vehicle.")]
    public float distance = 20f;
    [Tooltip("Speed with which to move from current distance to desired distance.")]
    public float distanceSnapTime;
    [Tooltip("Allows the camera to zoom in and out based on car's speed.")]
    public float distanceMultiplier;

    [Tooltip("Ideal follow height above the target car.")]
    public float height = 5f;
    [Tooltip("Speed with which to move from current height to desired height.")]
    public float heightDamping = 2f;

    [Tooltip("Speed with which to move from current yaw to target's yaw.")]
    public float rotationSnapTime;

    private Vector3 smoothTarget;
    private Vector3 smoothTargetVelocity;
    private float cameraDistance;
    private float rotationVelocity = 0f;
    private float distanceVelocity = 0f;

    void Start() {
        transform.position = target.transform.position +
            target.transform.forward * -distance +
            new Vector3(0, height, 0);
        transform.LookAt(target.transform.position + targetOffset);
        smoothTarget = transform.position;
    }

    void LateUpdate() {
        Vector3 cameraPosition = target.transform.position;
        cameraPosition.y = Mathf.Lerp(transform.position.y, target.position.y + height,
            heightDamping * Time.deltaTime);

        float distanceScale = target.velocity.magnitude * distanceMultiplier;
        cameraDistance = Mathf.SmoothDamp(cameraDistance, distance + distanceScale,
            ref distanceVelocity, distanceSnapTime);

        float cameraRotation = Mathf.SmoothDampAngle(transform.eulerAngles.y,
            target.transform.eulerAngles.y, ref rotationVelocity, rotationSnapTime);

        Vector3 distanceOffset = new Vector3(0f, 0f, -cameraDistance);
        cameraPosition += Quaternion.Euler(0f, cameraRotation, 0f) * distanceOffset;

        transform.position = cameraPosition;
        transform.LookAt(target.position + targetOffset);
    }
}
