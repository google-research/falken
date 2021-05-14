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

public class KeyboardInputController : InputController
{

    public override Vector2 GetAxis1()
    {
        Vector2 vec = new Vector2();
        if (Input.GetKey(KeyCode.Keypad8) || Input.GetKey(KeyCode.W))
        {
            // N
            vec += Vector2.up;
        }
        if (Input.GetKey(KeyCode.Keypad7))
        {
            // NW
            vec += Vector2.up + Vector2.left;
        }
        if (Input.GetKey(KeyCode.Keypad4) || Input.GetKey(KeyCode.A))
        {
            // W
            vec += Vector2.left;
        }
        if (Input.GetKey(KeyCode.Keypad1))
        {
            // SW
            vec += Vector2.left + Vector2.down;
        }
        if (Input.GetKey(KeyCode.Keypad2) || Input.GetKey(KeyCode.S))
        {
            // S
            vec += Vector2.down;
        }
        if (Input.GetKey(KeyCode.Keypad3))
        {
            // SE
            vec += Vector2.down + Vector2.right;
        }
        if (Input.GetKey(KeyCode.Keypad6) || Input.GetKey(KeyCode.D))
        {
            // E
            vec += Vector2.right;
        }
        if (Input.GetKey(KeyCode.Keypad9))
        {
            // NE
            vec += Vector2.right + Vector2.up;
        }
        return vec.magnitude > 1 ? vec.normalized : vec;
    }

    // Returns keyboard yaw / pitch input (QEXZ).
    public override Vector2 GetAxis2()
    {
        Vector2 result = new Vector2();

        if (Input.GetKey(KeyCode.Q))
        {
            result.x -= 1f;
        }
        if (Input.GetKey(KeyCode.E))
        {
            result.x += 1f;
        }
        if (Input.GetKey(KeyCode.Z))
        {
            result.y -= 1f;
        }
        if (Input.GetKey(KeyCode.X))
        {
            result.y += 1f;
        }

        return result;
    }
}
