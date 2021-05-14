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

using NUnit.Framework;

/// <summary>
/// Test GreeterFromResource and GreeterFromTheVoid.
/// </summary>
public class GreeterWithDependenciesTest {

    /// <summary>
    /// Ensure Goodbye() is understood.
    /// </summary>
    [Test]
    public void Goodbye() {
        Assert.AreEqual("Au revoir Patty", Staff.GreeterFromResource.Goodbye());
    }

    /// <summary>
    /// Check the meaning of everything.
    /// </summary>
    [Test]
    public void Explain() {
        Assert.AreEqual("The answer is 42", Staff.GreeterFromTheVoid.Explain());
    }
}
