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

using UnityEngine;
using UnityEngine.UI;
using System;
using System.Collections;

public abstract class Player : MonoBehaviour
{
    #region Editor variables
    public Arena arena;
    public float movementRate = 5.0f;
    public float steeringRate = 0.15f;
    public float drag = 2f;
    public float angularDrag = 5f;

    [Range(0.0f, 5.0f)]
    public float maxSpeed = 5f;

    [Range(0.0f, 5.0f)]
    public float maxTurn = 5f;

    // Controls
    public VirtualJoystick joystick;
    public Bullet bullet;
    public float recoil = 2f;
    public float cooldown = 0.5f;
    public float maxHealth = 100.0f;
    public Slider healthSlider;
    #endregion

    #region Protected and private attributes
    protected Rigidbody _rBody;
    protected float _boostedUntil = -1;
    protected float _currentHealth;
    private float _lastFired = float.MinValue;
    private Blinker _blinker;
    #endregion

    #region Getters and Setters
    /// <summary>
    /// Boosted property of player.
    /// </summary>
    public bool Boosted
    {
        get
        {
            return _boostedUntil > Time.fixedTime;
        }
    }

    /// <summary>
    /// This property lets you know if the current player is wether alive or not.
    /// </summary>
    public bool Alive
    {
        get
        {
            return _currentHealth > 0.0f;
        }
    }
    #endregion

    #region Unity Callbacks
    public virtual void OnEnable()
    {
        _rBody = gameObject.GetComponent<Rigidbody>();
        _currentHealth = maxHealth;
        if (!_rBody)
        {
            Debug.LogWarning("Player does not have rigidbody component and won't be moved.");
        }
        if (healthSlider != null)
        {
            healthSlider.minValue = 0;
            healthSlider.maxValue = maxHealth;
        }
        _blinker = GetComponent<Blinker>();
        Reset();
    }

    public virtual void FixedUpdate()
    {
        // Update the currerennt status of the player.
        Controls movement = CalculateActions();
        ApplySteeringForces(movement);
        UpdateBlinking();

        // Kill the player if not alive.
        if (!Alive)
        {
            Die();
        }

        UpdateHealth();
    }
    #endregion

    #region Player overrides
    /// <summary>
    /// Reset the current player to its original status
    /// </summary>
    public void Reset()
    {
        _lastFired = float.MinValue;

        // Restore life
        _currentHealth = maxHealth;
    }

    protected virtual Controls CalculateActions()
    {
        // If no joystick was provided, return no control.
        if (joystick == null)
        {
            return new Controls();
        }

        return joystick.Controls;
    }
    #endregion

    #region Helper Objects
    public void Boost(float duration)
    {
        _boostedUntil = Time.fixedTime + duration;
    }

    /// <summary>
    /// Fires a bullet and takes damage if hits somebody.
    /// </summary>
    public void Fire()
    {
        if (Time.fixedTime - _lastFired < cooldown)
        {
            return;
        }

        _lastFired = Time.fixedTime;
        var b = Instantiate(bullet);
        if (Boosted)
        {
            b.damage *= 4;
        }
        b.transform.position = transform.position + transform.forward * 0.2f;
        b.transform.forward = transform.forward;
        b.firedBy = gameObject;
        if (_rBody)
        {
            _rBody.AddForce(-recoil * transform.forward);
        }
    }

    /// <summary>
    /// Move the current player
    /// </summary>
    /// <param name="actions"> direction in which the player should move.</param>
    public void ApplySteeringForces(Controls actions)
    {
        // If no body was set return.
        if (!_rBody)
        {
            return;
        }

        // You cannot move if you are not alive.
        if (!Alive)
        {
            return;
        }

        _rBody.maxAngularVelocity = maxTurn;
        _rBody.angularDrag = angularDrag;
        _rBody.drag = drag;

        // Going backwards is slower.
        if (actions.Throttle < 0)
        {
            actions.Throttle *= 0.5f;
        }
        if (_rBody.velocity.magnitude < maxSpeed)
        {
            _rBody.AddForce(actions.Throttle * transform.forward * movementRate);
        }
        if (_rBody.angularVelocity.magnitude < maxTurn)
        {
            _rBody.AddTorque(new Vector3(0, actions.Steering * steeringRate, 0.0f));
        }

        if (actions.Fire)
        {
            Fire();
        }
    }

    /// <summary>
    /// Update current life of the player when gets damaged.
    /// </summary>
    public void TakeDamage(float damage)
    {
        _currentHealth = Math.Max(_currentHealth - damage, 0.0f);
    }

    /// <summary>
    /// Check if the player should blink.
    /// </summary>
    public void UpdateBlinking()
    {
        if (_blinker != null)
        {
            _blinker.enabled = Boosted;
        }

    }

    /// <summary>
    /// Update the healthslider.
    /// </summary>
    public void UpdateHealth()
    {
        if (healthSlider != null)
        {
            healthSlider.value = _currentHealth;
        }
    }

    /// <summary>
    /// Hides the current player.
    /// </summary>
    protected void Die()
    {
        // Hide current player
        MeshRenderer renderer = gameObject.GetComponentInChildren<MeshRenderer>();
        renderer.enabled = false;
    }

    /// <summary>
    /// Restore MirrorPlayer initial state.
    /// </summary>
    public void Respawn()
    {
        // Show current player
        MeshRenderer renderer = gameObject.GetComponentInChildren<MeshRenderer>();
        renderer.enabled = true;

        // Get the bounds of the current player.
        Vector3 playerExtents = gameObject.GetComponent<Collider>().bounds.extents;
        // Generate random angle to spawn.
        float randomAngle = UnityEngine.Random.Range(0f, 360f);
        // Start player from a random position
        var randomPos = arena.GenerateRandomGroundPos(this, randomAngle);
        transform.SetPositionAndRotation(randomPos, Quaternion.AngleAxis(randomAngle, Vector3.up));

        // The player should not move when starting.
        if (_rBody)
        {
            _rBody.velocity = new Vector3(0, 0, 0);
            _rBody.angularVelocity = new Vector3(0, 0, 0);
        }
        _boostedUntil = -1;
    }

    #endregion
}
