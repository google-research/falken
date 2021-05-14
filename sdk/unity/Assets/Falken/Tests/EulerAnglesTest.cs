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

// Do not warn about missing documentation.
#pragma warning disable 1591

namespace FalkenTests
{
    public class EulerAnglesTest
    {
        [Test]
        public void ConstructEmpty()
        {
            var eulerAngles = new Falken.EulerAngles();
            Assert.AreEqual(0.0f, eulerAngles.Roll);
            Assert.AreEqual(0.0f, eulerAngles.Pitch);
            Assert.AreEqual(0.0f, eulerAngles.Yaw);
        }

        [Test]
        public void ConstructFromAngles()
        {
            var eulerAngles = new Falken.EulerAngles(90.0f, 120.0f, 180.0f);
            Assert.AreEqual(90.0f, eulerAngles.Roll);
            Assert.AreEqual(120.0f, eulerAngles.Pitch);
            Assert.AreEqual(180.0f, eulerAngles.Yaw);
        }
    }
}
