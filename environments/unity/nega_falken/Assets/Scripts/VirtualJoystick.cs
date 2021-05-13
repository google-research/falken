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

﻿using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class VirtualJoystick : JoystickBase
{
    #region Editor variables
    // Keys for each movement.
    public KeyCode thrust = KeyCode.W;
    public KeyCode left = KeyCode.A;
    public KeyCode right = KeyCode.D;
    public KeyCode back = KeyCode.S;
    public KeyCode fire = KeyCode.Space;

    // Max values for steering and throttle.
    public float maxThrottle = 1.0f;
    public float maxSteering = 1.0f;
    #endregion

    #region Unity Callbacks
    // Start is called before the first frame update
    public override void OnEnable()
    {
        _controls.Steering = 0.0f;
        _controls.Throttle = 0.0f;
        _controls.Fire = false;
    }

    // Update is called once per frame
    public override void FixedUpdate()
    {
        _controls.Throttle = 0.0f;
        if (Input.GetKey(thrust))
        {
            _controls.Throttle = maxThrottle;
        }
        else if (Input.GetKey(back))
        {
            _controls.Throttle = - maxThrottle;
        }

        _controls.Steering = 0.0f;
        if (Input.GetKey(left))
        {
            _controls.Steering = - maxThrottle;
        }
        else if (Input.GetKey(right))
        {
            _controls.Steering = maxThrottle;
        }

        if (Input.GetKey(fire))
        {
            _controls.Fire = true;
        }
        else
        {
            _controls.Fire = false;
        }
    }
    #endregion
}
