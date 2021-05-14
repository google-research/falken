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

public class PlayerEntity : Falken.EntityBase
{
    [Range(-1.5f, 1.5f)]
    public float angle;
    [Range(0f, 3.0f)]
    public float distance_to_enemy;
    public bool boosted;
    public Falken.Feelers feelers = new Falken.Feelers(
        0.8f, 0.0f, 90.0f, 14, null);
}

public class PlayerActions : Falken.ActionsBase
{
    [Range(-1f, 1f)]
    public float throttle;
    [Range(-1f, 1f)]
    public float steering;
    public bool fire;
}

public class PlayerObservations : Falken.ObservationsBase
{
    public Falken.EntityBase enemy = new Falken.EntityBase("enemy");

    public PlayerObservations()
    {
        player = new PlayerEntity();
    }
}

public class PlayerBrainSpec : Falken.BrainSpec<PlayerObservations, PlayerActions>
{
}

public class FalkenPlayer : Player
{
    #region Editor variables
    public float autopilotSeconds = 2;
    #endregion

    #region Protected and private attributes
    protected Falken.Session _session;
    protected PlayerBrainSpec _brainSpec;
    private Falken.Episode _episode = null;
    private float _lastUserInputFixedTime = float.MinValue;
    #endregion

    #region Getters and Setters
    /// <summary>
    /// Returns true if an episode was already started.
    /// </summary>
    public bool EpisodeStarted
    {
        get
        {
            return _episode != null && !_episode.Completed;
        }
    }

    /// <summary>
    /// Current Falken session.
    /// </summary>
    public Falken.Session Session
    {
        set
        {
            _session = value;
        }
        get
        {
            return _session;
        }
    }

    /// <summary>
    /// BrainSpec of the brain to be trained.
    /// </summary>
    public PlayerBrainSpec BrainSpec
    {
        set
        {
            _brainSpec = value;
        }
        get
        {
            return _brainSpec;
        }
    }

    /// <summary>
    /// If the user does not move a specific amount of time, enable autopilot
    /// </summary>
    /// </returns> True if autopilot should be enabled.
    protected bool AutopilotEnabled
    {
        get
        {
            return (Time.fixedTime - _lastUserInputFixedTime) > autopilotSeconds;
        }

    }

    /// <summary>
    /// Player should move only if this property is true.
    /// </summary>
    protected bool BrainInControl
    {
        get
        {
            if (_brainSpec.Actions.ActionsSource == Falken.ActionsBase.Source.BrainAction)
            {
                return true;
            }
            return false;
        }
    }
    #endregion

    #region Unity Callbacks
    public override void OnEnable()
    {
        base.OnEnable();
        Reset();
    }

    public override void FixedUpdate()
    {
        UpdateHealth();
        UpdateBlinking();

        if (EpisodeStarted)
        {
            DateTime before_complete = DateTime.Now;
            // Reset if goal was reached.
            if (!Alive)
            {
                EndEpisode(Falken.Episode.CompletionState.Failure);
                return;
            }
            else if (_episode.Completed)
            {
                // Reset if maxSteps reached
                EndEpisode(Falken.Episode.CompletionState.Aborted);
                return;
            }
            else if (!arena.EnemiesAlive)
            {
                EndEpisode(Falken.Episode.CompletionState.Success);
                return;
            }

            // Update the brainSpec with the observations and actions of this frame.
            CalculateObservations();
            // backup actions because Step will overwrite them
            var control = CalculateActions();

            // Step if there are enemies alive.
            if (arena.EnemiesAlive)
            {
                // Check if the player is in autopilot.
                _episode.Step();
            }

            // Move the player accordingly.
            if (BrainInControl)
            {
                control.Throttle = _brainSpec.Actions.throttle;
                control.Steering = _brainSpec.Actions.steering;
                control.Fire = _brainSpec.Actions.fire;
            }
            ApplySteeringForces(control);
        }
    }
    #endregion

    #region Auxiliary methods
    /// <summary>
    /// Reset the current mirror player to its original state
    /// </summary>
    public void EndEpisode(Falken.Episode.CompletionState episodeState)
    {
        // Finish the episode.
        if (EpisodeStarted)
        {
            _episode.Complete(episodeState);
        }

        // Hide current player
        base.Die();
    }

    /// <summary>
    /// Update the actions of brainspec based on the current status of the mirror player.
    /// </summary>
    /// </returns> Copy of the updated PlayerActions.
    protected void CalculateObservations()
    {
        var playerForward = gameObject.transform.forward;
        var enemy = arena.GetClosestEnemy(this);
        var enemyPosition = enemy.transform.position;

        var playerToEnemy = enemyPosition - transform.position;
        var directionToEnemy = playerToEnemy.normalized;
        var sideSign = Math.Sign(Vector3.Dot(directionToEnemy,
            gameObject.transform.right));

        // Angle represented as a [-1,1] value, with 0 pointing at the goal,
        // 1 or -1 away, with positive numbers on the left and negative on the
        // right.

        var playerEntity = (PlayerEntity) _brainSpec.Observations.player;
        playerEntity.angle = sideSign * (1f + Vector3.Dot(directionToEnemy,
                                             -playerForward)) * 0.5f;
        playerEntity.distance_to_enemy = Mathf.Log(playerToEnemy.magnitude + 1);
        playerEntity.feelers.Update(
            gameObject.transform, new Vector3(0.0f, 0.0f, 0.0f), true);
        if (Boosted)
        {
            playerEntity.boosted = true;
        }
        else
        {
            playerEntity.boosted = false;
        }

        playerEntity.position = gameObject.transform.position;
        playerEntity.rotation = gameObject.transform.rotation;

        _brainSpec.Observations.enemy.rotation =
            Quaternion.FromToRotation(transform.forward, enemy.transform.forward);
        _brainSpec.Observations.enemy.position = enemyPosition;
    }

    /// <summary>
    /// Update the actions of brainspec based on the current status of the mirror player.
    /// </summary>
    /// </returns> Copy of the updated PlayerActions.
    protected override Controls CalculateActions()
    {
        var controls = base.CalculateActions();

        if (controls.MovementApplied)
        {
            _lastUserInputFixedTime = Time.fixedTime;
        }

        if (!AutopilotEnabled)
        {
            _brainSpec.Actions.throttle = controls.Throttle;
            _brainSpec.Actions.steering = controls.Steering;
            _brainSpec.Actions.fire = controls.Fire;
            _brainSpec.Actions.ActionsSource = Falken.ActionsBase.Source.HumanDemonstration;
        }
        else
        {
            _brainSpec.Actions.ActionsSource = Falken.ActionsBase.Source.None;
        }

        return controls;
    }

    /// <summary>
    /// Start the episode if not already started.
    /// </summary>
    public void StartEpisode()
    {
        // Start the episode if not already started.
        if (!EpisodeStarted)
        {
            // Reset life bar.
            Reset();

            // Respawn the current player.
            Respawn();

            _episode = _session.StartEpisode();
        }
    }
    #endregion
}
