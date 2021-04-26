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

"""Tests for ContinuousImitationBrain."""

import glob
import os
import random
import tempfile
import time
from unittest import mock

from absl import flags
from absl.testing import absltest
from absl.testing import parameterized
from learner import test_data
from learner.brains import continuous_imitation_brain
from learner.brains import demonstration_buffer
import numpy as np
import tensorflow as tf


class ContinuousImitationBrainTest(parameterized.TestCase):

  _STEPS_PER_EPISODE = 6
  _EPISODES_TO_RUN = 10
  _EPISODE_ID = 0

  def setUp(self):
    super().setUp()
    self.temp_dirs = []
    self.temp_path = self._temporary_directory('cil_test_')
    self.checkpoint_path = os.path.join(self.temp_path, 'checkpoint')
    self.summary_path = os.path.join(self.temp_path, 'summary')
    self.brain_spec = test_data.brain_spec()

  def tearDown(self):
    """Clean up all temporary directories."""
    super().tearDown()
    for temp_dir in self.temp_dirs:
      temp_dir.cleanup()

  def _temporary_directory(self, prefix):
    """Create a temporary directory under the test temporary dir.

    Args:
      prefix: Prefix for the temporary directory name.

    Returns:
      Name of the temporary directory.
    """
    temp_dir = tempfile.TemporaryDirectory(
        prefix=os.path.join(flags.FLAGS.test_tmpdir, prefix))
    self.temp_dirs.append(temp_dir)
    return temp_dir.name

  def _init_brain(self):
    hparams = continuous_imitation_brain.BCAgent.default_hparams()
    hparams['use_xla_jit'] = False
    hparams['num_batches_to_sample'] = 5
    hparams['batch_size'] = 500
    hparams['training_examples'] = 500
    self.brain = continuous_imitation_brain.ContinuousImitationBrain(
        brain_id=0,
        spec_pb=self.brain_spec,
        checkpoint_path=self.checkpoint_path,
        summary_path=self.summary_path,
        hparams=hparams)
    self.assertEqual(self.brain.hparams['training_steps'], 1)

  def test_trajectory_subdivision(self):
    self._init_brain()

    def test_generator():
      yield {'a': tf.constant([0, 1, 2, 3, 4])}, 5
      yield {'a': tf.constant([0, 1, 2, 3, 4, 5])}, 6
      yield {'a': tf.constant([0, 1, 2, 3, 4, 5])}, 6

    rng = mock.MagicMock()
    rng.randint.side_effect = [0, 2, 5]

    result = list(
        continuous_imitation_brain._select_sub_trajectories(
            test_generator(), 0.2, rng))

    result = tf.nest.map_structure(  # convert tensors to lists
        lambda x: x.numpy().tolist() if hasattr(x, 'numpy') else x, result)

    self.assertEqual(result[0], (None, {'a': [0]}, {'a': [1, 2, 3, 4]}))

    self.assertEqual(result[1], ({'a': [0, 1]}, {'a': [2]}, {'a': [3, 4, 5]}))

    self.assertEqual(result[2], ({'a': [0, 1, 2, 3, 4]}, {'a': [5]}, None))

  @staticmethod
  def _random_step_generator():
    """Generate random training data.

    Yields:
      (observation_data_proto, action_data_proto) populated with random data.
    """
    yield (test_data.observation_data(
        random.uniform(0, 100.0),
        (random.uniform(0, 50), random.uniform(0, 50), random.uniform(0, 50))),
           test_data.action_data(
               random.randrange(0, 1), random.uniform(-1.0, 1.0)))

  @staticmethod
  def _constant_step_generator():
    """Generate constant training data.

    Yields:
      (observation_data_proto, action_data_proto) populated with constan data.
    """
    yield (test_data.observation_data(50.0, (10, 15, 20)),
           test_data.action_data(1, 0.3))

  def _add_training_data_to_brain(self,
                                  number_of_episodes,
                                  steps_per_episode,
                                  first_episode_id=0,
                                  constant=False):
    """Add training data to the test's brain.

    Args:
      number_of_episodes: Episode to create.
      steps_per_episode: Number of steps in each episode.
      first_episode_id: Integer ID of the first episode.
      constant: Use constant data for all steps.
    """
    step_generator = (
        self._constant_step_generator
        if constant else self._random_step_generator)
    reward = 0
    for episode_index in range(number_of_episodes):
      for i, step_phase in (demonstration_buffer.generate_index_and_step_phase(
          steps_per_episode, demonstration_buffer.StepPhase.SUCCESS)):
        observation_data, action_data = next(step_generator())
        self.brain.record_step(observation_data, reward, step_phase,
                               first_episode_id + episode_index, action_data,
                               episode_index + i)

  def test_short_episodes(self):
    self._init_brain()
    steps_per_episode = 3
    episodes_to_run = 100
    self._add_training_data_to_brain(episodes_to_run, steps_per_episode)

    got_frames = self.brain.num_train_frames + self.brain.num_eval_frames

    # Eval frames received are sent as pairs (cur, next), so we get one less
    # than the length of the episode.
    want_frames = (steps_per_episode - 1) * episodes_to_run

    # Check that we recorded all the frames:
    self.assertEqual(got_frames, want_frames)
    # Check that we have some versions in the eval datastore.
    self.assertNotEmpty(self.brain._eval_datastore.versions)

  def test_train_brain(self):
    """Tests training a brain using continuous imitation learning."""
    self._init_brain()
    self._add_training_data_to_brain(
        self._EPISODES_TO_RUN,
        self._STEPS_PER_EPISODE,
        first_episode_id=self._EPISODE_ID,
        constant=True)

    got_frames = self.brain.num_train_frames + self.brain.num_eval_frames
    # Eval frames received are sent as pairs (cur, next), so we get one less
    # than the length of the episode.
    want_frames = (self._STEPS_PER_EPISODE - 1) * self._EPISODES_TO_RUN

    # Check that we recorded all the frames:
    self.assertEqual(got_frames, want_frames)
    # Check that we have some versions in the eval datastore.
    self.assertNotEmpty(self.brain._eval_datastore.versions)
    self.assertLen(self.brain._eval_datastore.versions, self._EPISODES_TO_RUN)
    # Check that we have some frames in the eval datastore.
    self.assertEqual(self.brain._eval_datastore.eval_frames,
                     self._EPISODES_TO_RUN * int(self._STEPS_PER_EPISODE * 0.2))

    # Check that the difference between versions is of the expected size.
    last_frames = 0
    for v in self.brain._eval_datastore.versions:
      data = self.brain._eval_datastore.get_version(v)

      def batch_size(tensor_nest):
        """Return outermost dim of tensors in tensor nest."""
        size = 0

        def _set_size(t):
          nonlocal size
          size = len(t)

        tf.nest.map_structure(_set_size, tensor_nest)
        return size

      frames = batch_size(data)
      diff = frames - last_frames

      self.assertEqual(diff, int(self._STEPS_PER_EPISODE * 0.2))
      last_frames = frames

    # Save policy before training.
    policy_0_path = self._temporary_directory('before_training')
    p0_saved_model_dir = os.path.join(policy_0_path, 'saved_model')
    p0_checkpoint_dir = os.path.join(policy_0_path, 'checkpoint')
    p0_tflite_dir = os.path.join(p0_saved_model_dir, 'tflite')
    os.makedirs(p0_checkpoint_dir)

    self.brain.save_checkpoint(p0_checkpoint_dir)
    self.brain.export_saved_model(p0_saved_model_dir)
    self.brain.convert_model_to_tflite(p0_saved_model_dir, p0_tflite_dir)

    self.brain.train()

    # Save policy after training.
    policy_1_path = self._temporary_directory('after_training')
    p1_saved_model_dir = os.path.join(policy_1_path, 'saved_model')
    p1_checkpoint_dir = os.path.join(policy_1_path, 'checkpoint')
    p1_tflite_dir = os.path.join(p1_saved_model_dir, 'tflite')
    os.makedirs(p1_checkpoint_dir)

    self.brain.save_checkpoint(p1_checkpoint_dir)
    self.brain.export_saved_model(p1_saved_model_dir)
    self.brain.convert_model_to_tflite(p1_saved_model_dir, p1_tflite_dir)

    # Test evaluation:
    full_eval = list(self.brain.compute_full_evaluation())
    # Test evaluation when frehly loading the recent checkpoint.
    from_checkpoint_full_eval = list(
        self.brain.compute_full_evaluation(policy_1_path))
    # Test evaluation on older checkpoint
    prev_full_eval = list(self.brain.compute_full_evaluation(policy_0_path))

    # Data is the same, so eval score should be the same for each version.
    _, score0 = full_eval[0]
    _, scores = zip(*full_eval)
    _, from_checkpoint_scores = zip(*from_checkpoint_full_eval)
    for score, ckpt_score in zip(scores, from_checkpoint_scores):

      def _assert_float_eq(f1, f2):
        self.assertLess(abs(float(f1) - float(f2)), 1e-5)

      # Should be equal to score[0]
      _assert_float_eq(score, score0)
      _assert_float_eq(ckpt_score, score)

    _, prev_scores = zip(*prev_full_eval)

    # Check that the eval score is different before and after training.
    self.assertTrue(any(old != new for old, new in zip(prev_scores, scores)))

  def test_save_policy(self):
    self._init_brain()
    temp_path = self._temporary_directory('save_policy')

    saved_checkpoint_dir = os.path.join(temp_path, 'checkpoint')
    os.makedirs(saved_checkpoint_dir)
    saved_model_dir = os.path.join(temp_path, 'saved_model')
    checkpoint_dir = os.path.join(temp_path, 'checkpoint')
    tflite_dir = os.path.join(saved_model_dir, 'tflite')

    self.brain.save_checkpoint(saved_checkpoint_dir)
    self.brain.export_saved_model(saved_model_dir)
    self.brain.convert_model_to_tflite(saved_model_dir, tflite_dir)

    dir_contents = {
        saved_model_dir: [
            'assets',
            'policy_specs.pbtxt',
            'saved_model.pb',
            'tflite',
            'variables',
        ],
        checkpoint_dir: [
            'ckpt-0.index', 'ckpt-0.data-00000-of-00001', 'checkpoint'
        ],
        tflite_dir: ['model.tflite']
    }
    if not self.brain._write_tflite:
      del dir_contents[tflite_dir]

    for path, contents in dir_contents.items():
      self.assertCountEqual(
          glob.glob(path + '/*'), [os.path.join(path, c) for c in contents])

  def test_checkpoint_restore(self):
    self._init_brain()
    tmp1 = self._temporary_directory('cil_ckpt_restore1')
    tmp2 = self._temporary_directory('cil_ckpt_restore2')
    tmp3 = self._temporary_directory('cil_ckpt_restore3')

    observation_data = test_data.observation_data(50.0, (10, 15, 20))
    action_data = test_data.action_data(1, 0.3)
    reward = 1

    def _record_steps():
      self.brain.record_step(observation_data, reward,
                             demonstration_buffer.StepPhase.START,
                             self._EPISODE_ID, action_data, 0)
      self.brain.record_step(observation_data, reward,
                             demonstration_buffer.StepPhase.IN_PROGRESS,
                             self._EPISODE_ID, action_data, 1)
      self.brain.record_step(observation_data, reward,
                             demonstration_buffer.StepPhase.SUCCESS,
                             self._EPISODE_ID, action_data, 2)

    self.brain.save_checkpoint(tmp1)
    for _ in range(100):
      _record_steps()
    self.brain.train()
    self.brain.save_checkpoint(tmp2)
    del self.brain  # Delete and reinitialize the brain from checkpoint.
    self._init_brain()
    for _ in range(100):
      _record_steps()
    self.brain.train()
    self.brain.save_checkpoint(tmp3)

    global_step = self.brain.tf_agent.train_step_counter
    self.assertEqual(global_step, self.brain.hparams['training_steps'] * 2)

  @parameterized.parameters((1,), (2,), (3,))
  def test_only_discrete_actions(self, num_actions):
    self._init_brain()
    self.brain_spec.action_spec.Clear()
    spec = self.brain_spec.action_spec
    spec.Clear()

    # Fix up spec to match requested number of actions.
    for i in range(num_actions):
      action = spec.actions.add()
      action.name = f'action_{i}'
      action.category.enum_values.append('False')
      action.category.enum_values.append('True')

    self._init_brain()  # Ensure brain can initialize on discrete action space.
    tmp = os.path.join(
        self._temporary_directory('only_discrete'), 'saved_model')
    self.brain.export_saved_model(tmp)  # Ensure we can save policies.

  def test_reinitialize_faster_than_initialize(self):
    """Verify that reinitializing a brain is faster than initialization."""
    start_time = time.perf_counter()
    self._init_brain()
    initialization_time = time.perf_counter() - start_time

    # Set the step counter variable which should be overwritten when
    # reinitializing the brain.
    train_step_counter = self.brain.tf_agent.train_step_counter
    train_step_counter.assign(123)

    start_time = time.perf_counter()
    self.brain.reinitialize_agent()
    reinitialization_time = time.perf_counter() - start_time

    # Training step counter should be restored from the initial checkpoint.
    self.assertEqual(int(train_step_counter), 0)

    # Reinitialization should be >100x faster than initialization.
    # Initialization / compilation should take tens of seconds and
    # reinitialization should typically take tens to hundres of milliseconds.
    print(f'Initialized in {initialization_time}s, '
          f'Reinitialized in {reinitialization_time}s')
    self.assertLess(reinitialization_time * 100, initialization_time)

    # Add trajectories and train, which should be faster than compilation.
    training_times = []
    for i in range(6):
      # Add training data every other iteration.
      if i % 2 == 0:
        self._add_training_data_to_brain(
            self._EPISODES_TO_RUN,
            self._STEPS_PER_EPISODE,
            first_episode_id=self._EPISODE_ID)
      start_time = time.perf_counter()
      self.brain.train()
      training_times.append(time.perf_counter() - start_time)

    print(f'Initialized in {initialization_time}s, '
          f'Training times in seconds {training_times}')
    # Training time should be significantly >10x less than initialization
    # time.
    self.assertLess(training_times[0] * 10, initialization_time)
    # Sequential training times should be nearly the same (within ~1s).
    self.assertLess(np.var(training_times), 1)


if __name__ == '__main__':
  absltest.main()
