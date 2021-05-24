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
/// <c>Weapon</c> Manages the state of a weapon, primarily to create projectiles and apply damage.
/// </summary>
public class Weapon : MonoBehaviour
{
    [Tooltip("The projectile to spawn when firing.")]
    public Projectile projectile;
    [Tooltip("The maximum rate at which this weapon can fire.")]
    public float maxFireRate = 0.1f;
    [Tooltip("The relative offset at which to create projectiles.")]
    public Vector3 muzzleOffset;

    private float nextFireTime;

    /// <summary>
    /// Requests the Weapon to fire at the specified target.
    /// </summary>
    public bool Fire(GameObject target, Vector3 targetPos) {
        if (projectile && Time.fixedTime >= nextFireTime) {
            Vector3 toTarget = (targetPos - transform.position).normalized;
            GameObject newProjectile = GameObject.Instantiate(projectile.gameObject,
                transform.position + transform.rotation * muzzleOffset, transform.rotation);
            newProjectile.transform.forward = toTarget;
            newProjectile.GetComponent<Projectile>().SetTarget(target, targetPos);
            nextFireTime = Time.fixedTime + maxFireRate;
            return true;
        }
        return false;
    }
}
