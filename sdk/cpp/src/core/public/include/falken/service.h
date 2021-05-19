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

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_SERVICE_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_SERVICE_H_

#include <map>
#include <memory>
#include <string>

#include "falken/allocator.h"
#include "falken/brain.h"
#include "falken/config.h"

namespace falken {

class ServiceTest;

/// Falken service.
class FALKEN_EXPORT Service {
  friend class BrainBase;
  friend class ServiceTest;

 public:
  ~Service();
  /// Find a brain with the specified ID that conforms to the BrainSpec type T.
  ///
  /// @param brain_id Brain ID.
  /// @param snapshot_id Optional snapshot ID. A snapshot represents a point in
  ///     the evolution of a brain as it gains experience. If you want to
  ///     continue to train / evolve a brain, provide no snapshot ID and the
  ///     latest snapshot of the brain will be used. If you're happy with a
  ///     brain's performance, store the snapshot ID returned by
  ///     Session::Stop(). When you next load the brain, for example when
  ///     restarting the application, use the snapshot ID to restore the brain
  ///     to its prior state.
  /// @return Loaded Brain instance.
  template <typename T>
  std::shared_ptr<Brain<T>> GetBrain(const char* brain_id,
                                      const char* snapshot_id = nullptr);
  /// Find a brain with the specified ID.
  ///
  /// @deprecated Use GetBrain. This method will be
  /// removed in the future.
  template <typename T>
  FALKEN_DEPRECATED std::shared_ptr<Brain<T>> LoadBrain(const char* brain_id,
                                      const char* snapshot_id = nullptr) {
    return GetBrain<T>(brain_id, snapshot_id);
  }
  /// Find a brain with the specified ID.
  ///
  /// @param brain_id Brain ID.
  /// @param snapshot_id Optional snapshot ID.
  /// @return Loaded Brain instance.
  std::shared_ptr<BrainBase> GetBrain(const char* brain_id,
                                       const char* snapshot_id = nullptr);
  /// Find a brain with the specified ID.
  ///
  /// @deprecated Use GetBrain. This method will be
  /// removed in the future.
  FALKEN_DEPRECATED std::shared_ptr<BrainBase> LoadBrain(
      const char* brain_id, const char* snapshot_id = nullptr);

  /// Create a brain in this service with a given BrainSpec type T.
  ///
  /// @param display_name Brain display name.
  /// @return Created Brain instance.
  template <typename T>
  std::shared_ptr<Brain<T>> CreateBrain(const char* display_name);
  /// Create a brain in this service.
  ///
  /// @param display_name Brain display name.
  /// @param brain_spec Brain specs.
  /// @return Created Brain instance.
  std::shared_ptr<BrainBase> CreateBrain(const char* display_name,
                                         const BrainSpecBase& brain_spec);
  /// Gets all of the Brains in the current Project.
  ///
  /// @return A vector of Brains in the current Project.
  Vector<std::shared_ptr<BrainBase>> ListBrains();

  /// Connect to a Falken project.
  ///
  /// @param project_id Project ID. This parameter is optional if json_config
  ///     specifies it. If set, this value overrides the project_id value in
  ///     json_config.
  /// @param api_key API key. This parameter is optional if json_config
  ///     specifies it. If set, this value overrides the api_key value in
  ///     json_config.
  /// @param json_config Configuration as a JSON. This parameter is optional if
  ///     project_id and api_key are specified. It must follow the following
  ///     format:
  ///     @code{.json}
  ///     {
  ///       "api_key": "API_KEY",
  ///       "project_id": "PROJECT_ID"
  ///     }
  ///     @endcode
  ///     <ul>
  ///     <li><b>API_KEY</b>: API key used to connect to Falken. This defaults
  ///     to an empty string so must be set via this configuration value or the
  ///     api_key argument.</li>
  ///     <li><b>PROJECT_ID</b>: Falken project ID to use. This defaults to an
  ///     empty string so must be set via this configuration value or the
  ///     project_id argument.</li>
  ///     </ul>
  /// @return Falken service instance.
  static std::shared_ptr<Service> Connect(const char* project_id = nullptr,
                                          const char* api_key = nullptr,
                                          const char* json_config = nullptr);

  /// Sets the path to be used as Falken's temporary directory.
  /// @note The temporary directory path should be set via this method before
  ///     any other method in the SDK is called.
  ///
  /// @param temporary_directory Temporary directory absolute path.
  /// @return false if the specified directory does not exist and therefore
  ///     cannot be set, true otherwise.
  static bool SetTemporaryDirectory(const char* temporary_directory);

  /// Gets the path currently used as Falken's temporary directory.
  ///
  /// @return Path of the temporary directory.
  static String GetTemporaryDirectory();

  FALKEN_DEFINE_NEW_DELETE

 private:
  // Provides a weak_ptr form of this
  std::weak_ptr<Service>& WeakThis();
  void AddBrain(const std::shared_ptr<BrainBase>& brain, const char* type_id);
  std::shared_ptr<BrainBase> LookupBrain(const char* brain_id,
                                         const char* type_id);
  // Create a brain and retrieve its id.
  // Returns an empty string if a Brain could not be created.
  String CreateBrainInternal(const char* display_name,
                             const BrainSpecBase& brain_spec);
  // Load a brain and verify that it complies with the given brain spec.
  bool GetAndVerifyBrain(const char* brain_id,
                         const BrainSpecBase& brain_spec,
                         String* display_name) const;

  Service();

  FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_START
  // Private data.
  struct ServiceData;
  std::unique_ptr<ServiceData> service_data_;
  FALKEN_ALLOW_DATA_IN_EXPORTED_CLASS_END
};

template <typename T>
std::shared_ptr<Brain<T>> Service::GetBrain(const char* brain_id,
                                            const char* snapshot_id) {
  std::shared_ptr<BrainBase> brain_base_ptr = LookupBrain(brain_id,
                                                          typeid(T).name());
  if (brain_base_ptr) {
    return std::static_pointer_cast<Brain<T>>(brain_base_ptr);
  }

  String display_name;
  if (!GetAndVerifyBrain(brain_id, T(), &display_name)) {
    return std::shared_ptr<Brain<T>>();
  }
  std::shared_ptr<Brain<T>> brain_ptr(std::shared_ptr<Brain<T>>(new Brain<T>(
      WeakThis(), brain_id, display_name.c_str(), snapshot_id)));
  AddBrain(brain_ptr, typeid(T).name());
  return brain_ptr;
}

template <typename T>
std::shared_ptr<Brain<T>> Service::CreateBrain(
    const char* display_name) {
  const String brain_id = CreateBrainInternal(display_name, T());
  if (brain_id.empty()) {
    return std::shared_ptr<Brain<T>>();
  }
  std::shared_ptr<Brain<T>> brain_ptr(
      new Brain<T>(WeakThis(), brain_id.c_str(), display_name, nullptr));
  AddBrain(brain_ptr, typeid(T).name());
  return brain_ptr;
}

}  // namespace falken

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_SERVICE_H_
