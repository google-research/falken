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
using System.Collections.Generic;
using System.Reflection;

namespace Falken
{

    /// <summary>
    /// <c>Feelers</c> Establishes a connection with a Falken's FeelerAttribute.
    /// </summary>
    public class Feelers : Falken.AttributeBase
    {

        /// <summary>
        /// <c>InvalidFeelerPropertiesException</c> thrown when
        /// there are invalid properties defined in a
        /// FeelersProperties class.
        /// </summary>
        [Serializable]
        public class InvalidFeelerPropertiesException : Exception
        {
            internal InvalidFeelerPropertiesException()
            {
            }

            internal InvalidFeelerPropertiesException(string message)
              : base(message) { }

            internal InvalidFeelerPropertiesException(
              string message, Exception inner) : base(message, inner) { }
        }

        // Length of the feeler.
        private float _length;
        // Thickness of the feeler.
        private float _thickness;
        private float _fovAngle;

        /// <summary>
        /// Get feeler's length.
        /// </summary>
        public float Length
        {
            get
            {
                return _length;
            }
        }

        /// <summary>
        /// Get feeler's thickness.
        /// </summary>
        public float Thickness
        {
            get
            {
                return _thickness;
            }
        }

        /// <summary>
        /// Get feeler's field of view (FoV) angle in degrees.
        /// </summary>
        public float FovAngle
        {
            get
            {
                return _fovAngle;
            }
        }

        // Store the names of the ids.
        private List<string> _feelerIdNames = new List<string>();
        // Feeler distances bound to the internal Falken's representation.
        private List<Falken.Number> _distances = new List<Falken.Number>();
        // Feeler ids bound to the internal Falken's representation.
        private List<Falken.Category> _ids = new List<Falken.Category>();

        /// <summary>
        /// Get the names used for feeler's ids.
        /// </summary>
        public List<string> IdNames
        {
            get
            {
                return _feelerIdNames;
            }
        }

        /// <summary>
        /// Get feeler's distances.
        /// </summary>
        public List<Falken.Number> Distances
        {
            get
            {
                return _distances;
            }
        }

        /// <summary>
        /// Get feeler's ids.
        /// </summary>
        public List<Falken.Category> Ids
        {
            get
            {
                return _ids;
            }
        }

        /// <summary>
        /// Verify that the given object can be converted/assigned
        /// to a feelers object.
        /// </summary>
        static internal bool CanConvertToFeelersType(object obj)
        {
            Type objType = obj.GetType();
            return objType.IsSubclassOf(typeof(Feelers)) ||
              objType == typeof(Feelers);
        }

        /// <summary>
        /// Initialize's feeler attributes.
        /// </summary>
        /// <param name="length">Length of each feeler.</param>
        /// <param name="thickness">Thickness value for spherical raycast.
        /// This parameter should be set to 0 if ray casts have no volume.</param>
        /// <param name="fieldOfView">Field of view angle in degrees.</param>
        /// <param name="numberOfFeelers">Number of feelers.</param>
        /// <param name="ids">Categories for the feelers.</param>
        /// <exception> InvalidOperationException thrown if no feelers count is zero and
        ///  ids is null or empty.</exception>
        private void Initialize(float length, float thickness, float fieldOfView,
                                int numberOfFeelers, List<string> ids)
        {
            _length = length;
            _thickness = thickness;
            if (numberOfFeelers == 1 && fieldOfView != 0.0f)
            {
                Log.Warning("A Feeler attribute with 1 feeler and FoV angle different than 0.0 " +
                            $"is not allowed. Changing FoV angle from {fieldOfView} to 0.0");
                fieldOfView = 0.0f;
            }
            _fovAngle = fieldOfView;
            for (int i = 0; i < numberOfFeelers; ++i)
            {
                string distanceName = "distance_" + i.ToString();
                _distances.Add(new Falken.Number(distanceName, 0.0f, length));
            }
            if (ids != null && ids.Count > 0)
            {
                _feelerIdNames = ids;
                for (int i = 0; i < numberOfFeelers; ++i)
                {
                    string id = "id_" + i.ToString();
                    _ids.Add(new Falken.Category(id, ids));
                }
            }
            if (_ids.Count == 0 && _distances.Count == 0)
            {
                throw new InvalidOperationException("Can't construct empty Feelers.");
            }
        }

        /// <summary>
        /// Create an empty Falken.Feelers. DO NOT USE.
        /// This is used internally only.
        /// </summary>
        public Feelers()
        {
        }

        /// <summary>
        /// Create an empty Falken.Feelers that will be bound later
        /// using a field from a class that contains this attribute.
        /// </summary>
        /// <param name="length">Length of each feeler.</param>
        /// <param name="thickness">Thickness value for spherical raycast.
        /// This parameter should be set to 0 if ray casts have no volume.</param>
        /// <param name="fieldOfView">Field of view angle in degrees.</param>
        /// <param name="numberOfFeelers">Number of feelers.</param>
        /// <param name="recordDistances">Whether distances should be recorded. This parameter
        /// is present only for backwards compatibility, and should now be always set
        /// to true.</param>
        /// <param name="ids">Categories for the feelers. This parameter can't be empty if
        /// recordDistances is set to false.</param>
        [ObsoleteAttribute("This constructor is deprecated, since distances are no longer " +
                           "optional. Use Feelers(float length, float thickness, " +
                           "float fieldOfView, int numberOfFeelers, List<string> ids) " +
                           "instead.", false)]
        public Feelers(float length, float thickness, float fieldOfView, int numberOfFeelers,
                       bool recordDistances, List<string> ids)
        {
            if (!recordDistances)
            {
                throw new InvalidOperationException(
                    "Constructing Feelers with recordDistances == false is not valid anymore.");
            }
            Initialize(length, thickness, fieldOfView, numberOfFeelers, ids);
        }

        /// <summary>
        /// Create a dynamic Falken.Feelers.
        /// </summary>
        /// <param name="name">Name of the feelers attribute.</param>
        /// <param name="length">Length of each feeler.</param>
        /// <param name="thickness">Thickness value for spherical raycast.
        /// This parameter should be set to 0 if ray casts have no volume.</param>
        /// <param name="fieldOfView">Field of view angle in degrees.</param>
        /// <param name="numberOfFeelers">Number of feelers.</param>
        /// <param name="recordDistances">Whether distances should be recorded. This parameter
        /// is present only for backwards compatibility, and should now be always set
        /// to true.</param>
        /// <param name="ids">Categories for the feelers. This parameter can't be empty if
        /// recordDistances is set to false.</param>
        [ObsoleteAttribute("This constructor is deprecated, since distances are no longer " +
                           "optional. Use Feelers(string name, float length, float thickness, " +
                           "float fieldOfView, int numberOfFeelers, List<string> ids) " +
                           "instead.", false)]
        public Feelers(string name, float length, float thickness, float fieldOfView,
                       int numberOfFeelers, bool recordDistances, List<string> ids) : base(name)
        {
            if (!recordDistances)
            {
                throw new InvalidOperationException(
                    "Constructing Feelers with recordDistances == false is not valid anymore.");
            }
            Initialize(length, thickness, fieldOfView, numberOfFeelers, ids);
        }

        /// <summary>
        /// Create an empty Falken.Feelers that will be bound later
        /// using a field from a class that contains this attribute.
        /// </summary>
        /// <param name="length">Length of each feeler.</param>
        /// <param name="thickness">Thickness value for spherical raycast.
        /// This parameter should be set to 0 if ray casts have no volume.</param>
        /// <param name="fieldOfView">Field of view angle in degrees.</param>
        /// <param name="numberOfFeelers">Number of feelers.</param>
        /// <param name="ids">Categories for the feelers.</param>
        public Feelers(float length, float thickness, float fieldOfView, int numberOfFeelers,
                       List<string> ids)
        {
            Initialize(length, thickness, fieldOfView, numberOfFeelers, ids);
        }

        /// <summary>
        /// Create a dynamic Falken.Feelers.
        /// </summary>
        /// <param name="name">Name of the feelers attribute.</param>
        /// <param name="length">Length of each feeler.</param>
        /// <param name="thickness">Thickness value for spherical raycast.
        /// This parameter should be set to 0 if ray casts have no volume.</param>
        /// <param name="fieldOfView">Field of view angle in degrees.</param>
        /// <param name="numberOfFeelers">Number of feelers.</param>
        /// <param name="ids">Categories for the feelers.</param>
        public Feelers(string name, float length, float thickness, float fieldOfView,
                       int numberOfFeelers, List<string> ids) : base(name)
        {
            Initialize(length, thickness, fieldOfView, numberOfFeelers, ids);
        }

        /// <summary>
        /// Establish a connection between a C# attribute and a Falken's attribute.
        /// </summary>
        /// <param name="fieldInfo">Metadata information of the field this is being bound
        /// to.</param>
        /// <param name="fieldContainer">Object that contains the value of the field.</param>
        /// <param name="container">Internal container to add the attribute to.</param>
        /// <exception>AlreadyBoundException thrown when trying to bind the attribute when it was
        /// bound already.</exception>
        internal override void BindAttribute(FieldInfo fieldInfo, object fieldContainer,
                                             FalkenInternal.falken.AttributeContainer container)
        {
            SetNameToFieldName(fieldInfo, fieldContainer);
            ThrowIfBound(fieldInfo);
            if (fieldInfo == null || fieldContainer == null ||
                !CanConvertToGivenType(typeof(Feelers), fieldInfo.GetValue(fieldContainer)))
            {
                ClearBindings();
            }
            SetFalkenInternalAttribute(
                new FalkenInternal.falken.AttributeBase(
                    container, _name, Distances.Count > 0 ? Distances.Count : Ids.Count,
                    Length, Utils.DegreesToRadians(FovAngle), Thickness,
                    new FalkenInternal.std.StringVector(IdNames.ToArray())),
                fieldInfo, fieldContainer);
        }

        /// <summary>
        /// Clear all field and attribute bindings.
        /// </summary>
        protected override void ClearBindings()
        {
            base.ClearBindings();
        }

        /// <summary>
        /// Bind the distances and ids to a Falken.Number and Falken.Category respectively.
        /// </summary>
        private void BindFeelerDistancesAndIds()
        {
            // If both are empty, this means that the
            // attribute is being loaded, therefore we have
            // to retrieve all the attribute's information.
            if (Distances.Count == 0 && Ids.Count == 0)
            {
                int numberOfFeelers;
                List<string> idNames;
                if (_attribute.feelers_ids().Count > 0)
                {
                    numberOfFeelers = _attribute.feelers_ids().Count;
                    idNames = new List<string>(_attribute.feelers_ids()[0].category_values());
                }
                else
                {
                    numberOfFeelers = _attribute.feelers_distances().Count;
                    idNames = null;
                }
                Initialize(_attribute.feelers_length(), _attribute.feelers_thickness(),
                           Utils.RadiansToDegrees(_attribute.feelers_fov_angle()), numberOfFeelers,
                           idNames);
            }
            int index = 0;
            foreach (FalkenInternal.falken.NumberAttribute distance in
                _attribute.feelers_distances())
            {
                Falken.Number feelerDistance = Distances[index];
                feelerDistance.SetFalkenInternalAttribute(distance, null, null);
                ++index;
            }
            index = 0;
            foreach (FalkenInternal.falken.CategoricalAttribute id in _attribute.feelers_ids())
            {
                Falken.Category feelerId = Ids[index];
                feelerId.SetFalkenInternalAttribute(id, null, null);
                ++index;
            }
        }

        /// <summary>
        /// Change internal attribute. Also do so for
        /// the feeler ids and distances.
        /// </summary>
        internal override void Rebind(
          FalkenInternal.falken.AttributeBase attributeBase)
        {
            base.Rebind(attributeBase);
            BindFeelerDistancesAndIds();
        }

        /// <summary>
        /// Read a field value and cast to the attribute's data type.
        /// </summary>
        /// <returns>Field value or null if it can't be converted to the required type or
        /// the attribute isn't bound to a field.</returns>
        internal override object ReadField()
        {
            return null;
        }

        /// <summary>
        /// Subclasses that use a separate C# representation of attribute value must reflect the
        /// C# value into the underlying attribute in this method.
        /// </summary>
        internal override void Read()
        {
            // A feeler is updated whenever one changes the distance or the id
            // value. Since we access those values directly, there's no need
            // to do anything here.
        }

        /// <summary>
        /// Call parent implementation. Also bind feeler's distance and ids.
        /// </summary>
        /// <param name="attributeBase">Internal attribute to associate with this instance.</param>
        /// <param name="field">Field metadata for a field on the fieldValue object.</param>
        /// <param name="fieldValue">Object that contains the field.</param>
        internal override void SetFalkenInternalAttribute(
          FalkenInternal.falken.AttributeBase attributeBase, FieldInfo field, object fieldValue)
        {
            base.SetFalkenInternalAttribute(attributeBase, field, fieldValue);
            BindFeelerDistancesAndIds();
        }

        /// <summary>
        /// Update C# field's value to match Falken's attribute value.
        /// </summary>
        internal override void Write()
        {
            // There's nothing to do here since distances and ids
            // are read/set from/to Falken's attribute directly,
            // therefore any update over them will be reflected
            // to the list of attributes we store in this class.
        }

        /// <summary>
        /// Get the angle which we start sensing in degrees.
        /// </summary>
        private float StartAngle
        {
            get
            {
                return -1.0f * FovAngle / 2.0f;
            }
        }

        /// <summary>
        /// Get the angle between each feeler in degrees.
        /// </summary>
        private float DeltaAngle
        {
            get
            {
                if (Distances.Count > 1)
                {
                    return FovAngle / (Distances.Count - 1);
                }
                return 0.0f;
            }
        }

        /// <summary>
        /// Returns the angle (in degrees) to cast out the feeler with the given index.
        /// </summary>
        private float YawAngleForFeeler(int index)
        {
            return StartAngle + (index * DeltaAngle);
        }

#if UNITY_5_3_OR_NEWER
        /// <summary>
        /// Updates the state of the Feelers object by casting rays into the
        /// scene, recording both the distance and id of the part of the world
        /// sensed by the feeler.
        /// </summary>
        /// <remarks>This method is only available in the Unity SDK.</remarks>
        public virtual void Update(
          UnityEngine.Transform epicenter, UnityEngine.Vector3 offset, bool debugRender,
          int layerMask = UnityEngine.Physics.DefaultRaycastLayers)
        {
            for (int i = 0; i < Distances.Count; i++)
            {
                UnityEngine.Vector3 origin = epicenter.position + offset;
                UnityEngine.Vector3 dir = UnityEngine.Quaternion.AngleAxis(
                   YawAngleForFeeler(i), UnityEngine.Vector3.up) * epicenter.forward;
                dir.Normalize();
                bool hitSomething = false;
                UnityEngine.RaycastHit hit;
                float thickness = Thickness;
                float length = Length;
                if (thickness > 0f)
                {
                    hitSomething = UnityEngine.Physics.SphereCast(origin, thickness, dir, out hit,
                                                                  length, layerMask);
                }
                else
                {
                    hitSomething = UnityEngine.Physics.Raycast(origin, dir, out hit, length,
                                                               layerMask);
                }
                List<Falken.Number> distances = Distances;
                if (distances != null && distances.Count > 0)
                {
                    distances[i].Value = hitSomething ? hit.distance : length;
                }
                List<Falken.Category> ids = Ids;
                if (ids != null && ids.Count > 0)
                {
                    ids[i].Value = OnHit(hitSomething, hit);
                }

                if (debugRender)
                {
                    dir *= distances[i].Value;
                    var rayColor = hitSomething ? UnityEngine.Color.red : UnityEngine.Color.green;
                    UnityEngine.Debug.DrawRay(origin, dir, rayColor);
                }
            }
        }
#endif  // UNITY_5_3_OR_NEWER

#if UNITY_5_3_OR_NEWER
        /// <summary>
        /// Subclasses implement this to convert a hit result into an id,
        /// Feeler ids are effectively an index into the IdNames array.
        /// </summary>
        /// <returns>The id of the hit which is an index into IdNames</returns>
        public virtual int OnHit(bool hitSomething, UnityEngine.RaycastHit hit)
        {
            return hitSomething ? 1 : 0;
        }
#endif  // UNITY_5_3_OR_NEWER
    }
}
