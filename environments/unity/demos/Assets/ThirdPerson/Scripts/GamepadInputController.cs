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

public class GamepadInputController : InputController
{
    public InputController passThrough;

    public override Vector2 GetAxis1()
    {
        Vector2 result = new Vector2(
            Input.GetAxis("Axis1 X"),
            Input.GetAxis("Axis1 Y"));
        if (passThrough != null)
        {
            result += passThrough.GetAxis1();
        }
        return result;
    }

    public override Vector2 GetAxis2()
    {
        Vector2 result = new Vector2(
            Input.GetAxis("Axis2 X"),
            Input.GetAxis("Axis2 Y"));
        if (passThrough != null)
        {
            result += passThrough.GetAxis2();
        }
        return result;
    }
}
