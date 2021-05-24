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
using System.Collections.Generic;
using System.IO;
using NUnit.Framework;

// Do not warn about missing documentation.
#pragma warning disable 1591

namespace FalkenTests
{
    public class LogTest
    {
        Falken.LogLevel logLevel;
        string logFilename;

        [SetUp]
        public void Setup()
        {
            logLevel = Falken.Log.Level;
            logFilename = Falken.Log.Filename;
        }

        [TearDown]
        public void TearDown()
        {
            Falken.Log.Level = logLevel;
            Falken.Log.Filename = logFilename;
        }

        [Test]
        public void FromInternalLogLevel()
        {
            Assert.AreEqual(
                Falken.Log.FromInternalLogLevel(FalkenInternal.falken.LogLevel.kLogLevelDebug),
                Falken.LogLevel.Debug);
            Assert.AreEqual(
                Falken.Log.FromInternalLogLevel(FalkenInternal.falken.LogLevel.kLogLevelVerbose),
                Falken.LogLevel.Verbose);
            Assert.AreEqual(
                Falken.Log.FromInternalLogLevel(FalkenInternal.falken.LogLevel.kLogLevelInfo),
                Falken.LogLevel.Info);
            Assert.AreEqual(
                Falken.Log.FromInternalLogLevel(FalkenInternal.falken.LogLevel.kLogLevelWarning),
                Falken.LogLevel.Warning);
            Assert.AreEqual(
                Falken.Log.FromInternalLogLevel(FalkenInternal.falken.LogLevel.kLogLevelError),
                Falken.LogLevel.Error);
            Assert.AreEqual(
                Falken.Log.FromInternalLogLevel(FalkenInternal.falken.LogLevel.kLogLevelFatal),
                Falken.LogLevel.Fatal);
        }

        [Test]
        public void ToInternalLogLevel()
        {
            Assert.AreEqual(
                Falken.Log.ToInternalLogLevel(Falken.LogLevel.Debug),
                FalkenInternal.falken.LogLevel.kLogLevelDebug);
            Assert.AreEqual(
                Falken.Log.ToInternalLogLevel(Falken.LogLevel.Verbose),
                FalkenInternal.falken.LogLevel.kLogLevelVerbose);
            Assert.AreEqual(
                Falken.Log.ToInternalLogLevel(Falken.LogLevel.Info),
                FalkenInternal.falken.LogLevel.kLogLevelInfo);
            Assert.AreEqual(
                Falken.Log.ToInternalLogLevel(Falken.LogLevel.Warning),
                FalkenInternal.falken.LogLevel.kLogLevelWarning);
            Assert.AreEqual(
                Falken.Log.ToInternalLogLevel(Falken.LogLevel.Error),
                FalkenInternal.falken.LogLevel.kLogLevelError);
            Assert.AreEqual(
                Falken.Log.ToInternalLogLevel(Falken.LogLevel.Fatal),
                FalkenInternal.falken.LogLevel.kLogLevelFatal);
        }

        [Test]
        public void LogToFile()
        {
            Assert.IsFalse(String.IsNullOrEmpty(logFilename));
            Assert.IsTrue(File.Exists(logFilename));
            var tempPath = Path.GetTempPath();
#if UNITY_5_3_OR_NEWER && UNITY_ASSERTIONS
            tempPath = UnityEngine.Application.temporaryCachePath;
#endif  // UNITY_5_3_OR_NEWER && UNITY_ASSERTIONS
            var newLogFilename = Path.Combine(tempPath, "falken_log.txt");
            try
            {
                Falken.Log.Filename = newLogFilename;
                Falken.Log.Level = Falken.LogLevel.Info;
                Assert.AreEqual(newLogFilename, Falken.Log.Filename);
                Assert.AreEqual(Falken.LogLevel.Info, Falken.Log.Level);
                // Make sure everything is written to the log file regardless of Log.Level.
                Falken.Log.Debug("Hello");
                // Close the log file so it can be read.
                Falken.Log.Filename = null;
                Assert.AreEqual(File.ReadAllText(newLogFilename).Trim(), "[Falken] DEBUG: Hello");
            }
            finally
            {
                if (File.Exists(newLogFilename))
                {
                    File.Delete(newLogFilename);
                }
            }
        }

        [Test]
        public void Debug()
        {
            Falken.Log.Level = Falken.LogLevel.Debug;
            Falken.Log.Debug("debug");
#if UNITY_5_3_OR_NEWER && UNITY_ASSERTIONS
            UnityEngine.TestTools.LogAssert.Expect(UnityEngine.LogType.Log, "debug");
#endif  // UNITY_5_3_OR_NEWER && UNITY_ASSERTIONS
        }

        [Test]
        public void LogVerbose()
        {
            Falken.Log.Level = Falken.LogLevel.Verbose;
            Falken.Log.Verbose("verbose");
#if UNITY_5_3_OR_NEWER && UNITY_ASSERTIONS
            UnityEngine.TestTools.LogAssert.Expect(UnityEngine.LogType.Log, "verbose");
#endif  // UNITY_5_3_OR_NEWER && UNITY_ASSERTIONS
        }

        [Test]
        public void LogInfo()
        {
            Falken.Log.Level = Falken.LogLevel.Info;
            Falken.Log.Info("info");
#if UNITY_5_3_OR_NEWER && UNITY_ASSERTIONS
            UnityEngine.TestTools.LogAssert.Expect(UnityEngine.LogType.Log, "info");
#endif  // UNITY_5_3_OR_NEWER && UNITY_ASSERTIONS
        }

        [Test]
        public void LogWarning()
        {
            Falken.Log.Level = Falken.LogLevel.Warning;
            Falken.Log.Warning("warning");
#if UNITY_5_3_OR_NEWER && UNITY_ASSERTIONS
            UnityEngine.TestTools.LogAssert.Expect(UnityEngine.LogType.Warning, "warning");
#endif  // UNITY_5_3_OR_NEWER && UNITY_ASSERTIONS
        }

        [Test]
        public void LogError()
        {
            Falken.Log.Level = Falken.LogLevel.Error;
            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Falken.Log.Error("error");
            }
#if UNITY_5_3_OR_NEWER && UNITY_ASSERTIONS
            UnityEngine.TestTools.LogAssert.Expect(UnityEngine.LogType.Error, "error");
#endif  // UNITY_5_3_OR_NEWER && UNITY_ASSERTIONS
        }

        [Test]
        public void LogFatal()
        {
            Falken.Log.Level = Falken.LogLevel.Fatal;
            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Assert.That(() => Falken.Log.Fatal("fatal"),
                            Throws.TypeOf<ApplicationException>());
            }
#if UNITY_5_3_OR_NEWER && UNITY_ASSERTIONS
            UnityEngine.TestTools.LogAssert.Expect(UnityEngine.LogType.Error, "fatal");
#endif  // UNITY_5_3_OR_NEWER && UNITY_ASSERTIONS
        }

        [Test]
        public void NotifyOnLog()
        {
            Falken.Log.MessageArgs notification = null;
            System.EventHandler<Falken.Log.MessageArgs> handler = (object source,
                                                                   Falken.Log.MessageArgs args) =>
            {
                notification = args;
            };
            Falken.Log.OnMessage += handler;
            try
            {
                Falken.Log.Level = Falken.LogLevel.Info;
                // All log messages should be forwarded.
                Falken.Log.Debug("debug");
                Assert.IsNotNull(notification);
                Assert.AreEqual(notification.LogLevel, Falken.LogLevel.Debug);
                Assert.AreEqual(notification.Message, "debug");
            }
            finally
            {
                Falken.Log.OnMessage -= handler;
            }
        }

        [Test]
        public void ExceptionInNotifyOnLog()
        {
            System.EventHandler<Falken.Log.MessageArgs> handler = (object source,
                                                                   Falken.Log.MessageArgs args) =>
            {
                throw new FormatException("Bad log format string");
            };
            Falken.Log.OnMessage += handler;
            try
            {
                Assert.That(() => Falken.Log.Debug("debug"), Throws.TypeOf<FormatException>());
            }
            finally
            {
                Falken.Log.OnMessage -= handler;
            }
        }
    }
}
