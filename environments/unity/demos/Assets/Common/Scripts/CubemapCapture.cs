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
/// <c>CubemapCapture</c> Captures a cubemap texture from a camera.
/// Can also generate reflectors for pretty highlights.
/// </summary>
[RequireComponent(typeof(Camera))]
[ExecuteInEditMode]
public class CubemapCapture : MonoBehaviour
{
    [Tooltip("The mesh to apply to each reflector.")]
    public Mesh ReflectorMesh;
    [Tooltip("The material to apply to each reflector.")]
    public Material ReflectorMaterial;
    [Tooltip("The number of reflectors to generate.")]
    [Range(0, 100)]
    public int NumReflectors;
    [Range(0, 1)]
    [Tooltip("The size of the generated reflectors.")]
    public float ReflectorSize = 0.5f;
    [Tooltip("The cubemap to render into.")]
    public Cubemap Target;

    [SerializeField] [HideInInspector]
    private List<GameObject> reflectors = new List<GameObject>();
    private Mesh prevMesh = null;
    private Material prevMaterial = null;
    private float prevSize = -1;

    /// <summary>
    /// Renders this object's camera into the Target cubemap.
    /// </summary>
    public void Capture() {
        if (Target) {
            GetComponent<Camera>().RenderToCubemap(Target);
        }
    }

#if UNITY_EDITOR
    protected void Update() {
        if (reflectors.Count != NumReflectors) {
            for (int i = 0; i < reflectors.Count; ++i) {
                DestroyImmediate(reflectors[i]);
            }
            reflectors.Clear();
            prevMesh = null;
            prevMaterial = null;
            prevSize = -1;

            for (int i = 0; i < NumReflectors; ++i) {
                GameObject reflector = new GameObject("Reflector_" + i);
                reflector.transform.parent = transform;
                reflector.transform.localPosition = Random.onUnitSphere;
                reflector.transform.LookAt(transform);
                reflector.transform.Rotate(0, 180f, 0, Space.Self);
                reflector.AddComponent<MeshFilter>();
                reflector.AddComponent<MeshRenderer>();
                reflectors.Add(reflector);
            }
        }

        if (ReflectorMesh != prevMesh) {
            for (int i = 0; i < reflectors.Count; ++i) {
                reflectors[i].GetComponent<MeshFilter>().sharedMesh = ReflectorMesh;
            }
            prevMesh = ReflectorMesh;
        }

        if (ReflectorMaterial != prevMaterial) {
            for (int i = 0; i < reflectors.Count; ++i) {
                reflectors[i].GetComponent<MeshRenderer>().sharedMaterial = ReflectorMaterial;
            }
            prevMaterial = ReflectorMaterial;
        }

        if (ReflectorSize != prevSize) {
            for (int i = 0; i < reflectors.Count; ++i) {
                reflectors[i].transform.localScale =
                    new Vector3(ReflectorSize, ReflectorSize, ReflectorSize);
            }
            prevSize = ReflectorSize;
        }
    }
#endif
}
