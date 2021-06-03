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

using System;
using System.Threading;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

/// <summary>
/// <c> NegaActions </c> Describes the control Actions a NegaFalken player can perform.
/// </summary>
public class NegaActions : Falken.ActionsBase
{
    public Falken.Number throttle = new Falken.Number(-1f, 1f);
    public Falken.Number steering = new Falken.Number(-1f, 1f);
    public Falken.Boolean fire = new Falken.Boolean();
}

/// <summary>
/// <c>HelloPlayerEntity</c> Observations that sense the enemy and environment around the player.
/// </summary>
public class NegaPlayerEntity : Falken.EntityBase
{
    public Falken.Number angle = new Falken.Number(-1.5f, 1.5f);
    public Falken.Number distance_to_enemy = new Falken.Number(0f, 3f);
    public Falken.Feelers feelers = new Falken.Feelers(3f, 0f, 360.0f, 14, null);
}

/// <summary>
/// <c>HelloObservations</c> Final observations with player and enemy entities.
/// </summary>
public class NegaObservations : Falken.ObservationsBase
{
    public Falken.EntityBase enemy = new Falken.EntityBase("enemy");

    public NegaObservations()
    {
        player = new NegaPlayerEntity();
    }
}

/// <summary>
/// <c>NegaBrainSpec</c> Binding of Actions and Observations for this player.
/// </summary>
public class NegaBrainSpec : Falken.BrainSpec<NegaObservations, NegaActions> {}

/// <summary>
/// <c>NegaFalkenPlayer</c> Implements an asteroids-like player that can turn, thurst and fire.
/// </summary>
[RequireComponent(typeof(Ship))]
[RequireComponent(typeof(Health))]
[RequireComponent(typeof(Weapon))]
public class NegaFalkenPlayer : MonoBehaviour
{
    #region Editor variables
    [Tooltip("Magnitude of the backwards impulse to apply when firing.")]
    [Range(0, 100)]
    public float recoil = 2f;
    #endregion

    #region Protected and private attributes
    private Ship _ship;
    private Health _health;
    private Weapon _weapon;
    private Slider _healthSlider;

    private NegaFalkenGame _game;
    private NegaBrainSpec _brainSpec = null;
    private Falken.Episode _episode = null;
    private bool _humanControlled = false;
    #endregion

    #region Getters and Setters
    /// <summary>
    /// Sets a slider UI object to represent this player's health.
    /// </summary>
    public Slider HealthSlider
    {
        set
        {
            _healthSlider = value;
            if (_healthSlider)
            {
                _healthSlider.minValue = 0;
                _healthSlider.maxValue = _health.maxHealth;
            }
        }
    }

    /// <summary>
    /// Sets the current SessionController.
    /// </summary>
    public NegaFalkenGame Game { set { _game = value; } }

    /// <summary>
    /// Sets the current NegaPlayerBrainSpec.
    /// </summary>
    public NegaBrainSpec BrainSpec { set { _brainSpec = value; } }

    /// <summary>
    /// Sets whether this agent is human or AI controlled.
    /// </summary>
    public bool HumanControlled
    {
        set { _humanControlled = value; }
        get { return _humanControlled; }
    }

    /// <summary>
    /// Accessor for this player's Falken episode.
    /// </summary>
    public Falken.Episode Episode
    {
        set { _episode = value; }
        get { return _episode; }
    }
    #endregion

    #region Unity Callbacks
    void OnEnable()
    {
        _ship = GetComponent<Ship>();
        _health = GetComponent<Health>();
        _weapon = GetComponent<Weapon>();
    }

    void FixedUpdate()
    {
        if (_healthSlider != null)
        {
            _healthSlider.value = _health.CurrentHealth;
        }

        // Update the brainSpec with the observations and actions of this frame.
        CalculateObservations();

        float steering = _humanControlled ? Input.GetAxis("Steering") : 0f;
        float throttle = _humanControlled ? Input.GetAxis("Gas") - Input.GetAxis("Brake") : 0f;
        bool fire = _humanControlled ? Input.GetButtonDown("Fire") : false;

        _brainSpec.Actions.steering.Value = steering;
        _brainSpec.Actions.throttle.Value = throttle;
        _brainSpec.Actions.fire.Value = fire;
        _brainSpec.Actions.ActionsSource = _humanControlled ?
            Falken.ActionsBase.Source.HumanDemonstration :
            Falken.ActionsBase.Source.BrainAction;

        _episode.Step();

        if (_brainSpec.Actions.ActionsSource == Falken.ActionsBase.Source.BrainAction)
        {
            steering = _brainSpec.Actions.steering.Value;
            throttle = _brainSpec.Actions.throttle.Value;
            fire = _brainSpec.Actions.fire.Value;
        }
        ApplyActions(steering, throttle, fire);
    }
    #endregion

    #region Auxiliary methods
    /// <summary>
    /// Update the observations of brainspec based on the current status of the player.
    /// </summary>
    private void CalculateObservations()
    {
        var playerForward = gameObject.transform.forward;
        var enemy = _game.GetClosestEnemy(this);
        var enemyPosition = enemy.transform.position;

        var playerToEnemy = enemyPosition - transform.position;
        var directionToEnemy = playerToEnemy.normalized;
        var sideSign = Math.Sign(Vector3.Dot(directionToEnemy,
            gameObject.transform.right));

        // Angle represented as a [-1,1] value, with 0 pointing at the goal,
        // 1 or -1 away, with positive numbers on the left and negative on the
        // right.

        var playerEntity = (NegaPlayerEntity) _brainSpec.Observations.player;
        playerEntity.angle.Value = sideSign * (1f + Vector3.Dot(directionToEnemy,
            -playerForward)) * 0.5f;
        playerEntity.distance_to_enemy.Value = Mathf.Log(playerToEnemy.magnitude + 1);
        playerEntity.feelers.Update(
            gameObject.transform, new Vector3(0.0f, 0.0f, 0.0f), true);

        playerEntity.position = gameObject.transform.position;
        playerEntity.rotation = gameObject.transform.rotation;

        _brainSpec.Observations.enemy.position = enemyPosition;
        _brainSpec.Observations.enemy.rotation = enemy.transform.rotation;
    }

    /// <summary>
    /// Apply steering, throttle, and fire Actions to the player.
    /// </summary>
    private void ApplyActions(float steering, float throttle, bool fire)
    {
        // Going backwards is slower.
        if (throttle < 0)
        {
            throttle *= 0.5f;
        }
        _ship.ApplyActions(throttle, steering);

        if (fire)
        {
            _weapon.Fire(null, transform.position + transform.forward * 10f);
            _ship.ApplyRecoil(recoil);
        }
    }
    #endregion
}
