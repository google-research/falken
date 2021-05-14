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
 * @fileoverview Utility functions for the dashboard.
 */

/**
 * Converts a google.protobuf.timestamp into a JS Date.
 * @param {object} timestamp The Timestamp to convert.
 * @return {object} The Timestamp as a JS Date.
 */
const timestampToDate = function(timestamp) {
  const MillisecondsPerSecond = 1000;
  const NanosecondsPerMillisecond = 1000000;
  return new Date(timestamp.seconds * MillisecondsPerSecond +
    (timestamp.nanos / NanosecondsPerMillisecond));
}

/**
 * Converts a JS Date into a DateTime-Local string
 * @param {object} date The JS Date to convert.
 * @return {string} The JS Date as a DateTime-Local string.
 */
const dateToDateTimeLocal = function(date) {
  const MillisecondsPerMinute = 60000;
  // DateTime-Local wants the same format as ISO Date, but without the
  // Timezone component of the ISO date, so we shift the time by the local
  // offset and then slice off the timezone from the final string.
  const offsetDate = new Date(date.getTime() -
    date.getTimezoneOffset() * MillisecondsPerMinute);
  return offsetDate.toJSON().slice(0, 16);
}

/**
 * Converts a JS Date into a compact string.
 * @param {object} date The JS Date to convert.
 * @return {string} The JS Date as a compact string.
 */
const labelFromDate = function(date) {
  let language;
  if (window.navigator.languages) {
    language = window.navigator.languages[0];
  } else {
    language = window.navigator.userLanguage || window.navigator.language;
  }
  const options = {dateStyle : "short", timeStyle : "short"};
  return " (" + date.toLocaleString(language, options) + ")";
}

export { timestampToDate, dateToDateTimeLocal, labelFromDate };
