//  Copyright 2021 Google LLC
//
//  Licensed under the Apache License, Version 2.0 (the "License");
//  you may not use this file except in compliance with the License.
//  You may obtain a copy of the License at
//
//       http://www.apache.org/licenses/LICENSE-2.0
//
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.

#ifndef FALKEN_SDK_CORE_TENSOR_H_
#define FALKEN_SDK_CORE_TENSOR_H_

#include <sstream>
#include <string>
#include <utility>
#include <vector>

#include "absl/status/status.h"
#include "absl/strings/str_cat.h"

namespace falken {
namespace tensor {

// Values are int equivalent to those of the ::tensorflow::DataType
// enum.
enum DataType {
  // Not a legal value for DataType.  Used to indicate a DataType field
  // has not been set.
  DT_INVALID = 0,

  // Subset of Tensorflow types used by Falken.
  DT_FLOAT = 1,
  DT_INT32 = 3
};

// Partially compatible implementation of Eigen::TensorMap.
template <typename M>
class TensorMap {
 public:
  // Typedefs unsupported by Eigen::TensorMap but provided to enable
  // compatibility with methods that iterate over std::vector<M>.
  typedef M value_type;
  typedef M* const_iterator;

 public:
  TensorMap() : elements_(nullptr) {}
  explicit TensorMap(const std::vector<M>& elements)
      : TensorMap(&elements[0], elements.size()) {}
  TensorMap(const M* elements, int size)
      : elements_(const_cast<M*>(elements)), size_(size) {}

  size_t size() const { return size_; }
  M* data() const { return elements_; }
  M& operator()(int i) { return elements_[i]; }
  const M& operator()(int i) const { return elements_[i]; }

  // Members not supported by Eigen::TensorMap but provided to simplify the
  // comparison of TensorMap with arrays and vectors in tests.
  M& operator[](int i) { return operator()(i); }
  const M& operator[](int i) const { return operator()(i); }

  M* begin() const { return elements_; }
  M* end() const { return elements_ + size_; }

  bool operator==(const std::vector<M>& other) const {
    if (other.size() != size()) return false;
    for (int i = 0; i < size(); ++i) {
      if (operator[](i) != other[i]) return false;
    }
    return true;
  }

 private:
  M* elements_;
  int size_;
};

// Use "long long" for dimension datatype here as tensorflow::TensorShape has
// dimension type defined as Eigen's int64 which is unfortunately defined as
// "long long" vs. int64_t which is "long" for 64-bit architectures.
typedef long long TensorShapeDimension;  // NOLINT

class TensorShape : public std::vector<TensorShapeDimension> {
 public:
  TensorShape() {}
  TensorShape(const std::initializer_list<TensorShapeDimension>& dimensions)
      : std::vector<TensorShapeDimension>(dimensions) {}

  // Number of dimensions in the tensor.
  int dims() const { return size(); }

  // Get the size of a dimension.
  int dim_size(int d) const { return operator[](d); }

  // Convert a TensorShape to a string.
  // TensorShapeType must implement dims() which returns the number of
  // dimensions and dim_size(i) which returns the size of each dimension.
  template <typename TensorShapeType>
  static std::string DebugString(const TensorShapeType& shape) {
    std::string s = "[";
    int number_of_dimensions = shape.dims();
    for (int dimension = 0; dimension < number_of_dimensions; ++dimension) {
      auto dimension_size = shape.dim_size(dimension);
      s += dimension_size < 0 ? "?" : std::to_string(dimension_size);
      if (dimension < number_of_dimensions - 1) s += ", ";
    }
    s += "]";
    return s;
  }

  // Find the next dimension that is greater than size 1 or of an unknown size.
  //
  // Updates dimension with the found dimension + 1 and returns the size of
  // the next dimension or 0 if no more dimensions are found.
  template <typename TensorShapeType>
  static TensorShapeDimension FindNextDimensionWithSizeGreaterThanOne(
      const TensorShapeType& shape, int number_of_dimensions,
      int& dimension) {
    while (dimension < number_of_dimensions) {
      auto dimension_size = shape.dim_size(dimension);
      dimension++;
      if (dimension_size == -1 || dimension_size >= 2) return dimension_size;
    }
    return 0;
  }

  // Calculate the flat size of a tensor shape.
  template <typename TensorShapeType>
  static TensorShapeDimension FlatSize(const TensorShapeType& shape) {
    auto flat_size = static_cast<TensorShapeDimension>(1);
    int number_of_dimensions = shape.dims();
    int current_dimension = 0;
    for ( ; ; ) {
      auto dimension_size =
          TensorShape::FindNextDimensionWithSizeGreaterThanOne(
              shape, number_of_dimensions, current_dimension);
      if (!dimension_size) break;
      // Ignore unknown dimensions.
      if (dimension_size > 0) flat_size *= dimension_size;
    }
    return flat_size;
  }

  // Compare two TensorShapes.
  //
  // Each TensorShapeType must implement dims() which returns the number of
  // dimensions and dim_size(i) which returns the size of each dimension.
  template <typename TensorShapeTypeLhs, typename TensorShapeTypeRhs>
  static bool Compare(const TensorShapeTypeLhs& lhs,
                      const TensorShapeTypeRhs& rhs) {
    int lhs_dimension = 0;
    auto lhs_number_of_dimensions = lhs.dims();
    int rhs_dimension = 0;
    auto rhs_number_of_dimensions = rhs.dims();
    while (lhs_dimension != lhs_number_of_dimensions &&
           rhs_dimension != rhs_number_of_dimensions) {
      int lhs_dimension_size =
          TensorShape::FindNextDimensionWithSizeGreaterThanOne(
              lhs, lhs_number_of_dimensions, lhs_dimension);
      int rhs_dimension_size =
          TensorShape::FindNextDimensionWithSizeGreaterThanOne(
              rhs, rhs_number_of_dimensions, rhs_dimension);
      if (!(lhs_dimension_size == -1 || rhs_dimension_size == -1 ||
            lhs_dimension_size == rhs_dimension_size)) {
        return false;
      }
    }
    return true;
  }
};

// Deprecated, use TensorShape::DebugString() instead.
template <typename TensorShapeType>
std::string TensorShapeDebugString(const TensorShapeType& shape) {
  return TensorShape::DebugString(shape);
}

// Deprecated, use TensorShape::Compare() instead.
template <typename TensorShapeTypeLhs, typename TensorShapeTypeRhs>
bool CompareTensorShapes(const TensorShapeTypeLhs& lhs,
                         const TensorShapeTypeRhs& rhs) {
  return TensorShape::Compare(lhs, rhs);
}

// Falken's TensorSpec, which describes the format of a Tensor.
class TensorSpec {
 public:
  TensorSpec() : data_type_(DT_INVALID) {}
  TensorSpec(DataType data_type, const TensorShape& shape) :
      data_type_(data_type), shape_(shape) {}
  TensorSpec(DataType data_type, TensorShape&& shape) :
      data_type_(data_type), shape_(std::move(shape)) {}

  TensorSpec(TensorSpec&& tensor_spec) :
      data_type_(tensor_spec.data_type_),
      shape_(std::move(tensor_spec.shape_)) {}

  TensorSpec(const TensorSpec& tensor_spec) :
      data_type_(tensor_spec.data_type_),
      shape_(tensor_spec.shape_) {}

  TensorSpec& operator=(TensorSpec&& tensor_spec) {
    data_type_ = tensor_spec.data_type_;
    shape_ = std::move(tensor_spec.shape_);
    return *this;
  }

  TensorSpec& operator=(const TensorSpec& tensor_spec) {
    data_type_ = tensor_spec.data_type_;
    shape_ = tensor_spec.shape_;
    return *this;
  }

  const TensorShape& shape() const { return shape_; }

  DataType dtype() const { return data_type_; }

  // Compare with another tensor spec conforming to the TensorSpec interface
  // reporting differences if they're found.
  // Each TensorSpecType must implement dtype() which returns an enum
  // value compatible with DataType and shape() which returns an object with
  // an TensorShape compatible interface.
  template <typename TensorSpecTypeLhs, typename TensorSpecTypeRhs>
  static absl::Status Compare(const TensorSpecTypeLhs& spec,
                              const TensorSpecTypeRhs& other_spec) {
    std::stringstream error;
    if (static_cast<tensor::DataType>(spec.dtype()) !=
        static_cast<tensor::DataType>(other_spec.dtype())) {
      error << "TensorSpec data types do not match " << spec.dtype()
            << " != " << other_spec.dtype() << ", ";
    }
    if (!CompareTensorShapes(spec.shape(), other_spec.shape())) {
      error << "TensorSpec shapes do not match "
            << TensorShapeDebugString(spec.shape())
            << " != " << TensorShapeDebugString(other_spec.shape());
    }
    std::string error_string = error.str();
    return error_string.empty() ? absl::OkStatus()
                                : absl::FailedPreconditionError(error_string);
  }

 private:
  // Datatype, values are int equivalent to those of the ::tensorflow::DataType
  // enum.
  DataType data_type_;

  // Vector shape (dimensions).
  TensorShape shape_;
};

// Falken's Tensor, which allows to store data in a similar format to that of
// Tensorflow Tensors.
class Tensor {
 public:
  Tensor() {}
  Tensor(DataType data_type, const TensorShape& shape);
  explicit Tensor(const TensorSpec& spec)
      : Tensor(spec.dtype(), spec.shape()) {}
  Tensor(Tensor&& t);
  Tensor(const Tensor& t);

  Tensor& operator=(Tensor&& t);
  Tensor& operator=(const Tensor& t);

  template <typename T>
  const TensorMap<T> flat() const;

  template <typename T>
  TensorMap<T> flat();

  const TensorShape& shape() const { return spec_.shape(); }

  DataType dtype() const { return spec_.dtype(); }

  const TensorSpec& spec() const { return spec_; }

  // Copy elements of type DataType from input_tensor to output_tensor where
  // both types conform to the Tensor interface.
  template <typename DataType, typename InputTensorType,
            typename OutputTensorType>
  static absl::Status Copy(const InputTensorType& input_tensor,
                           OutputTensorType& output_tensor) {
#if !defined(NDEBUG)
    auto status = TensorSpec::Compare(input_tensor, output_tensor);
    if (!status.ok()) return status;
#endif  // !defined(NDEBUG)
    const auto input_flat_data = input_tensor.template flat<DataType>();
    auto input_flat_data_size = input_flat_data.size();
    auto output_flat_data = output_tensor.template flat<DataType>();
    ABSL_ASSERT(input_flat_data_size == output_flat_data.size());
    for (size_t i = 0; i < input_flat_data_size; ++i) {
      output_flat_data(i) = input_flat_data(i);
    }
    return absl::OkStatus();
  }

  // Copy elements of type data_type from input_tensor to output_tensor where
  // both types conform to the Tensor interface.
  template <typename InputTensorType, typename OutputTensorType>
  static absl::Status Copy(DataType data_type,
                           const InputTensorType& input_tensor,
                           OutputTensorType& output_tensor) {
    switch (data_type) {
      case DT_INVALID:
        return absl::FailedPreconditionError(absl::StrCat(
            "Unable to copy tensor with invalid data type ", data_type));
      case DT_FLOAT:
        return Copy<float>(input_tensor, output_tensor);
      case DT_INT32:
        return Copy<int>(input_tensor, output_tensor);
    }
    return absl::OkStatus();
  }

 private:
  // We don't use a template to make it easier to handle structures that
  // must contain a mix of Tensors of different types.
  std::vector<int> int_data_;
  std::vector<float> float_data_;

  TensorSpec spec_;
};

template <>
TensorMap<int> Tensor::flat<int>();

template <>
const TensorMap<int> Tensor::flat<int>() const;

template <>
TensorMap<float> Tensor::flat<float>();

template <>
const TensorMap<float> Tensor::flat<float>() const;

using NamedTensor = std::pair<std::string, Tensor>;

using NamedTensorSpec = std::pair<std::string, TensorSpec>;

}  // namespace tensor
}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_TENSOR_H_
