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
/// <c>Cityscacpe</c> Procedurally creates a grid of buildings, avoiding pre-existing collision geo.
/// </summary>
[RequireComponent(typeof(MeshRenderer))]
[RequireComponent(typeof(MeshFilter))]
public class Cityscape : MonoBehaviour
{
    [Tooltip("Defines the size of a side of the building's footprint.")]
    [Range(0, 100)]
    public float width = 10;
    [Tooltip("Minimum height for a building.")]
    [Range(0, 100)]
    public float minHeight = 20;
    [Tooltip("Maximum height for a building.")]
    [Range(0, 100)]
    public float maxHeight = 40;
    [Tooltip("Reduces the height of buildings closer to the origin.")]
    [Range(0, 1)]
    public float nearHeightScale = 1;
    [Tooltip("The smallest a building's top can become from tapering.")]
    [Range(0, 1)]
    public float taperMin = 0.2f;
    [Tooltip("The largest a building's top can become from tapering.")]
    [Range(0, 1)]
    public float taperMax = 1;
    [Tooltip("The min hue a building can have.")]
    [Range(0, 1)]
    public float hueMin = 0;
    [Tooltip("The max hue a building can have.")]
    [Range(0, 1)]
    public float hueMax = 0;
    [Tooltip("The min saturation a building can have.")]
    [Range(0, 1)]
    public float saturationMin = 0;
    [Tooltip("The max saturation a building can have.")]
    [Range(0, 1)]
    public float saturationMax = 0;
    [Tooltip("The darkest a building can be.")]
    [Range(0, 1)]
    public float valueMin = 1f;
    [Tooltip("The brightest a building can be.")]
    [Range(0, 1)]
    public float valueMax = 1;
    [Tooltip("The amount of space between buildings.")]
    [Range(0, 100)]
    public int spacing = 5;
    [Tooltip("The number of buildings to place in each dimension.")]
    [Range(4, 50)]
    public int structures = 10;

    /// <summary>
    /// Creates a new cityscape mesh, destroying any previously created cityscape on this object.
    /// </summary>
    public void CreateCityscape() {
        float offset = -(ComputeCityWidth() * 0.5f - width * 0.5f);
        Vector3 cubeOrigin = new Vector3(offset, 0, offset);

        QuadMesh quadMesh = new QuadMesh();
        for(int x = 0; x < structures; ++x) {
            for(int z = 0; z < structures; ++z) {
                TryAppendBuilding(transform.TransformPoint(cubeOrigin), quadMesh);
                cubeOrigin.z += width + spacing;
            }
            cubeOrigin.x += width + spacing;
            cubeOrigin.z = offset;
        }

        MeshFilter meshFilter = GetComponent<MeshFilter>();
        Mesh mesh = meshFilter.sharedMesh;
        if (!mesh) {
            mesh = new Mesh();
            meshFilter.sharedMesh = mesh;
        } else {
            mesh.Clear();
        }
        quadMesh.AddToMesh(ref mesh);
    }

    /// <summary>
    /// Contructs a randomly generated building mesh and appends it to the cityscape mesh.
    /// </summary>
    private void TryAppendBuilding(Vector3 origin, QuadMesh quadMesh) {
        RaycastHit hit;
        Vector3 castStart = new Vector3(origin.x, maxHeight, origin.z);
        float buildingRadius = Mathf.Sqrt(2f * (width * 0.5f) * (width * 0.5f));
        float castDistance = maxHeight * 1.5f;
        if (Physics.SphereCast(castStart, buildingRadius, Vector3.down, out hit, castDistance)) {
            return;
        }

        float height = Random.Range(minHeight, maxHeight);
        float halfCityWidth = ComputeCityWidth() * 0.5f;
        float normalizedDistance = Mathf.Clamp(
            Vector3.Distance(transform.position, origin) / halfCityWidth, 0f, 1f);
        height *= Mathf.Lerp(nearHeightScale, 1f, normalizedDistance);
        float taperWidth = width * Random.Range(taperMin, taperMax);

        Vector3[] cubePositions = {
            new Vector3(-width * .5f, 0f, width * .5f),
            new Vector3(width * .5f, 0f, width * .5f),
            new Vector3(width * .5f, 0f, -width * .5f),
            new Vector3(-width * .5f, 0f, -width * .5f),
            new Vector3(-taperWidth * .5f, height, taperWidth * .5f),
            new Vector3(taperWidth * .5f, height, taperWidth * .5f),
            new Vector3(taperWidth * .5f, height, -taperWidth * .5f),
            new Vector3(-taperWidth * .5f, height, -taperWidth * .5f),
        };
        for(int i = 0; i < cubePositions.Length; ++i) {
            cubePositions[i] += origin;
        }

        float offset = (width - taperWidth) / 2;
        Vector2[] bottomUVs = {
            new Vector2(width, 0),
            new Vector2(0, 0),
            new Vector2(0, width),
            new Vector2(width, width)
        };
        Vector2[] sideUVs = {
            new Vector2(width, 0f),
            new Vector2(0f, 0f),
            new Vector2(offset, height),
            new Vector2(width - offset, height)
        };
        Vector2[] topUVs = {
            new Vector2(width - offset, offset),
            new Vector2(offset, offset),
            new Vector2(offset, width - offset),
            new Vector2(width - offset, width - offset)
        };

        Color cubeColor = Color.HSVToRGB(
            Random.Range(hueMin, hueMax),
            Random.Range(saturationMin, saturationMax),
            Random.Range(valueMin, valueMax));
        Color[] colors = { cubeColor, cubeColor, cubeColor, cubeColor };

        // Bottom
        quadMesh.AddQuad(
            new Vector3[] {cubePositions[3], cubePositions[2], cubePositions[1], cubePositions[0]},
            new Vector3[] {Vector3.down, Vector3.down, Vector3.down, Vector3.down},
            bottomUVs, colors, transform );
        // Left
        quadMesh.AddQuad(
            new Vector3[] {cubePositions[3], cubePositions[0], cubePositions[4], cubePositions[7]},
            new Vector3[] {Vector3.left, Vector3.left, Vector3.left, Vector3.left},
            sideUVs, colors, transform );
        // Front
        quadMesh.AddQuad(
            new Vector3[] {cubePositions[0], cubePositions[1], cubePositions[5], cubePositions[4]},
            new Vector3[] {Vector3.forward, Vector3.forward, Vector3.forward, Vector3.forward},
            sideUVs, colors, transform );
        // Back
        quadMesh.AddQuad(
            new Vector3[] {cubePositions[2], cubePositions[3], cubePositions[7], cubePositions[6]},
            new Vector3[] {Vector3.back, Vector3.back, Vector3.back, Vector3.back},
            sideUVs, colors, transform );
        // Right
        quadMesh.AddQuad(
            new Vector3[] {cubePositions[1], cubePositions[2], cubePositions[6], cubePositions[5]},
            new Vector3[] {Vector3.right, Vector3.right, Vector3.right, Vector3.right},
            sideUVs, colors, transform );
        // Top
        quadMesh.AddQuad(
            new Vector3[] {cubePositions[4], cubePositions[5], cubePositions[6], cubePositions[7]},
            new Vector3[] {Vector3.up, Vector3.up, Vector3.up, Vector3.up},
            topUVs, colors, transform );
    }

    /// <summary>
    /// Computes the length of a side of the cityscape.
    /// </summary>
    private float ComputeCityWidth() {
        return width * structures + spacing * (structures - 1);
    }
}
