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
"""Initializes weights of layers and models."""

import tensorflow as tf
from tf_agents.keras_layers import bias_layer
from tf_agents.networks import categorical_projection_network
from tf_agents.networks import nest_map
from tf_agents.networks import network
from tf_agents.networks import normal_projection_network
from tf_agents.networks import sequential


class WeightInitializationInterface:
  """Interface that allows weights to be reinitialized.

  Inherit from this class and overload initialize_weights() for
  WeightsInitializer to reinitialize weights.
  """

  def initialize_weights(self):
    """Initialize weights in the layer or model."""
    raise NotImplementedError(f'{type(self)} does not implement '
                              'initialize_weights()')


class NoWeightsInterface:
  """Interface that tells WeightsInitializer that the class has no weights.

  Inherit from this class to ignore the object when initializing weights
  with WeightsInitializer.
  """
  pass


class ModelWeightsInitializer(WeightInitializationInterface):
  """Initializes weights in a simple model that just contains layers.

  The derived class should implement a "layers" property that returns a list of
  contained layers.
  """

  def initialize_weights(self):
    """Initialize weights in the layer or model."""
    for layer in self.layers:
      WeightsInitializer.initialize_layer_or_model(layer)


class WeightsInitializer:
  """Initializes weights with tf.keras.initializers.Initializer."""

  # See _get_class_to_initializer().
  _CLASS_TO_INITIALIZER = None

  @staticmethod
  def _get_class_to_initializer():
    """Get the class to initializer list.

    Returns:
      List of (class_types, initializer) tuples where class_types is the
      a tuple of a tf.Layer or tf.Model classes and initializer is a method
      that takes a layer or model instance as an argument and initializes the
      weights in the layer or model.
    """
    if not WeightsInitializer._CLASS_TO_INITIALIZER:
      # NOTE: The order of this matters. Only first match of the layer_or_model
      # type in this list will be applied.
      WeightsInitializer._CLASS_TO_INITIALIZER = (
          # Recurse models or layers that implement a "layers" property.
          ((tf.keras.Model,),
           WeightsInitializer._initialize_model_layers),
          # Layers without weights.
          ((tf.keras.layers.Lambda,
            tf.keras.layers.MaxPool1D,
            NoWeightsInterface),
           WeightsInitializer._check_layer_with_no_weights),
          # Layers with initialize_weights() methods.
          ((WeightInitializationInterface,),
           WeightsInitializer._initialize_layer_with_weight_reset),
          # Layers with bias weights.
          ((bias_layer.BiasLayer,),
           WeightsInitializer._initialize_layer_with_bias),
          # Layers with kernel and bias weights.
          ((tf.keras.layers.Dense,
            tf.keras.layers.Conv1D),
           WeightsInitializer._initialize_layer_with_kernel_and_bias),
          # BatchNormalization.
          ((tf.keras.layers.BatchNormalization,),
           WeightsInitializer._initialize_batch_normalization_layer),
          # Simple TF Agents networks that just contain layers that should be
          # initialized.
          ((sequential.Sequential,
            nest_map.NestMap,
            categorical_projection_network.CategoricalProjectionNetwork,
            normal_projection_network.NormalProjectionNetwork),
           WeightsInitializer._initialize_model_layers),
          # The generic TF Agents network should be after all specializations.
          ((network.Network,),
           WeightsInitializer._initialize_tfa_network_layers),
      )
    return WeightsInitializer._CLASS_TO_INITIALIZER

  @staticmethod
  def initialize(weights, initializer):
    """Initialize weights using an initializer.

    Args:
      weights: tf.Tensor containing the weights to initialize.
      initializer: tf.keras.initializers.Initializer to initialize the weights.
    """
    weights.assign(initializer(weights.shape, dtype=weights.dtype))

  @staticmethod
  def _check_layer_with_no_weights(layer):
    """Leaves a layer unmodified.

    Args:
      layer: Layer to check
    """
    assert not layer.get_weights(), (
        f'Layer {type(layer)} has unexpected weights.')

  @staticmethod
  def _initialize_model_layers(model):
    """Initializes weights in layers of a model.

    Args:
      model: tf.keras.Model or object that implements a "layers" property whose
        contained layers should be initialized.
    """
    for layer in model.layers:
      WeightsInitializer.initialize_layer_or_model(layer)

  @staticmethod
  def _initialize_layer_with_weight_reset(layer):
    """Initialize weights in layers with an initialize_weights() method.

    Args:
      layer: Layer with an initialize_weights() method.
    """
    layer.initialize_weights()

  @staticmethod
  def _initialize_layer_with_kernel_and_bias(layer):
    """Initialize layer with kernel and bias weights.

    Args:
      layer: Layer with kernel and bias weights.
    """
    WeightsInitializer.initialize(layer.kernel, layer.kernel_initializer)
    WeightsInitializer.initialize(layer.bias, layer.bias_initializer)

  @staticmethod
  def _initialize_layer_with_bias(layer):
    """Initialize layer with bias weights.

    Args:
      layer: Layer with bias weights.
    """
    WeightsInitializer.initialize(layer.bias, layer.bias_initializer)

  @staticmethod
  def _initialize_batch_normalization_layer(layer):
    """Initialize weights in a batch normalization layer.

    Args:
      layer: tf.keras.layers.BatchNormalization instance.
    """
    WeightsInitializer.initialize(layer.gamma, layer.gamma_initializer)
    WeightsInitializer.initialize(layer.beta, layer.beta_initializer)
    WeightsInitializer.initialize(layer.moving_mean,
                                  layer.moving_mean_initializer)
    WeightsInitializer.initialize(layer.moving_variance,
                                  layer.moving_variance_initializer)

  @staticmethod
  def _initialize_tfa_network_layers(tf_agents_network):
    """Initialize subcomponents of a TF Agents network.

    Args:
      tf_agents_network: tf_agents.networks.Network instance to initialize.
    """
    WeightsInitializer._initialize_model_layers(tf_agents_network)
    assert not tf_agents_network.trainable_variables, (
        f'TF Agents network {type(tf_agents_network)} does not have a weight '
        'initialization method but has trainable weights. A weight '
        'initialization method needs to be implemented for this class.')

  @staticmethod
  def initialize_layer_or_model(layer_or_model):
    """Initialize weights of supported layers.

    Args:
      layer_or_model: tf.Layer or tf.Model derived instance to initialize.
        This method will assert when attempting to initialize unsupported
        layers.
    """
    initialized = False
    # pylint: disable=not-an-iterable
    for class_types, initializer in (
        WeightsInitializer._get_class_to_initializer()):
      if class_types and isinstance(layer_or_model, class_types):
        initializer(layer_or_model)
        initialized = True
        break

    assert initialized, (f'Layer/Model {type(layer_or_model)} weights can not '
                         'be reinitialized.')
