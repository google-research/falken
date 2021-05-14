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

using System;

namespace FalkenTests
{
  /// <summary>
  /// Instance this class to ignore error messages.
  /// </summary>
  /// <example>
  /// using (var ignoreErrorMessages = new IgnoreErrorMessages())
  /// {
  ///   // Code that generates error messages.
  /// }
  /// </example>
  public class IgnoreErrorMessages : IDisposable {

    private static int references = 0;
    private bool disposed = false;

    /// <summary>
    /// Start ignoring error messages.
    /// </summary>
    public IgnoreErrorMessages()
    {
      lock (typeof(IgnoreErrorMessages))
      {
        if (references == 0)
        {
#if UNITY_5_3_OR_NEWER
          UnityEngine.TestTools.LogAssert.ignoreFailingMessages = true;
#endif  // UNITY_UNITY_5_3_OR_NEWER
        }
        references++;
      }
    }

    /// <summary>
    /// Stop ignoring error messages.
    /// </summary>
    ~IgnoreErrorMessages()
    {
      Dispose(false);
    }

    /// <summary>
    /// Stop ignoring error messages.
    /// </summary>
    public void Dispose()
    {
      Dispose(true);
    }

    /// <summary>
    /// Stop ignoring error messages.
    /// </summary>
    /// <param name="disposing">Unused.</param>
    protected virtual void Dispose(bool disposing)
    {
      lock (typeof(IgnoreErrorMessages))
      {
        if (!disposed)
        {
          disposed = true;
          if (references > 0)
          {
            references--;
          }
          if (references == 0)
          {
#if UNITY_5_3_OR_NEWER
            UnityEngine.TestTools.LogAssert.ignoreFailingMessages = false;
#endif  // UNITY_UNITY_5_3_OR_NEWER
          }
        }
      }
    }
  }
}
