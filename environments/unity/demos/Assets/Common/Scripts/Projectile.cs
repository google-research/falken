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
/// <c>Projectile</c> An object which flies through the air, intsersects objects, and applies damage.
/// </summary>
public class Projectile : MonoBehaviour
{
    [Tooltip("The speed at which this projectile flies.")]
    [Range(0, 10)]
    public float speed = 1;
    [Tooltip("The amount of damage delivered on contact.")]
    [Range(0, 1000)]
    public int damage = 1;
    [Tooltip("The maximum number of seconds this projectile can exist.")]
    [Range(0, 100)]
    public int lifetime = 5;
    [Tooltip("Whether this projectile should fly straight or vector towards a target.")]
    public bool homing;
    [Tooltip("Maximum turning speed (only for homing projectiles).")]
    [Range(0, 1000)]
    public float maxTurnSpeed = 1;

    private float length;
    private float expirationTime;
    private Vector3 lastPos;
    private GameObject target;
    private Vector3 targetPos;

    /// <summary>
    /// Sets the target object and/or position for this projectile.
    /// </summary>
    public void SetTarget(GameObject target, Vector3 targetPos) {
        this.target = target;
        this.targetPos = target ? target.transform.InverseTransformPoint(targetPos) : targetPos;
    }

    void Start() {
        lastPos = transform.position;
        expirationTime = Time.fixedTime + lifetime;

        MeshRenderer renderer = GetComponent<MeshRenderer>();
        if (renderer) {
            length = renderer.bounds.extents.z;
        }
    }

    void FixedUpdate() {
        if (Time.fixedTime >= expirationTime) {
            Destroy(gameObject);
            return;
        }

        if (homing) {
            float step = maxTurnSpeed * Time.fixedDeltaTime;
            Vector3 targetWS = target ? target.transform.TransformPoint(targetPos) : targetPos;
            Quaternion rotationToTarget = Quaternion.LookRotation(targetWS - transform.position);
            transform.rotation =
                Quaternion.RotateTowards(transform.rotation, rotationToTarget, step);
        }

        float moveDistance = speed * Time.fixedDeltaTime;
        Vector3 newPosition = lastPos + transform.forward * moveDistance;
        RaycastHit hit;
        if (Physics.Raycast(lastPos, transform.forward, out hit, moveDistance + length)) {
            newPosition = hit.point;
            if (hit.collider) {
                Health health = hit.collider.GetComponent<Health>();
                if (health) {
                    health.TakeDamage(damage);
                }
            }
            GameObject.Destroy(gameObject);
        }
        transform.position = newPosition;
        lastPos = newPosition;
    }
}
