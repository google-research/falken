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
using System.IO;
using System.Diagnostics;
using NUnit.Framework;

/// <summary>
/// Tests HelloMain.
/// </summary>
public class HelloMainTest {

    /// <summary>
    /// Launch HelloMain capture the output and make sure it's friendly.
    /// </summary>
    [Test]
    public void LaunchHelloMain() {
        using (var process = Process.Start(new ProcessStartInfo() {
                    FileName = Path.Combine(Directory.GetCurrentDirectory(), "HelloMain.exe")
                    ,RedirectStandardOutput = true,
                    UseShellExecute = false,
                })) {
            var output = process.StandardOutput.ReadToEnd();
            process.WaitForExit();
            Assert.AreEqual(0, process.ExitCode);
            Assert.AreEqual("Hello World\n" +
                            "Hi Chuck\n" +
                            "Au revoir Patty\n" +
                            "The answer is 42\n",
                            output);
        }
    }
}
