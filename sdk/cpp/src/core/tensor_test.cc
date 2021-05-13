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

#include "src/core/tensor.h"

#include <utility>

#include "gmock/gmock.h"
#include "gtest/gtest.h"
#if defined(FALKEN_TENSORFLOW_CORE_ENABLED)
#include "tensorflow/core/framework/tensor.h"
#include "tensorflow/core/framework/tensor_shape.h"
#include "tensorflow/core/framework/tensor_shape.pb.h"  // NOLINT
#endif  // defined(FALKEN_TENSORFLOW_CORE_ENABLED)

using testing::ElementsAreArray;

#if defined(FALKEN_TENSORFLOW_CORE_ENABLED)
TEST(TensorDataType, EqualsTensorFlowTypes) {
  EXPECT_EQ(static_cast<int>(falken::tensor::DT_FLOAT),
            static_cast<int>(tensorflow::DT_FLOAT));
  EXPECT_EQ(static_cast<int>(falken::tensor::DT_INT32),
            static_cast<int>(tensorflow::DT_INT32));
}
#endif  // defined(FALKEN_TENSORFLOW_CORE_ENABLED)

TEST(TensorMap, ElementAccessors) {
  std::vector<int> backing_store({1, 4, 2});
  falken::tensor::TensorMap<int> v(backing_store);
  EXPECT_EQ(v(0), 1);
  EXPECT_EQ(v(1), 4);
  EXPECT_EQ(v(2), 2);
  EXPECT_EQ(v[0], 1);
  EXPECT_EQ(v[1], 4);
  EXPECT_EQ(v[2], 2);
  const auto& cv = v;
  EXPECT_EQ(cv(0), 1);
  EXPECT_EQ(cv(1), 4);
  EXPECT_EQ(cv(2), 2);
  EXPECT_EQ(cv[0], 1);
  EXPECT_EQ(cv[1], 4);
  EXPECT_EQ(cv[2], 2);

  v(0) = 5;
  v(1) = 6;
  v(2) = 7;
  EXPECT_THAT(backing_store, ElementsAreArray({5, 6, 7}));
  EXPECT_THAT(v, ElementsAreArray({5, 6, 7}));
  v[0] = 8;
  v[1] = 9;
  v[2] = 1;
  EXPECT_THAT(backing_store, ElementsAreArray({8, 9, 1}));
  EXPECT_THAT(v, ElementsAreArray({8, 9, 1}));

  std::vector<int> expected{8, 9, 1};
  EXPECT_THAT(v, expected);
}

TEST(TensorMap, Iterate) {
  std::vector<int> backing_store({1, 4, 2});
  falken::tensor::TensorMap<int> v(backing_store);
  falken::tensor::TensorMap<int>::const_iterator it;
  int index = 0;
  for (it = v.begin(); it != v.end(); ++it, ++index) {
    EXPECT_EQ(*it, backing_store[index]) << "offset: " << index;
  }
}

TEST(TensorShapeTest, Construct) {
  falken::tensor::TensorShape shape({2, 32, 3});
  EXPECT_EQ(shape[0], 2);
  EXPECT_EQ(shape[1], 32);
  EXPECT_EQ(shape[2], 3);
}

TEST(TensorShapeTest, DebugString) {
  EXPECT_EQ(falken::tensor::TensorShape::DebugString(
                falken::tensor::TensorShape({2, 32, 3})),
            "[2, 32, 3]");
}

TEST(TensorShapeTest, FindNextDimensionWithSizeGreaterThanOne) {
  falken::tensor::TensorShape shape({1, 2, -1, 1, 3});
  int number_of_dimensions = shape.dims();
  int dimension = 0;
  EXPECT_EQ(
      falken::tensor::TensorShape::FindNextDimensionWithSizeGreaterThanOne(
          shape, number_of_dimensions, dimension), 2);
  EXPECT_EQ(dimension, 2);
  EXPECT_EQ(
      falken::tensor::TensorShape::FindNextDimensionWithSizeGreaterThanOne(
          shape, number_of_dimensions, dimension), -1);
  EXPECT_EQ(dimension, 3);
  EXPECT_EQ(
      falken::tensor::TensorShape::FindNextDimensionWithSizeGreaterThanOne(
          shape, number_of_dimensions, dimension), 3);
  EXPECT_EQ(dimension, 5);
  EXPECT_EQ(
      falken::tensor::TensorShape::FindNextDimensionWithSizeGreaterThanOne(
          shape, number_of_dimensions, dimension), 0);
}

TEST(TensorShapeTest, FlatSize) {
  falken::tensor::TensorShape shape({1, 2, -1, 1, 3});
  EXPECT_EQ(falken::tensor::TensorShape::FlatSize(shape), 6);
}

#if defined(FALKEN_TENSORFLOW_CORE_ENABLED)
TEST(TensorShapeTest, Compare) {
  EXPECT_TRUE(falken::tensor::TensorShape::Compare(
      falken::tensor::TensorShape({2, 32, 3}),
      tensorflow::TensorShape({2, 32, 3})));
  EXPECT_TRUE(falken::tensor::TensorShape::Compare(
      falken::tensor::TensorShape({2, -1, 3}),
      tensorflow::TensorShape({2, 32, 3})));
  EXPECT_TRUE(falken::tensor::TensorShape::Compare(
      tensorflow::TensorShape({2, 32, 3}),
      falken::tensor::TensorShape({2, 32, -1})));
  EXPECT_TRUE(falken::tensor::TensorShape::Compare(
      falken::tensor::TensorShape({1, 1}),
      tensorflow::TensorShape({1, 1, 1})));
  EXPECT_FALSE(falken::tensor::TensorShape::Compare(
      falken::tensor::TensorShape({2, 32, 3}),
      tensorflow::TensorShape({2, 5})));
  EXPECT_FALSE(falken::tensor::TensorShape::Compare(
      falken::tensor::TensorShape({1, 2, 3}),
      tensorflow::TensorShape({1, 3, 2})));
}
#endif  // defined(FALKEN_TENSORFLOW_CORE_ENABLED)

TEST(TensorSpecTest, Construct) {
  falken::tensor::TensorSpec spec;
  EXPECT_EQ(spec.dtype(), falken::tensor::DT_INVALID);
  EXPECT_EQ(spec.shape(), falken::tensor::TensorShape());
}

TEST(TensorSpecTest, ConstructWithTypeAndShape) {
  falken::tensor::TensorSpec spec(falken::tensor::DT_INT32,
                                  falken::tensor::TensorShape({1, 2, 3}));
  EXPECT_EQ(spec.dtype(), falken::tensor::DT_INT32);
  EXPECT_EQ(spec.shape(), falken::tensor::TensorShape({1, 2, 3}));
}

TEST(TensorSpecTest, MoveConstruct) {
  {
    falken::tensor::TensorShape shape({1, 2, 3});
    falken::tensor::TensorSpec spec(falken::tensor::DT_INT32, shape);
    falken::tensor::TensorSpec other(std::move(spec));
    EXPECT_EQ(other.dtype(), falken::tensor::DT_INT32);
    EXPECT_EQ(other.shape(), falken::tensor::TensorShape({1, 2, 3}));
  }
  {
    falken::tensor::TensorShape shape({1, 2, 3});
    falken::tensor::TensorSpec spec(falken::tensor::DT_INT32,
                                    std::move(shape));
    EXPECT_EQ(spec.dtype(), falken::tensor::DT_INT32);
    EXPECT_EQ(spec.shape(), falken::tensor::TensorShape({1, 2, 3}));
  }
}

TEST(TensorSpecTest, CopyConstruct) {
  falken::tensor::TensorSpec spec(falken::tensor::DT_INT32,
                                  falken::tensor::TensorShape({1, 2, 3}));
  falken::tensor::TensorSpec other(spec);
  EXPECT_EQ(other.dtype(), falken::tensor::DT_INT32);
  EXPECT_EQ(other.shape(), falken::tensor::TensorShape({1, 2, 3}));
}

TEST(TensorSpecTest, Move) {
  falken::tensor::TensorSpec spec(falken::tensor::DT_INT32,
                                  falken::tensor::TensorShape({1, 2, 3}));
  falken::tensor::TensorSpec other;
  other = std::move(spec);
  EXPECT_EQ(other.dtype(), falken::tensor::DT_INT32);
  EXPECT_EQ(other.shape(), falken::tensor::TensorShape({1, 2, 3}));
}

TEST(TensorSpecTest, Copy) {
  falken::tensor::TensorSpec spec(falken::tensor::DT_INT32,
                                  falken::tensor::TensorShape({1, 2, 3}));
  falken::tensor::TensorSpec other;
  other = spec;
  EXPECT_EQ(other.dtype(), falken::tensor::DT_INT32);
  EXPECT_EQ(other.shape(), falken::tensor::TensorShape({1, 2, 3}));
}

#if defined(FALKEN_TENSORFLOW_CORE_ENABLED)
TEST(TensorSpecTest, Compare) {
  falken::tensor::TensorSpec spec(falken::tensor::DT_INT32,
                                  falken::tensor::TensorShape({1, 2, 3}));
  {
    tensorflow::Tensor tf_tensor(tensorflow::DT_INT32,
                                 tensorflow::TensorShape({1, 2, 3}));
    EXPECT_TRUE(falken::tensor::TensorSpec::Compare(spec, tf_tensor).ok());
  }
  {
    // Mismatched types.
    tensorflow::Tensor tf_tensor(tensorflow::DT_FLOAT,
                                 tensorflow::TensorShape({1, 2, 3}));
    EXPECT_FALSE(falken::tensor::TensorSpec::Compare(spec, tf_tensor).ok());
  }
  {
    // Mismatched shapes.
    tensorflow::Tensor tf_tensor(tensorflow::DT_FLOAT,
                                 tensorflow::TensorShape({1, 2}));
    EXPECT_FALSE(falken::tensor::TensorSpec::Compare(spec, tf_tensor).ok());
  }
}
#endif  // defined(FALKEN_TENSORFLOW_CORE_ENABLED)

TEST(TensorTest, ConstructWithTypeAndShape) {
  falken::tensor::Tensor tensor(falken::tensor::DT_INT32,
                                falken::tensor::TensorShape({1, 2, 3}));
  EXPECT_EQ(tensor.dtype(), falken::tensor::DT_INT32);
  EXPECT_EQ(tensor.shape(), falken::tensor::TensorShape({1, 2, 3}));
  EXPECT_TRUE(falken::tensor::TensorSpec::Compare(
                  tensor.spec(), falken::tensor::TensorSpec(
                                     falken::tensor::DT_INT32,
                                     falken::tensor::TensorShape({1, 2, 3})))
                  .ok());
  EXPECT_EQ(tensor.flat<int>().size(), 6);
}

TEST(TensorTest, ConstructWithSpec) {
  falken::tensor::TensorSpec spec(falken::tensor::DT_INT32,
                                  falken::tensor::TensorShape({4, 2, 3}));
  falken::tensor::Tensor tensor(spec);
  EXPECT_TRUE(falken::tensor::TensorSpec::Compare(tensor.spec(), spec).ok());
  EXPECT_EQ(tensor.flat<int>().size(), 24);
}

TEST(TensorTest, MoveConstruct) {
  falken::tensor::TensorSpec spec(falken::tensor::DT_INT32,
                                  falken::tensor::TensorShape({4, 2, 3}));
  falken::tensor::Tensor source(spec);
  falken::tensor::Tensor tensor(std::move(source));
  EXPECT_TRUE(falken::tensor::TensorSpec::Compare(tensor.spec(), spec).ok());
  EXPECT_EQ(tensor.flat<int>().size(), 24);
}

TEST(TensorTest, CopyConstruct) {
  falken::tensor::TensorSpec spec(falken::tensor::DT_INT32,
                                  falken::tensor::TensorShape({4, 2, 3}));
  falken::tensor::Tensor source(spec);
  falken::tensor::Tensor tensor(source);
  EXPECT_TRUE(falken::tensor::TensorSpec::Compare(source.spec(), spec).ok());
  EXPECT_EQ(source.flat<int>().size(), 24);
  EXPECT_TRUE(falken::tensor::TensorSpec::Compare(tensor.spec(), spec).ok());
  EXPECT_EQ(tensor.flat<int>().size(), 24);
}

TEST(TensorTest, Move) {
  falken::tensor::TensorSpec spec(falken::tensor::DT_INT32,
                                  falken::tensor::TensorShape({4, 2, 3}));
  falken::tensor::Tensor source(spec);
  falken::tensor::Tensor tensor;
  tensor = std::move(source);
  EXPECT_TRUE(falken::tensor::TensorSpec::Compare(tensor.spec(), spec).ok());
  EXPECT_EQ(tensor.flat<int>().size(), 24);
}

TEST(TensorTest, Copy) {
  falken::tensor::TensorSpec spec(falken::tensor::DT_INT32,
                                  falken::tensor::TensorShape({4, 2, 3}));
  falken::tensor::Tensor source(spec);
  falken::tensor::Tensor tensor;
  tensor = source;
  EXPECT_TRUE(falken::tensor::TensorSpec::Compare(source.spec(), spec).ok());
  EXPECT_EQ(source.flat<int>().size(), 24);
  EXPECT_TRUE(falken::tensor::TensorSpec::Compare(tensor.spec(), spec).ok());
  EXPECT_EQ(tensor.flat<int>().size(), 24);
}

template <typename TensorType, typename DataType>
void InitializeTensor(TensorType& tensor, const DataType* array,
                      int array_size) {
  for (int i = 0; i < array_size; ++i) {
    tensor.template flat<DataType>()(i) = array[i];
  }
}

TEST(TensorTest, AccessElements) {
  const int kExpected[] = {6, 5, 4, 3, 2, 1};
  falken::tensor::Tensor tensor(falken::tensor::DT_INT32,
                                falken::tensor::TensorShape({2, 3}));
  ASSERT_EQ(tensor.flat<int>().size(), ABSL_ARRAYSIZE(kExpected));
  InitializeTensor(tensor, kExpected, ABSL_ARRAYSIZE(kExpected));
  {
    auto elements = tensor.flat<int>();
    EXPECT_THAT(std::vector<int>(elements.data(),
                                 elements.data() + elements.size()),
                ElementsAreArray(kExpected));
  }
  {
    const auto const_tensor = tensor;
    auto elements = const_tensor.flat<int>();
    EXPECT_THAT(std::vector<int>(elements.data(),
                                 elements.data() + elements.size()),
                ElementsAreArray(kExpected));
  }
}

#if defined(FALKEN_TENSORFLOW_CORE_ENABLED)
TEST(TensorTest, CopyBetweenTensorTypesWithCompileTimeDataType) {
  // Copy from a Falken to TensorFlow tensor.
  {
    const int kExpected[] = {6, 5, 4, 3, 2, 1};
    falken::tensor::Tensor tensor(falken::tensor::DT_INT32,
                                  falken::tensor::TensorShape({2, 3}));
    tensorflow::Tensor tf_tensor(tensorflow::DT_INT32,
                                 tensorflow::TensorShape({2, 3}));
    InitializeTensor(tensor, kExpected, ABSL_ARRAYSIZE(kExpected));
    EXPECT_TRUE(falken::tensor::Tensor::Copy<int>(tensor, tf_tensor).ok());
    auto tensor_map = tf_tensor.flat<int>();
    EXPECT_THAT(std::vector<int>(tensor_map.data(),
                                 tensor_map.data() + tensor_map.size()),
                ElementsAreArray(kExpected));
  }

  // Copy from a TensorFlow to Falken tensor.
  {
    const int kExpected[] = {6, 5, 4, 3, 2, 1};
    falken::tensor::Tensor tensor(falken::tensor::DT_INT32,
                                  falken::tensor::TensorShape({2, 3}));
    tensorflow::Tensor tf_tensor(tensorflow::DT_INT32,
                                 tensorflow::TensorShape({2, 3}));
    InitializeTensor(tf_tensor, kExpected, ABSL_ARRAYSIZE(kExpected));
    EXPECT_TRUE(falken::tensor::Tensor::Copy<int>(tf_tensor, tensor).ok());
    auto tensor_map = tensor.flat<int>();
    EXPECT_THAT(std::vector<int>(tensor_map.data(),
                                 tensor_map.data() + tensor_map.size()),
                ElementsAreArray(kExpected));
  }
}
#endif  // defined(FALKEN_TENSORFLOW_CORE_ENABLED)

#if defined(FALKEN_TENSORFLOW_CORE_ENABLED)
TEST(TensorTest, CopyBetweenTensorTypesWithRuntimeTimeDataType) {
  // Copy from a Falken to TensorFlow tensor.
  {
    const int kExpected[] = {6, 5, 4, 3, 2, 1};
    falken::tensor::Tensor tensor(falken::tensor::DT_INT32,
                                  falken::tensor::TensorShape({2, 3}));
    tensorflow::Tensor tf_tensor(tensorflow::DT_INT32,
                                 tensorflow::TensorShape({2, 3}));
    InitializeTensor(tensor, kExpected, ABSL_ARRAYSIZE(kExpected));
    EXPECT_TRUE(
        falken::tensor::Tensor::Copy(tensor.dtype(), tensor, tf_tensor).ok());
    auto tensor_map = tf_tensor.flat<int>();
    EXPECT_THAT(std::vector<int>(tensor_map.data(),
                                 tensor_map.data() + tensor_map.size()),
                ElementsAreArray(kExpected));
  }

  // Copy from a TensorFlow to Falken tensor.
  {
    const int kExpected[] = {6, 5, 4, 3, 2, 1};
    falken::tensor::Tensor tensor(falken::tensor::DT_INT32,
                                  falken::tensor::TensorShape({2, 3}));
    tensorflow::Tensor tf_tensor(tensorflow::DT_INT32,
                                 tensorflow::TensorShape({2, 3}));
    InitializeTensor(tf_tensor, kExpected, ABSL_ARRAYSIZE(kExpected));
    EXPECT_TRUE(
        falken::tensor::Tensor::Copy(tensor.dtype(), tf_tensor, tensor).ok());
    auto tensor_map = tensor.flat<int>();
    EXPECT_THAT(std::vector<int>(tensor_map.data(),
                                 tensor_map.data() + tensor_map.size()),
                ElementsAreArray(kExpected));
  }

  // Try copying with an unsupported data type.
  {
    falken::tensor::Tensor tensor(falken::tensor::DT_INT32,
                                  falken::tensor::TensorShape({2, 3}));
    tensorflow::Tensor tf_tensor(tensorflow::DT_INT32,
                                 tensorflow::TensorShape({2, 3}));
    EXPECT_FALSE(falken::tensor::Tensor::Copy(falken::tensor::DT_INVALID,
                                              tf_tensor, tensor).ok());
  }
}
#endif  // defined(FALKEN_TENSORFLOW_CORE_ENABLED)
