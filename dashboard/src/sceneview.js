/**
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/**
 * @fileoverview Functionality that enables rendering a 3D view of an Episode.
 */

import { FeelersCurve } from './episode.js';
import * as THREE from 'three';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import {
  BufferGeometryUtils
} from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import TextSprite from '@seregpie/three.text-sprite';

const zUpToYUpMat = new THREE.Matrix4();
zUpToYUpMat.set(1, 0, 0, 0, 0, 0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 1);
const zUpToYUpQuat = new THREE.Quaternion();
zUpToYUpQuat.setFromRotationMatrix(zUpToYUpMat);
const lineMaterial =
    new THREE.LineBasicMaterial({vertexColors : THREE.VertexColors});
const pointMaterial =
    new THREE.PointsMaterial({size : 0.1, vertexColors : true});

/**
 * Extracts an entity position at a specific step and converts it
 * from Falken space to three.js space.
 * @param {object} entity Entity with the position to extract.
 * @param {number} stepIndex The time at which to get the position.
 * @return {object} The position as a THREE.Vector3.
 */
function falkenToThreePos(entity, stepIndex, zUp) {
  const x = entity.positionCurve.xCurve.steps[stepIndex];
  const y = entity.positionCurve.yCurve.steps[stepIndex];
  const z = entity.positionCurve.zCurve.steps[stepIndex];
  const position = new THREE.Vector3(x, y, z);
  if (zUp) {
    position.applyMatrix4(zUpToYUpMat);
  }
  return position;
};

/**
 * Extracts an entity rotation at a specific step and converts it
 * from Falken space to three.js space.
 * @param {object} entity Entity with the rotation to extract.
 * @param {number} stepIndex The time at which to get the position.
 * @return {object} The rotation as a THREE.Quaternion.
 */
function falkenToThreeRot(entity, stepIndex, zUp) {
  const x = entity.rotationCurve.xCurve.steps[stepIndex];
  const y = entity.rotationCurve.yCurve.steps[stepIndex];
  const z = entity.rotationCurve.zCurve.steps[stepIndex];
  const w = entity.rotationCurve.wCurve.steps[stepIndex];
  const rotation = new THREE.Quaternion(x, y, z, w);
  rotation.normalize();

  if (zUp) {
    rotation.premultiply(zUpToYUpQuat);
  }
  return rotation;
};

/**
 * Creates the geometry for a feeler, which can either be a set of line
 * segments or a set of points.
 * @param {object} field The Feelers field to extract from.
 * @param {number} stepIndex The time at which to sample the feelers.
 * @param {object} xform Entity transform for these feelers
 * @param {array} feelersVertices Line position buffer to append to.
 * @param {array} feelersColors Line color buffer to append to.
 * @param {array} pointsVertices Point position buffer to append to.
 * @param {array} pointsColors Point color buffer to append to.
 */
function createFeelerGeo(field, stepIndex, xform, feelersVertices,
  feelersColors, pointsVertices, pointsColors) {
  const feelersColor = new THREE.Color(field.color);
  const pointsColor = new THREE.Color(field.color);
  pointsColor.multiplyScalar(0.8);

  // Creates the raw position and color data by combining the feeler
  // spec data with the values at the specified stepIndex.
  for (let i = 0; i < field.angles.length; ++i) {
    let angle = field.angles[i];
    if (field.degrees) {
      angle *= Math.PI / 180;
    }
    const distance = field.feelerCurves[i].steps[stepIndex];
    const start = new THREE.Vector3(0, 0, 0);
    const end = new THREE.Vector3(Math.sin(angle) * distance,
                                  0,
                                  Math.cos(angle) * distance);
    // We should revisit this when we track offsets.
    start.applyMatrix4(xform);
    end.applyMatrix4(xform);

    feelersVertices.push(start.x, start.y, start.z);
    feelersColors.push(feelersColor.r, feelersColor.g, feelersColor.b);
    feelersVertices.push(end.x, end.y, end.z);
    feelersColors.push(feelersColor.r, feelersColor.g, feelersColor.b);

    // In point cloud mode, we only create points where feelers
    // hit something (i.e. where feeler length is less than max).
    if (distance < field.maximum) {
      pointsVertices.push(end.x, end.y, end.z);
      pointsColors.push(pointsColor.r, pointsColor.g, pointsColor.b);
    }
  }
}

/** Renders a 3D view of an Episode. */
class SceneView {
  /** Initialization of three.js in the dashboard
   * @constructor
   * @param {object} grapher The grapher object to query for selected time.
   */
  constructor(grapher) {
    this.grapher = grapher;
    this.currentEpisode = null;
    this.gridHelper = null;
    this.sceneEntities = {};
    this.sceneTrajectories = {};
    this.zUp = false;

    // State used to detect when we need to rebuild the scene view.
    this.lastEpisode = null;
    this.lastMinStep = null;
    this.lastMaxStep = null;
    this.lastStep = null;
    this.lastZUp = null;

    // DOM elements
    this.sceneviewDiv = document.getElementById('scene_view_3d');
    this.sceneviewUpAxis = document.getElementById('up_axis');
    this.sceneviewUpAxis.onchange = (value) => {
      this.zUp = this.sceneviewUpAxis.value == "+Z";
    }

    this.pageStyles = {};
    for (let i = 0; i < document.styleSheets[0].rules.length; ++i) {
      const rule = document.styleSheets[0].rules[i];
      if (rule.selectorText) {
        this.pageStyles[rule.selectorText] = rule.style;
      }
    }

    // Constructs the underlying three.js rendering primitives.
    const sceneHeight = this.sceneviewDiv.offsetHeight;
    const sceneWidth = this.sceneviewDiv.offsetWidth;
    const aspectRatio = sceneWidth / sceneHeight;
    const clearColor = new THREE.Color(1.0, 1.0, 1.0);

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(75, aspectRatio, 0.1, 1000);

    this.renderer = new THREE.WebGLRenderer();
    this.renderer.setSize(sceneWidth, sceneHeight);
    this.renderer.setClearColor(clearColor);
    this.sceneviewDiv.appendChild(this.renderer.domElement);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);

    // Start the frame pump.
    const update = () => {
      requestAnimationFrame(update);
      this.updateScene();
    }
    requestAnimationFrame(update);
  }

  /**
   * Handles viewport resize events.
   */
  onResize() {
    const sceneHeight = this.sceneviewDiv.offsetHeight;
    const sceneWidth = this.sceneviewDiv.offsetWidth;
    this.camera.aspect = sceneWidth / sceneHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(sceneWidth, sceneHeight);
  }

  /**
   * Sets the episode to render.
   * @param {object} episode The episode to render. Null will clear.
   */
  setEpisode(episode) {
    this.currentEpisode = episode;
  }

  /**
   * Creates a THREE.Object3D manifestation of a Falken Entity as well
   * an representation of its spatial data over time.
   * @param {object} entity The Falken entity to instantiate.
   */
  createEntity(entity) {
    let numSteps = entity.positionCurve.numSteps;
    const stepIndex =
      this.grapher.currentStep >= 0 ? this.grapher.currentStep : numSteps - 1;

    // Feelers are currently the only attribute that can be rendeered in
    // 3D (other than position and rotation).
    const feelers = [];
    entity.fieldCurves.forEach((field) => {
      if (field instanceof FeelersCurve) {
        feelers.push(field);
      }
    });

    // Create an Object3D for the entity, which will be updated
    // based on the currentTime.
    const entityGroup = new THREE.Group();
    // Add an element that represents the xform of the entity.
    // We could implement custom rendering of the Entity xformhere.
    const axes = new THREE.AxesHelper(5);
    entityGroup.add(axes);
    // Add a text label of the entity name.
    const textStyle = this.pageStyles['.scene_text_3d'];
    let label = new TextSprite({
      fontFamily : textStyle.fontFamily,
      alignment : textStyle.textAlign,
      color : entity.color,
      text : entity.name,
      // This size likely needs to change based on world size.
      fontSize : 1,
    });
    label.position.y = 1;
    entityGroup.add(label);

    // Add the new
    this.scene.add(entityGroup);
    this.sceneEntities[entity.name] = entityGroup;

    // Create an accumulation of spatial data for the entity during the
    // entire episode.
    let minSaturation = 0.2;
    const saturationIncrement = (1 - minSaturation) / numSteps;

    // Structures to accumulate geometry into
    const vertices = [];
    const colors = [];
    const feelersVertices = [];
    const feelersColors = [];
    const feelersStepIndices = [0];
    const pointsVertices = [];
    const pointsColors = [];
    const cloudStepIndices = [0];

    // Walk through the entire episode and accumulate as needed.
    for (let i = 0; i < numSteps; ++i) {
      // Convert Falken transform in to three.js format.
      const position = falkenToThreePos(entity, i, this.zUp);
      const rotation = falkenToThreeRot(entity, i, this.zUp);
      const xform = new THREE.Matrix4();
      xform.compose(position, rotation, new THREE.Vector3(1, 1, 1));

      // Append this step's position to the trajectory
      vertices.push(position.x, position.y, position.z);
      // Color fades from lighter at the start of the episode to
      // darker at the end of the episode.
      const lineColor = new THREE.Color(entity.color);
      const desat = new THREE.Color(0.1, 0.1, 0.1);
      const color = desat.lerp(lineColor, minSaturation);
      colors.push(color.r, color.g, color.b);
      minSaturation += saturationIncrement;

      // Append this step's feelers to the point cloud.
      feelers.forEach((feeler) => {
        createFeelerGeo(feeler, i, xform, feelersVertices, feelersColors,
          pointsVertices, pointsColors);
        // Because we only store the results of feelers that hit the world
        // we can get different results every step. So we need to record
        // the size of the buffer at each step to enable setDrawRange
        // (below).
        feelersStepIndices.push(feelersVertices.length / 3);
        cloudStepIndices.push(pointsVertices.length / 3);
      });
    }

    // Finally, create the Object3D versions of the accumulated data,
    // and add them to the scene.
    let lineGeo = null;
    let lineObject = null;
    if (vertices.length) {
      lineGeo = new THREE.BufferGeometry();
      lineGeo.setAttribute('position',
        new THREE.Float32BufferAttribute(vertices, 3));
      lineGeo.setAttribute('color',
        new THREE.Float32BufferAttribute(colors, 3));
      lineObject = new THREE.Line(lineGeo, lineMaterial);
      this.scene.add(lineObject);
    }

    let feelersGeo = null;
    let feelersObject = null;
    if (feelersVertices.length > 0) {
      feelersGeo = new THREE.BufferGeometry();
      feelersGeo.setAttribute('position',
        new THREE.Float32BufferAttribute(feelersVertices, 3));
      feelersGeo.setAttribute('color',
        new THREE.Float32BufferAttribute(feelersColors, 3));
      feelersObject = new THREE.LineSegments(feelersGeo, lineMaterial);
      this.scene.add(feelersObject);
    }

    let pointCloudGeo = null;
    let pointCloud = null;
    if (pointsVertices.length > 0) {
      pointCloudGeo = new THREE.BufferGeometry();
      pointCloudGeo.setAttribute('position',
        new THREE.Float32BufferAttribute(pointsVertices, 3));
      pointCloudGeo.setAttribute('color',
        new THREE.Float32BufferAttribute(pointsColors, 3));
      pointCloud = new THREE.Points(pointCloudGeo, pointMaterial);
      this.scene.add(pointCloud);
    }

    this.sceneTrajectories[entity.name] = {
      line : lineObject,
      lineGeo : lineGeo,
      feelers : feelersObject,
      feelersGeo : feelersGeo,
      feelersStepIndices : feelersStepIndices,
      pointCloud : pointCloud,
      pointCloudGeo : pointCloudGeo,
      cloudStepIndices : cloudStepIndices,
    };
  }

  /**
   * Updates the transform of the three.js Object3D that corresponds
   * to a given Falken Entity.
   * @param {object} entity The Falken entity to update from.
   * @param {number} stepIndex The time at which to get the position.
   */
  updateEntityTransform(entity, stepIndex) {
    const entityGroup = this.sceneEntities[entity.name];
    const position = falkenToThreePos(entity, stepIndex, this.zUp);
    const rotation = falkenToThreeRot(entity, stepIndex, this.zUp);
    entityGroup.position.copy(position);
    entityGroup.rotation.setFromQuaternion(rotation);
  }

  /**
   * Positions camera, controls, and grid based on current (sub)episode.
   */
  initCameraGrid() {
    // Determine the actual min, max, and current frames as they
    // may or may not be currently defined by the user.
    const numSteps = this.currentEpisode.player.positionCurve.numSteps;
    const startIndex = this.grapher.minStep ? this.grapher.minStep : 0;
    let endIndex = this.grapher.maxStep ? this.grapher.maxStep : numSteps - 1;
    if (this.grapher.currentStep >= 0) {
      endIndex = Math.min(endIndex, this.grapher.currentStep);
    }

    // Compute a bounding sphere for the scene that we will use to
    // position the camera, grid, and other global objects. For now, we
    // only base this on the player's trajectory as we're primarily
    // interested in visualizing their actions with the world.
    const bounds = new THREE.Box3();
    for (let i = startIndex; i < endIndex; ++i) {
      const position =
        falkenToThreePos(this.currentEpisode.player, i, this.zUp);
      bounds.expandByPoint(position);
    }
    let boundingSphere = new THREE.Sphere();
    bounds.getBoundingSphere(boundingSphere);

    // Initialize the camera and controls to look at and orbit around
    // the previously computed bounds.
    const zoomFactor = 2;
    let cameraOffset = new THREE.Vector3();
    cameraOffset.copy(boundingSphere.center);
    cameraOffset.add(new THREE.Vector3(boundingSphere.radius,
                                       boundingSphere.radius,
                                       boundingSphere.radius));
    this.camera.far = (boundingSphere.radius * 2) * zoomFactor;
    this.camera.position.copy(cameraOffset);
    this.camera.updateProjectionMatrix();
    this.controls.target = boundingSphere.center;
    this.controls.maxDistance = boundingSphere.radius * zoomFactor;
    this.controls.update();

    // Create a local grid along the XZ plane to help ground the space.
    // We should expose this value as a tweakable.
    if (this.gridHelper) {
      this.scene.remove(this.gridHelper);
      this.gridHelper = null;
    }

    const unitsPerDivision = 10;
    const divisions =
        Math.ceil(boundingSphere.radius * 2 / unitsPerDivision);
    const gridSize = unitsPerDivision * divisions;
    const gridPosition = new THREE.Vector3();
    gridPosition.copy(boundingSphere.center);
    gridPosition.y = 0;
    gridPosition.x =
        Math.round(gridPosition.x / unitsPerDivision) * unitsPerDivision;
    gridPosition.z =
        Math.round(gridPosition.z / unitsPerDivision) * unitsPerDivision;
    this.gridHelper = new THREE.GridHelper(gridSize, divisions);
    this.gridHelper.position.copy(boundingSphere.center);
    this.scene.add(this.gridHelper);
  }

  /**
   * Clears the current scene and creates all of the objects
   * necessary to render the current episode.
   */
  initScene() {
    this.scene.remove.apply(this.scene, this.scene.children);
    this.sceneEntities = {};
    this.sceneTrajectories = {};

    this.initCameraGrid();

    // Create three.js manifestations of all entities in the scene.
    this.createEntity(this.currentEpisode.player);
    if (this.currentEpisode.camera) {
      this.createEntity(this.currentEpisode.camera);
    }
    this.currentEpisode.globalEntities.forEach(
        (entity) => { this.createEntity(entity); });
  }

  /**
   * The main render loop for the Dashboard Scene panel..
   */
  updateScene() {
    if (this.currentEpisode && this.currentEpisode.hasSteps) {
      // If the current episode has changed or the z-up state has
      // changed we need to clear and rebuild the scene.
      if (this.currentEpisode != this.lastEpisode || this.zUp != this.lastZUp) {
        this.initScene();
        this.lastStep = null;
        this.lastEpisode = this.currentEpisode;
        this.lastZUp = this.zUp;
      }

      // If the current, min, or max step has changed, we need to update
      // the state of the objects in the current scene.
      if (this.grapher.currentStep != this.lastStep ||
          this.grapher.minStep != this.lastMinStep ||
          this.grapher.maxStep != this.lastMaxStep) {

        if (this.grapher.maxStep != this.lastMaxStep) {
          this.initCameraGrid();
        }

        // Determine the actual min, max, and current frames as they
        // may or may not be currently defined by the user.
        const numSteps = this.currentEpisode.player.positionCurve.numSteps;
        const startIndex =
          this.grapher.minStep ? this.grapher.minStep : 0;
        let endIndex =
          this.grapher.maxStep ? this.grapher.maxStep : numSteps - 1;
        if (this.grapher.currentStep >= 0) {
          endIndex = Math.min(endIndex, this.grapher.currentStep);
        }

        // Update all of the entity transforms to the correct step.
        this.updateEntityTransform(this.currentEpisode.player, endIndex);
        if (this.currentEpisode.camera) {
          this.updateEntityTransform(this.currentEpisode.camera, endIndex);
        }
        this.currentEpisode.globalEntities.forEach(
            (entity) => { this.updateEntityTransform(entity, endIndex); });

        // Update the accumulated trajectory data to match the current
        // range of steps.
        for (let entityName in this.sceneTrajectories) {
          const trajectory = this.sceneTrajectories[entityName];
          if (trajectory.lineGeo) {
            trajectory.lineGeo.setDrawRange(startIndex,
                                            endIndex - startIndex);
          }
          if (trajectory.feelersGeo) {
            const feelersIndices = trajectory.feelersStepIndices;
            trajectory.feelersGeo.setDrawRange(
                feelersIndices[endIndex],
                feelersIndices[endIndex + 1] - feelersIndices[endIndex]);
          }
          if (trajectory.pointCloudGeo) {
            const cloudIndices = trajectory.cloudStepIndices;
            trajectory.pointCloudGeo.setDrawRange(
                cloudIndices[startIndex],
                cloudIndices[endIndex] - cloudIndices[startIndex]);
          }
        }
      }

      this.lastMinStep = this.grapher.minStep;
      this.lastMaxStep = this.grapher.maxStep;
      this.lastStep = this.grapher.currentStep;
    } else {
      this.scene.remove.apply(this.scene, this.scene.children);
      this.sceneEntities = {};
      this.sceneTrajectories = {};
      this.lastEpisode = null;
      this.lastStep = null;
    }

    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  };
}

export { SceneView }
