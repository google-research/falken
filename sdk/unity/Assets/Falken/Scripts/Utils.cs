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

namespace Falken
{
    /// <summary>
    /// <c>Utils</c> utilities required by the falken API.
    /// </summary>
    internal class Utils
    {

        /// <summary>
        /// Convert an angle from radians to degrees.
        /// </summary>
        /// <param name="angle">Angle in radians.</param>
        /// <returns>Angle in degrees.</returns>
        public static float RadiansToDegrees(float angle)
        {
            return (angle / (float)Math.PI) * 180.0f;
        }

        /// <summary>
        /// Convert an angle from degrees to radians.
        /// </summary>
        /// <param name="angle">Angle in degrees.</param>
        /// <returns>Angle in radians.</returns>
        public static float DegreesToRadians(float angle)
        {
            return (angle / 180.0f) * (float)Math.PI;
        }
    }
}
