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
    public sealed class Vector3
    {
        /// <summary>
        /// X component of the vector.
        /// </summary>
        public float X
        {
            get
            {
                return _internalVector3.x;
            }
            set
            {
                _internalVector3.x = value;
            }
        }

        /// <summary>
        /// Y component of the vector.
        /// </summary>
        public float Y
        {
            get
            {
                return _internalVector3.y;
            }
            set
            {
                _internalVector3.y = value;
            }
        }

        /// <summary>
        /// Z component of the vector.
        /// </summary>
        public float Z
        {
            get
            {
                return _internalVector3.z;
            }
            set
            {
                _internalVector3.z = value;
            }
        }

        /// <summary>
        /// Default constructor. Set every component to 0.0f.
        /// </summary>
        public Vector3()
        {
            _internalVector3 = new FalkenInternal.falken.Vector3();
            X = 0.0f;
            Y = 0.0f;
            Z = 0.0f;
        }

        /// <summary>
        /// Construct a Vector3 with the given component values.
        /// </summary>
        public Vector3(float newX, float newY, float newZ) : this()
        {
            X = newX;
            Y = newY;
            Z = newZ;
        }

        /// <summary>
        /// Initialize the rotation with the internal Falken rotation class.
        /// </summary>
        internal Vector3(FalkenInternal.falken.Vector3 vector) : this()
        {
            X = vector.x;
            Y = vector.y;
            Z = vector.z;
        }

        /// <summary>
        /// Modify a falken internal vector with the instance's attributes.
        /// </summary>
        internal FalkenInternal.falken.Vector3 ToInternalVector3()
        {
            return _internalVector3;
        }

        private FalkenInternal.falken.Vector3 _internalVector3;
    }
}
