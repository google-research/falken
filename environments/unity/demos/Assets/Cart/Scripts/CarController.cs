using UnityEngine;
using System.Collections;
using System.Collections.Generic;

/// <summary>
/// <c>CarController</c> Transforms player input into lower level physical vehicle controls.
/// </summary>
public class CarController : MonoBehaviour {
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

    void FixedUpdate()
    {
        float playerSteering = Input.GetAxis("Steering");
        float playerThrottle = Input.GetAxis("Gas") - Input.GetAxis("Brake");
        float playerHandbrake = Input.GetAxis("Handbrake");
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
}