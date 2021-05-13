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

﻿using UnityEngine;
using System.Collections;

public delegate void NotifyGoalReached();

public class GameLogic : MonoBehaviour
{
    public ThirdPersonController player;
    public GameObject goal;
    public GameObject floor;

    public event NotifyGoalReached notifyGoalReached;

    public int boardSize = 6;

    // Difference in position that counts as 'goal reached'.
    public const float GoalReachedEpsilon = 2.5f;

    public GameLogic()
    {
    }

    void SetRandomPosition(GameObject obj, bool y = false)
    {
        obj.transform.position = new Vector3(
            Random.Range(-boardSize / 2, boardSize / 2),
            y ? Random.Range(-boardSize / 2, boardSize / 2) :
                obj.transform.position.y,
            Random.Range(-boardSize / 2, boardSize / 2));
    }

    void SetRandomRotation(GameObject obj)
    {
        obj.transform.rotation = Quaternion.AngleAxis(
            Random.value * 360, new Vector3(0f, 1.0f, 0f));
    }

    public void Reset()
    {
        bool flight = (
            player.controlType == ControlType.Flight ||
            player.controlType == ControlType.AutoFlight);

        if (flight)
        {
            player.transform.rotation = Quaternion.identity;
            SetRandomPosition(player.gameObject, flight);
            SetRandomPosition(goal, flight);
            goal.transform.position += new Vector3(
                0, boardSize, boardSize);
        }
        else
        {
            SetRandomPosition(player.gameObject, flight);
            SetRandomRotation(player.gameObject);
            SetRandomPosition(goal, flight);
        }


        if (floor) {
            floor.SetActive(!flight);
        }


    }

    void Start()
    {
        Reset();
    }

    void Update()
    {
        if (Vector3.Distance(player.transform.position,
                             goal.transform.position) < GoalReachedEpsilon)
        {
            notifyGoalReached();
            Reset();
        }
    }
}
