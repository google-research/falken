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

using System;
using UnityEngine;

/// <summary>
/// This class stores all the possible controls that the player can input.
/// </summary>
public struct Controls
{
    /// <summary>
    /// Constructor of the class.
    /// </summary>
    /// <param name="throttle">Current throttle of the control.</param>
    /// <param name="steering">Current steering of the control.</param>
    /// <param name="fire">whether player is firing or not.</param>
    public Controls(float throttle, float steering, bool fire)
    {
        Throttle = throttle;
        Steering = steering;
        Fire = fire;
    }

    /// <summary>
    /// Speed of the tank. Positive values represent a forward movement.
    /// </summary>
    public float Throttle
    {
        get; set;
    }

    /// <summary>
    /// Steering speed of the tank. Positive values will make robot turn tank.
    /// </summary>
    public float Steering
    {
        get;
        set;
    }

    /// <summary>
    /// If this is true, the tank should fire a bullet.
    /// </summary>
    public bool Fire
    {
        get; set;
    }

    /// <summary>
    /// Checks if there is no movement applied to the current instance.
    /// </summary>
    public bool MovementApplied
    {
        get
        {
            return Math.Abs(Throttle) >= _epsilon || Math.Abs(Steering) >= _epsilon || Fire;
        }
    }

    /// <summary>
    /// below this value throttle and steering will be considered 0.
    /// </summary>
    private const double _epsilon = 1e-20;
}

/// <summary>
/// Interface used to manage the input data from player.
/// </summary>
public abstract class JoystickBase : MonoBehaviour
{
    #region Protected and private attributes
    protected Controls _controls;
    #endregion

    #region Getters and Setters
    public Controls Controls
    {
        get
        {
            return _controls;
        }
    }
    #endregion

    #region Unity Callbacks
    /// <summary>
    /// Unity callbacks to be implemented in child class.
    /// </summary>
    public abstract void OnEnable();

    /// <summary>
    /// Unity callbacks to be implemented in child class.
    /// </summary>
    public abstract void FixedUpdate();
    #endregion
}
