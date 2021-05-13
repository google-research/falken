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

﻿using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class Powerpill : MonoBehaviour
{
    public float lifetime = 7;
    public float blinkDuration = 1;
    public float effectDuration = 5;

    private float startTime;
    private MeshRenderer meshRenderer;
    private Blinker blinker;


    // Start is called before the first frame update
    void OnEnable()
    {
        startTime = Time.fixedTime;
        meshRenderer = GetComponent<MeshRenderer>();
        blinker = GetComponent<Blinker>();
        if (blinker != null)
            blinker.enabled = false;
    }

    void FixedUpdate()
    {
        var timeAlive = Time.fixedTime - startTime;
        if (timeAlive > lifetime - blinkDuration)
        {
            if (blinker != null && !blinker.enabled)
                blinker.enabled = true;
        }
        if (timeAlive > lifetime)
        {
            Destroy(gameObject);
        }
    }

    public void OnTriggerEnter(Collider collision)
    {
        var mPlayer = collision.gameObject.GetComponent<FalkenPlayer>();

        if (mPlayer != null)
        {
            mPlayer.Boost(effectDuration);
        }

        Destroy(gameObject);
    }
}
