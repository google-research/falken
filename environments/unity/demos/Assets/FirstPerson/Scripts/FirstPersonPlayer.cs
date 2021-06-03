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
/// <c>FirstPersonPlayer</c> Player controller for a first-person style game.
/// </summary>
[RequireComponent(typeof(CharacterController))]
[RequireComponent(typeof(Health))]
public class FirstPersonPlayer : MonoBehaviour
{
    [Tooltip("The speed at which the player moves while walking.")]
    [Range(0, 100)]
    public float walkingSpeed = 7f;
    [Tooltip("The speed at which the player moves while running (the default).")]
    [Range(0, 100)]
    public float runningSpeed = 11f;
    [Tooltip("The speed at which the player leaves the ground when jumping.")]
    [Range(0, 100)]
    public float jumpSpeed = 8f;
    [Tooltip("The strength of gravity to apply to the player.")]
    [Range(0, 100)]
    public float gravity = 20f;

    [Tooltip("The camera object to use in lookoing, aiming, and firing.")]
    public Camera playerCamera;
    [Tooltip("The rate at which the camera should rotate based on player input.")]
    [Range(0, 10)]
    public float lookSpeed = 2f;
    [Tooltip("The maximum angle a player can above or below the horizon.")]
    [Range(0, 80)]
    public float lookPitchLimit = 45f;

    [Tooltip("The maximum distance to scan for reticle targets.")]
    public Texture reticleTexture;
    [Tooltip("The size of the reticle (in normailzed device coords).")]
    [Range(0, 0.5f)]
    public float reticleSize = 0.1f;
    [Tooltip("The alpha value of the reticle.")]
    [Range(0, 1)]
    public float reticleAlpha = 0.5f;
    [Tooltip("The maximum distance to scan for reticle targets.")]
    [Range(0, 1000)]
    public float reticleMaxRange = 100f;

    [Tooltip("The weapon class to use when firing.")]
    public Weapon weapon;

    /// <summary>
    /// Returns a list of all enabled FirstPersonPlayers in the world.
    /// </summary>
    public static List<FirstPersonPlayer> Players { get { return players; } }

    private CharacterController characterController;
    private Health health;
    private Vector3 moveDirection = Vector3.zero;
    private float rotationX;
    private GameObject reticleTarget;
    private Vector3 reticleHit;
    private static List<FirstPersonPlayer> players = new List<FirstPersonPlayer>();

    void OnEnable()
    {
        characterController = GetComponent<CharacterController>();
        health = GetComponent<Health>();
        Cursor.lockState = CursorLockMode.Locked;
        Cursor.visible = false;
        players.Add(this);
    }

    void OnDisable() {
        characterController = null;
        health = null;
        Cursor.lockState = CursorLockMode.None;
        Cursor.visible = true;
        players.Remove(this);
    }

    void FixedUpdate()
    {
        Move(new Vector2(Input.GetAxis("MoveX"), Input.GetAxis("MoveY")),
            Input.GetKey(KeyCode.LeftShift), Input.GetButton("Jump"));

        Look(new Vector2(Input.GetAxis("LookX"), -Input.GetAxis("LookY")));

        if (Input.GetButtonDown("Trigger"))
        {
            Fire();
        }
    }

    void OnGUI() {
        if (reticleTexture) {
            Color reticleColor = reticleTarget && reticleTarget.GetComponent<Health>() ? Color.red : Color.white;
            reticleColor.a = reticleAlpha;
            GUI.color = reticleColor;
            int reticlePixels = (int)(Screen.width * reticleSize);
            Rect reticleRect = new Rect(Screen.width * 0.5f - reticlePixels * 0.5f,
                Screen.height * 0.5f - reticlePixels * 0.5f,
                reticlePixels, reticlePixels);
            GUI.DrawTexture(reticleRect, reticleTexture);
        }

        if (!health.infiniteHealth) {
            var background = GUI.skin.box.normal.background;
            GUI.skin.box.normal.background = Texture2D.whiteTexture;
            GUI.backgroundColor = Color.red;
            float healthPercentage = (float)health.CurrentHealth / health.maxHealth;
            int healthWidth = (int)(Screen.width * 0.05f);
            int healtHeight = (int)(Screen.height * 0.2f * healthPercentage);
            GUI.Box(new Rect(healthWidth, Screen.height - healthWidth - healtHeight,
                healthWidth, healtHeight), "");
            GUI.skin.box.normal.background = background;
        }
    }

    /// <summary>
    /// Applies steering and jumping inputs onto the CharacterController.
    /// </summary>
    private void Move(Vector2 input, bool walking, bool jumping) {
        float speed = walking ? walkingSpeed : runningSpeed;
        Vector2 curSpeed = input * speed;
        float movementDirectionY = moveDirection.y;
        moveDirection = (transform.forward * curSpeed.y) + (transform.right * curSpeed.x);

        if (jumping && characterController.isGrounded)
        {
            moveDirection.y = jumpSpeed;
        }
        else
        {
            moveDirection.y = movementDirectionY;
        }

        if (!characterController.isGrounded)
        {
            moveDirection.y -= gravity * Time.fixedDeltaTime;
        }

        // Move the controller
        characterController.Move(moveDirection * Time.fixedDeltaTime);
    }

    /// <summary>
    /// Applies look inputs on the the associated Camera.
    /// </summary>
    private void Look(Vector2 input) {
        // Player and Camera rotation
        rotationX += input.y * lookSpeed;
        rotationX = Mathf.Clamp(rotationX, -lookPitchLimit, lookPitchLimit);
        playerCamera.transform.localRotation = Quaternion.Euler(rotationX, 0, 0);
        transform.rotation *= Quaternion.Euler(0, input.x * lookSpeed, 0);

        RaycastHit hit;
        Transform cameraTransform = playerCamera.transform;
        if (Physics.Raycast(
            cameraTransform.position, cameraTransform.forward, out hit, reticleMaxRange)) {
            reticleTarget = hit.collider.gameObject;
            reticleHit = hit.point;
        } else {
            reticleTarget = null;
            reticleHit = Vector3.zero;
        }
    }

    /// <summary>
    /// Requests that the associated weapon fire at the target under the reticle.
    /// </summary>
    private void Fire() {
        if (weapon) {
            if (reticleTarget) {
                weapon.Fire(reticleTarget, reticleHit);
            } else {
                weapon.Fire(null, playerCamera.transform.position +
                    playerCamera.transform.forward * reticleMaxRange);
            }
        }
    }
}
