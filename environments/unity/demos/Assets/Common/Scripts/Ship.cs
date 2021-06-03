using System.Collections;
using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// <c>Ship</c> Implements an asteroids-style ship w/ basic physics.
/// </summary>
[RequireComponent(typeof(Rigidbody))]
public class Ship : MonoBehaviour
{
    [Tooltip("Maximum amount of force to apply when accelerating.")]
    [Range(0, 10)]
    public float movementRate = 10f;
    [Tooltip("Maximum amount of torque to apply when steering.")]
    [Range(0, 10)]
    public float steeringRate = 10f;
    [Tooltip("Maximum linear speed for this player.")]
    [Range(0, 10)]
    public float maxSpeed = 5f;
    [Tooltip("Maximum angular speed for this player.")]
    [Range(0, 10)]
    public float maxTurn = 5f;

    private Rigidbody _rigidBody;

    /// <summary>
    /// Applies throttle and steering as forces onto the ship's RigidBody.
    /// </summary>
    public void ApplyActions(float throttle, float steering)
    {
        if (_rigidBody.velocity.magnitude < maxSpeed)
        {
            _rigidBody.AddForce(throttle * transform.forward * movementRate);
        }

        if (_rigidBody.angularVelocity.magnitude < maxTurn)
        {
            _rigidBody.AddTorque(new Vector3(0, steering * steeringRate, 0f));
        }
    }

    /// <summary>
    /// Applies a recoil force onto the ship's RigidBody.
    /// </summary>
    public void ApplyRecoil(float recoil)
    {
        _rigidBody.AddForce(-recoil * transform.forward);
    }

    /// <summary>
    /// Stops the ship from moving or turning.
    /// </summary>
    public void Stop()
    {
        _rigidBody.velocity = new Vector3(0, 0, 0);
        _rigidBody.angularVelocity = new Vector3(0, 0, 0);
    }

    void OnEnable()
    {
        _rigidBody = gameObject.GetComponent<Rigidbody>();
        _rigidBody.maxAngularVelocity = maxTurn;
    }
}
