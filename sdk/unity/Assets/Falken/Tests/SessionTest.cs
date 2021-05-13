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
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using NUnit.Framework;

// Do not warn about missing documentation.
#pragma warning disable 1591

namespace FalkenTests
{
    public class SessionTest
    {

        [Test]
        public void FromInternalSessionType()
        {
            Falken.Session.Type type =
              Falken.Session.FromInternalType(FalkenInternal.falken.Session.Type.kTypeInvalid);
            Assert.AreEqual(Falken.Session.Type.Invalid, type);
            type =
              Falken.Session.FromInternalType(
                  FalkenInternal.falken.Session.Type.kTypeInteractiveTraining);
            Assert.AreEqual(Falken.Session.Type.InteractiveTraining, type);
            type =
              Falken.Session.FromInternalType(FalkenInternal.falken.Session.Type.kTypeInference);
            Assert.AreEqual(Falken.Session.Type.Inference, type);
            type =
              Falken.Session.FromInternalType(FalkenInternal.falken.Session.Type.kTypeEvaluation);
            Assert.AreEqual(Falken.Session.Type.Evaluation, type);
        }

        [Test]
        public void ToInternalSessionType()
        {
            FalkenInternal.falken.Session.Type type =
              Falken.Session.ToInternalType(Falken.Session.Type.Invalid);
            Assert.AreEqual(FalkenInternal.falken.Session.Type.kTypeInvalid, type);
            type =
              Falken.Session.ToInternalType(Falken.Session.Type.InteractiveTraining);
            Assert.AreEqual(FalkenInternal.falken.Session.Type.kTypeInteractiveTraining, type);
            type =
              Falken.Session.ToInternalType(Falken.Session.Type.Inference);
            Assert.AreEqual(FalkenInternal.falken.Session.Type.kTypeInference, type);
            type =
              Falken.Session.ToInternalType(Falken.Session.Type.Evaluation);
            Assert.AreEqual(FalkenInternal.falken.Session.Type.kTypeEvaluation, type);
        }
    }
}
