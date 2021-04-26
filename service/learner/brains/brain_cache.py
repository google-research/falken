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
"""LRU cache for brain instances."""

import collections

from learner.brains import continuous_imitation_brain
from log import falken_logging


class BrainCache:
  """Least Recently Used (LRU) cache of brain instances."""

  def __init__(self, hparam_defaults_populator_and_validator, size=8):
    """Initialize the cache.

    Args:
      hparam_defaults_populator_and_validator: Callable that takes a dictionary
        of hyperparameters, validates them, populates the dictionary with
        defaults and returns the validated dictionary.
      size: Number of brains to cache.
    """
    # Cache of brains by an opaque key string.
    # Items are ordered by most recently used first, least recently used last.
    self._brains = collections.OrderedDict()
    self._size = size
    self._hparam_defaults_populator_and_validator = (
        hparam_defaults_populator_and_validator)

  def GetOrCreateBrain(self, hparams, brain_spec, checkpoint_path,
                       summary_path):
    """Get a brain from the cache or create a new one if it isn't found.

    Args:
      hparams: Hyperparmeters used to create the brain.
      brain_spec: BrainSpec proto used to create the brain.
      checkpoint_path: Path to store checkpoints of the brain.
      summary_path: Path to store summaries of the brain.

    Returns:
      (brain, hparams) tuple where brain is a ContinuousImitationBrain instance
      and hparams are the hyperparameters used to create the brain.
    """
    hparams = self._hparam_defaults_populator_and_validator(hparams)
    key = str(brain_spec) + str(hparams)
    brain = self._brains.get(key)
    if brain:
      falken_logging.info(f'Retrieved cache brain, hparams: {hparams}\n'
                          f'Brain spec: {brain_spec}')
      brain.summary_path = summary_path
      brain.checkpoint_path = checkpoint_path
      brain.reinitialize_agent()
      brain.clear_step_buffers()
    else:
      # If we've exceeded the cache size, delete the least recently used item.
      if len(self._brains) == self._size:
        lru_brain = self._brains.popitem()
        if lru_brain:
          del lru_brain

      falken_logging.info(f'Creating brain, hparams: {hparams}\n'
                          f'Brain spec: {brain_spec}')
      brain = continuous_imitation_brain.ContinuousImitationBrain(
          '', brain_spec, checkpoint_path=checkpoint_path,
          summary_path=summary_path, hparams=hparams)
      falken_logging.info(f'Brain created, hparams: {brain.hparams}')
      self._brains[key] = brain

    # Move the selected brain to the start of the cache.
    self._brains.move_to_end(key, last=False)

    # Return a copy of the hyperparameters with the brain's hyperparameters
    # overlaid.
    result_hparams = dict(hparams)
    result_hparams.update(brain.hparams)
    return (brain, result_hparams)
