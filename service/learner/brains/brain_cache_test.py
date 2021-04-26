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
"""Tests for BrainCache."""

from unittest import mock

from absl.testing import absltest
from learner import test_data
from learner.brains import brain_cache
from learner.brains import continuous_imitation_brain


class BrainCacheTest(absltest.TestCase):

  @mock.patch.object(continuous_imitation_brain, 'ContinuousImitationBrain',
                     autospec=True)
  def test_create_and_get_cached_brain(self, mock_continuous_imitation_brain):
    """Create a brain then fetch the brain from the cache."""
    creation_hparams = {'continuous': False, 'save_interval_batches': 100000,
                        'activation_fn': 'relu'}
    mock_hparams = dict(creation_hparams)
    mock_hparams['a_default_param'] = 42
    mock_hparams_validator = mock.Mock()
    mock_hparams_validator.return_value = mock_hparams

    mock_brain = mock.Mock()
    mock_brain.hparams = mock_hparams
    mock_continuous_imitation_brain.return_value = mock_brain
    brain_spec = test_data.brain_spec()

    # Create the brain.
    cache = brain_cache.BrainCache(mock_hparams_validator)
    brain, hparams = cache.GetOrCreateBrain(
        creation_hparams, brain_spec, 'checkpoints', 'summaries')
    self.assertEqual(brain, mock_brain)
    self.assertEqual(hparams, mock_brain.hparams)
    mock_hparams_validator.assert_called_once_with(creation_hparams)
    mock_continuous_imitation_brain.assert_called_once_with(
        '', brain_spec, checkpoint_path='checkpoints',
        summary_path='summaries', hparams=mock_hparams)
    mock_continuous_imitation_brain.reset_mock()

    # Fetch the cached brain.
    brain, hparams = cache.GetOrCreateBrain(
        creation_hparams, brain_spec, 'other_checkpoints', 'other_summaries')
    self.assertEqual(brain, mock_brain)
    self.assertEqual(hparams, mock_brain.hparams)
    self.assertEqual(brain.checkpoint_path, 'other_checkpoints')
    self.assertEqual(brain.summary_path, 'other_summaries')
    mock_brain.reinitialize_agent.assert_called_once()
    mock_brain.clear_step_buffers.assert_called_once()
    mock_continuous_imitation_brain.assert_not_called()

  @mock.patch.object(continuous_imitation_brain, 'ContinuousImitationBrain',
                     autospec=True)
  def test_evict_oldest_brain_from_cache(self, mock_continuous_imitation_brain):
    """Ensure the oldest brain is evicted from the cache when it's full."""
    brain_spec = test_data.brain_spec()
    cache = brain_cache.BrainCache(lambda hparams: hparams, size=2)

    creation_hparams1 = {'activation_fn': 'relu'}
    mock_brain1 = mock.Mock()
    mock_brain1.hparams = creation_hparams1
    mock_continuous_imitation_brain.return_value = mock_brain1
    brain1, _ = cache.GetOrCreateBrain(creation_hparams1, brain_spec,
                                       'checkpoints', 'summaries')
    self.assertEqual(brain1, mock_brain1)
    mock_continuous_imitation_brain.assert_called_once()
    mock_continuous_imitation_brain.reset_mock()

    creation_hparams2 = {'activation_fn': 'swish'}
    mock_brain2 = mock.Mock()
    mock_brain2.hparams = creation_hparams2
    mock_continuous_imitation_brain.return_value = mock_brain2
    brain2, _ = cache.GetOrCreateBrain(creation_hparams2, brain_spec,
                                       'checkpoints', 'summaries')
    self.assertEqual(brain2, mock_brain2)
    mock_continuous_imitation_brain.assert_called_once()
    mock_continuous_imitation_brain.reset_mock()

    # brain1 should be fetched from the cache, mock_brains is unmodified.
    brain1, _ = cache.GetOrCreateBrain(creation_hparams1, brain_spec,
                                       'checkpoints', 'summaries')
    self.assertEqual(brain1, mock_brain1)
    mock_continuous_imitation_brain.assert_not_called()
    mock_continuous_imitation_brain.reset_mock()

    # This should cause mock_brain2 to be evicted from the cache.
    creation_hparams3 = {'activation_fn': 'sigmoid'}
    mock_brain3 = mock.Mock()
    mock_brain3.hparams = creation_hparams3
    mock_continuous_imitation_brain.return_value = mock_brain3
    brain3, _ = cache.GetOrCreateBrain(creation_hparams3, brain_spec,
                                       'checkpoints', 'summaries')
    self.assertEqual(brain3, mock_brain3)
    mock_continuous_imitation_brain.assert_called_once()
    mock_continuous_imitation_brain.reset_mock()

    # Getting the brain associated with creation_hparams2 should create
    # a new brain.
    mock_brain4 = mock.Mock()
    mock_brain4.hparams = creation_hparams2
    mock_continuous_imitation_brain.return_value = mock_brain4
    brain4, _ = cache.GetOrCreateBrain(creation_hparams2, brain_spec,
                                       'checkpoints', 'summaries')
    self.assertEqual(brain4, mock_brain4)
    mock_continuous_imitation_brain.assert_called_once()

if __name__ == '__main__':
  absltest.main()
