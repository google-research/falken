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
/// <c>QuadMesh</c> Utility class that stores a mesh of quads and converts it into a unity Mesh.
/// </summary>
class QuadMesh {
    struct Quad {
        public Vector3[] positions;
        public Vector3[] normals;
        public Vector2[] uvs;
        public Color[] colors;
    }

    private List<Quad> quads = new List<Quad>();

    /// <summary>
    /// Adds a single quad to the mesh datastructure.
    /// </summary>
    public void AddQuad(Vector3[] positions, Vector3[] normals, Vector2[] uvs, Color[] colors,
        Transform transform) {
        Debug.Assert(positions.Length == 4);
        Debug.Assert(normals.Length == 4);
        Debug.Assert(uvs.Length == 4);
        Debug.Assert(colors == null || colors.Length == 4);
        Quad quad = new Quad {
            positions = positions, normals = normals, uvs = uvs, colors = colors
        };
        if (quad.colors == null) {
            quad.colors = new Color[] { Color.white, Color.white, Color.white, Color.white };
        }
        for (int i = 0; i < 4; ++i) {
            quad.positions[i] = transform.InverseTransformPoint(quad.positions[i]);
            quad.normals[i] = transform.InverseTransformDirection(quad.normals[i]);
        }
        quads.Add(quad);
    }

    /// <summary>
    /// Adds a single quad to the mesh datastructure.
    /// </summary>
    public void AddQuad(Vector3[] positions, Vector3[] normals, Vector2[] uvs,
        Transform transform) {
        AddQuad(positions, normals, uvs, null, transform);
    }

    /// <summary>
    /// Appends the data in this quad-mesh to the passed in Unity mesh.
    /// </summary>
    public void AddToMesh(ref Mesh mesh, int subMeshIndex = -1) {
        bool subMesh = subMeshIndex >= 0;
        List<Vector3> positions = new List<Vector3>(mesh.vertices);
        List<Vector3> normals  = new List<Vector3>(mesh.normals);
        List<Vector2> uvs = new List<Vector2>(mesh.uv);
        List<Color> colors = new List<Color>(mesh.colors);
        List<int> indices = subMesh ? new List<int>() :  new List<int>(mesh.triangles);
        for (int i = 0; i < quads.Count; ++i) {
            int baseIndex = positions.Count;
            positions.AddRange(quads[i].positions);
            normals.AddRange(quads[i].normals);
            uvs.AddRange(quads[i].uvs);
            colors.AddRange(quads[i].colors);
            int[] quadIndices = { baseIndex + 0, baseIndex + 1, baseIndex + 2,
                                  baseIndex + 0, baseIndex + 2, baseIndex + 3 };
            indices.AddRange(quadIndices);
        }
        mesh.vertices = positions.ToArray();
        mesh.normals = normals.ToArray();
        mesh.uv = uvs.ToArray();
        mesh.colors = colors.ToArray();

        if (subMeshIndex >= 0) {
            Debug.Assert(subMeshIndex < mesh.subMeshCount);
            mesh.SetIndices(indices.ToArray(), MeshTopology.Triangles, subMeshIndex);
        } else {
            mesh.triangles = indices.ToArray();
        }
    }
}