// Copyright 2021 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <cassert>
#include <string>
#include <utility>

#include "src/core/tensor.h"

namespace falken {
namespace tensor {

Tensor::Tensor(const Tensor& t) :
  int_data_(t.int_data_),
  float_data_(t.float_data_),
  spec_(t.spec_) {}

Tensor::Tensor(Tensor&& t) :
  int_data_(std::move(t.int_data_)),
  float_data_(std::move(t.float_data_)),
  spec_(std::move(t.spec_)) {}

Tensor& Tensor::operator=(Tensor&& t) {
  std::swap(t.int_data_, int_data_);
  std::swap(t.float_data_, float_data_);
  std::swap(t.spec_, spec_);
  return *this;
}

Tensor& Tensor::operator=(const Tensor& t) {
  int_data_ = t.int_data_;
  float_data_ = t.float_data_;
  spec_ = t.spec_;
  return *this;
}


Tensor::Tensor(DataType data_type, const TensorShape& shape)
    : spec_(data_type, shape) {
  if (shape.empty()) {
    return;
  }
  auto flat_size = TensorShape::FlatSize(shape);
  switch (data_type) {
    case DT_FLOAT:
      float_data_.resize(flat_size);
      break;
    case DT_INT32:
      int_data_.resize(flat_size);
      break;
    case DT_INVALID:
      ABSL_ASSERT("Unable to construct a tensor with an invalid data type." ==
                  nullptr);
      break;
  }
}

template <>
TensorMap<int> Tensor::flat<int>() {
  ABSL_ASSERT(dtype() == DT_INT32);
  return TensorMap<int>(int_data_);
}

template <>
const TensorMap<int> Tensor::flat<int>() const {
  ABSL_ASSERT(dtype() == DT_INT32);
  return TensorMap<int>(int_data_);
}

template <>
TensorMap<float> Tensor::flat<float>() {
  ABSL_ASSERT(dtype() == DT_FLOAT);
  return TensorMap<float>(float_data_);
}

template <>
const TensorMap<float> Tensor::flat<float>() const {
  ABSL_ASSERT(dtype() == DT_FLOAT);
  return TensorMap<float>(float_data_);
}

}  // namespace tensor
}  // namespace falken
