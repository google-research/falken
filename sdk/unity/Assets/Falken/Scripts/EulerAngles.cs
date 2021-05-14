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
    /// <c>Vector3</c> defines a class for representing Vectors in space.
    /// </summary>
    [Serializable]
    public sealed class EulerAngles
    {
        /// <summary>
        /// Roll component of the angles. Values are in degrees.
        /// </summary>
        public float Roll
        {
            get
            {
                return Utils.RadiansToDegrees(_internalEulerAngles.roll);
            }
            set
            {
                _internalEulerAngles.roll = Utils.DegreesToRadians(value);
            }
        }

        /// <summary>
        /// Pitch component of the angles. Values are in degrees.
        /// </summary>
        public float Pitch
        {
            get
            {
                return Utils.RadiansToDegrees(_internalEulerAngles.pitch);
            }
            set
            {
                _internalEulerAngles.pitch = Utils.DegreesToRadians(value);
            }
        }

        /// <summary>
        /// Yaw component of the angles. Values are in degrees.
        /// </summary>
        public float Yaw
        {
            get
            {
                return Utils.RadiansToDegrees(_internalEulerAngles.yaw);
            }
            set
            {
                _internalEulerAngles.yaw = Utils.DegreesToRadians(value);
            }
        }

        /// <summary>
        /// Default constructor. Set every component to 0.0f.
        /// </summary>
        public EulerAngles()
        {
            _internalEulerAngles = new FalkenInternal.falken.EulerAngles();
            Roll = 0.0f;
            Pitch = 0.0f;
            Yaw = 0.0f;
        }

        /// <summary>
        /// Construct an EulerAngles with the given component values. Values are in degrees.
        /// </summary>
        public EulerAngles(float newRoll, float newPitch, float newYaw) : this()
        {
            Roll = newRoll;
            Pitch = newPitch;
            Yaw = newYaw;
        }

        /// <summary>
        /// Initialize the EulerAngles with the internal Falken EulerAngles class.
        /// Values are in degrees.
        /// </summary>
        internal EulerAngles(FalkenInternal.falken.EulerAngles angles) : this()
        {
            // When working with internal EulerAngles, there is no need to convert to radians.
            _internalEulerAngles = angles;
        }

        /// <summary>
        /// Modify a falken internal EulerAngles with the instance's attributes.
        /// </summary>
        internal FalkenInternal.falken.EulerAngles ToInternalEulerAngles()
        {
            return _internalEulerAngles;
        }

        private FalkenInternal.falken.EulerAngles _internalEulerAngles;
    }
}
