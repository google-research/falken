# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility functions to create test data for tests."""

# pylint: disable=g-bad-import-order
import json
import os
import numpy as np
import tensorflow as tf

from tf_agents.trajectories import policy_step
from tf_agents.trajectories import time_step as ts
from tf_agents.trajectories import trajectory as tf_trajectory

from google.protobuf import text_format

import common.generate_protos  # pylint: disable=unused-import

import action_pb2
import brain_pb2
import episode_pb2
import observation_pb2
import data_store_pb2

from learner.brains import specs


PROJECT_ID = 'project_id_1'
BRAIN_ID = 'brain_1'
SESSION_ID = 'session_1'
EPISODE_ID = 'episode_1'
ASSIGNMENT_ID = (
    # Choose settings that maximize speed and reduce non-determinism.
    '{"batch_size": 500, "training_examples": 500, "save_interval_batches": 5,'
    ' "synchronous_export": true, "use_xla_jit": false, '
    ' "num_batches_to_sample": 5}')
SUBTASK_ID = 'subtask_1'


def populate_data_store(data_store, assignment_id=None, episode_ids=None,
                        steps_per_episode_chunk=None):
  """Populate a datastore with an assignment.

  Args:
    data_store: DataStore instance to populate.
    assignment_id: Assignment ID to create or ASSIGNMENT_ID if this is None.
    episode_ids: IDs of episodes to create or a single episode with
      EPISODE_ID if this is None.
    steps_per_episode_chunk: List of number of steps for each episode chunk.
      For example, [2, 4] would create two chunks with 2 and 4 steps
      respectively. If this is None, this argument defaults to [2, 2].

  Returns:
    (assignment_resource_id, episode_chunk_resource_ids) where
    assignment_resource_id is resource ID of the written assignment and
    episode_chunk_resource_ids is a list of episode chunk resource IDs written
    to the data store.
  """
  assignment_proto = assignment(assignment_id=assignment_id)
  assignment_resource_id = data_store.to_resource_id(assignment_proto)
  protos = [
      project(),
      data_store_brain(),
      session(),
      assignment_proto,
  ]
  if not steps_per_episode_chunk:
    steps_per_episode_chunk = [2, 2]
  if episode_ids is None:
    episode_ids = [EPISODE_ID]
  episode_chunk_resource_ids = []
  if episode_ids:
    for episode_id in episode_ids:
      for chunk in episode_chunks(steps_per_episode_chunk, episode_id):
        episode_chunk_resource_ids.append(data_store.to_resource_id(chunk))
        protos.append(chunk)
  for proto in protos:
    data_store.write(proto)
  return assignment_resource_id, episode_chunk_resource_ids


def project():
  """Return a test data_store_pb2.Project."""
  return data_store_pb2.Project(project_id=PROJECT_ID)


def data_store_brain():
  """Return a test data_store_pb2.Brain."""
  return data_store_pb2.Brain(
      project_id=PROJECT_ID,
      brain_id=BRAIN_ID,
      brain_spec=brain_spec())


def session():
  """Return a test data_store_pb2.Session."""
  return data_store_pb2.Session(
      project_id=PROJECT_ID,
      brain_id=BRAIN_ID,
      session_id=SESSION_ID)


def create_assignment_id(override_dict):
  """Return the default test assignment id with hparam overrides."""
  assignment_dict = json.loads(ASSIGNMENT_ID)
  assignment_dict.update(override_dict)
  return json.dumps(assignment_dict)


def assignment(assignment_id=None):
  """Returns a test data_store_pb2.Assignment.

  Args:
    assignment_id: Assignment ID string to use or None to use
      ASSIGNMENT_ID.

  Returns:
    data_store_pb2.Assignment instance.
  """
  return data_store_pb2.Assignment(
            project_id=PROJECT_ID,
            brain_id=BRAIN_ID,
            session_id=SESSION_ID,
            assignment_id=(assignment_id if assignment_id else ASSIGNMENT_ID))


def episode_chunks(steps_per_episode_chunk, episode_id):
  """Get example episode chunks.

  Args:
    steps_per_episode_chunk: List of number of steps for each episode chunk.
      For example, [2, 4] would create two chunks with 2 and 4 steps
      respectively.
    episode_id: ID of the episode all chunks belong to.

  Returns:
    List of episode_pb2.EpisodeChunk protos.
  """
  chunk = episode_pb2.EpisodeChunk()
  chunks = []
  step_timestamp = 0
  number_of_chunks = len(steps_per_episode_chunk)
  for chunk_index, chunk_size in enumerate(steps_per_episode_chunk):
    chunk = data_store_pb2.EpisodeChunk(
        project_id=PROJECT_ID,
        brain_id=BRAIN_ID,
        session_id=SESSION_ID,
        episode_id=episode_id,
        chunk_id=chunk_index)
    for _ in range(chunk_size):
      step = episode_pb2.Step()
      step.timestamp_millis = step_timestamp
      step_timestamp += 1000
      step.observation.CopyFrom(observation_data(50, [1, 2, 3]))
      step.action.CopyFrom(action_data(1, 0.3))

      chunk.data.episode_id = episode_id
      chunk.data.chunk_id = chunk_index
      chunk.data.steps.append(step)
      if chunk_index < number_of_chunks - 1:
        chunk.data.episode_state = episode_pb2.IN_PROGRESS
      else:
        chunk.data.episode_state = episode_pb2.SUCCESS
    chunks.append(chunk)

  return chunks


def _read_text_file(filename):
  """Read the contents of a text file relative into a string.

  Args:
    filename: Path to a file relative to this module.

  Returns:
    String contents of the file.
  """
  with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), filename),
            mode='rt') as file_obj:
    return file_obj.read()


def observation_spec():
  """Builds an example ObservationSpec."""
  spec = observation_pb2.ObservationSpec()
  text_format.Parse(_read_text_file('example_model/observation_spec.pbtxt'),
                    spec)
  return spec


def observation_data(health, position):
  """Builds an example ObservationData object."""
  data = observation_pb2.ObservationData()
  text_format.Parse(
      _read_text_file(
          'example_model/observation_data.pbtxt_template').format(
              position0=position[0],
              position1=position[1],
              position2=position[2],
              health=health), data)
  return data


def action_spec():
  """Builds an example ActionSpec."""
  spec = action_pb2.ActionSpec()
  text_format.Parse(_read_text_file('example_model/action_spec.pbtxt'), spec)
  return spec


def action_data(switch_weapon, throttle,
                joy1=None, joy2=None, joy3=None):
  """Builds an example ActionData."""
  joy1 = None or [1.0, 0.0]
  joy2 = None or [0.0, -1.0]
  joy3 = None or [-1.0, 0.5]
  data = action_pb2.ActionData()
  text_format.Parse(
      _read_text_file('example_model/action_data.pbtxt_template').format(
          switch_weapon=switch_weapon,
          throttle=throttle,
          joy1_x_axis=joy1[0],
          joy1_y_axis=joy1[1],
          joy2_x_axis=joy2[0],
          joy2_y_axis=joy2[1],
          joy3_x_axis=joy3[0],
          joy3_y_axis=joy3[1]), data)
  return data


def brain_spec():
  return brain_pb2.BrainSpec(
      observation_spec=observation_spec(),
      action_spec=action_spec())


def brain():
  return data_store_pb2.Brain(
      project_id=PROJECT_ID,
      brain_id=BRAIN_ID,
      name='test_brain',
      brain_spec=brain_spec())


def trajectory(health=100, position=(0, 0, 0), switch_weapon=0, throttle=1.0,
               add_batch_dimension=False):
  """Return a single frame example trajectory.

  Args:
    health: Health to add to the observation. (0.0...100.0)
    position: Position to add to the player entity.
      (3 component tuple of floats)
    switch_weapon: Switch weapon action. (0...4)
    throttle: Throttle action. (-1.0...1.0)
    add_batch_dimension: Whether to add a batch (outer most) dimension of size
      1 around each tensor in the trajectory.

  Returns:
    TF Agents Trajectory instance.
  """
  obs_spec = specs.ObservationSpec(observation_spec())
  act_spec = specs.ActionSpec(action_spec())
  obs_data = obs_spec.tfa_value(observation_data(health, position))
  act_data = act_spec.tfa_value(action_data(switch_weapon, throttle))

  act_step = policy_step.PolicyStep(action=act_data)
  reward_array = np.array([0.0], dtype=np.float32)
  discount_array = np.array([0.99], dtype=np.float32)

  time_step = ts.transition(
      obs_data, reward=reward_array, discount=discount_array)
  traj = tf_trajectory.from_transition(
      time_step, act_step, time_step)
  if add_batch_dimension:
    traj = tf.nest.map_structure(lambda tensor: tf.expand_dims(tensor, axis=0),
                                 traj)
  return traj
