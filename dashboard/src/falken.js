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
 * @fileoverview Interfaces with Falken OP API.
 */

const d3 = require('d3');
import { Episode } from './episode.js';
import { Grapher } from './grapher.js';
import { SceneView } from './sceneview.js';
import { timestampToDate, dateToDateTimeLocal,
         labelFromDate } from './utils.js';
import { getServiceUrl } from '../gen/endpoint.js';

/**
 * Defines the Falken class that clients can use to talk to the service.
 * @constructor
 */
export var Falken = function() {
  /**
   * Updates the dashboard to focus on the specified Brain.
   * @param {string} brainId The id of the Brain to select.
   */
  const selectBrain = function(brainId) {
    if ((!currentBrain || brainId != currentBrain.brainId) &&
        brainId in brains) {
      currentBrain = brains[brainId];
      currentSession = null;
      currentEpisode = null;
      updateUrl();
      renderCurrentEpisode();
      listSessions();
    }
  };

  /**
   * Updates the dashboard to focus on the specified Session.
   * @param {string} sessionId The id of the Session to select.
   */
  const selectSession = function(sessionId) {
    if ((!currentSession || sessionId != currentSession.name) &&
        sessionId in currentBrain.sessions) {
      currentSession = currentBrain.sessions[sessionId];
      currentEpisode = null;
      updateUrl();
      renderCurrentEpisode();
      listEpisodes();
    }
  };

  /**
   * Updates the dashboard to focus on the specified Episode.
   * @param {string} episodeId The id of the Episode to select.
   */
  const selectEpisode = function(episodeId) {
    if ((!currentEpisode || episodeId != currentEpisode.id) &&
        episodeId in currentSession.episodes) {
      currentEpisode = currentSession.episodes[episodeId];
      updateUrl();
      renderCurrentEpisode();
      if (!currentEpisode.hasSteps) {
        listSteps();
      }
    }
  };

  /**
   * Queries the backend for the Brains associated with the Project
   * and then populates the relevant data structures and UI.
   */
  const listBrains = function() {
    brainsInputDOM.value = '';
    brainsListDOM.innerHTML = '';
    sessionsInputDOM.value = '';
    sessionsListDOM.innerHTML = '';
    episodesInputDOM.value = '';
    episodesListDOM.innerHTML = '';

    const request = new falkenProto.ListBrainsRequest();
    request.setProjectId(projectId);

    // The listBrains API call may be paginated, so this response handler
    // is written accordingly. We don't update any dashboard state incrementally
    // as that logic is more complex and we can generally get all brain data
    // fairly quickly.
    function responseHandler(err, response) {
      if (err) {
        console.log(err);
        showLoader(false);
      } else if (response) {
        response.getBrainsList().forEach((brainProto) => {
          // Convert every brain proto into a dashboard friendly representation
          // And add it to a master list of brains.
          if (!(brainProto.getBrainId() in brains)) {
            const brain = brainProto.toObject();
            brain.sessions = {};
            brain.createDateTime = timestampToDate(brain.createTime);
            brains[brain.brainId] = brain;
          }
        });

        // If there are additional pages of brains, then kick off a new request.
        if (response.getBrainsList().length > 0 &&
            response.getNextPageToken() != '') {
          request.setPageToken(response.getNextPageToken());
          service.listBrains(request, apiKeyMeta, responseHandler);
        } else {
          // If this was the final page, then update the UI accordingly.
          populateHeaderItems();
          showLoader(false);
          // A "pending" brain is one that was requested via the URL params.
          // We apply it after populating the UI so that it goes through the
          // same flows as if the user selected it manually.
          selectComboBoxById(pendingBrain, selectBrain, brainsListDOM,
                             brainsInputDOM);
          pendingBrain = null;
        }
      }
    }

    showLoader(true);
    service.listBrains(request, apiKeyMeta, responseHandler);
  };

  /**
   * Queries the backend for the Sessions associated with the Project
   * and then populates the relevant data structures and UI.
   */
  const listSessions = function() {
    sessionsInputDOM.value = '';
    sessionsListDOM.innerHTML = '';
    episodesInputDOM.value = '';
    episodesListDOM.innerHTML = '';

    const request = new falkenProto.ListSessionsRequest();
    request.setProjectId(projectId);
    request.setBrainId(currentBrain.brainId);

    // Follows the same paginated structure as Brain.
    function responseHandler(err, response) {
      if (err) {
        console.log(err);
        showLoader(false);
      } else if (response) {
        response.getSessionsList().forEach((sessionProto) => {
          if (!(sessionProto.getName() in currentBrain.sessions)) {
            const session = sessionProto.toObject();
            session.episodes = {};
            session.createDateTime = timestampToDate(session.createTime);
            currentBrain.sessions[session.name] = session;
          }
        });

        // If there are additional pages of Sessions then make a new request.
        if (response.getSessionsList().length > 0 &&
            response.getNextPageToken() != '') {
          request.setPageToken(response.getNextPageToken());
          service.listSessions(request, apiKeyMeta, responseHandler);
        } else {
          // If this was the final page, then update the UI accordingly.
          populateHeaderItems();
          showLoader(false);
          // A "pending" Session is one that was requested via the URL params.
          // We apply it after populating the UI so that it goes through the
          // same flows as if the user selected it manually.
          selectComboBoxById(pendingSession, selectSession,
                             sessionsListDOM, sessionsInputDOM);
          pendingSession = null;
        }
      }
    }

    showLoader(true);
    service.listSessions(request, apiKeyMeta, responseHandler);
  };

  /**
   * Queries the backend for the Episodes associated with the Project
   * and then populates the relevant data structures and UI.
   */
  const listEpisodes = function() {
    episodesInputDOM.value = "";
    episodesListDOM.innerHTML = '';

    const request = new falkenProto.ListEpisodeChunksRequest();
    request.setProjectId(projectId);
    request.setBrainId(currentBrain.brainId);
    request.setSessionId(currentSession.name);
    // This filter allows us to retrieve many episdoes at once, but without
    // the overhead of getting the Step data for each of them.
    request.setFilter(falkenProto.ListEpisodeChunksRequest.Filter.EPISODE_IDS);

    // Follows the same paginated structure as Session and Brain
    let episodeIndex = 0;
    function responseHandler(err, response) {
      if (err) {
        console.log(err);
        showLoader(false);
      } else if (response) {
        response.getEpisodeChunksList().forEach((chunk) => {
          if (!(chunk.getEpisodeId() in currentSession.episodes)) {
            currentSession.episodes[chunk.getEpisodeId()] = new Episode(
                chunk.getEpisodeId(), currentBrain.brainSpec, episodeIndex++);
          }
        });

        // If there are additional pages of Episodes, then make a new request.
        if (response.getEpisodeChunksList().length > 0 &&
            response.getNextPageToken() != '') {
          request.setPageToken(response.getNextPageToken());
          service.listEpisodeChunks(request, apiKeyMeta, responseHandler);
        } else {
          // If this was the final page, then update the UI accordingly.
          populateHeaderItems();
          showLoader(false);
          // A "pending" Episode is one that was requested via the URL params.
          // We apply it after populating the UI so that it goes through the
          // same flows as if the user selected it manually.
          selectComboBoxById(pendingEpisode, selectEpisode,
                             episodesListDOM, episodesInputDOM);
          pendingEpisode = null;
        }
      }
    }

    showLoader(true);
    service.listEpisodeChunks(request, apiKeyMeta, responseHandler);
  };

  /**
   * Retrieves Steps for the current Episode from the backend.
   */
  const listSteps = function() {
    if (currentEpisode.hasSteps) {
      return;
    }

    const request = new falkenProto.ListEpisodeChunksRequest();
    request.setProjectId(projectId);
    request.setBrainId(currentBrain.brainId);
    request.setSessionId(currentSession.name);
    // Steps are very heavyweight (MBs per Episode) so we only retrieve
    // the Steps for a single Episode at a time.
    request.setFilter(
        falkenProto.ListEpisodeChunksRequest.Filter.SPECIFIED_EPISODE);
    request.setEpisodeId(currentEpisode.id);

    // Written with the same pagination structure as Brains/Sessions/Episodes
    // even though we currently store and return a single chunk per Episode.
    function responseHandler(err, response) {
      if (err) {
        console.log(err);
        showLoader(false);
      } else if (response) {
        response.getEpisodeChunksList().forEach((chunk) => {
          chunk.getStepsList().forEach(
              (step) => { currentEpisode.addStep(step.toObject()); });
        });

        // If there are additional pages of Episodes, then make a new request.
        if (response.getEpisodeChunksList().length > 0 &&
            response.getNextPageToken() != '') {
          request.setPageToken(response.getNextPageToken());
          service.listEpisodeChunks(request, apiKeyMeta, responseHandler);
        } else {
          // If this was the final page, then update the UI accordingly.
          showLoader(false);
          currentEpisode.computeControlSegments();
          renderCurrentEpisode();
        }
      }
    }

    showLoader(true);
    service.listEpisodeChunks(request, apiKeyMeta, responseHandler);
  };

  /**
   * Clears the current rendering state and renders
   * the currentEpisode (if there is one).
   */
  const renderCurrentEpisode = function() {
    // Reset the relevant rendering state
    grapher.clearGraphs();
    sceneview.setEpisode(null);

    // Render the current episode (if we have one)
    if (currentEpisode && currentEpisode.hasSteps) {
      grapher.minStep = 0;
      grapher.maxStep = currentEpisode.player.positionCurve.numSteps - 1;

      grapher.render(currentEpisode);
      sceneview.setEpisode(currentEpisode);
    }
  };

  /**
   * Handle window resize events. Currently only updates the 3D view
   * as we expect the graphs to auto-resize when the browser changes the
   * containing divs.
   */
  window.onresize = function() {
    sceneview.onResize();
  }

  /**
   * Shows or hides the progress notification icon.
   * Reference counted in case multiple, async reqiests are active at once.
   * @param {boolean} show True reveals, false hides.
   */
  const showLoader = function(show) {
    if (show) {
      ++loaderRefCount;
    } else {
      --loaderRefCount;
    }
    loader.style.opacity = (loaderRefCount > 0) ? 1 : 0;
  };

  /**
   * Updates the URL params to match the current state of the dashboard.
   * @param {boolean} show True reveals, false hides.
   */
  const updateUrl = function() {
    var searchParams = new URLSearchParams();
    searchParams.append(PROJECT_PARAM, projectId);
    searchParams.append(API_KEY_PARAM, apiKey);
    if (endpoint == "dev") {
      searchParams.append(ENDPOINT_PARAM, "dev");
    }
    if (currentBrain) {
      searchParams.append(BRAIN_PARAM, currentBrain.brainId);
    }
    if (currentSession) {
      searchParams.append(SESSION_PARAM, currentSession.name);
    }
    if (currentEpisode) {
      searchParams.append(EPISODE_PARAM, currentEpisode.id);
    }
    if (timeFilterStart.value) {
      const startTime = new Date(timeFilterStart.value);
      searchParams.append(FILTER_START_PARAM, startTime.getTime());
    }
    if (timeFilterEnd.value) {
      const endTime = new Date(timeFilterEnd.value);
      searchParams.append(FILTER_END_PARAM, endTime.getTime());
    }
    const newUrl = window.location.pathname + "?" + searchParams.toString();
    window.history.pushState(null, '', newUrl);
  }

  /**
   * Utility function to apply a pending Brain/Session/Episode.
   */
  const selectComboBoxById = function(pending, selector, list, input) {
    if (pending) {
      for (var i = 0; i < list.childNodes.length; i++) {
        if (list.childNodes[i].id == pending) {
          selector(pending);
          input.value = list.childNodes[i].value;
          pending = null;
          break;
        }
      }
      if(pending) {
        alert(pending + " is not a valid " + input.labels[0].textContent + ".");
      }
    }
  }

  /**
   * Utility function for user selecting a Brain/Session/Episode.
  */
  const selectComboBoxByValue = function(input, list, action) {
    for (var i = 0; i < list.childNodes.length; i++) {
      if (list.childNodes[i].value === input.value) {
        action(list.childNodes[i].id);
        break;
      }
    }
  };

  /**
   * Updates the Brain/Session/Episode dropdowns, including the application
   * of date-time filters.
   */
  const populateHeaderItems = function() {
    // Filters can come from URL params, so make sure to apply them first.
    if (pendingFilterStart) {
      const startTime = new Date(parseInt(pendingFilterStart));
      timeFilterStart.value = dateToDateTimeLocal(startTime);
      pendingFilterStart = null;
    }
    if (pendingFilterEnd) {
      const endTime = new Date(parseInt(pendingFilterEnd));
      timeFilterEnd.value = dateToDateTimeLocal(endTime);
      pendingFilterEnd = null;
    }

    // Filter min and max are optional. Users can specify one, both, or neither.
    const dateTimeMin =
        timeFilterStart.value ? new Date(timeFilterStart.value) : null;
    const dateTimeMax =
        timeFilterEnd.value ? new Date(timeFilterEnd.value) : null;

    if (brains) {
      // Brains are sorted by creation date, with newest at the top.
      const sortedBrains = Object.values(brains);
      sortedBrains.sort(
          (a, b) => { return b.createDateTime - a.createDateTime; });

      // The oldest brain determines the min time of the filters, as it's
      // impossible to have anything older than that in the project.
      const oldestBrain = sortedBrains[sortedBrains.length - 1];
      const beginTime = dateToDateTimeLocal(oldestBrain.createDateTime);
      timeFilterStart.min = beginTime;
      timeFilterStart.readOnly = false;
      timeFilterEnd.min = beginTime;
      timeFilterEnd.readOnly = false;

      // Populate the dropdown UI with a filtered list.
      brainsListDOM.innerHTML = "";
      sortedBrains.forEach((brain) => {
        if ((!dateTimeMin || brain.createDateTime >= dateTimeMin) &&
            (!dateTimeMax || brain.createDateTime <= dateTimeMax)) {
          const option = document.createElement('option');
          option.id = brain.brainId;
          option.value = brain.brainId + labelFromDate(brain.createDateTime);
          brainsListDOM.appendChild(option);
        }
      });
    }

    if (currentBrain && currentBrain.sessions) {
      // Sessions are sorted by creation date, with newest at the top.
      const sortedSessions = Object.values(currentBrain.sessions);
      sortedSessions.sort(
          (a, b) => { return b.createDateTime - a.createDateTime; });

      // Populate the dropdown UI with a filtered list.
      sessionsListDOM.innerHTML = "";
      sortedSessions.forEach((session) => {
        const option = document.createElement('option');
        option.id = session.name;
        option.value = session.name + labelFromDate(session.createDateTime);
        sessionsListDOM.appendChild(option);
      });
    }

    // We should revisit this if createTime becomes available for Episodes.
    if (currentSession && currentSession.episodes) {
      // Episodes are sorted by index as we don't have creation date.
      // Because the backend returns them in chronological order, this should
      // keep the newest at the top.
      const sortedEpisodes = Object.values(currentSession.episodes);
      sortedEpisodes.sort((a, b) => { return b.index - a.index; });

      // Populate the dropdown UI with an unfiltered list.
      episodesListDOM.innerHTML = "";
      sortedEpisodes.forEach((episode) => {
        const option = document.createElement('option');
        option.id = episode.id;
        option.value = episode.id;
        episodesListDOM.appendChild(option);
      });
    }

    updateUrl();
  }

  // Global state for the dashboard
  let brains = {};
  let currentBrain = null;
  let currentSession = null;
  let currentEpisode = null;
  let loaderRefCount = 0;

  const grapher = new Grapher();
  const sceneview = new SceneView(grapher);

  // One time lookup of important DOM elements and, for some of them,
  // definitions of custom event handlers.
  const brainsListDOM = document.getElementById("brains_list");
  const brainsInputDOM = document.getElementById("brains_input");
  brainsInputDOM.oninput = function() {
    selectComboBoxByValue(brainsInputDOM, brainsListDOM, selectBrain); };
  const sessionsListDOM = document.getElementById("sessions_list");
  const sessionsInputDOM = document.getElementById("sessions_input");
  sessionsInputDOM.oninput = function() {
    selectComboBoxByValue(sessionsInputDOM, sessionsListDOM, selectSession);
  };
  const episodesListDOM = document.getElementById("episodes_list");
  const episodesInputDOM = document.getElementById("episodes_input");
  episodesInputDOM.oninput = function() {
    selectComboBoxByValue(episodesInputDOM, episodesListDOM, selectEpisode);
  };
  const timeFilterStart = document.getElementById('time_filter_start');
  timeFilterStart.onchange = function() { populateHeaderItems(); }
  const timeFilterEnd = document.getElementById('time_filter_end');
  timeFilterEnd.onchange = function() { populateHeaderItems(); }
  const loader = document.getElementById('loader');

  // The URL names of dashboard parameters that we persist.
  const PROJECT_PARAM = "projectId";
  const API_KEY_PARAM = "apiKey";
  const ENDPOINT_PARAM = "endpoint";
  const BRAIN_PARAM = "brainId";
  const SESSION_PARAM = "sessionId";
  const EPISODE_PARAM = "episodeId";
  const FILTER_START_PARAM = "filterStart";
  const FILTER_END_PARAM = "filterEnd";

  // Extract current URL params
  const urlParams = new URLSearchParams(window.location.search);
  const projectId = urlParams.get(PROJECT_PARAM);
  const apiKey = urlParams.get(API_KEY_PARAM);
  const endpoint = urlParams.get(ENDPOINT_PARAM);
  let pendingBrain = urlParams.get(BRAIN_PARAM);
  let pendingSession = urlParams.get(SESSION_PARAM);
  let pendingEpisode = urlParams.get(EPISODE_PARAM);
  let pendingFilterStart = urlParams.get(FILTER_START_PARAM);
  let pendingFilterEnd = urlParams.get(FILTER_END_PARAM);

  // Connect to the service and initialize the dashboard with a list of Brains.
  const apiKeyMeta = {'X-Goog-Api-Key' : apiKey};
  const service = new falkenProto.FalkenServiceClient(
      getServiceUrl(endpoint == "dev"), null, null);
  listBrains();
};
