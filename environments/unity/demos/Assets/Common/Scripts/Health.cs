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
/// <c>Health</c> Represents an object thaht can take damage and be destroyed.
/// </summary>
[RequireComponent(typeof(Collider))]
public class Health : MonoBehaviour
{
    [Tooltip("The starting and maximum amount of health that this object can have.")]
    [Range(1, 1000)]
    public int maxHealth = 100;

    private int health;
    private bool dead;

    /// <summary>
    /// Callback to be notified when this GameObject is killed.
    /// </summary>
    public delegate void DeathHandler(Health killed);
    public event DeathHandler OnKilled;

    /// <summary>
    /// Returns the current amount of health.
    /// </summary>
    public int CurrentHealth { get { return health; } }

    /// <summary>
    /// Applies a specific amount of damage to the object, potentially destroying it.
    /// </summary>
    public void TakeDamage(int amount) {
        if (!dead) {
            health -= amount;
            if (health <= 0) {
                dead = true;
                if (OnKilled != null) {
                    OnKilled(this);
                } else {
                    GameObject.Destroy(gameObject);
                }
            }
        }
    }

    void Start() {
        health = maxHealth;
    }
}
