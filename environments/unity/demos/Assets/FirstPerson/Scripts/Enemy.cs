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
/// <c>Enemy</c> A simple npc designed to move and attack the player.
/// </summary>
[RequireComponent(typeof(Weapon))]
[RequireComponent(typeof(Health))]
public class Enemy : MonoBehaviour
{
    public enum AttackStyle {
        None = 0,
        /// Move up from initial positon, attack, move back down, repeat.
        Up = (1 << 0),
        /// Move down from initial positon, attack, move back up, repeat.
        Down = (1 << 1),
        /// Move left from initial positon, attack, move back right, repeat.
        Left = (1 << 2),
        /// Move right from initial positon, attack, move back left, repeat.
        Right = (1 << 3),
        /// Randomly attack Up or Down.
        Vertical = Up | Down,
        /// Randomly attack Left or Right.
        Horizontal = Left | Right,
        /// Randomly select between Up, Left, and Right.
        HorizontalUp = Up | Horizontal,
        /// Randomly select any of the 4 attack behaviors.
        All = Vertical | Horizontal,
    };

    [Tooltip("Distance at which to start attacking the player.")]
    [Range(1, 100)]
    public float activationRange = 10f;
    [Tooltip("Duration of the firing phase of the attack.")]
    [Range(0, 100)]
    public float attackDuration = 5f;
    [Tooltip("Duration of the hiding/waiting phase of the attack.")]
    [Range(0, 100)]
    public float hideDuration = 5f;
    [Tooltip("How far to move from intial position when attacking.")]
    [Range(0,100)]
    public float moveDistance = 1;
    [Tooltip("How quickly to move while attacking.")]
    [Range(0,100)]
    public float moveDuration = 1;
    [Tooltip("How much randomness to add to each attack timer.")]
    [Range(0,1)]
    public float timingVariance = 0;
    public AttackStyle attackStyle;

    private Vector3 initialPosition;
    private Quaternion initialRotation;
    private Weapon weapon;
    private Health health;
    private FirstPersonPlayer player;
    private Room room;
    private bool firing;
    private IEnumerator attackRoutine;

    private static List<Enemy> enemies = new List<Enemy>();

    /// <summary>
    /// Returns true if the enemy is firing.
    /// </summary>
    public bool Firing { get { return firing; } }

    /// <summary>
    /// Returns a list of all enabled Enemies in the world.
    /// </summary>
    public static List<Enemy> Enemies { get { return enemies; } }

    void OnEnable() {
        enemies.Add(this);
        initialPosition = transform.position;
        initialRotation = transform.rotation;
        weapon = GetComponent<Weapon>();
        health = GetComponent<Health>();

        room = null;
        int nRooms = Room.Rooms.Count;
        Vector3 position = transform.position;
        for (int i = 0; i < nRooms; ++i) {
            if (Room.Rooms[i].Bounds.Contains(position)) {
                 room = Room.Rooms[i];
                 room.AddEnemy(this);
                 break;
            }
        }
    }

    void OnDisable() {
        if (room) {
            room.RemoveEnemy(this);
        }
        enemies.Remove(this);
    }

    IEnumerator Start() {
        attackRoutine = Attack();
        yield return StartCoroutine(attackRoutine);
    }

    void FixedUpdate() {
        if (firing && player) {
            transform.LookAt(player.TargetPos);
        } else {
            transform.rotation = initialRotation;
        }

        if (attackRoutine != null && health.Dead) {
            StopCoroutine(attackRoutine);
            attackRoutine = null;
        }
    }

    /// <summary>
    /// Defines a very simple attack sequence.
    /// </summary>
    IEnumerator Attack() {
        while (true) {
            player = GetPlayer();
            if (player && Vector3.Distance(
                player.transform.position, transform.position) <= activationRange) {
                Vector3 attackPosition = GetAttackLocation(attackStyle);

                Vector3 moveDirection = attackPosition - transform.position;
                float moveDistance = moveDirection.magnitude;
                moveDirection /= moveDistance;

                Vector3 attackDirection = player.TargetPos - attackPosition;
                float attackDistance = attackDirection.magnitude;
                attackDistance /= attackDistance;

                yield return Wait(hideDuration);
                if (!Physics.Raycast(transform.position, moveDirection, moveDistance) &&
                    !Physics.Raycast(attackPosition, attackDirection, attackDistance)) {
                    firing = true;
                    yield return Move(attackPosition, 1f);
                    yield return Fire(attackDuration);
                    yield return Move(initialPosition, 1f);
                    firing = false;
                }
            }
            yield return new WaitForFixedUpdate();
        }
    }

    /// <summary>
    /// Moves the Enemy from one position to another.
    /// </summary>
    IEnumerator Move(Vector3 goalPos, float moveTime) {
        Vector3 startingPos  = transform.position;
        float elapsedTime = 0;
        while (elapsedTime < moveTime)
        {
            float t = elapsedTime / moveTime;
            transform.position = new Vector3(
                Mathf.SmoothStep(startingPos.x, goalPos.x, t),
                Mathf.SmoothStep(startingPos.y, goalPos.y, t),
                Mathf.SmoothStep(startingPos.z, goalPos.z, t));
            elapsedTime += Time.fixedDeltaTime;
            yield return new WaitForFixedUpdate();
        }
    }

    /// <summary>
    /// Fires at the player for the specified amount of time.
    /// </summary>
    IEnumerator Fire(float duration) {
        float elapsedTime = 0;
        while (elapsedTime < duration)
        {
            if (player) {
                weapon.Fire(player.gameObject, player.TargetPos);
            }
            elapsedTime += Time.fixedDeltaTime;
            yield return new WaitForFixedUpdate();
        }
    }

    /// <summary>
    /// Waits for a specified amount of time.
    /// </summary>
    IEnumerator Wait(float duration) {
        float elapsedTime = 0;
        float variation = duration * timingVariance * 0.5f;
        duration = Random.Range(duration - variation, duration + variation);
        while (elapsedTime < duration)
        {
            elapsedTime += Time.fixedDeltaTime;
            yield return new WaitForFixedUpdate();
        }
    }

    /// <summary>
    /// Returns the current FirstPersonPlayer instance.
    /// </summary>
    private FirstPersonPlayer GetPlayer() {
        return FirstPersonPlayer.Players.Count > 0 ? FirstPersonPlayer.Players[0] : null;
    }

    /// <summary>
    /// Computes an attack location based on the specified attackStyle
    /// </summary>
    private Vector3 GetAttackLocation(AttackStyle attackStyle) {
        AttackStyle chosenStyle;
        switch (attackStyle) {
            case AttackStyle.Vertical:
                chosenStyle = Random.value > 0.5 ? AttackStyle.Up : AttackStyle.Down;
                break;
            case AttackStyle.Horizontal:
                chosenStyle = Random.value > 0.5 ? AttackStyle.Left : AttackStyle.Right;
                break;
            case AttackStyle.All:
                chosenStyle = (AttackStyle)(1 << Random.Range(0, 3));
                break;
            default:
                chosenStyle = attackStyle;
                break;
        }

        Vector3 moveDirection = Vector3.zero;
        switch (chosenStyle) {
            case AttackStyle.Left:
                moveDirection = Vector3.left;
                break;
            case AttackStyle.Right:
                moveDirection = Vector3.right;
                break;
            case AttackStyle.Up:
                moveDirection = Vector3.up;
                break;
            case AttackStyle.Down:
                moveDirection = Vector3.down;
                break;
        }

        return initialPosition + initialRotation * (moveDirection * moveDistance);
    }
}
