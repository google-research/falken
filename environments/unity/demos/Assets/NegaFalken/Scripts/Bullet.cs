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
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class Bullet : MonoBehaviour
{
    public GameObject firedBy;
    public float speed = 2f;
    public float lifetime = 2;
    public float damage = 20;

    private float startTime;

    int hitFrame = int.MaxValue;

    private void Start()
    {
        var rb = gameObject.GetComponent<Rigidbody>();
        startTime = Time.fixedTime;
        rb.velocity = speed * transform.forward;
        rb.drag = 0;
    }

    public void FixedUpdate()
    {
        if (Time.fixedTime - startTime > lifetime)
        {
            Destroy(gameObject);
        }

        if (Time.frameCount - hitFrame > 0)
        {
            Destroy(gameObject);
        }
    }

    public void OnCollisionEnter(Collision collision)
    {
        var mPlayer = collision.gameObject.GetComponent<NegaFalkenPlayer>();

        if (collision.gameObject != firedBy)
        {
            hitFrame = Time.frameCount;

            if (mPlayer != null)
            {
                mPlayer.TakeDamage(damage);
            }
        }
    }
}
