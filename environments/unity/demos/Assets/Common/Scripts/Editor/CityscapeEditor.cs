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
using UnityEditor;

/// <summary>
/// <c>CityscapeEditor</c> Custom inspector GUI for <c>Cityscape</c>.
/// </summary>
[CustomEditor(typeof(Cityscape))]
public class CityscapeEditor : Editor
{
    public override void OnInspectorGUI() {
        base.OnInspectorGUI();

        Cityscape myCityscape = (Cityscape)target;

        if (GUILayout.Button("Generate Cityscape")) {
            myCityscape.CreateCityscape();
        }
    }
}
