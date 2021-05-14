# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Prevent gtest/gmock from getting added to the installation package
option(INSTALL_GTEST "CPack should not install GTest" OFF)
option(INSTALL_GMOCK "CPack should not install GMock" OFF)

include(FetchContent)
FetchContent_Declare(googletest
  GIT_REPOSITORY    https://github.com/google/googletest.git
  GIT_TAG           703bd9caab50b139428cea1aaff9974ebee5742e    # tag: v1.10.0
)
FetchContent_MakeAvailable(googletest)

