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

﻿using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class PowerpillArena : Arena
{
    public float pillInterval = 3f;
    public float pillStdDev = 1f;


    public Powerpill powerpill;
    private List<Powerpill> _pills;

    private float _nextPill;

    public PowerpillArena()
    {
        _pills = new List<Powerpill>();
    }

    // Compute Gaussian with the Marsaglia polar method, see:
    // https://en.wikipedia.org/wiki/Marsaglia_polar_method
    private float NextGaussian(float mean, float stddev)
    {
        float v1, v2, s;
        do
        {
            v1 = 2.0f * UnityEngine.Random.Range(0f, 1f) - 1.0f;
            v2 = 2.0f * UnityEngine.Random.Range(0f, 1f) - 1.0f;
            s = v1 * v1 + v2 * v2;
        } while (s >= 1.0f || s <= 1e-20f);

        s = Mathf.Sqrt((-2.0f * Mathf.Log(s)) / s);
        return mean + stddev * (v1 * s);
    }

    public override void FixedUpdate()
    {
        base.FixedUpdate();

        if (_nextPill < Time.fixedTime)
        {
            if (_nextPill > 0)
            {
                CreatePill();
            }
            _nextPill = Time.fixedTime + NextGaussian(pillInterval, pillStdDev);
        }
    }

    private void CreatePill()
    {
        var pill = Instantiate<Powerpill>(powerpill);
        // Generate random angle to spawn.
        float randomAngle = UnityEngine.Random.Range(0f, 360f);
        var pos = GenerateRandomGroundPos(this, randomAngle);
        pos.y = pill.transform.position.y;
        pill.transform.position = pos;
        _pills.Add(pill);
    }

    public void Reset()
    {
        _nextPill = -1f;

        foreach (var pill in _pills)
        {
            if (pill != null)
            {
                Destroy(pill.gameObject);
            }
        }
        _pills.Clear();
    }
}
