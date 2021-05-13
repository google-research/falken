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

using System.IO;
using System.Reflection;

namespace Staff {

    /// <summary>
    /// Class that says goodbye from a file.
    /// </summary>
    public static class GreeterFromResource {

        /// <summary>
        /// Returns a goodbye message.
        /// </summary>
        public static string Goodbye() {
            return File.ReadAllText(
              Path.Combine(
                Path.GetDirectoryName(Assembly.GetAssembly(typeof(GreeterFromResource)).Location),
                "goodbye.txt")).Trim();
        }
    }
}


