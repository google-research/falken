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

# Lint as: python3
"""Brain that can continuously learn from human demonstrations."""

import glob
import math
import os
import random
import shutil
import time

from learner.brains import demonstration_buffer
from learner.brains import eval_datastore
from learner.brains import imitation_loss
from learner.brains import networks
from learner.brains import numpy_replay_buffer
from learner.brains import policies
from learner.brains import saved_model_to_tflite_model
from learner.brains import specs
from log import falken_logging
import tensorflow as tf
from tf_agents.agents.behavioral_cloning import behavioral_cloning_agent
from tf_agents.policies import greedy_policy
from tf_agents.policies import policy_saver
from tf_agents.trajectories import time_step as ts
from tf_agents.utils import common


_DEFAULT_REPLAY_BUFFER_CAPACITY = 2 * 3600 * 10  # 2 hours at 10 fps.


class UnknownHParamError(Exception):
  """Raised if there is an unknown hyperparameter in the assignment."""


class NoCheckpointFoundError(Exception):
  """Raised if not checkpoint was found at a specified location."""


class BCAgent(behavioral_cloning_agent.BehavioralCloningAgent):
  """A behavioral cloning based TF agent."""

  def __init__(self,
               brain_spec,
               hparams,
               use_summaries):
    """Create a new BC tf-agent with the provided hyperparameters."""
    assert brain_spec
    falken_logging.info(f'Creating BC Agent with hparams: {hparams}')

    self.actor_net = networks.FalkenNetwork(brain_spec, hparams)

    optimizer = tf.compat.v1.train.AdamOptimizer(
        learning_rate=hparams['learning_rate'])

    super().__init__(
        ts.time_step_spec(brain_spec.observation_spec.tfa_spec),
        brain_spec.action_spec.tfa_spec,
        optimizer=optimizer,
        cloning_network=self.actor_net,
        num_outer_dims=2,
        loss_fn=self._dict_loss,
        debug_summaries=use_summaries,
        train_step_counter=tf.Variable(0, dtype=tf.int64, trainable=False,
                                       name='train_step_counter'),
        summarize_grads_and_vars=False)

    self.initialize()

    # Force variable initialization. This triggers the initializers to
    # be called and pruned avoiding errand placeholders in the
    # checkpoint.
    self.policy.variables()

  def _dict_loss(self, experience, training=True):
    batch_size = (
        tf.compat.dimension_value(experience.step_type.shape[0]) or
        tf.shape(experience.step_type)[0])

    network_state = self.cloning_network.get_initial_state(batch_size)
    values, _ = self.cloning_network(
        experience.observation,
        experience.step_type,
        training=training,
        network_state=network_state)

    targets = experience.action
    return imitation_loss.dict_loss(values, targets)

  @staticmethod
  def update_derived_hparams(hparams):
    """Update a hyperparameter dictionary with derived parameters.

    Args:
      hparams: Hyperparameter dictionary to modify.

    Returns:
      Dictionary updated with derived hparameters.
    """
    hparams['training_steps'] = (
        int(math.ceil(hparams['training_examples'] / hparams['batch_size'])))
    return hparams

  @staticmethod
  def default_hparams():
    """Return the default hyperparameters for BC Agent."""
    return BCAgent.update_derived_hparams(dict(
        learning_rate=5e-4,
        fc_layers=[32],
        # 'feelers_version' is one of:
        #   'v1': Classic feelers.
        #   'v2': New feelers, as defined in go/updated-feelers.
        feelers_version='v1',
        feelers_v2_output_channels=3,
        feelers_v2_kernel_size=5,
        dropout=None,
        activation_fn='swish',
        # 'policy_type' is one of the following:
        #   'greedy': Selects the mode of the action distributions.
        #   'noisy': Stochastically samples from the action distributions.
        #   'greedy_float': Uses 'greedy' for float-valued actions and
        #        'noisy' for all others (e.g., categorical actions).
        policy_type='greedy_float',
        # Number of trajectories in each training batch processed by train().
        batch_size=500,
        # Number of trajectories to process on each call to train().
        training_examples=1000000,
        # Whether to compile the graphs.
        use_tf_function=True,
        # 'use_xla_jit' indicates whether we want to translate the inner
        # training loop using XLA JIT.
        use_xla_jit=True,
        # 'num_batches_to_sample' is the number of batches to sample before
        # entering the inner training loop. Presampled batches are used in a
        # round-robin fashion. A value of 50 should ensure that the sample is
        # representative even for larger replay buffers while adding around
        # ~35% to required memory compared to the replay buffer.
        num_batches_to_sample=50))

  def evaluate(self, data):
    """Compute average eval loss for a trajectory of data."""
    with tf.name_scope('eval_loss'):
      loss = self._dict_loss(data)
      return tf.math.reduce_mean(loss)


def _outer_dim_length(nested_tensor):
  """Return length of the outer (time or batch) dimension."""
  flat = tf.nest.flatten(nested_tensor)
  if not flat:
    return 0
  else:
    return len(flat[0])


def _select_sub_trajectories(traj_generator,
                             select_fraction,
                             rng):
  """Selects a random subtrajectory of a specified length.

  This selects a contiguous segment from the input trajectory and returns the
  trajectory split into three sub-trajectories: Before the selected fragment,
  the selected fragment and after the selected fragment.

  Args:
    traj_generator: Generates pairs (trajectory, length) where length indicates
        the size of the outermost (=time) dimension of the trajectory data.
    select_fraction: Fraction of the trajectory to select.
    rng: Random number generator.

  Yields:
    Triplets of trajectory (before, selected, after), which randomly subdivide
    the trajectory object into three subtrajectories. The middle element has
    length select_fraction * trajectory_length. Note that tuple elements yielded
    will be None if any trajectory segment would have length 0.
  """
  for trajectory, frames in traj_generator:
    select_frames = int(select_fraction * frames)

    if not select_frames:
      yield trajectory, None, None
      continue

    last_select_index = frames - select_frames
    start = rng.randint(0, last_select_index)
    end = start + select_frames
    assert end <= frames

    def select(start, end):
      if start == end:
        return None
      return tf.nest.map_structure(
          lambda x: x[start: end],  # pylint: disable=cell-var-from-loop
          trajectory)  # pylint: disable=cell-var-from-loop

    yield select(0, start), select(start, end), select(end, frames)


def _create_checkpointer(checkpoint_dir, trackable_objects):
  """Create a checkpoint manager for the specified directory.

  Args:
    checkpoint_dir: Directory to manage and optionally load checkpoints
      from.
    trackable_objects: Dictionary of TensorFlow objects to save in the
      checkpoint.

  Returns:
    (checkpointer, restored) tuple where checkpointer is an instance to a
    TF agents Checkpointer instance and restored is a bool value indicating
    whether the checkpointer restored from the checkpoint.
  """
  checkpointer = common.Checkpointer(ckpt_dir=checkpoint_dir, max_to_keep=1,
                                     **trackable_objects)
  if not checkpointer.checkpoint_exists:
    checkpointer.initialize_or_restore()
  return (checkpointer, checkpointer.checkpoint_exists)


def _generate_random_steps(number_of_frames, brain_spec):
  """Generate demonstration_buffer.Step instances.

  Args:
    number_of_frames: Number of frames of random steps to generate.
    brain_spec: BrainSpec to use to generate the data.

  Yields:
    demonstration_buffer.Step instance populated with random data that
    conforms to the provided brain_spec.
  """
  for i, step_phase in demonstration_buffer.generate_index_and_step_phase(
      number_of_frames, demonstration_buffer.StepPhase.SUCCESS):
    yield demonstration_buffer.Step(
        observation_pb=specs.DataProtobufGenerator.from_spec_node(
            brain_spec.observation_spec.proto_node,
            modify_data_proto=(
                specs.DataProtobufGenerator.randomize_leaf_data_proto))[0],
        reward=0, phase=step_phase, episode_id='0',
        action_pb=specs.DataProtobufGenerator.from_spec_node(
            brain_spec.action_spec.proto_node,
            modify_data_proto=(
                specs.DataProtobufGenerator.randomize_leaf_data_proto))[0],
        timestamp_micros=i)


class ContinuousImitationBrain:
  """An ML powered brain that continuously learns from demonstration.

  Attributes:
    id: string, GUID for each Brain instance.
    spec_pb: BrainSpec proto that was used to create the Brain.
    policy_path: string, the path where the policies are stored.
    summary_path: string, the path where TF summaries are stored.
    checkpoint_path: string, the path where model checkpoints are stored.
    brain_spec: specs.BrainSpec created from spec_pb.
    tf_agent: tf_agent object, the agent created for the purposes of training.
    data_timestamp_micros: Either 0 if no data present or the timestamp up to
      which episode data has been fetched.
    latest_checkpoint: The latest local checkpoint or None if not present.
    policy_saver: PolicySaver instance which can be used to save the current
      policy.
  """

  # Fraction of frames to keep in eval buffer.
  _EVAL_FRACTION = 0.2

  # Seed for the RNG that divides episodes into training and eval set.
  # The implementation uses a fixed seed, since we sometimes offline scores need
  # to be compared across sessions (e.g., during a vizier study).
  _EVAL_SPLIT_SEED = 12345

  # How often to write summaries in seconds.
  _SUMMARIES_FLUSH_SECS = 10

  def __init__(self,
               brain_id,
               spec_pb,
               checkpoint_path,
               summary_path=None,
               replay_buffer_capacity=_DEFAULT_REPLAY_BUFFER_CAPACITY,
               hparams=None,
               write_tflite=True,
               use_summaries=False,
               compile_graph=True):
    """Create a new ContinuousImitationBrain.

    Args:
      brain_id: Deprecated, will be removed.
      spec_pb: BrainSpec proto describing the properties of the brain to create.
      checkpoint_path: string, path where the TF checkpoints will be stored.
      summary_path: string, path where the TF summaries will be stored.
      replay_buffer_capacity: Frame capacity of the replay buffer.
      hparams: dict with hyperparameters for BCAgent, or None if default
        hparams should be used.
      write_tflite: Whether to convert saved models to tf-lite when saving
        policies.
      use_summaries: Whether to write TF summaries.
      compile_graph: Whether to compile the graph.

    Raises:
      ValueError: if any of the paths isn't set.
    """
    assert spec_pb
    _ = brain_id
    self.spec_pb = spec_pb
    self.brain_spec = specs.BrainSpec(spec_pb)

    self.tf_agent = None
    self._eval_split_rng = random.Random(self._EVAL_SPLIT_SEED)
    self._demo_buffer = None
    self._eval_datastore = None
    self._replay_buffer = None
    self._replay_buffer_capacity = replay_buffer_capacity

    # Non-parameter members:
    self._reinitialize_dataset()
    self._hparams = (
        BCAgent.update_derived_hparams(dict(hparams)) if hparams else
        BCAgent.default_hparams())

    self._write_tflite = write_tflite

    self._policy_saver = None

    # Stats logged while training.
    self._num_train_frames = tf.Variable(0, dtype=tf.int32, trainable=False,
                                         name='_num_train_frames')
    self._num_eval_frames = tf.Variable(0, dtype=tf.int32, trainable=False,
                                        name='_num_eval_frames')

    if not checkpoint_path or (use_summaries and not summary_path):
      raise ValueError(
          'checkpoint_path and summary_path (when using summaries) must be '
          'set.')

    self._use_summaries = use_summaries
    self._summary_path = None
    self._train_summary_writer = None
    self.summary_path = summary_path  # Optionally create the summary writer.

    self._checkpoint_path = checkpoint_path
    self._checkpoint_trackable_objects = None
    self._checkpointer = None

    self._get_experiences = None
    self._train_step = None
    self.reinitialize_agent(compile_graph)  # Also sets up checkpointer.

  def _initialize_step_buffers(self):
    """Initialize the replay buffer, demo buffer and eval datastore."""
    # TF Replay buffer
    self._replay_buffer = numpy_replay_buffer.NumpyReplayBuffer(
        self.tf_agent.collect_data_spec,
        capacity=self._replay_buffer_capacity)
    self._reinitialize_dataset()

    # Temporary data buffer that accumulates full episodes before dividing the
    # data between training and eval set
    self._demo_buffer = demonstration_buffer.DemonstrationBuffer(
        self.brain_spec)

    # Storage for eval data.
    self._eval_datastore = eval_datastore.EvalDatastore()
    self.clear_step_buffers()

  def reinitialize_agent(self, compile_graph=False):
    """Re-initialize the tf-agent.

    If the checkpoint directory is wiped before calling this, this will trigger
    a reinitialization of network weights.

    Args:
      compile_graph: Whether to pre-compile the graph.
    """
    falken_logging.info('(Re-)initializing BCAgent.')
    if not self.tf_agent:
      self.tf_agent = BCAgent(
          self.brain_spec,
          self._hparams,
          use_summaries=self._use_summaries)

      # We trigger retracing of the train_step function on restart, since
      # otherwise, some of the variables seem to be reused.
      inital_time = time.perf_counter()
      if self._hparams['use_tf_function']:
        self._get_experiences = common.function(
            self._py_fun_get_experiences,
            autograph=True)
        self._train_step = common.function(
            self._py_fun_train_step,
            autograph=True,
            experimental_compile=self._hparams['use_xla_jit'])
      else:
        self._get_experiences = self._py_fun_get_experiences
        self._train_step = self._py_fun_train_step
      falken_logging.info('Retraced train functions in '
                          f'{time.perf_counter() - inital_time} secs.')
      # Initialize demo, eval and replay buffers.
      self._initialize_step_buffers()

      # Force JIT compilation.
      if compile_graph:
        self._compile_graph()

      # Keys are names, values are trackable objects (see tf.train.Checkpoint
      # for details on trackables).
      self._checkpoint_trackable_objects = {
          'agent': self.tf_agent,
          'train_step_counter': self.tf_agent.train_step_counter,
          'actor_net': self.tf_agent.actor_net,
      }

    # Create a checkpointer and, if it exists, restore from a checkpoint.
    self._checkpointer, restored_from_checkpoint = _create_checkpointer(
        self._checkpoint_path, self._checkpoint_trackable_objects)
    # If we didn't restore from a checkpoint, try restoring from the initial
    # state.
    if not restored_from_checkpoint:
      self.tf_agent.train_step_counter.assign(0)
      # Reset the model weights.
      if compile_graph:
        self.tf_agent.actor_net.initialize_weights()

  def _compile_graph(self):
    """Force compilation of the graph."""
    # Ideally we would execute the graph with a minimum number of steps (i.e set
    # batch_size, num_batches_to_sample and training_steps to 1) to avoid
    # biasing the initial weights and minimize initialization time.
    # However, using tf.Variable instances to configure training parameters
    # has a number of drawbacks:
    # - It's not possible to _currently_ communicate variables across device
    #   boundaries with XLA enabled.
    # - When variables that affect control flow in the graph are modified,
    #   partial recompilation occurs.
    #
    # So instead this populates the demonstration buffer with random data
    # and trains for a single step to force compilation.
    self._replay_buffer.Add(demonstration_buffer.batch_trajectories(
        demonstration_buffer.episode_steps_to_trajectories(
            _generate_random_steps(self._hparams['batch_size'] *
                                   self._hparams['num_batches_to_sample'],
                                   self.brain_spec),
            self.brain_spec)))
    self._reinitialize_dataset()

    inital_time = time.perf_counter()
    self.train()
    falken_logging.info(f'Compiled in {time.perf_counter() - inital_time}s')

    self.tf_agent.train_step_counter.assign(0)
    self._replay_buffer.Clear()
    self._reinitialize_dataset()

  @property
  def num_train_frames(self):
    """Number of frames collected for training."""
    return int(self._num_train_frames)

  @property
  def num_eval_frames(self):
    """Number of frames collected for training."""
    return int(self._num_eval_frames)

  @property
  def global_step(self):
    """Number of batched gradient updates / global steps."""
    return int(self.tf_agent.train_step_counter)

  @property
  def hparams(self):
    """Hyperparameter settings in dict form used in the brain currently."""
    return dict(self._hparams)

  @property
  def summary_path(self):
    """Get the directory to write summaries."""
    return self._summary_path

  @summary_path.setter
  def summary_path(self, path):
    """Set the summary directory to write summaries.

    Args:
      path: Directory to write summaries if _use_summaries is True.
    """
    # Create a train summary writer that flushes periodically.
    if self._summary_path != path:
      self._summary_path = path
      if self._use_summaries:
        self._train_summary_writer = tf.compat.v2.summary.create_file_writer(
            self._summary_path, flush_millis=self.SUMMARIES_FLUSH_SECS * 1000)
        self._train_summary_writer.set_as_default()
      else:
        self._train_summary_writer = None

  @property
  def checkpoint_path(self):
    """Get the checkpoint directory."""
    return self._checkpoint_path

  @checkpoint_path.setter
  def checkpoint_path(self, path):
    """Set the checkpoint directory and try to load from the directory.

    Args:
      path: Directory to write checkpoints.
    """
    self._checkpoint_path = path
    self._checkpointer, _ = _create_checkpointer(
        self._checkpoint_path, self._checkpoint_trackable_objects)

  def _reinitialize_dataset(self):
    """Force dataset recreation from the replay buffer on _setup_dataset()."""
    self._dataset = None
    self._dataset_iterator = None

  def _setup_dataset(self):
    """Set up dataset and iterator."""
    if self._dataset:
      return

    # TF agents expects a time dimension, so we add one dummy dimension in
    # front.
    def _add_time_dim(tensor_nest):
      # Add dummy time dimension of 1.
      return tf.nest.map_structure(lambda x: tf.expand_dims(x, axis=0),
                                   tensor_nest)

    ds = self._replay_buffer.AsDataset().map(_add_time_dim).cache().repeat()
    ds = ds.shuffle(
        self._replay_buffer.size).batch(self._hparams['batch_size'])
    # We apply a second batch dimension so that a batch of batches can be
    # prefetched before we enter the XLA/jit translated train function.
    # (which does not like the 'next' operator)
    ds = ds.batch(self._hparams['num_batches_to_sample'])
    ds = ds.prefetch(buffer_size=tf.data.experimental.AUTOTUNE)
    self._dataset = ds
    self._dataset_iterator = iter(ds)

  def train(self):
    """Trains the brain using the collected data."""
    initial_count_steps = int(self.global_step)
    initial_time = time.perf_counter()

    # set up dataset + iterator
    self._setup_dataset()

    with tf.compat.v2.summary.record_if(self._use_summaries):
      # TODO(wun): Determine why this is necessary. Currently without
      # this line, the default summary writer somehow gets set to
      # None, resulting in an empty TensorBoard.
      if self._train_summary_writer:
        self._train_summary_writer.set_as_default()

      self._train_step(self._get_experiences(self._dataset_iterator))

    falken_logging.info(
        f'Trained {int(self.global_step) - initial_count_steps} steps in '
        f'{time.perf_counter() - initial_time} seconds from '
        f'{self._num_train_frames.numpy()} training_frames.')
    falken_logging.info(
        f'Trained {self.tf_agent.train_step_counter.numpy()} steps in '
        f'total from {self._num_train_frames.numpy()} training frames.')

  def record_step(self, observation_pb, reward, phase, episode_id, action_pb,
                  timestamp_micros):
    """Records a known state+action from a given env.

    Args:
        observation_pb: The observation data for this step.
        reward: The reward for this step.
        phase: The phase of the episode this step represents.
        episode_id: Id for the episode that's collecting this step.
        action_pb: Action data from brain or user.
        timestamp_micros: Microsecond timestamp of the step.
    """
    self._demo_buffer.record_step(
        demonstration_buffer.Step(
            observation_pb=observation_pb,
            reward=reward,
            phase=phase,
            episode_id=episode_id,
            action_pb=action_pb,
            timestamp_micros=timestamp_micros))

    # Add new completed episodes to buffers.
    for before, eval_trajectory, after in _select_sub_trajectories(
        self._demo_buffer.flush_episode_demonstrations(),
        self._EVAL_FRACTION, self._eval_split_rng):

      if not eval_trajectory:
        # If episode is too short for splitting, stochastically assign it to
        # either eval or training.
        assert not after
        if self._eval_split_rng.random() < self._EVAL_FRACTION:
          before, eval_trajectory = eval_trajectory, before

      for trajectory in [before, after]:
        if not trajectory:  # Skip empty trajectory chunks.
          continue
        self._replay_buffer.Add(trajectory)
        chunk_size = _outer_dim_length(trajectory)
        self._num_train_frames.assign_add(chunk_size)
        falken_logging.info(f'Added {chunk_size} training frames.')

      self._reinitialize_dataset()

      if eval_trajectory:
        self._eval_datastore.add_trajectory(eval_trajectory)
        chunk_size = _outer_dim_length(eval_trajectory)
        self._num_eval_frames.assign_add(chunk_size)
        self._eval_datastore.create_version()
        falken_logging.info(f'Added {chunk_size} eval frames.')

  def clear_step_buffers(self):
    """Clear all steps from demo, eval and replay buffers."""
    # Reset training and eval counters.
    self._num_train_frames.assign(0)
    self._num_eval_frames.assign(0)

    # Clear buffers.
    self._replay_buffer.Clear()
    self._demo_buffer.clear()
    self._eval_datastore.clear()
    self._reinitialize_dataset()

  @property
  def latest_checkpoint(self):
    return self._checkpointer.manager.latest_checkpoint

  def _create_export_policy(self):
    """Creates the policy for export based on hparams."""
    assert isinstance(self.tf_agent.policy, greedy_policy.GreedyPolicy)
    stochastic_policy = self.tf_agent.policy.wrapped_policy
    policy_type = self._hparams['policy_type']

    if policy_type == 'greedy':
      return self.tf_agent.policy
    elif policy_type == 'greedy_float':
      return policies.GreedyFloatPolicy(stochastic_policy)
    elif policy_type == 'noisy':
      return stochastic_policy
    else:
      raise UnknownHParamError(f'unknown policy_type: {policy_type}')

  @property
  def policy_saver(self):
    if not self._policy_saver:
      policy = self._create_export_policy()
      self._policy_saver = policy_saver.PolicySaver(policy, batch_size=1)
    return self._policy_saver

  def export_saved_model(self, path):
    """Export saved model."""
    # Wrap in GreedyPolicy to make sure behavior is smooth.
    falken_logging.info(f'Exporting policy with action signature '
                        f'{self.policy_saver.action_input_spec}')
    falken_logging.info(f'Exporting policy with policy_step_spec'
                        f'{self.policy_saver.policy_step_spec}')
    falken_logging.info(f'Exporting policy with policy_state_spec'
                        f'{self.policy_saver.policy_state_spec}')
    os.makedirs(path, exist_ok=True)
    self.policy_saver.save(path)
    falken_logging.info(f'Exported SavedModel to policy to {path}')

  def convert_model_to_tflite(self, saved_model_path, tflite_path):
    """Convert saved model to tf-lite model."""
    filename = 'model.tflite'
    os.makedirs(tflite_path, exist_ok=True)
    tflite_file = os.path.join(tflite_path, filename)
    with open(tflite_file, 'wb') as f:
      f.write(saved_model_to_tflite_model.convert(saved_model_path, ['action']))

  def save_checkpoint(self, save_dir):
    """Serializes the trained policy to disk and moves to save_dir.

    Args:
      save_dir: Directory to save the latest checkpoint.
        This directory *must* be on the same filesystem as checkpoint_path
        specified on construction of this object.
    """
    global_step = self.tf_agent.train_step_counter
    self._checkpointer.save(global_step)
    checkpoint_path_prefix = self.latest_checkpoint
    checkpoint_dir = os.path.dirname(checkpoint_path_prefix)

    # Move information on the latest checkpoint from the local
    # tensorflow checkpoint dir to the export location at policy_path.
    # Checkpoint files start with '<checkpoint_name>.'.
    os.makedirs(save_dir, exist_ok=True)
    for checkpoint_filename, copy in (
        [(fname, False) for fname in glob.glob(checkpoint_path_prefix + '.*')] +
        # Copy 'checkpoint' metadata file (tracks state of the checkpoint
        # manager).
        [(os.path.join(checkpoint_dir, 'checkpoint'), True)]):
      target_filename = os.path.join(
          save_dir, os.path.basename(checkpoint_filename))
      if copy:
        shutil.copy(checkpoint_filename, target_filename)
      else:
        # Create a hard link to the checkpoint file in the output directory.
        os.link(checkpoint_filename, target_filename)

  def full_eval_from_datastore(self, eval_ds):
    """Same as compute_full_evaluation, but from an external EvalDatastore.

    Args:
      eval_ds: EvalDatastore instance to use to evaluate this brain instance.

    Yields:
      (eval_dataset_version_id, mean_score) tuples where
      eval_dataset_version_id is the version of the evaluation dataset and
      mean_score is the evaluation score of the brain against the dataset.
    """
    prev_size = 0
    prev_score = 0
    # Successive versions just incrementally add data. Since we're computing an
    # average score for each version, we can compute the evaluation
    # incrementally as well.
    for version_id, size, delta in eval_ds.get_version_deltas():
      delta_score = self.tf_agent.evaluate(delta)
      weight = size / (size + prev_size)
      mean_score = weight * delta_score + (1 - weight) * prev_score
      yield version_id, float(mean_score)  # Cast to float from tensor.
      prev_score, prev_size = mean_score, size + prev_size

  def compute_full_evaluation(self, path=None):
    """Yields a sequence of pairs of the form (eval_version, eval_score).

    Args:
      path: An optional policy path if we want to evaluate a different version
        rather than the currently active one.
    Yields:
      A sequence of pairs of the form (eval_version, eval_score).
    Raises:
      NoCheckpointFoundError: If the path was set but no checkpoint was found.
    """
    if path is None:
      yield from self.full_eval_from_datastore(self._eval_datastore)
    else:
      # Create a copy of this brain for eval:
      with tf.name_scope('eval_brain'):
        cp_path = os.path.join(os.path.join(path, 'checkpoint/'))
        eval_brain = ContinuousImitationBrain(
            '',
            spec_pb=self.spec_pb,
            checkpoint_path=cp_path,
            # TODO(lph): Check if we need to use a separate summary path.
            summary_path=self._summary_path,
            replay_buffer_capacity=self._replay_buffer_capacity,
            hparams=self._hparams)
        if not eval_brain.latest_checkpoint:
          raise NoCheckpointFoundError(
              f'No checkpoints found in dir {cp_path}, {cp_path}/* is '
              + str(glob.glob(cp_path + '*')))
        yield from eval_brain.full_eval_from_datastore(self._eval_datastore)

  def _py_fun_get_experiences(self, iterator):
    """Return a batch of batches for use in _py_fun_train_step.

    Args:
      iterator: A dataset iterator.

    Returns:
      A Trajectory object representing a nest of tensors, where each tensor
      has batch dimensions num_batches_to_sample x batch_size.
    """
    return next(iterator)

  def _py_fun_train_step(self, experiences):
    """Train for a single step.

    We pre-sample batches and consider them as input so that this function
    can be translated via experimental_compile=True with JIT XLA compilation.
    (The 'next' function does not support JIT XLA compilation right now.)

    Args:
      experiences: A Trajectory with data batched across two dimensions. The
        outer batch dimension is 'num_batches_to_sample' the inner batch
        dimension is 'batch_size'. In each training step, we move round robin
        around the outer batch dimension and feed an inner batch to tf-agents'
        train function. (The datastructure is generated by calling the function
        on the generating dataset - which is already batched).
    """
    num_batches = self._hparams['num_batches_to_sample']
    for i in tf.range(self._hparams['training_steps']):
      def _select_outer_batch(tensor):
        """Selects the ith outer batch of a tensor."""
        # Using the loop variable i is ok here, since we're only ever using the
        # function inside the loop.
        return tensor[i % num_batches]  # pylint: disable=cell-var-from-loop
      # Data in experiences has two batch dimensions (see the generation of the
      # dataset object in _setup_dataset()). We now create an object
      # that selects an outer batch, thus leaving the resulting object with
      # only one batch dimension.
      experience = tf.nest.map_structure(_select_outer_batch, experiences)
      self.tf_agent.train(experience=experience)
