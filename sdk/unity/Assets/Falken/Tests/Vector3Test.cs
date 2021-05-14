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
    public class Vector3Test
    {
        [Test]
        public void ConstructEmpty()
        {
            var eulerAngles = new Falken.Vector3();
            Assert.AreEqual(0.0f, eulerAngles.X);
            Assert.AreEqual(0.0f, eulerAngles.Y);
            Assert.AreEqual(0.0f, eulerAngles.Z);
        }

        [Test]
        public void ConstructFromAngles()
        {
            var eulerAngles = new Falken.Vector3(1.0f, 2.0f, 3.0f);
            Assert.AreEqual(1.0f, eulerAngles.X);
            Assert.AreEqual(2.0f, eulerAngles.Y);
            Assert.AreEqual(3.0f, eulerAngles.Z);
        }
    }
}

