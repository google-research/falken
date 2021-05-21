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
/// <c>Door</c> Represents an entrance or an exit from a <c>Room</c>.
/// </summary>
[ExecuteInEditMode]
public class Door : MonoBehaviour
{
    [Tooltip("Controls whether the door is open or closed.")]
    public bool open;
    [Tooltip("The room that leads into this door.")]
    public Room from;
    [Tooltip("The room that this door leads into.")]
    public Room to;

    void Update() {
        MeshRenderer meshRenderer = GetComponent<MeshRenderer>();
        if (meshRenderer) {
            meshRenderer.enabled = !open;
        }

        Collider collider = GetComponent<Collider>();
        if (collider) {
            collider.enabled = !open;
        }
    }
}
