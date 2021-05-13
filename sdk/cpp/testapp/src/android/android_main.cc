// Copyright 2016 Google Inc. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <android/log.h>
#include <android_native_app_glue.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdio.h>

#include <cassert>
#include <string>

#include "main.h"  // NOLINT

// This implementation is derived from http://github.com/google/fplutil

extern "C" int common_main(int argc, const char* argv[]);

static struct android_app* g_app_state = nullptr;
static bool g_destroy_requested = false;
static bool g_started = false;
static bool g_restarted = false;
static pthread_mutex_t g_started_mutex;
static std::string g_temporary_directory;  // NOLINT

// Handle state changes from via native app glue.
static void OnAppCmd(struct android_app* app, int32_t cmd) {
  g_destroy_requested |= cmd == APP_CMD_DESTROY;
}

// Process events pending on the main thread.
// Returns true when the app receives an event requesting exit.
bool ProcessEvents(int msec) {
  struct android_poll_source* source = nullptr;
  int events;
  int looperId = ALooper_pollAll(msec, nullptr, &events,
                                 reinterpret_cast<void**>(&source));
  if (looperId >= 0 && source) {
    source->process(g_app_state, source);
  }
  return g_destroy_requested | g_restarted;
}

// Get the activity.
jobject GetActivity() { return g_app_state->activity->clazz; }

// Get the window context. For Android, it's a jobject pointing to the Activity.
jobject GetWindowContext() { return g_app_state->activity->clazz; }

// Find a class, attempting to load the class if it's not found.
jclass FindClass(JNIEnv* env, jobject activity_object, const char* class_name) {
  jclass class_object = env->FindClass(class_name);
  if (env->ExceptionCheck()) {
    env->ExceptionClear();
    // If the class isn't found it's possible NativeActivity is being used by
    // the application which means the class path is set to only load system
    // classes.  The following falls back to loading the class using the
    // Activity before retrieving a reference to it.
    jclass activity_class = env->FindClass("android/app/Activity");
    jmethodID activity_get_class_loader = env->GetMethodID(
        activity_class, "getClassLoader", "()Ljava/lang/ClassLoader;");

    jobject class_loader_object =
        env->CallObjectMethod(activity_object, activity_get_class_loader);

    jclass class_loader_class = env->FindClass("java/lang/ClassLoader");
    jmethodID class_loader_load_class =
        env->GetMethodID(class_loader_class, "loadClass",
                         "(Ljava/lang/String;)Ljava/lang/Class;");
    jstring class_name_object = env->NewStringUTF(class_name);

    class_object = static_cast<jclass>(env->CallObjectMethod(
        class_loader_object, class_loader_load_class, class_name_object));

    if (env->ExceptionCheck()) {
      env->ExceptionClear();
      class_object = nullptr;
    }
    env->DeleteLocalRef(class_name_object);
    env->DeleteLocalRef(class_loader_object);
  }
  return class_object;
}

// Checks for JNI exceptions, logs them to the console if any, and clear them.
void CheckAndClearJniExceptions(JNIEnv* env) {
  if (env->ExceptionCheck()) {
    // Get the exception text.
    jthrowable exception = env->ExceptionOccurred();
    env->ExceptionClear();

    // Convert the exception to a string.
    jclass object_class = env->FindClass("java/lang/Object");
    jmethodID toString =
        env->GetMethodID(object_class, "toString", "()Ljava/lang/String;");
    jstring s = (jstring)env->CallObjectMethod(exception, toString);
    const char* exception_text = env->GetStringUTFChars(s, nullptr);

    // Log the exception text.
    __android_log_print(ANDROID_LOG_INFO, APP_FRAMEWORK_TESTAPP_NAME,
                        "-------------------JNI exception:");
    __android_log_print(ANDROID_LOG_INFO, APP_FRAMEWORK_TESTAPP_NAME, "%s",
                        exception_text);
    __android_log_print(ANDROID_LOG_INFO, APP_FRAMEWORK_TESTAPP_NAME,
                        "-------------------");

    // Also, assert fail.
    assert(false);

    // In the event we didn't assert fail, clean up.
    env->ReleaseStringUTFChars(s, exception_text);
    env->DeleteLocalRef(s);
    env->DeleteLocalRef(exception);
  }
}

// Vars that we need available for appending text to the log window:
class LoggingUtilsData {
 public:
  LoggingUtilsData()
      : logging_utils_class_(nullptr),
        logging_utils_add_log_text_(0),
        logging_utils_init_log_window_(0) {}

  ~LoggingUtilsData() {
    JNIEnv* env = GetJniEnv();
    assert(env);
    if (logging_utils_class_) {
      env->DeleteGlobalRef(logging_utils_class_);
    }
  }

  void Init() {
    JNIEnv* env = GetJniEnv();
    assert(env);

    jclass logging_utils_class =
        FindClass(env, GetActivity(), "com/google/example/LoggingUtils");
    assert(logging_utils_class != 0);

    // Need to store as global references so it don't get moved during garbage
    // collection.
    logging_utils_class_ =
        static_cast<jclass>(env->NewGlobalRef(logging_utils_class));
    env->DeleteLocalRef(logging_utils_class);

    logging_utils_init_log_window_ = env->GetStaticMethodID(
        logging_utils_class_, "initLogWindow", "(Landroid/app/Activity;)V");
    logging_utils_add_log_text_ = env->GetStaticMethodID(
        logging_utils_class_, "addLogText", "(Ljava/lang/String;)V");

    env->CallStaticVoidMethod(logging_utils_class_,
                              logging_utils_init_log_window_, GetActivity());
  }

  void AppendText(const char* text) {
    if (logging_utils_class_ == 0) return;  // haven't been initted yet
    JNIEnv* env = GetJniEnv();
    assert(env);
    jstring text_string = env->NewStringUTF(text);
    env->CallStaticVoidMethod(logging_utils_class_, logging_utils_add_log_text_,
                              text_string);
    env->DeleteLocalRef(text_string);
    CheckAndClearJniExceptions(env);
  }

 private:
  jclass logging_utils_class_;
  jmethodID logging_utils_add_log_text_;
  jmethodID logging_utils_init_log_window_;
};

LoggingUtilsData* g_logging_utils_data;

// Log a message that can be viewed in "adb logcat".
void LogPrintV(int priority, const char* format, va_list list) {
  static const int kLineBufferSize = 100;
  char buffer[kLineBufferSize + 2];

  int string_len = vsnprintf(buffer, kLineBufferSize, format, list);
  string_len = string_len < kLineBufferSize ? string_len : kLineBufferSize;
  // append a linebreak to the buffer:
  buffer[string_len] = '\n';
  buffer[string_len + 1] = '\0';

  __android_log_vprint(priority, APP_FRAMEWORK_TESTAPP_NAME, format, list);
  g_logging_utils_data->AppendText(buffer);
}

void LogMessage(const char* format, ...) {
  va_list list;
  va_start(list, format);
  LogPrintV(ANDROID_LOG_INFO, format, list);
  va_end(list);
}

void LogError(const char* format, ...) {
  va_list list;
  va_start(list, format);
  LogPrintV(ANDROID_LOG_ERROR, format, list);
  va_end(list);
}

// Get the JNI environment.
JNIEnv* GetJniEnv() {
  JavaVM* vm = g_app_state->activity->vm;
  JNIEnv* env;
  jint result = vm->AttachCurrentThread(&env, nullptr);
  return result == JNI_OK ? env : nullptr;
}

// Returns the temporary directory path.
const char* GetTemporaryDirectoryPath() {
  if (!g_temporary_directory.empty()) {
    return g_temporary_directory.c_str();
  }

  JNIEnv* env = GetJniEnv();
  jclass native_activity_class = env->FindClass("android/app/NativeActivity");
  CheckAndClearJniExceptions(env);
  jmethodID get_cache_dir_method = env->GetMethodID(
      native_activity_class, "getCacheDir", "()Ljava/io/File;");
  CheckAndClearJniExceptions(env);
  jobject cache_dir =
      env->CallObjectMethod(GetActivity(), get_cache_dir_method);
  CheckAndClearJniExceptions(env);
  jclass file_class = env->FindClass("java/io/File");
  CheckAndClearJniExceptions(env);
  jmethodID get_path_method =
      env->GetMethodID(file_class, "getPath", "()Ljava/lang/String;");
  CheckAndClearJniExceptions(env);
  jstring cache_dir_path_string =
      (jstring)env->CallObjectMethod(cache_dir, get_path_method);
  CheckAndClearJniExceptions(env);

  const char* cache_dir_path =
      env->GetStringUTFChars(cache_dir_path_string, NULL);
  CheckAndClearJniExceptions(env);
  g_temporary_directory.assign(cache_dir_path);
  env->ReleaseStringUTFChars(cache_dir_path_string, cache_dir_path);
  CheckAndClearJniExceptions(env);
  return g_temporary_directory.c_str();
}

// Execute common_main(), flush pending events and finish the activity.
extern "C" void android_main(struct android_app* state) {
  // native_app_glue spawns a new thread, calling android_main() when the
  // activity onStart() or onRestart() methods are called.  This code handles
  // the case where we're re-entering this method on a different thread by
  // signalling the existing thread to exit, waiting for it to complete before
  // reinitializing the application.
  if (g_started) {
    g_restarted = true;
    // Wait for the existing thread to exit.
    pthread_mutex_lock(&g_started_mutex);
    pthread_mutex_unlock(&g_started_mutex);
  } else {
    g_started_mutex = PTHREAD_MUTEX_INITIALIZER;
  }
  pthread_mutex_lock(&g_started_mutex);
  g_started = true;

  // Save native app glue state and setup a callback to track the state.
  g_destroy_requested = false;
  g_app_state = state;
  g_app_state->onAppCmd = OnAppCmd;

  // Create the logging display.
  g_logging_utils_data = new LoggingUtilsData();
  g_logging_utils_data->Init();

  // Execute cross platform entry point.
  static const char* argv[] = {APP_FRAMEWORK_TESTAPP_NAME};
  int return_value = common_main(1, argv);
  (void)return_value;  // Ignore the return value.
  ProcessEvents(10);

  // Clean up logging display.
  delete g_logging_utils_data;
  g_logging_utils_data = nullptr;

  // Finish the activity.
  if (!g_restarted) ANativeActivity_finish(state->activity);

  g_app_state->activity->vm->DetachCurrentThread();
  g_started = false;
  g_restarted = false;
  pthread_mutex_unlock(&g_started_mutex);
}
