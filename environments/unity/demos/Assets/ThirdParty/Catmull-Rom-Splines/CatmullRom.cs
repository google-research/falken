using System;
using UnityEngine;
using System.Collections;
using System.Collections.Generic;

namespace JPBotelho
{
    /*
        Catmull-Rom splines are Hermite curves with special tangent values.
        Hermite curve formula:
        (2t^3 - 3t^2 + 1) * p0 + (t^3 - 2t^2 + t) * m0 + (-2t^3 + 3t^2) * p1 + (t^3 - t^2) * m1
        For points p0 and p1 passing through points m0 and m1 interpolated over t = [0, 1]
        Tangent M[k] = (P[k+1] - P[k-1]) / 2
    */
    public class CatmullRom
    {
        //Struct to keep position, normal and tangent of a spline point
        [System.Serializable]
        public struct CatmullRomPoint
        {
            public Vector3 position;
            public Vector3 tangent;
            public Vector3 normal;

            public CatmullRomPoint(Vector3 position, Vector3 tangent, Vector3 normal)
            {
                this.position = position;
                this.tangent = tangent;
                this.normal = normal;
            }
        }

        private int resolution; //Amount of points between control points. [Tesselation factor]
        private bool closedLoop;

        private CatmullRomPoint[] splinePoints; //Generated spline points

        private Vector3[] controlPoints;

        //Returns spline points. Count is contorolPoints * resolution + [resolution] points if closed loop.
        public CatmullRomPoint[] GetPoints()
        {
            if(splinePoints == null)
            {
                throw new System.NullReferenceException("Spline not Initialized!");
            }

            return splinePoints;
        }

        public CatmullRom(Transform[] controlPoints, int resolution, bool closedLoop)
        {
            if(controlPoints == null || controlPoints.Length <= 2 || resolution < 2)
            {
                throw new ArgumentException("Catmull Rom Error: Too few control points or resolution too small");
            }

            this.controlPoints = new Vector3[controlPoints.Length];
            for(int i = 0; i < controlPoints.Length; i++)
            {
                this.controlPoints[i] = controlPoints[i].position;
            }

            this.resolution = resolution;
            this.closedLoop = closedLoop;

            GenerateSplinePoints();
        }

        //Updates control points
        public void Update(Transform[] controlPoints)
        {
            if(controlPoints.Length <= 0 || controlPoints == null)
            {
                throw new ArgumentException("Invalid control points");
            }

            this.controlPoints = new Vector3[controlPoints.Length];
            for(int i = 0; i < controlPoints.Length; i++)
            {
                this.controlPoints[i] = controlPoints[i].position;
            }

            GenerateSplinePoints();
        }

        //Updates resolution and closed loop values
        public void Update(int resolution, bool closedLoop)
        {
            if(resolution < 2)
            {
                throw new ArgumentException("Invalid Resolution. Make sure it's >= 1");
            }
            this.resolution = resolution;
            this.closedLoop = closedLoop;

            GenerateSplinePoints();
        }

        //Draws a line between every point and the next.
        public void DrawSpline(Color color)
        {
            if(ValidatePoints())
            {
                for(int i = 0; i < splinePoints.Length; i++)
                {
                    if(i == splinePoints.Length - 1 && closedLoop)
                    {
                        Debug.DrawLine(splinePoints[i].position, splinePoints[0].position, color);
                    }
                    else if(i < splinePoints.Length - 1)
                    {
                        Debug.DrawLine(splinePoints[i].position, splinePoints[i+1].position, color);
                    }
                }
            }
        }

        public void DrawNormals(float extrusion, Color color)
        {
            if(ValidatePoints())
            {
                for(int i = 0; i < splinePoints.Length; i++)
                {
                    Debug.DrawLine(splinePoints[i].position, splinePoints[i].position + splinePoints[i].normal * extrusion, color);
                }
            }
        }

        public void DrawTangents(float extrusion, Color color)
        {
            if(ValidatePoints())
            {
                for(int i = 0; i < splinePoints.Length; i++)
                {
                    Debug.DrawLine(splinePoints[i].position, splinePoints[i].position + splinePoints[i].tangent * extrusion, color);
                }
            }
        }

        //Validates if splinePoints have been set already. Throws nullref exception.
        private bool ValidatePoints()
        {
            if(splinePoints == null)
            {
                throw new NullReferenceException("Spline not initialized!");
            }
            return splinePoints != null;
        }

        //Sets the length of the point array based on resolution/closed loop.
        private void InitializeProperties()
        {
            int pointsToCreate;
            if (closedLoop)
            {
                pointsToCreate = resolution * controlPoints.Length; //Loops back to the beggining, so no need to adjust for arrays starting at 0
            }
            else
            {
                pointsToCreate = resolution * (controlPoints.Length - 1);
            }

            splinePoints = new CatmullRomPoint[pointsToCreate];
        }

        //Math stuff to generate the spline points
        private void GenerateSplinePoints()
        {
            InitializeProperties();

            Vector3 p0, p1; //Start point, end point
            Vector3 m0, m1; //Tangents

            // First for loop goes through each individual control point and connects it to the next, so 0-1, 1-2, 2-3 and so on
            int closedAdjustment = closedLoop ? 0 : 1;
            for (int currentPoint = 0; currentPoint < controlPoints.Length - closedAdjustment; currentPoint++)
            {
                bool closedLoopFinalPoint = (closedLoop && currentPoint == controlPoints.Length - 1);

                p0 = controlPoints[currentPoint];

                if(closedLoopFinalPoint)
                {
                    p1 = controlPoints[0];
                }
                else
                {
                    p1 = controlPoints[currentPoint + 1];
                }

                // m0
                if (currentPoint == 0) // Tangent M[k] = (P[k+1] - P[k-1]) / 2
                {
                    if(closedLoop)
                    {
                        m0 = p1 - controlPoints[controlPoints.Length - 1];
                    }
                    else
                    {
                        m0 = p1 - p0;
                    }
                }
                else
                {
                    m0 = p1 - controlPoints[currentPoint - 1];
                }

                // m1
                if (closedLoop)
                {
                    if (currentPoint == controlPoints.Length - 1) //Last point case
                    {
                        m1 = controlPoints[(currentPoint + 2) % controlPoints.Length] - p0;
                    }
                    else if (currentPoint == 0) //First point case
                    {
                        m1 = controlPoints[currentPoint + 2] - p0;
                    }
                    else
                    {
                        m1 = controlPoints[(currentPoint + 2) % controlPoints.Length] - p0;
                    }
                }
                else
                {
                    if (currentPoint < controlPoints.Length - 2)
                    {
                        m1 = controlPoints[(currentPoint + 2) % controlPoints.Length] - p0;
                    }
                    else
                    {
                        m1 = p1 - p0;
                    }
                }

                m0 *= 0.5f; //Doing this here instead of  in every single above statement
                m1 *= 0.5f;

                float pointStep = 1.0f / resolution;

                if ((currentPoint == controlPoints.Length - 2 && !closedLoop) || closedLoopFinalPoint) //Final point
                {
                    pointStep = 1.0f / (resolution - 1);  // last point of last segment should reach p1
                }

                // Creates [resolution] points between this control point and the next
                for (int tesselatedPoint = 0; tesselatedPoint < resolution; tesselatedPoint++)
                {
                    float t = tesselatedPoint * pointStep;

                    CatmullRomPoint point = Evaluate(p0, p1, m0, m1, t);

                    splinePoints[currentPoint * resolution + tesselatedPoint] = point;
                }
            }
        }

        //Evaluates curve at t[0, 1]. Returns point/normal/tan struct. [0, 1] means clamped between 0 and 1.
        public static CatmullRomPoint Evaluate(Vector3 start, Vector3 end, Vector3 tanPoint1, Vector3 tanPoint2, float t)
        {
            Vector3 position = CalculatePosition(start, end, tanPoint1, tanPoint2, t);
            Vector3 tangent = CalculateTangent(start, end, tanPoint1, tanPoint2, t);
            Vector3 normal = NormalFromTangent(tangent);

            return new CatmullRomPoint(position, tangent, normal);
        }

        //Calculates curve position at t[0, 1]
        public static Vector3 CalculatePosition(Vector3 start, Vector3 end, Vector3 tanPoint1, Vector3 tanPoint2, float t)
        {
            // Hermite curve formula:
            // (2t^3 - 3t^2 + 1) * p0 + (t^3 - 2t^2 + t) * m0 + (-2t^3 + 3t^2) * p1 + (t^3 - t^2) * m1
            Vector3 position = (2.0f * t * t * t - 3.0f * t * t + 1.0f) * start
                + (t * t * t - 2.0f * t * t + t) * tanPoint1
                + (-2.0f * t * t * t + 3.0f * t * t) * end
                + (t * t * t - t * t) * tanPoint2;

            return position;
        }

        //Calculates tangent at t[0, 1]
        public static Vector3 CalculateTangent(Vector3 start, Vector3 end, Vector3 tanPoint1, Vector3 tanPoint2, float t)
        {
            // Calculate tangents
            // p'(t) = (6t² - 6t)p0 + (3t² - 4t + 1)m0 + (-6t² + 6t)p1 + (3t² - 2t)m1
            Vector3 tangent = (6 * t * t - 6 * t) * start
                + (3 * t * t - 4 * t + 1) * tanPoint1
                + (-6 * t * t + 6 * t) * end
                + (3 * t * t - 2 * t) * tanPoint2;

            return tangent.normalized;
        }

        //Calculates normal vector from tangent
        public static Vector3 NormalFromTangent(Vector3 tangent)
        {
            return Vector3.Cross(tangent, Vector3.up).normalized;
        }
    }
}