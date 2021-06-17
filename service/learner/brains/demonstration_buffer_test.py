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

"""Tests for demonstration_buffer."""

# pylint: disable=g-bad-import-order
from absl.testing import absltest
from unittest import mock

import numpy as np
import tensorflow as tf

from tf_agents.trajectories import time_step as ts
from tf_agents.trajectories import trajectory

import common.generate_protos  # pylint: disable=unused-import
import action_pb2
from learner import test_data
from learner.brains import demonstration_buffer
from learner.brains import tfa_specs


class DemonstrationBufferTest(absltest.TestCase):

  _EPISODE_LENGTH = 10
  _NUMBER_OF_EPISODES = 100

  @staticmethod
  def _generate_episode_steps(episode_index, number_of_steps, final_phase):
    """Generates steps for an episode.

    Args:
      episode_index: Index of the episode, used to generate the episode_id.
      number_of_steps: Number of steps to generate.
      final_phase: Step phase for the final step.

    Yields:
      Step instance for each generated step in the episode up to
      number_of_steps.
    """
    episode_id = f'episode_{episode_index}'
    reward = 1.0
    for i, phase in demonstration_buffer.generate_index_and_step_phase(
        number_of_steps, final_phase):
      # Generate observations and actions within range of the spec.
      observation = test_data.observation_data(i % 100, (i, i, i))
      action = test_data.action_data(0, (i % 100) / 100)
      yield demonstration_buffer.Step(
          episode_id=episode_id,
          phase=phase,
          observation_pb=observation,
          action_pb=action,
          reward=reward,
          timestamp_micros=(episode_index * number_of_steps) + i)

  def test_do_not_populated_with_aborted_episodes(self):
    """Test non-success episodes are ignored when populating the buffer."""
    demo_buffer = demonstration_buffer.DemonstrationBuffer(
        tfa_specs.BrainSpec(test_data.brain_spec()))

    buffered_episode_phases = (demonstration_buffer.StepPhase.SUCCESS,
                               demonstration_buffer.StepPhase.FAILURE,
                               demonstration_buffer.StepPhase.GAVE_UP)

    for i in range(self._NUMBER_OF_EPISODES):
      final_phase = buffered_episode_phases[i % len(buffered_episode_phases)]
      for step in self._generate_episode_steps(i, self._EPISODE_LENGTH,
                                               final_phase):
        demo_buffer.record_step(step)
      # Aborted episodes should be ignored.
      for step in self._generate_episode_steps(
          self._NUMBER_OF_EPISODES + i, self._EPISODE_LENGTH,
          demonstration_buffer.StepPhase.ABORTED):
        demo_buffer.record_step(step)

    frame_count = 0
    for _, frames in demo_buffer.flush_episode_demonstrations():
      frame_count += frames
    self.assertEqual(frame_count,
                     (self._EPISODE_LENGTH - 1) * self._NUMBER_OF_EPISODES)

  def test_clear(self):
    """Test clearing a demonstration buffer."""
    # Populate the buffer with some data.
    demo_buffer = demonstration_buffer.DemonstrationBuffer(
        tfa_specs.BrainSpec(test_data.brain_spec()))
    for step in DemonstrationBufferTest._generate_episode_steps(
        0, self._EPISODE_LENGTH,
        demonstration_buffer.StepPhase.SUCCESS):
      demo_buffer.record_step(step)
    demo_buffer.clear()
    self.assertEmpty(list(demo_buffer.flush_episode_demonstrations()))

  def test_episode_steps_to_trajectories(self):
    """Test converting episode steps to trajectories."""
    brain_spec = tfa_specs.BrainSpec(test_data.brain_spec())
    steps = list(self._generate_episode_steps(
        0, 5, demonstration_buffer.StepPhase.SUCCESS))
    # Ignore steps 0 & 2
    steps[0].action_pb.source = action_pb2.ActionData.ActionSource.BRAIN_ACTION
    steps[2].action_pb.source = action_pb2.ActionData.ActionSource.BRAIN_ACTION

    expected_steps = [steps[1], steps[3], steps[4]]
    expected_time_steps = [s.get_time_step(brain_spec.observation_spec)
                           for s in expected_steps]
    expected_action_steps = [s.get_action_step(brain_spec.action_spec)
                             for s in expected_steps]

    trajectories = demonstration_buffer.episode_steps_to_trajectories(
        steps, brain_spec)

    number_of_trajectories = len(trajectories)
    expected_number_of_trajectories = len(expected_steps) - 1
    self.assertEqual(number_of_trajectories, expected_number_of_trajectories)
    for i, current_trajectory in enumerate(trajectories):
      step_msg = f'step{i}'
      expected_time_step = expected_time_steps[i]
      next_expected_time_step = expected_time_steps[i + 1]
      expected_action_step = expected_action_steps[i]
      self.assertEqual(current_trajectory.step_type,
                       expected_time_step.step_type,
                       msg=step_msg)
      tf.nest.assert_same_structure(current_trajectory.observation,
                                    expected_time_step.observation,
                                    expand_composites=True)
      tf.nest.assert_same_structure(current_trajectory.action,
                                    expected_action_step.action,
                                    expand_composites=True)
      self.assertEqual(current_trajectory.policy_info,
                       expected_action_step.info,
                       msg=step_msg)
      self.assertEqual(current_trajectory.next_step_type,
                       next_expected_time_step.step_type,
                       msg=step_msg)
      self.assertEqual(current_trajectory.reward,
                       next_expected_time_step.reward,
                       msg=step_msg)
      self.assertEqual(current_trajectory.discount,
                       next_expected_time_step.discount,
                       msg=step_msg)

  def testBatchTrajectories(self):
    """Test batching episode trajectories into a single Trajectory object."""
    batched_trajectory = demonstration_buffer.batch_trajectories([
        trajectory.Trajectory(
            step_type=ts.StepType.MID,
            observation={
                'player': {
                    'distance_to_goal': np.array([10.0]),
                    'fuel': np.array([3]),
                },
            },
            action={
                'yoke': np.array([-0.5, 0.1]),
                'throttle': np.array([0.15]),
            },
            policy_info=[],
            next_step_type=ts.StepType.MID,
            reward=0.5,
            discount=0.5,
        ),
        trajectory.Trajectory(
            step_type=ts.StepType.MID,
            observation={
                'player': {
                    'distance_to_goal': np.array([9.0]),
                    'fuel': np.array([2]),
                },
            },
            action={
                'yoke': np.array([0.2, -0.5]),
                'throttle': np.array([1.0]),
            },
            policy_info=[],
            next_step_type=ts.StepType.LAST,
            reward=1.0,
            discount=0.0,
        )])
    expected_trajectory = trajectory.Trajectory(
        step_type=tf.constant([ts.StepType.MID, ts.StepType.MID]),
        observation={
            'player': {
                'distance_to_goal': tf.constant([[10.0, 9.0]]),
                'fuel': tf.constant([[3, 2]]),
            },
        },
        action={
            'yoke': tf.constant([[[0.5, 0.1], [0.2, -0.5]]]),
            'throttle': tf.constant([[0.15], [1.0]]),
        },
        policy_info=[],
        next_step_type=tf.constant([ts.StepType.MID, ts.StepType.LAST]),
        reward=tf.constant([0.5, 1.0]),
        discount=tf.constant([0.5, 0.0]))
    tf.nest.assert_same_structure(batched_trajectory,
                                  expected_trajectory,
                                  expand_composites=True)

  @mock.patch.object(demonstration_buffer, 'batch_trajectories')
  def testEpisodesToTrajectories(self, mock_batch_trajectories):
    """Test converting episodes to batched trajectories."""
    episode_step_generators = []
    number_of_steps = 5
    for i in range(2):
      episode_step_generators.append(
          self._generate_episode_steps(
              i, number_of_steps, demonstration_buffer.StepPhase.SUCCESS))

    mock_trajectories = [42, 21]
    mock_batch_trajectories.side_effect = lambda _: mock_trajectories.pop(0)
    trajectories_and_sizes = list(demonstration_buffer.episodes_to_trajectories(
        episode_step_generators, tfa_specs.BrainSpec(test_data.brain_spec())))
    self.assertEqual(trajectories_and_sizes,
                     [(42, number_of_steps - 1), (21, number_of_steps - 1)])


if __name__ == '__main__':
  absltest.main()
