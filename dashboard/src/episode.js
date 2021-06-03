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
 * @fileoverview Defines a set of classes that store Episode data in a format
 * that is easy for the dashboard to use when rendering data in both 2D and 3D.
 */

const d3 = require('d3');

let entityColorIndex = 0;
const ENTITY_COLORS = d3.schemeSet1;

let curveColorIndex = 0;
const CURVE_COLORS = d3.schemeCategory10;

let feelerColorIndex = 0;
const FEELER_COLORS = d3.schemeTableau10;

/** Represents a single Episode and all of the Step data within it. */
class Episode {
  /**
   * Creates a new Episode instance, transforming the supplied spec into
   * a set of AttributeCurves for all Actions and Observations.
   * @constructor
   * @param {string} id Unique id of this Episode
   * @param {object} spec The BrainSpec associated with this Episode.
   * @param {int} index The chronological index of this Episode in its Session.
   */
  constructor(id, spec, index) {
    this.id = id;
    this.index = index;
    this.actions = [];
    const actionSpec = spec.actionSpec;
    actionSpec.actionsList.forEach((actionSpec, actionIndex) => {
      let actionCurve = null;
      if (actionSpec.number) {
        actionCurve =
            new NumberCurve('action', actionSpec.name, actionSpec.number);
      } else if (actionSpec.category) {
        actionCurve =
            new CategoryCurve('action', actionSpec.name, actionSpec.category);
      } else if (actionSpec.joystick) {
        actionCurve =
            new JoystickCurve('action', actionSpec.name, actionSpec.joystick);
      }
      if (actionCurve) {
        this.actions[actionIndex] = actionCurve;
      }
    });

    const observationSpec = spec.observationSpec;
    this.player = observationSpec.player
                      ? new Entity(observationSpec.player, 'player')
                      : null;
    this.camera = observationSpec.camera
                      ? new Entity(observationSpec.camera, 'camera')
                      : null;
    this.globalEntities = [];
    observationSpec.globalEntitiesList.forEach((entitySpec, entityIndex) => {
      this.globalEntities[entityIndex] =
          new Entity(entitySpec, 'entity' + entityIndex);
    });
    this.controlSteps = [];
    this.controlSegments = [];
    this.hasSteps = false;
  }

  /**
   * Adds a single Step to this Episode and the AttributeCurves it contains.
   * @param {object} step The Step proto to extract data from.
   */
  addStep(step) {
    const actionData = step.action;
    actionData.actionsList.forEach((actionStep, actionIndex) => {
      const actionCurve = this.actions[actionIndex];
      if (actionCurve) {
        actionCurve.addStep(actionStep);
      }
    });
    const observationData = step.observation;
    if (observationData.player) {
      this.player.addStep(observationData.player);
    }
    if (observationData.camera) {
      this.camera.addStep(observationData.player);
    }
    observationData.globalEntitiesList.forEach((entityStep, entityIndex) => {
      this.globalEntities[entityIndex].addStep(entityStep);
    });
    this.hasSteps = true;

    const human = step.action.source ==
                  falkenProto.ActionData.ActionSource.HUMAN_DEMONSTRATION;
    this.controlSteps.push(human);
  }

  /**
   * Computes a set of segments of contiguous human or AI control.
   * Should be called after all steps have been added for this Episode.
   */
  computeControlSegments() {
    if (this.controlSteps.length) {
      this.controlSegments = [];
      let segment = { start : 0, end : 0, human : this.controlSteps[0] }
      for (let i = 0; i < this.controlSteps.length; ++i) {
        const humanStep = this.controlSteps[i];
        if (humanStep != segment.human) {
          this.controlSegments.push(segment);
          segment = { start : i, end : i, human : humanStep };
        } else {
          segment.end = i;
        }
      }
      this.controlSegments.push(segment);
    }
  }
}

/** Represents a single Entity within an Episode, including AttributeCurves for
 * position, rotation, and all fields in the Entity.
 */
class Entity {
  /**
   * Creates a new Entity instance, transforming the supplied spec into
   * a set of AttributeCurves for every Field in the Entity.
   * @constructor
   * @param {object} spec The ObservationSpec associated with this Entity.
   * @param {string} name The name of the Entity.
   */
  constructor(spec, name) {
    this.spec = spec;
    this.name = name;
    this.positionCurve = new PositionCurve(name, 'position');
    this.rotationCurve = new RotationCurve(name, 'rotation');
    this.fieldCurves = [];
    spec.entityFieldsList.forEach((field, fieldIndex) => {
      let fieldCurve = null;
      if (field.number) {
        fieldCurve = new NumberCurve(name, field.name, field.number);
      } else if (field.category) {
        fieldCurve = new CategoryCurve(name, field.name, field.category);
      } else if (field.feeler) {
        fieldCurve = new FeelersCurve(name, field.name, field.feeler);
      }
      if (fieldCurve) {
        this.fieldCurves[fieldIndex] = fieldCurve;
      }
    });
    this.color = ENTITY_COLORS[entityColorIndex];
    entityColorIndex = (++entityColorIndex) % ENTITY_COLORS.length;
  }

  /**
   * Adds a single Step to this Entity and the AttributeCurves it contains.
   * @param {object} step The Step proto to extract data from.
   */
  addStep(step) {
    this.positionCurve.addStep(step.position);
    this.rotationCurve.addStep(step.rotation);
    step.entityFieldsList.forEach((fieldStep, fieldIndex) => {
      const fieldCurve = this.fieldCurves[fieldIndex];
      if (fieldCurve) {
        fieldCurve.addStep(fieldStep);
      }
    });
  }
}

/** The base class for all Attribute timeseries data. */
class AttributeCurve {
  /**
   * Creates a new AttributeCurve instance.
   * @constructor
   * @param {string} prefix The action or field that this curve represents.
   * @param {string} name The name of the Attribute.
   */
  constructor(prefix, name) {
    this.prefix = prefix;
    this.name = name;
    this.color = CURVE_COLORS[curveColorIndex];
    curveColorIndex = (++curveColorIndex) % CURVE_COLORS.length;
    this.numSteps = 0;
  }

  /**
   * Adds a single Step to this AttributeCurve.
   * Subclasses must override this function and call the base class from it.
   * @param {object} step The Step proto to extract data from.
   */
  addStep(step) { ++this.numSteps; }

  /**
   * Returns a d3 scale object that represents the Y axis of this curve.
   * Subclasses must override this function and call the base class from it.
   * @param {int} height The height of the graph (in pixels).
   * @return {object} A d3 scale object to be used in a Y axis.
   */
  yScale(height) { console.assert(false, "Must implement yScale"); }

  /**
   * Returns a list of labels for the Y Axis.
   * @return {array} A list of labels for the Y Axis.
   */
  yAxisLabels() { console.assert(false, "Must implement yAxisLabels"); }

  /**
   * Returns a list of AttributeCurves contained in this AttributeCurves.
   * This allows us to easily support both simple and complex attribute types.
   * @return {array} A list of AttributeCurves contined in this AttributeCurve.
   */
  getCurves() { console.assert(false, "Curves must implement getCurves"); }

  /**
   * Returns a nicely formated string for the specified Step.
   * Subclasses may override this function.
   * @return {string} The formatted step.
   */
  printStep(stepIndex) {}

  /**
   * Returns a nicely formated label string for this AttributeCurve.
   * Subclasses should not override this function.
   * @return {string} The formatted label.
   */
  getLabel() { return this.prefix + ":" + this.name; }
}

/** Represents a simple timeseries of a single numerical value. */
class NumberCurve extends AttributeCurve {
  constructor(prefix, name, spec) {
    super(prefix, name);
    this.minimum = spec.minimum;
    this.maximum = spec.maximum;
    this.steps = [];
  }

  addStep(step) {
    super.addStep(step);
    if (step.number) {
      this.steps.push(step.number.value);
    } else if (step.distance) {
      this.steps.push(step.distance.value);
    } else {
      this.steps.push(step);
    }
  }

  yScale(height) {
    return d3.scaleLinear().domain([ this.minimum, this.maximum ]).range([
      height, 0
    ]);
  }

  yAxisLabels() { return [ this.minimum, this.maximum ]; }

  getCurves() { return [ this ]; }

  printStep(stepIndex) { return this.steps[stepIndex].toFixed(2); }
}

/** Represents a simple timeseries of a single categorical value. */
class CategoryCurve extends AttributeCurve {
  constructor(prefix, name, spec) {
    super(prefix, name);
    this.categories = spec.enumValuesList;
    this.steps = [];
  }

  addStep(step) {
    super.addStep(step);
    this.steps.push(this.categories[step.category.value]);
  }

  yScale(height) {
    return d3.scalePoint().domain(this.categories).range([ height, 0 ]);
  }

  yAxisLabels() { return this.categories; }

  getCurves() { return [ this ]; }

  printStep(stepIndex) { return this.steps[stepIndex].substring(0, 6); }
}

/** Represents timeseries data of a Joystick type Action. */
class JoystickCurve extends AttributeCurve {
  constructor(prefix, name, spec) {
    super(prefix, name);
    this.axesMode = spec.axesMode;
    this.controlledEntity = spec.controlledEntity;
    this.controlFrame = spec.controlFrame;
    this.minimum = -1;
    this.maximum = 1;
    const subSpec = {minimum : this.minimum, maximum : this.maximum};
    this.xCurve = new NumberCurve(prefix, name + "_x", subSpec);
    this.yCurve = new NumberCurve(prefix, name + "_y", subSpec);
  }

  addStep(step) {
    super.addStep(step);
    this.xCurve.addStep(step.joystick.xAxis);
    this.yCurve.addStep(step.joystick.yAxis);
  }

  yScale(height) {
    return d3.scaleLinear().domain([ this.minimum, this.maximum ]).range([
      height, 0
    ]);
  }

  yAxisLabels() { return [ this.minimum, this.maximum ]; }

  getCurves() { return [ this.xCurve, this.yCurve ]; }
}

/** Represents timeseries data of a Position type Observation. */
class PositionCurve extends AttributeCurve {
  constructor(prefix, name) {
    super(prefix, name);
    this.minimum = Number.POSITIVE_INFINITY;
    this.maximum = Number.NEGATIVE_INFINITY;
    const posSpec = {minimum : this.minimum, maximum : this.maximum};
    this.xCurve = new NumberCurve(prefix, name + "_x", posSpec);
    this.yCurve = new NumberCurve(prefix, name + "_y", posSpec);
    this.zCurve = new NumberCurve(prefix, name + "_z", posSpec);
  }

  addStep(step) {
    super.addStep(step);
    function addToCurve(parent, curve, step) {
      curve.addStep(step);
      curve.minimum = Math.min(curve.minimum, step);
      curve.maximum = Math.max(curve.maximum, step);
      parent.minimum = Math.min(parent.minimum, curve.minimum);
      parent.maximum = Math.max(parent.maximum, curve.maximum);
    }
    addToCurve(this, this.xCurve, step.x);
    addToCurve(this, this.yCurve, step.y);
    addToCurve(this, this.zCurve, step.z);
  }

  yScale(height) {
    return d3.scaleLinear().domain([ this.minimum, this.maximum ]).range([
      height, 0
    ]);
  }

  yAxisLabels() { return [ this.minimum, this.maximum ]; }

  getCurves() { return [ this.xCurve, this.yCurve, this.zCurve ]; }
}

/** Represents timeseries data of a Rotation type Observation. */
class RotationCurve extends AttributeCurve {
  constructor(prefix, name) {
    super(prefix, name);
    this.minimum = -1;
    this.maximum = 1;
    const posSpec = {minimum : this.minimum, maximum : this.maximum};
    this.xCurve = new NumberCurve(prefix, name + "_x", posSpec);
    this.yCurve = new NumberCurve(prefix, name + "_y", posSpec);
    this.zCurve = new NumberCurve(prefix, name + "_z", posSpec);
    this.wCurve = new NumberCurve(prefix, name + "_w", posSpec);
  }

  addStep(step) {
    super.addStep(step);
    this.xCurve.addStep(step.x);
    this.yCurve.addStep(step.y);
    this.zCurve.addStep(step.z);
    this.wCurve.addStep(step.w);
  }

  yScale(height) {
    return d3.scaleLinear().domain([ this.minimum, this.maximum ]).range([
      height, 0
    ]);
  }

  yAxisLabels() { return [ this.minimum, this.maximum ]; }

  getCurves() {
    return [ this.xCurve, this.yCurve, this.zCurve, this.wCurve ];
  }
}

/** Represents timeseries data of a Feelers type Observation. */
class FeelersCurve extends AttributeCurve {
  constructor(prefix, name, spec) {
    super(prefix, name);
    this.count = spec.count;
    this.minimum = spec.distance.minimum;
    this.maximum = spec.distance.maximum;
    this.angles = spec.yawAnglesList;
    this.degrees = false;
    this.feelerCurves = [];
    for (let i = 0; i < this.count; ++i) {
      this.feelerCurves[i] =
          new NumberCurve(prefix, name + "_" + i, spec.distance);
      if (Math.abs(this.angles[i]) > Math.PI) {
        this.degrees = true;
      }
    }
    this.color = FEELER_COLORS[feelerColorIndex];
    feelerColorIndex = (++feelerColorIndex) % FEELER_COLORS.length;
  }

  addStep(step) {
    super.addStep(step);
    for (let i = 0; i < this.count; ++i) {
      this.feelerCurves[i].addStep(step.feeler.measurementsList[i])
    }
  }

  yScale(height) {
    return d3.scaleLinear().domain([ this.minimum, this.maximum ]).range([
      height, 0
    ]);
  }

  yAxisLabels() { return [ this.minimum, this.maximum ]; }

  getCurves() { return this.feelerCurves; }
}

export { Episode, FeelersCurve }
