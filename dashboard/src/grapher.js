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
 * @fileoverview Defines functions for rendering AttributeCurves in d3.
 */

const d3 = require('d3');

/**
 * Encapsulates the functionality required to render 2D charts from an Episode.
 */
class Grapher {
  constructor() {
    this.graphGrid = document.getElementById('graphs_grid');
    this.timelineDiv = document.getElementById('timeline');
    this.resetZoomButton = document.getElementById('reset_zoom');
    this.resetZoomButton.hidden = true;

    this.currentEpisode = null;
    this.focusRange = null;
    this.minStep = null;
    this.maxStep = null;
    this.currentStep = null;
    this.selectedAttributes = {};

    this.mouseDown = false;
    this.shiftDragging = false;
    this.dragStart = null;
  }

  /**
   * Renders small multiples and timeline.
   * @param {object} episode The episode to render.
   */
  render(episode) {
    this.currentEpisode = episode;
    this.renderSmallMultiples();
    this.renderTimeline();
  }

  /**
   * Clears all state created by render().
   */
  clearGraphs() {
    this.currentEpisode = null;
    this.minStep = null;
    this.maxStep = null;
    this.currentStep = -1;
    this.selectedAttributes = {};

    this.graphGrid.innerHTML = "";
    this.timelineDiv.innerHTML = "";
  }

  /**
   * Renders the "small multiples" grid of attribute curves in the Charts panel.
   */
  renderSmallMultiples() {
    this.graphGrid.innerHTML = "";

    // Start by collecting a list of all attribute curves including both
    // Actions and Observations. The list of curves is deliberately determinstic
    // so that users always see actions followed by observations, globalEntities
    // after the player, etc.
    const attributes = [];
    attributes.push(...this.currentEpisode.actions);

    function addEntityAttributes(entity) {
      if (entity) {
        attributes.push(entity.positionCurve);
        attributes.push(entity.rotationCurve);
        entity.fieldCurves.forEach((field) => { attributes.push(field); });
      }
    }
    addEntityAttributes(this.currentEpisode.player);
    addEntityAttributes(this.currentEpisode.camera);
    this.currentEpisode.globalEntities.forEach(
        (entity) => { addEntityAttributes(entity); });

    // Determines the dimensions of the small multiples grid. We generally
    // prefer squares, but will favor vertical compression over horizontal
    // compression if need be as that is better for legibility.
    const cols = Math.floor(Math.sqrt(attributes.length));
    const rows = Math.ceil(attributes.length / cols);

    // Explicitly set the dimensions of the gridTemplate that will contain
    // the individual divs.
    let rowsString = "";
    for (let i = 0; i < rows; ++i) {
      rowsString += (1 / rows * 100) + "% ";
    }
    let colsString = "";
    for (let i = 0; i < cols; ++i) {
      colsString += (1 / cols * 100) + "% ";
    }
    this.graphGrid.style.gridTemplateColumns = colsString;
    this.graphGrid.style.gridTemplateRows = rowsString;

    attributes.forEach((attribute) => {
      // Create divs for each attribute in the list
      const attributeDiv = document.createElement("div");
      attributeDiv.id = attribute.prefix + "_" + attribute.name + "_graph";
      // Attributes are (de)selected when clicked.
      // Which updates the attribute graph and the timeline.
      attributeDiv.onclick = () => {
        if (this.selectedAttributes[attribute.getLabel()]) {
          delete this.selectedAttributes[attribute.getLabel()];
          attributeDiv.style.backgroundColor = 'white';
        } else {
          this.selectedAttributes[attribute.getLabel()] = attribute;
          attributeDiv.style.backgroundColor = 'lightgrey';
        }
        this.renderTimeline();
      };
      this.graphGrid.appendChild(attributeDiv);

      // Render a graph into the div for that attribute.
      this.renderAttributeCurves(attributeDiv, attribute.getCurves(),
                                 this.currentEpisode.controlSegments,
                                 attribute.getLabel());
    });
  };

  /**
   * Renders the attribute curves for the Timeline panel.
   */
  renderTimeline() {
    this.timelineDiv.innerHTML = "";

    // Create a custom collection of curves as a union of all of the
    // curves in all of the selected attributes.
    const combinedCurves = [];
    for (let key in this.selectedAttributes) {
      combinedCurves.push(...this.selectedAttributes[key].getCurves());
    }

    if (combinedCurves.length > 0) {
      this.renderAttributeCurves(this.timelineDiv, combinedCurves,
                                 this.currentEpisode.controlSegments);
    }
  }

  /**
   * The workhorse function for rendering graphs of attributes.
   * @param {object} parentDiv The Div to render these curves into.
   * @param {array} curves A list of AttributeCurves to render.
   * @param {array} controlSegments Sections of human vs AI control.
   * @param {string} label Optional label for this graph.
   */
  renderAttributeCurves(parentDiv, curves, controlSegments, label) {
    const labelHeight = 10;
    const baseCurve = curves[0];

    // Determine if all curves have the same Y axis values. If they do not,
    // then we skip ddrawing the labels on the Y axis.
    let commonY = true;
    const baseLabels = baseCurve.yAxisLabels();
    for (let i = 0; i < curves.length; ++i) {
      const curveLabels = curves[i].yAxisLabels();
      if (baseLabels.length != curveLabels.length ||
          (baseLabels.some((label, i) => label != curveLabels[i]))) {
        commonY = false;
        break;
      }
    }

    // Set the dimensions and margins of the graph
    // NB: These margins should ideally be derived from other properties of
    // the graph, but are holding off on that until the design is more settled.
    // See individual comments for more detail.
    const margin = {
      // Space to show a hover label as the text appears above the graph.
      top : 15,
      // Space to show max value of X axis.
      right : 10,
      // Space for x axis in timeline view, label in small multiples view.
      bottom : 20,
      // Space to show (optional) Y axis and the min value label of the X axis.
      left : commonY ? 30 : 10,
    };
    const width = parentDiv.scrollWidth - margin.left - margin.right;
    const height = parentDiv.scrollHeight - margin.top - margin.bottom;

    const xScale = d3.scaleLinear()
                    .domain([ this.minStep, this.maxStep ])
                    .range([ 0, width ]);

    // Create the svg that will contain the graph
    const svg = d3.select("#" + parentDiv.id)
      .append("svg")
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
      .append("g")
      .attr("transform", "translate(" + margin.left + "," + margin.top + ")")
      .attr("pointer-events", "none")
      .style("user-select", "none");

    const segmentHeight = height * 0.05;

    controlSegments.forEach((segment) => {
      if ((segment.start >= this.minStep && segment.start <= this.maxStep) ||
          (segment.end >= this.minStep && segment.end <= this.maxStep)) {
        const start = Math.max(segment.start, this.minStep);
        const end = Math.min(segment.end, this.maxStep);
        const controlRect = svg.append('rect')
          .attr("class", segment.human ? "human-rect" : "ai-rect")
          .attr("x", xScale(start))
          .attr("y", height)
          .attr("width", xScale(end) - xScale(start))
          .attr("height", segmentHeight);
        }
    });

    // We either create a label (small multiples) or an x axis (timeline)
    // but never both as it takes too much space and looks busy.
    if (label) {
      svg.append("text")
        .attr("class", "chart-label")
        .attr("x", width / 2)
        .attr("y", height + labelHeight * 1.5)
        .text(label)
        .attr("font-size", labelHeight + "px")
    } else {
      const xAxis = d3.axisBottom(xScale)
        .tickFormat(d3.format("d"))
        .tickValues([ this.minStep, this.maxStep ]);

      svg.append("g")
        .attr("class", "x_axis")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis);
    }

    // Render Y axis labels if they are the same for all curves.
    if (commonY) {
      const yAxis = d3.axisLeft(curves[0].yScale(height))
        .tickValues(baseLabels);

      svg.append("g")
        .attr("class", "y_axis")
        .call(yAxis);
    }

    // Bind the curves as data, andd create a subgroup for each curve.
    const attributes = svg.selectAll(".curve")
      .data(curves).enter()
      .append("g").attr("class", "curve");

    // Curves for the individual attributes
    attributes.append("path")
      .attr("class", "line")
      .attr("stroke", function(curve) { return curve.color; })
      .attr("d", function(curve) {
        const line = d3.line()
                         .x(function(d, i) { return xScale(i); })
                         .y(function(d) { return curve.yScale(height)(d); });
        return line(curve.steps);
      });

    // Elements that appear when the mouse is over a graph.
    const mouseG = svg.append("g")
      .attr("class", "mouse-over-effects")
      .attr("visibility", "hidden");

    // A support line from the graph point down to the x axis.
    // Currently only visible in timeline mode.
    mouseG.append("path")
      .attr("class", "mouse-line")
      .attr("visibility", label ? "hidden" : "visible");

    // Bind the curves and create a group for each curve.
    // These will be for per-curve effects.
    const mousePerCurve = mouseG.selectAll('.mouse-per-curve')
      .data(curves)
      .enter()
      .append("g")
      .attr("class", "mouse-per-curve");

    // A dot that will appear at point on the curve closest to the cursor.
    mousePerCurve.append("circle")
      .attr("class", "mouse-circle")
      .style("stroke", function(curve) { return curve.color; })
      .style("fill", function(curve) { return curve.color; });

    // A label of the value of the curve at the dot.
    mousePerCurve.append("text")
      .attr("class", "mouse-label")
      .attr("dy", labelHeight * -0.5)

    // Elements that appear based on the current time.
    // Currently only used in timeline mode.
    const currentStepG = svg.append("g")
      .attr("class", "current-step-group")
      .attr("visibility", "hidden");

    // A vertical line at the current time
    const currentStepLine = currentStepG.append("path")
      .attr("class", "current-step-line")

    // The frame number rendered beneath the vertical line.
    const currentStepText = currentStepG.append("text")
      .attr("pointer-events", "none")
      .attr("dy", height + segmentHeight + labelHeight);

    // Elements that appear while shift-dragging over the curve.
    // Currently only used in timeline mode.
    const shiftRect = svg.append('rect')
      .attr("class", "shift-rect")
      .attr("width", width)
      .attr("height", height)
      .attr("visibility", "hidden");

    // The workhorse function that handles mouse movement over a graph
    // including hovering, clicking, and dragging.
    function mouseMove(event, grapher) {
      // Compute the stepIndex that corresponds to the mouse position by
      // projecting the mouseX out via the curve's xScale.
      const stepIndex = Math.max(
          0, Math.round(xScale.invert(d3.pointer(event)[0])));

      // We often want to draw a line from the curve with the highest
      // normalized value down to the axes, so we compute that here.
      // NB: d3 has an upper left origin, hence the use of "least" here.
      const maxCurve =
          d3.least(curves, d => d.yScale(height)(d.steps[stepIndex]));
      const maxValue = maxCurve.yScale(height)(maxCurve.steps[stepIndex]);

      // Moves the root of the mouseover effects to the stepIndex.
      // This will automatically move all of the subitems.
      // The group only moves along X and the sub-items only move along Y
      // relative to that group.
      mouseG.attr("transform", function() {
        const x = xScale(stepIndex);
        const y = 0;
        return "translate(" + x + "," + y + ")";
      });

      // Update the vertical hover line to go from the axis to the highest
      // value in the graph.
      mouseG.select("path")
        .attr("d", function() {
          return d3.line()([ [ 0, maxValue ], [ 0, height ] ]);
        });

      // Update the mouseover dot for each curve in the list.
      mouseG.selectAll(".mouse-per-curve")
        .attr("transform", function(curve, i) {
          d3.select(this).select('text').text(curve.printStep(stepIndex));

          const x = 0;
          const y = curve.yScale(height)(curve.steps[stepIndex]);
          return "translate(" + x + "," + y + ")";
        });

      // Logic specific to clicking or dragging oon the graph.
      // Currently only used in the timeline.
      if (grapher.mouseDown) {
        grapher.currentStep = stepIndex;
        if (!grapher.dragStart) {
          grapher.dragStart = stepIndex;
        }

        // Shift-dragging defines a focus range, with one end anchored on
        // the start of the drag and the other at the current pointer value.
        if (grapher.shiftDragging) {
          if (!grapher.focusRange) {
            grapher.focusRange = {min : stepIndex, max : stepIndex};
          }
          const focusDelta = stepIndex - grapher.dragStart;
          if (focusDelta >= 0) {
            grapher.focusRange.min = grapher.dragStart;
            grapher.focusRange.max = stepIndex;
          } else {
            grapher.focusRange.min = stepIndex;
            grapher.focusRange.max = grapher.dragStart;
          }
        }

        // Render an overlay rectangle during a shift-drag.
        if (grapher.focusRange) {
          grapher.currentStep =
            Math.max(grapher.focusRange.min, grapher.currentStep);
          grapher.currentStep =
            Math.min(grapher.focusRange.max, grapher.currentStep);
          const scaledMin = xScale(grapher.focusRange.min);
          const scaledMax = xScale(grapher.focusRange.max);
          shiftRect.attr("visibility", "visible")
            .attr("x", scaledMin)
            .attr("width", scaledMax - scaledMin);
        } else {
          shiftRect.attr("visibility", "hidden");
        }

        // Update the visualization of the current time whenever the mouse
        // is down, whether clicking or ddragging.
        currentStepG
          .attr("transform",
                function() {
                  const x = xScale(grapher.currentStep);
                  const y = 0;
                  return 'translate(' + x + ',' + y + ')';
                })
          .attr("visibility", "visible");

        currentStepLine.attr("d", function() {
          return d3.line()([ [ 0, maxValue ], [ 0, height ] ]);
        });

        currentStepText.text(grapher.currentStep);
      }
    }

    // Creates a dedicated, transparent overlay to catch mouse events.
    const mouseInput = svg.append("svg:rect")
      .attr("class", "mouse-input")
      .attr("width", width)
      .attr("height", height)
      .on("mouseout", function(event) {
        mouseG.attr("visibility", "hidden");
      })
      .on("mouseover", function(event) {
        mouseG.attr("visibility", "visible");
      })
      .on("mousemove", (event) => { mouseMove(event, this); });

    // We only add handlers for press/release in timeline mode.
    if (!label) {
      mouseInput.on("mousedown", (event) => {
        this.mouseDown = true;
        this.shiftDragging = event.shiftKey;
        mouseMove(event, this);
      });
      mouseInput.on("mouseup", (event) => {
        this.shiftDragging = false;
        this.mouseDown = false;
        this.dragStart = null;

        // If a focus range was created then the user was shift-dragging
        // and we need to apply the results as a crop/zoom.
        if (this.focusRange) {
          this.minStep = this.focusRange.min;
          this.maxStep = this.focusRange.max;
          this.focusRange = null;
          this.renderTimeline();

          // Zooming in reveals the reset zoom button
          this.resetZoomButton.hidden = false;
          this.resetZoomButton.onclick = () => {
            this.minStep = 0;
            this.maxStep = baseCurve.numSteps;
            this.focusRange = null;
            this.resetZoomButton.onclick = null;
            this.resetZoomButton.hidden = true;
            this.renderTimeline();
          };
        }
      });
    }
  }
}

export { Grapher };
