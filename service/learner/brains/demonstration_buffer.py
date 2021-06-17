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

"""Collects falken demo steps and returns tf_agents trajectories."""

# pylint: disable=g-bad-import-order
import collections
import enum

import numpy as np
import tensorflow as tf

from tf_agents.trajectories import policy_step
from tf_agents.trajectories import time_step as ts
from tf_agents.trajectories import trajectory

import common.generate_protos  # pylint: disable=unused-import
import action_pb2


class StepPhase(enum.Enum):
  """Enum representing the possible phases of a step within an episode."""
  UNSPECIFIED = enum.auto()
  START = enum.auto()
  IN_PROGRESS = enum.auto()
  SUCCESS = enum.auto()
  FAILURE = enum.auto()
  ABORTED = enum.auto()
  GAVE_UP = enum.auto()


_END_STEP_PHASES = frozenset((StepPhase.SUCCESS, StepPhase.FAILURE,
                              StepPhase.ABORTED, StepPhase.GAVE_UP))


def _is_episode_end(step_phase):
  """Determine whether the specified phase is the end of an episode.

  Args:
    step_phase: StepPhase to query.

  Returns:
    A Boolean indicating whether the phase signifies the end of an episode.
  """
  return step_phase in _END_STEP_PHASES


class Step(
    collections.namedtuple(
        'Step',
        ','.join([
            'observation_pb',
            'reward',
            'phase',
            'episode_id',
            'action_pb',
            'timestamp_micros']))):
  """Represents data associated with a falken step at a specific time.

  Attributes:
    episode_id: Id for the episode that's collecting this step.
    phase: The phase of the episode this step represents.
    observation_pb: The observation data for this step.
    action_pb: Action data from brain or user.
    reward: The reward for this step.
    timestamp_micros: Microsecond timestamp of the step.
  """

  def get_time_step(self, observation_spec):
    """Extract TFA time_step from step.

    Arguments:
      observation_spec: The tfa_specs.ObservationSpec associated with the
        observation.

    Returns:
      The converted tf_agents TimeStep object.
    """

    # Converts incoming observations into TFA format
    tfa_observation = observation_spec.tfa_value(self.observation_pb)

    reward = np.array(self.reward, dtype=np.float32)
    discount = np.array(1.0, dtype=np.float32)

    if self.phase == StepPhase.START:
      time_step = ts.restart(tfa_observation)
    elif self.phase == StepPhase.SUCCESS or self.phase == StepPhase.ABORTED:
      time_step = ts.termination(tfa_observation, reward=reward)
    elif self.phase == StepPhase.ABORTED:
      time_step = ts.truncation(
          tfa_observation, reward=reward, discount=discount)
    else:
      time_step = ts.transition(
          tfa_observation, reward=reward, discount=discount)
    return time_step

  def get_action_step(self, action_spec):
    """Extract TFA action_step from step.

    Arguments:
      action_spec: The tfa_specs.ActionSpec associated with the action

    Returns:
      The converted tf_agents PolicyStep object.
    """
    return policy_step.PolicyStep(action=action_spec.tfa_value(
        self.action_pb))


def generate_index_and_step_phase(number_of_steps, final_phase):
  """Generate an index and phase for a number of steps.

  Args:
    number_of_steps: Number of step of data.
    final_phase: StepPhase of the last frame of data.

  Yields:
    Tuple of (step_index, phase) for each step with the first step
    containing StepPhase.START, intermediate frames with StepPhase.SUCCESS
    and the last step with final_phase.
  """
  for i in range(number_of_steps):
    if i == 0:
      step_phase = StepPhase.START
    elif i == number_of_steps - 1:
      step_phase = final_phase
    else:
      step_phase = StepPhase.IN_PROGRESS
    yield (i, step_phase)


def episode_steps_to_trajectories(episode_steps, brain_spec):
  """Convert human demonstration episode steps into Trajectory objects.

  Args:
    episode_steps: Iterable of Step instances.
    brain_spec: spec.BrainSpec instance used to convert observation and action
      data protos to TF agents data structures.

  Returns:
    A list of Trajectory instances from all steps with human demonstrations.
  """
  observation_spec = brain_spec.observation_spec
  action_spec = brain_spec.action_spec
  trajectories = []
  previous_timestep = None
  previous_episode_step = None
  for current_episode_step in episode_steps:
    if (current_episode_step.action_pb.source !=
        action_pb2.ActionData.HUMAN_DEMONSTRATION):
      # Ignore non-demo frames
      continue
    current_timestep = current_episode_step.get_time_step(observation_spec)
    if previous_timestep:
      trajectories.append(trajectory.from_transition(
          previous_timestep,
          previous_episode_step.get_action_step(action_spec),
          current_timestep))
      del previous_timestep
    previous_episode_step = current_episode_step
    previous_timestep = current_timestep
  return trajectories


def batch_trajectories(trajectories):
  """Combine a list of TF Agents Trajectory instances into a single batch.

  Args:
    trajectories: List of Trajectory instances, one per step, to combine into
      a single Trajectory instance.

  Returns:
    A TF agents Trajectory instance that references tensors which contains all
    steps in the provided trajectories list.
  """

  def _stack_trajectories(*trajectory_tensors):
    """Stack a list of tensors into a single tensor.

    Args:
      *trajectory_tensors: Tensor / numpy array instances in positional
        arguments as required to use tf.nest.map_structure().

    Returns:
      tf.Tensor instance in the form [trajectories0 .. trajectoriesN] i.e
      batched by N where N is the number of trajectories arguments passed to
      this method.
    """
    return tf.stack(trajectory_tensors)

  # Each tf_agents TimeStep (from observation) and tf_agents PolicyStep
  # (from action), referenced by each Trajectory instance, is a nested
  # dictionary with numpy arrays or tensors as leaves
  # (see tfa_specs.SpecBase.tfa_value()). This nested structure is converted
  # from a list of Trajectory instances to a single Trajectory instance
  # where each leaf is a tensor with a batch size of N where N is the
  # number of trajectories in the episode.
  return tf.nest.map_structure(_stack_trajectories, *trajectories)


def episodes_to_trajectories(episodes, brain_spec):
  """Convert human demonstration episode steps into Trajectory objects.

  Args:
    episodes: List of episode steps which are lists of Step instances
      in the form...
      [[episode0_step0 ... episode0_stepN], ... [episodeN_step0 ...]]
      Only human demonstration steps in the provided episodes are
      converted to Trajectory instances.
    brain_spec: spec.BrainSpec instance used to convert observation and action
      data protos to TF agents data structures.

  Yields:
    (batched_trajectory, size_of_batch) for each episode. Where
    batched_trajectory is a TF agents Trajectory instance that references
    tensors which contains all steps in the episode. size_of_batch is the
    number of steps in batched_trajectory.
  """
  for episode in episodes:
    trajectories = episode_steps_to_trajectories(episode, brain_spec)
    if trajectories:
      yield (batch_trajectories(trajectories), len(trajectories))


class DemonstrationBuffer:
  """DemonstrationBuffer accumulates frame data and returns tfa trajectories.

  Note that aborted episodes are silently removed.

  Usage:
    d = DemonstrationBuffer(brain_spec)
    while ...:
      for ...:
        d.record_step(step)
      for episode in d.flush_episode_demonstrations():
        for frame in episode:
          # frame is a trajectory that represents a demo frame.
          replay_buffer.add_batch(frame)
  """

  def __init__(self, brain_spec):
    """Initialize the demonstration buffer instance.

    Args:
      brain_spec: tfa_specs.BrainSpec instance used to convert Step instances to
        TF agents data structures.
    """
    # Maps episodes to lists of frames.
    self._episode_buffer = collections.defaultdict(list)
    self._completed_episodes = []
    self._brain_spec = brain_spec

  def record_step(self, step):
    """Records a known state+action from a given env.

    Args:
      step: A Step instance.
    """
    steps = self._episode_buffer[step.episode_id]
    steps.append(step)
    if _is_episode_end(step.phase):
      if step.phase != StepPhase.ABORTED:
        self._completed_episodes.append(steps)
      del self._episode_buffer[step.episode_id]

  def flush_episode_demonstrations(self):
    """Removes completed episodes and yields batched trajectories and length.

    Returns:
      Generator that yields (batched_trajectory, size_of_batch) for each
      episode. Where batched_trajectory is a TF agents Trajectory instance that
      references tensors which contains all steps in the episode.
      size_of_batch is the number of steps in batched_trajectory.
    """
    episodes = self._completed_episodes
    self._completed_episodes = []
    return episodes_to_trajectories(episodes, self._brain_spec)

  def clear(self):
    """Clear the demonstration buffer."""
    self._episode_buffer.clear()
    self._completed_episodes.clear()
