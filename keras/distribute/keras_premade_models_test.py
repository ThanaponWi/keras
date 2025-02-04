# Copyright 2019 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Tests for keras premade models using tf.distribute.Strategy."""

import tensorflow.compat.v2 as tf

from absl.testing import parameterized
import numpy as np
from keras.engine import sequential
from keras.layers import core
from keras.optimizer_v2 import adagrad
from keras.optimizer_v2 import gradient_descent
from keras.premade import linear
from keras.premade import wide_deep


def strategy_combinations_eager_data_fn():
  return tf.__internal__.test.combinations.combine(
      distribution=[
          tf.__internal__.distribute.combinations.default_strategy,
          tf.__internal__.distribute.combinations.one_device_strategy,
          tf.__internal__.distribute.combinations.one_device_strategy_gpu,
          tf.__internal__.distribute.combinations.mirrored_strategy_with_gpu_and_cpu,
          tf.__internal__.distribute.combinations.mirrored_strategy_with_two_gpus,
          tf.__internal__.distribute.combinations.mirrored_strategy_with_two_gpus_no_merge_call,
          tf.__internal__.distribute.combinations.multi_worker_mirrored_2x1_cpu,
          tf.__internal__.distribute.combinations.multi_worker_mirrored_2x1_gpu,
          tf.__internal__.distribute.combinations.multi_worker_mirrored_2x2_gpu,
          # NOTE: TPUStrategy not tested because the models in this test are
          # sparse and do not work with TPUs.
      ],
      mode=['eager'],
      data_fn=['numpy', 'dataset'])


def get_numpy():
  inputs = np.random.uniform(low=-5., high=5., size=(64, 2)).astype(np.float32)
  output = .3 * inputs[:, 0] + .2 * inputs[:, 1]
  return inputs, output


def get_dataset():
  inputs, output = get_numpy()
  dataset = tf.data.Dataset.from_tensor_slices((inputs, output))
  dataset = dataset.batch(10).repeat(10)
  return dataset


class KerasPremadeModelsTest(tf.test.TestCase, parameterized.TestCase):

  @tf.__internal__.distribute.combinations.generate(strategy_combinations_eager_data_fn())
  def test_linear_model(self, distribution, data_fn):
    with distribution.scope():
      model = linear.LinearModel()
      opt = gradient_descent.SGD(learning_rate=0.1)
      model.compile(opt, 'mse')
      if data_fn == 'numpy':
        inputs, output = get_numpy()
        hist = model.fit(inputs, output, epochs=5)
      else:
        hist = model.fit(get_dataset(), epochs=5)
      self.assertLess(hist.history['loss'][4], 0.2)

  @tf.__internal__.distribute.combinations.generate(strategy_combinations_eager_data_fn())
  def test_wide_deep_model(self, distribution, data_fn):
    with distribution.scope():
      linear_model = linear.LinearModel(units=1)
      dnn_model = sequential.Sequential([core.Dense(units=1)])
      wide_deep_model = wide_deep.WideDeepModel(linear_model, dnn_model)
      linear_opt = gradient_descent.SGD(learning_rate=0.05)
      dnn_opt = adagrad.Adagrad(learning_rate=0.1)
      wide_deep_model.compile(
          optimizer=[linear_opt, dnn_opt],
          loss='mse')
      if data_fn == 'numpy':
        inputs, output = get_numpy()
        hist = wide_deep_model.fit(inputs, output, epochs=5)
      else:
        hist = wide_deep_model.fit(get_dataset(), epochs=5)
      self.assertLess(hist.history['loss'][4], 0.2)


if __name__ == '__main__':
  tf.__internal__.distribute.multi_process_runner.test_main()
