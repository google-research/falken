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
/// <c>ProjectileImpact</c> Effect to spawn when a projectile hits something.
/// </summary>
public class ProjectileImpact : MonoBehaviour
{
    [Tooltip("Light animation Duration")]
    [Range(0, 1)]
    public float duration = .3f;

    private Light impactLight;
    private float initialLightIntensity;
    private float time;

    void Start() {
        impactLight = GetComponentInChildren<Light>();
        initialLightIntensity = impactLight.intensity;
    }

    void FixedUpdate() {
        time += Time.fixedDeltaTime;
        float t = time / duration;
        impactLight.intensity = (1.0f - t) * initialLightIntensity;
        if (time > duration) {
            GameObject.Destroy(gameObject);
        }
    }
}
