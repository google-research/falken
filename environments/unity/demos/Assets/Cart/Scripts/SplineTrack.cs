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
using JPBotelho;

/// <summary>
/// <c>SplineTrack</c> Race track representation and tools for quickly creating new tracks.
/// </summary>
[ExecuteInEditMode]
public class SplineTrack : MonoBehaviour
{
    [Tooltip("True creates a circular track. False creates a linear track.")]
    public bool loop;
    [Tooltip("The number of control points to create for this track.")]
    [Range(4, 100)]
    public int handles = 10;
    [Tooltip("The length of the track.")]
    [Range(10, 10000)]
    public float length = 1000;
    [Tooltip("The length of the road surface of the track.")]
    [Range(1, 20)]
    public float width = 2;
    [Tooltip("The height of the curb around the track.")]
    [Range(0, 10)]
    public float curbHeight = 0.5f;
    [Tooltip("The thickness of the curb around the track.")]
    [Range(0, 10)]
    public float curbWidth = 0.5f;
    [Tooltip("The resolution of the track mesh. Higher numbers create smoother geometry.")]
    [Range(1, 100)]
    public int resolution = 10;
    [Tooltip("The material to apply to the road.")]
    public Material roadMat;
    [Tooltip("The layer for the road.")]
    public LayerMask roadLayer;
    [Tooltip("The material to apply to the curb.")]
    public Material curbMat;
    [Tooltip("The layer for the curb.")]
    public LayerMask curbLayer;

        /// <summary>
    /// Returns the control points that define the track.
    /// </summary>
    public Transform[] GetControlPoints() { return controlPoints; }

    [SerializeField] [HideInInspector]
    private Transform[] controlPoints;
    [SerializeField] [HideInInspector]
    private GameObject road;
    [SerializeField] [HideInInspector]
    private GameObject curb;

#if UNITY_EDITOR
    private CatmullRom spline;
    private bool dirty = false;

    /// <summary>
    /// Creates baseline track data, including control points and mesh, from input params.
    /// </summary>
    public void CreateTrack() {
        if(controlPoints != null) {
            for (int i = 0; i < controlPoints.Length; ++i) {
                if (controlPoints[i]) {
                    GameObject.DestroyImmediate(controlPoints[i].gameObject);
                }
            }
        }

        if (road) {
            DestroyImmediate(road);
        }
        if (curb) {
            DestroyImmediate(curb);
        }

        float theta = 0f;
        Func<Vector3> calculateControlPoint;
        if (loop) {
            float increment = (2f * Mathf.PI) / handles;
            float radius = length / (2f * Mathf.PI);
            calculateControlPoint = () => {
                var position = new Vector3(radius * Mathf.Cos(theta), 0f,
                                            radius * Mathf.Sin(theta));
                theta += increment;
                return position;
            };
        }
        else {
            Vector3 controlPointPos = transform.forward * length * -0.5f;
            float stepSize = length / handles;
            calculateControlPoint = () => {
                var position = new Vector3(controlPointPos.x, controlPointPos.y, controlPointPos.z);
                controlPointPos += transform.forward * stepSize;
                return position;
            };
        }
        controlPoints = new Transform[handles];
        for (int i = 0; i < handles; ++i) {
            GameObject controlPoint = new GameObject("ControlPoint_" + i);
            controlPoint.transform.parent = transform;
            controlPoint.transform.localPosition = calculateControlPoint();
            controlPoint.transform.localRotation = Quaternion.identity;
            controlPoints[i] = controlPoint.transform;
        }

        road = CreateSubObject("Road", roadMat, roadLayer);
        curb = CreateSubObject("Curb", curbMat, curbLayer);

        dirty = true;
    }

    void OnValidate() {
        dirty = true;
    }

    void Start() {
        dirty = true;
    }

    void Update() {
        if (controlPoints != null) {
            for (int i = 0; i < controlPoints.Length; ++i) {
                var controlPoint = controlPoints[i];
                if (controlPoint != null) {
                    dirty |= controlPoint.hasChanged;
                    controlPoint.hasChanged = false;
                }
            }
        }

        if (dirty && controlPoints != null && controlPoints.Length > 4) {
            spline = new CatmullRom(controlPoints, resolution, loop);
            CatmullRom.CatmullRomPoint[] splinePoints = spline.GetPoints();
            int endIndex = loop ? controlPoints.Length : controlPoints.Length - 1;
            for (int i = 0; i < endIndex; ++i) {
                int controlPointIndex = i * resolution;
                int nextPointIndex = controlPointIndex + 1;
                Vector3 tangent = CatmullRom.CalculateTangent(
                    splinePoints[controlPointIndex].position, splinePoints[nextPointIndex].position,
                    splinePoints[controlPointIndex].tangent, splinePoints[nextPointIndex].tangent,
                    0f);
                tangent.y = 0;
                controlPoints[i].rotation = Quaternion.LookRotation(tangent.normalized,
                    controlPoints[i].up);
            }

            CreateTrackMesh();
            dirty = false;
        }
    }

    /// <summary>
    /// Creates the road and curb meshes based on the track spline and related parameters.
    /// </summary>
    private void CreateTrackMesh() {
        List<Vector3> vertices = new List<Vector3>();
        List<Vector3> normals = new List<Vector3>();
        List<Vector2> uvs = new List<Vector2>();
        List<int> triangles = new List<int>();

        CatmullRom.CatmullRomPoint[] points = spline.GetPoints();

        float splineLength = 0;
        for (int i = 0; i < points.Length - 1; ++i) {
            splineLength += Vector3.Distance(points[i].position, points[i + 1].position);
        }

        QuadMesh roadMesh = new QuadMesh();
        QuadMesh curbMesh = new QuadMesh();
        float uvIncrement = splineLength / points.Length;
        float prevV = 0f;
        for (int i = 0; i < points.Length - 1; ++i) {
            int prevControlIndex = i / resolution;
            int nextControlIndex = (prevControlIndex + 1) % controlPoints.Length;
            int controlRelativeIndex = prevControlIndex * resolution;
            Transform prevControl = controlPoints[prevControlIndex];
            Transform nextControl = controlPoints[nextControlIndex];

            Vector3 center = points[i].position;
            Vector3 normal = points[i].normal;
            normal.y -= Mathf.Lerp(prevControl.right.y, nextControl.right.y,
                (i - controlRelativeIndex) / (float)resolution);
            normal.Normalize();
            Vector3 left = center + normal * width * 0.5f;
            Vector3 right = center - normal * width * 0.5f;

            Vector3 next = points[i + 1].position;
            Vector3 nextNormal = points[i + 1].normal;
            nextNormal.y -= Mathf.Lerp(prevControl.right.y, nextControl.right.y,
                (i + 1 - controlRelativeIndex) / (float)resolution);
            nextNormal.Normalize();
            Vector3 nextLeft = next + nextNormal * width * 0.5f;
            Vector3 nextRight = next - nextNormal * width * 0.5f;

            // Road surface
            Vector3[] roadVerts = { left, nextLeft, nextRight, right };
            Vector3[] roadNorms = { Vector3.up, Vector3.up, Vector3.up, Vector3.up };
            float minV = prevV;
            float maxV = minV + uvIncrement;
            Vector2[] roadUVs = { new Vector2(0, minV), new Vector2(0, maxV),
                                  new Vector2(1f, maxV), new Vector2(1f, minV) };
            prevV = maxV;
            roadMesh.AddQuad(roadVerts, roadNorms, roadUVs, transform);

            // Curbs
            Vector3 curbOffsetY = new Vector3(0, curbHeight, 0);
            Vector3[] curbTopNormals = { Vector3.up, Vector3.up, Vector3.up, Vector3.up };

            // Left Curb
            Vector3 leftInnerBottom = left;
            leftInnerBottom.y = 0f;
            Vector3 leftInnerTop = left + curbOffsetY;
            Vector3 nextLeftInnerBottom = nextLeft;
            nextLeftInnerBottom.y = 0f;
            Vector3 nextLeftInnerTop = nextLeft + curbOffsetY;
            Vector3[] leftCurbFaceVerts = {
                leftInnerBottom, leftInnerTop, nextLeftInnerTop, nextLeftInnerBottom
            };
            Vector3[] leftCurbFaceNormals = {
                -normal, -normal, -nextNormal, -nextNormal
            };
            Vector2[] leftCurbFaceUVs = {
                new Vector2(minV, 0), new Vector2(minV, curbHeight),
                new Vector2(maxV, curbHeight), new Vector2(maxV, 0)
            };
            curbMesh.AddQuad(leftCurbFaceVerts, leftCurbFaceNormals, leftCurbFaceUVs, transform);

            Vector3 leftOuterTop = leftInnerTop + normal * curbWidth;
            Vector3 nextLeftOuterTop = nextLeftInnerTop + nextNormal * curbWidth;
            Vector3[] leftCurbTopVerts = {
                leftInnerTop, leftOuterTop, nextLeftOuterTop, nextLeftInnerTop
            };
            Vector2[] leftCurbTopUVs = {
                new Vector2(0, minV), new Vector2(curbWidth, minV),
                new Vector2(curbWidth, maxV), new Vector2(0, maxV)
            };
            curbMesh.AddQuad(leftCurbTopVerts, curbTopNormals, leftCurbTopUVs, transform);

            Vector3 leftOuterBottom = leftOuterTop;
            leftOuterBottom.y = 0f;
            Vector3 nextLeftOuterBottom = nextLeftOuterTop;
            nextLeftOuterBottom.y = 0f;
            Vector3[] leftCurbBackVerts = {
                leftOuterTop, leftOuterBottom, nextLeftOuterBottom, nextLeftOuterTop
            };
            Vector3[] leftCurbBackNormals = {
                normal, normal, nextNormal, nextNormal
            };
            curbMesh.AddQuad(leftCurbBackVerts, leftCurbBackNormals, leftCurbFaceUVs, transform);

            // Right Curb
            Vector3 rightInnerBottom = right;
            rightInnerBottom.y = 0f;
            Vector3 rightInnerTop = right + curbOffsetY;
            Vector3 nextRightInnerBottom = nextRight;
            nextRightInnerBottom.y = 0f;
            Vector3 nextRightInnerTop = nextRight + curbOffsetY;
            Vector3[] rightCurbFaceVerts = {
                rightInnerBottom, nextRightInnerBottom, nextRightInnerTop, rightInnerTop
            };
            Vector3[] rightCurbFaceNormals = {
                normal, nextNormal, nextNormal, normal
            };
            Vector2[] rightCurbFaceUVs = {
                new Vector2(minV, 0), new Vector2(maxV, 0),
                new Vector2(maxV, curbHeight), new Vector2(minV, curbHeight)
            };
            curbMesh.AddQuad(rightCurbFaceVerts, rightCurbFaceNormals, rightCurbFaceUVs, transform);

            Vector3 rightOuterTop = rightInnerTop - normal * curbWidth;
            Vector3 nextRightOuterTop = nextRightInnerTop - nextNormal * curbWidth;
            Vector3[] rightCurbTopVerts = {
                rightInnerTop, nextRightInnerTop, nextRightOuterTop, rightOuterTop,
            };
            Vector2[] rightCurbTopUVs = {
                new Vector2(0, minV), new Vector2(0, maxV),
                new Vector2(curbWidth, maxV), new Vector2(curbWidth, minV)
            };
            curbMesh.AddQuad(rightCurbTopVerts, curbTopNormals, rightCurbTopUVs, transform);

            Vector3 rightOuterBottom = rightOuterTop;
            rightOuterBottom.y = 0f;
            Vector3 nextRightOuterBottom = nextRightOuterTop;
            nextRightOuterBottom.y = 0f;
            Vector3[] rightCurbBackVerts = {
                    rightOuterTop, nextRightOuterTop, nextRightOuterBottom, rightOuterBottom
            };
            Vector3[] rightCurbBackNormals = {
                -normal, -nextNormal, -nextNormal, -normal
            };
            curbMesh.AddQuad(rightCurbBackVerts, rightCurbBackNormals, rightCurbFaceUVs, transform);
        }

        SetSubObject(road, roadMesh);
        SetSubObject(curb, curbMesh);
    }

    /// <summary>
    /// Creates a sub-object (i.e. road or curb)
    /// </summary>
    private GameObject CreateSubObject(string name, Material material, LayerMask layer) {
        GameObject subObject = new GameObject(name);
        subObject.transform.parent = transform;
        subObject.layer = layer >> 1;
        subObject.AddComponent<MeshFilter>();
        subObject.AddComponent<MeshCollider>();
        MeshRenderer renderer = subObject.AddComponent<MeshRenderer>();
        renderer.sharedMaterial = material;
        return subObject;
    }

    /// <summary>
    /// Updates the mesh of a sub-object.
    /// </summary>
    private void SetSubObject(GameObject subObject, QuadMesh quadMesh) {
        MeshFilter meshFilter = subObject.GetComponent<MeshFilter>();
        Mesh mesh = meshFilter.sharedMesh;
        if (mesh) {
            mesh.Clear();
        } else {
            mesh = new Mesh();
            meshFilter.sharedMesh = mesh;
        }
        quadMesh.AddToMesh(ref mesh);
        MeshCollider meshCollider = subObject.GetComponent<MeshCollider>();
        meshCollider.sharedMesh = mesh;
    }
#endif // UNITY_EDITOR
}
