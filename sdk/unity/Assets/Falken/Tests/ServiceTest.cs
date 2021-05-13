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
using System.IO;
using System.Reflection;
using System.Threading;
using NUnit.Framework;

using BaseBrainSpec = Falken.BrainSpec<Falken.ObservationsBase, Falken.ActionsBase>;
using FeelerBrainSpec = Falken.BrainSpec<FalkenTests.FalkenObservationsWithFeelerTest,
                                         FalkenTests.FalkenExampleActions>;
using TestBrainSpec =
    Falken.BrainSpec<FalkenTests.FalkenExampleObservations, FalkenTests.FalkenExampleActions>;
using TestTemplateBrainSpec =
    Falken.BrainSpec<FalkenTests.TestObservation, FalkenTests.TestActions>;

// Do not warn about missing documentation.
#pragma warning disable 1591

namespace FalkenTests
{
#if NUNIT_3 || UNITY_5_3_OR_NEWER
    using TestContext = NUnit.Framework.TestContext;
#else
  using TestContext = NUnit.Core.TestContext;
#endif

    /// <summary>
    /// Entity that emulates a player for testing purposes.
    /// </summary>
    public class TestEntity : Falken.EntityBase
    {
        [Falken.Range(0.0f, 3.0f)]
        public float health;
    }

    /// <summary>
    /// Observation class used for testing.
    /// </summary>
    public class TestObservation : Falken.ObservationsBase
    {
        public TestObservation()
        {
            // Initialization of player field of the base.
            player = new TestEntity();
        }
    }

    /// <summary>
    /// Action class used for testing.
    /// </summary>
    public class TestActions : Falken.ActionsBase
    {
        [Falken.Range(5.0f, 10.0f)]
        public float speed = 5.0f;
    }

    public class ServiceTest
    {
        private const string _kBrainName = "test_brain";

        // Constant to set the float threshold for comparing.
        private const float _kDelta = 1e-5f;

        // Threshold to consider actions as equal.
        private const float _kDeltaMaxAverageError = 0.15f;

        private uint _kMaxStepsPerEpisode = 2;

        [TearDown]
        public void TearDown()
        {
            // Wait for all objects to be garbage collected between test cases to
            // make it easier to attribute failures to specific cases.
            GC.Collect();
            GC.WaitForPendingFinalizers();
        }

        /// <summary>
        /// This method emulates the training data process. It assigns values
        /// to the Actions and Observations.
        /// </summary>
        /// <param name="spec">BrainSpec with data to be trained.</param>
        /// <param name="stepIndex">Current step of the episode.</param>
        /// <param name="numberOfStepsPerEpisode">Amount of steps per episode.</param>
        /// <param name="provideAction">If true, it also provides actions to the BrainSpec.</param>
        /// <returns>Value assigned to speed action.</returns>
        public float TrainingData(TestTemplateBrainSpec spec, int stepIndex,
          int numberOfStepsPerEpisode, bool provideAction = true)
        {
            // Linearly map observations to actions across the session.
            float phase = (float)(stepIndex) / (float)(numberOfStepsPerEpisode);
            float inversePhase = 1.0f - phase;

            // Cast the health to an attribute so it is possible get its maximum and minimum.
            var healthAttribute = spec.Observations.player["health"] as Falken.Number;
            // Assign a value to the health taking into account the current phase.
            var player = ((TestEntity)spec.Observations.player);
            player.health = healthAttribute.Minimum +
                (healthAttribute.Maximum - healthAttribute.Minimum) * inversePhase;
            // Empty position and rotation.
            player.position = new Falken.PositionVector(0.0f);
            player.rotation = new Falken.RotationQuaternion(0.0f);

            // Cast the speed to an attribute so it is possible get its maximum and minimum.
            var speedAttribute = spec.Actions["speed"] as Falken.Number;

            float trainingSpeedValue = speedAttribute.Minimum +
                (speedAttribute.Maximum - speedAttribute.Minimum) * (phase);

            if (provideAction)
            {
                // Assign a value to the speed taking into account the current phase.
                spec.Actions.speed = trainingSpeedValue;
            }
            return trainingSpeedValue;
        }

        /// <summary>
        /// Wait for training to advance to a valid state so that when the session is
        /// closed a snapshot can be generated.
        /// </summary>
        /// <param name="session">Training session.</param>
        /// <param name="brain">Brain which data is going to be trained.</param>
        /// <param name="completionThreshold">How far to train the brain.</param>
        void WaitForTrainingToComplete(
            Falken.Session session,
            Falken.Brain<TestTemplateBrainSpec> brain,
            float completionThreshold=0.0f)
        {
            float maxTrainingProgress = 0.0f;
            const int kTrainingPollIntervalMilliseconds = 1000;
            int timeout = 200 * kTrainingPollIntervalMilliseconds;
            while (timeout > 0 && maxTrainingProgress < completionThreshold)
            {
                // Submit empty episodes with no training data to poll the training state.
                Falken.Episode episode = session.StartEpisode();
                Assert.IsNotNull(episode);
                // We need to submit at least one step to workaround the service returning
                // an error.
                TrainingData(brain.BrainSpec, 0, 1);
                brain.BrainSpec.Actions.ActionsSource = Falken.ActionsBase.Source.None;
                TestContext.Out.WriteLine("Submitting dummy episode.");
                Assert.IsTrue(episode.Step());
                Assert.IsTrue(episode.Complete(Falken.Episode.CompletionState.Aborted));
                if (maxTrainingProgress < session.SessionTrainingProgress)
                {
                  maxTrainingProgress = session.SessionTrainingProgress;
                }
                TestContext.Out.WriteLine(
                    $"Training progress is {session.SessionTrainingProgress * 100}%");
                Thread.Sleep(kTrainingPollIntervalMilliseconds);
                timeout -= kTrainingPollIntervalMilliseconds;
                if (timeout <= 0)
                {
                    TestContext.Out.WriteLine("Timed out while waiting for training to complete.");
                }
            }
            Assert.IsTrue(maxTrainingProgress > 0.0);
            Assert.IsTrue(maxTrainingProgress <= 1.0);
        }


        /// <summary>
        /// Simulates a train session by training the data as much as training steps are provided.
        /// </summary>
        /// <param name="session">Training session.</param>
        /// <param name="brain"> Brain which data is going to be trained.</param>
        /// <param name="numberOfEpisodes"> Amount of episodes of the session.</param>
        /// <param name="numberOfStepsPerEpisode">Steps per episode for the session.</param>
        /// <param name="completionThreshold">How far to train the brain..</param>
        void TrainSession(Falken.Session session,
                          Falken.Brain<TestTemplateBrainSpec> brain,
                          int numberOfEpisodes, int numberOfStepsPerEpisode,
                          float completionThreshold = 0.0f)
        {
            // Train with some generated data.
            for (int ep = 0; ep < numberOfEpisodes; ++ep)
            {
                Falken.Episode episode = session.StartEpisode();
                Assert.IsNotNull(episode);
                for (int st = 0; st < numberOfStepsPerEpisode; ++st)
                {
                    // Train data for a new episode.
                    TrainingData(brain.BrainSpec, st, numberOfStepsPerEpisode);
                    Assert.IsTrue(episode.Step());
                }
                Assert.IsTrue(episode.Complete(
                    Falken.Episode.CompletionState.Success));
            }

            if (completionThreshold > 0.0)
            {
                WaitForTrainingToComplete(session, brain, completionThreshold);
            }
        }

        /// <summary>
        /// Runs the inference mode by providing observations to the brain.
        /// </summary>
        /// <param name="session">Inference session.</param>
        /// <param name="brain">Brain which data is going to be trained.</param>
        /// <param name="numberOfEpisodes">Amount of episodes of the session.</param>
        /// <param name="numberOfStepsPerEpisode">Steps per episode for the session.</param>
        /// <returns>Minimum average error of the training session.</returns>
        float RunInference(Falken.Session session,
                          Falken.Brain<TestTemplateBrainSpec> brain,
                          int numberOfEpisodes, int numberOfStepsPerEpisode)
        {
            int steps = 0;
            float minimumAverageError = Single.MaxValue;
            for (int ep = 0; ep < numberOfEpisodes; ++ep)
            {
                float totalErrorEpisode = 0.0f;

                Falken.Episode episode = session.StartEpisode();
                DateTime before = DateTime.Now;
                for (int step = 0; step < numberOfStepsPerEpisode; ++step)
                {
                    // Provide observations
                    float expectedAction = TrainingData(brain.BrainSpec, step,
                        numberOfStepsPerEpisode, false);
                    // Step the episode.
                    Assert.IsTrue(episode.Step());
                    ++steps;
                    // Store the inferred action.
                    float trainedAction = brain.BrainSpec.Actions.speed;
                    // Calculate the error.
                    totalErrorEpisode += Math.Abs(trainedAction - expectedAction);
                }
                DateTime after = DateTime.Now;
                double time_stepping = (double)(after - before).Milliseconds;
                Assert.IsTrue(episode.Complete(Falken.Episode.CompletionState.Success));
                TestContext.Out.WriteLine(
                  $"Performed {steps} step calls in {time_stepping}ms (excluding time spent in " +
                  "Complete() calls).\n" +
                  $"Overall speed: {((steps / time_stepping) * 1000.0d).ToString("0.##")}" +
                  " steps per second.");
                // Calculate average error of the episode.
                float averageErrorEpisode = totalErrorEpisode / numberOfStepsPerEpisode;

                // Keep track of the minimum average error.
                minimumAverageError = Math.Min(averageErrorEpisode, minimumAverageError);

                // Check that the inferred actions are below the acceptance error.
                Assert.LessOrEqual(minimumAverageError, _kDeltaMaxAverageError);
                // Test NaN explicity because comparison may not detect it
                Assert.IsFalse(System.Single.IsNaN(minimumAverageError));
            }
            return minimumAverageError;
        }

        /// <summary>
        /// Steps the evaluation session until it finishes. It also test that the eval session
        /// identifies the first model (the snapshot) to be the chosen model of the
        /// evaluation session. </summary>
        /// <param name="session">Evaluation session</param>
        /// <param name="brain">Brain which data is going to be trained.</param>
        /// <param name="numberOfEpisodes">Amount of episodes of the session.</param>
        /// <param name="numberOfStepsPerEpisode">Steps per episode for the session.</param>
        /// <param name="passingEpisodeAverageError">Minimum average error initially required to
        /// indicate a successful episode.</param>
        /// <returns>Minimum average error of the session.</returns>
        float RunEvaluation(Falken.Session session,
                            Falken.Brain<TestTemplateBrainSpec> brain,
                            int numberOfEpisodes, int numberOfStepsPerEpisode,
                            float passingEpisodeAverageError)
        {
            float minimumAverageError = passingEpisodeAverageError;
            SortedDictionary<float, int> errorOccurrence = new SortedDictionary<float, int>();
            for (int ep = 0; ep < numberOfEpisodes; ++ep)
            {
                float totalErrorEpisode = 0.0f;

                Falken.Episode episode = session.StartEpisode();
                Assert.IsNotNull(episode);
                Assert.AreNotEqual(Falken.Session.TrainingState.Invalid,
                                   session.SessionTrainingState);
                // Submit empty episodes with no training data to poll the training state.
                for (int step = 0; step < numberOfStepsPerEpisode; ++step)
                {
                    // Provide observations and step.
                    float expectedAction = TrainingData(brain.BrainSpec, step,
                      numberOfStepsPerEpisode, false);
                    Assert.IsTrue(episode.Step());

                    // Store the inferred action.
                    float trainedAction = brain.BrainSpec.Actions.speed;

                    // Calculate the error.
                    totalErrorEpisode += Math.Abs(trainedAction - expectedAction);
                }

                // Calculate average error of the episode.
                float averageErrorEpisode = totalErrorEpisode / numberOfStepsPerEpisode;

                // Add the error calculated to the occurrence dictionary.
                if (errorOccurrence.ContainsKey(averageErrorEpisode))
                {
                    ++errorOccurrence[averageErrorEpisode];
                }
                else
                {
                    errorOccurrence.Add(averageErrorEpisode, 1);
                }

                // Keep track of the minimum average error.
                minimumAverageError = Math.Min(averageErrorEpisode, minimumAverageError);

                // Check that the inferred actions are below the acceptance error.
                Falken.Episode.CompletionState completionState;
                if (averageErrorEpisode <= minimumAverageError)
                {
                    completionState = Falken.Episode.CompletionState.Success;
                }
                else
                {
                    completionState = Falken.Episode.CompletionState.Failure;
                }
                TestContext.Out.WriteLine(
                  $"Completing episode {ep} as {completionState}: " +
                  $"Average error per step {averageErrorEpisode}, current minimum " +
                  $"average error per step {minimumAverageError}");
                Assert.IsTrue(episode.Complete(completionState));
            }
            // Print out the occurrence of the error
            TestContext.Out.WriteLine("Average error occurrence after evaluation: ");
            foreach (var it in errorOccurrence)
            {
                TestContext.Out.WriteLine($"{it.Value}  episode[s] with error {it.Key}");
            }

            return minimumAverageError;
        }

        [Test]
        public void CreateService()
        {

            Assert.DoesNotThrow(() =>
            {
                var service = Falken.Service.Connect(null, null, null);
                Assert.IsNotNull(service);
            });
        }

        [Test]
        public void CreateBrainBase()
        {
            Falken.Service service = Falken.Service.Connect(
              null, null, null);
            Assert.IsNotNull(service);
            Falken.BrainSpecBase brainSpecBase =
              new Falken.BrainSpecBase(
                new FalkenExampleActions(), new FalkenExampleObservations());
            Falken.BrainBase brain =
              service.CreateBrain(_kBrainName, brainSpecBase);
            Falken.ActionsBase actions = brain.BrainSpecBase.ActionsBase;
            Assert.AreEqual(7, actions.Count);
            Assert.IsTrue(actions.ContainsKey("lookUpAngle"));
            Assert.IsTrue(actions.ContainsKey("jump"));
            Assert.IsTrue(actions.ContainsKey("weapon"));
            Assert.IsTrue(actions.ContainsKey("joystick"));
            Assert.IsTrue(actions.ContainsKey("numberAttribute"));
            Assert.IsTrue(actions.ContainsKey("categoryAttribute"));
            Assert.IsTrue(actions.ContainsKey("booleanAttribute"));

            Falken.ObservationsBase observations =
              brain.BrainSpecBase.ObservationsBase;
            Assert.AreEqual(2, observations.Count);
            Assert.IsTrue(observations.ContainsKey("player"));
            Assert.IsTrue(observations.ContainsKey("enemy"));
            Assert.IsTrue(observations["enemy"].ContainsKey("lookUpAngle"));
            Assert.IsTrue(observations["enemy"].ContainsKey("shoot"));
            Assert.IsTrue(observations["enemy"].ContainsKey("energy"));
            Assert.IsTrue(observations["enemy"].ContainsKey("weapon"));
        }

        [Test]
        public void CreateBrain()
        {
            Falken.Service service = Falken.Service.Connect(
              null, null, null);
            Assert.IsNotNull(service);
            Falken.Brain<TestBrainSpec> brain =
              service.CreateBrain<TestBrainSpec>(_kBrainName);

            FalkenExampleActions actions =
              (FalkenExampleActions)brain.BrainSpec.Actions;
            Assert.AreEqual(7, actions.Count);
            Assert.IsTrue(actions.ContainsKey("lookUpAngle"));
            Assert.IsTrue(actions.ContainsKey("jump"));
            Assert.IsTrue(actions.ContainsKey("weapon"));
            Assert.IsTrue(actions.ContainsKey("joystick"));
            Assert.IsTrue(actions.ContainsKey("numberAttribute"));
            Assert.IsTrue(actions.ContainsKey("categoryAttribute"));
            Assert.IsTrue(actions.ContainsKey("booleanAttribute"));

            FalkenExampleObservations observations =
              (FalkenExampleObservations)brain.BrainSpec.Observations;
            Assert.AreEqual(2, observations.Count);
            Assert.IsTrue(observations.ContainsKey("player"));
            Assert.IsTrue(observations.ContainsKey("enemy"));
            Assert.IsTrue(observations["enemy"].ContainsKey("lookUpAngle"));
            Assert.IsTrue(observations["enemy"].ContainsKey("shoot"));
            Assert.IsTrue(observations["enemy"].ContainsKey("energy"));
            Assert.IsTrue(observations["enemy"].ContainsKey("weapon"));
            Assert.IsTrue(observations["enemy"].ContainsKey("numberAttribute"));
            Assert.IsTrue(observations["enemy"].ContainsKey("categoryAttribute"));
            Assert.IsTrue(observations["enemy"].ContainsKey("booleanAttribute"));
        }

        [Test]
        public void CreateBrainUsingTypes()
        {
            Falken.Service service = Falken.Service.Connect(
              null, null, null);
            Assert.IsNotNull(service);
            Falken.Brain<TestBrainSpec> brain =
              service.CreateBrain<TestBrainSpec>(
                _kBrainName, typeof(FalkenExtendedExampleObservations),
                typeof(FalkenExtendedExampleActions));

            FalkenExtendedExampleActions actions =
              (FalkenExtendedExampleActions)brain.BrainSpec.Actions;
            Assert.AreEqual(8, actions.Count);
            Assert.IsTrue(actions.ContainsKey("lookUpAngle"));
            Assert.IsTrue(actions.ContainsKey("jump"));
            Assert.IsTrue(actions.ContainsKey("weapon"));
            Assert.IsTrue(actions.ContainsKey("joystick"));
            Assert.IsTrue(actions.ContainsKey("numberAttribute"));
            Assert.IsTrue(actions.ContainsKey("categoryAttribute"));
            Assert.IsTrue(actions.ContainsKey("booleanAttribute"));
            Assert.IsTrue(actions.ContainsKey("steering"));
            FalkenExtendedExampleObservations observations =
              (FalkenExtendedExampleObservations)brain.BrainSpec.Observations;
            Assert.AreEqual(3, observations.Count);
            Assert.IsTrue(observations.ContainsKey("player"));
            Assert.IsTrue(observations.ContainsKey("enemy"));
            Assert.IsTrue(observations["enemy"].ContainsKey("lookUpAngle"));
            Assert.IsTrue(observations["enemy"].ContainsKey("shoot"));
            Assert.IsTrue(observations["enemy"].ContainsKey("energy"));
            Assert.IsTrue(observations["enemy"].ContainsKey("weapon"));
            Assert.IsTrue(observations["enemy"].ContainsKey("numberAttribute"));
            Assert.IsTrue(observations["enemy"].ContainsKey("categoryAttribute"));
            Assert.IsTrue(observations["enemy"].ContainsKey("booleanAttribute"));
            Assert.IsTrue(observations.ContainsKey("enemy2"));
            Assert.IsTrue(observations["enemy2"].ContainsKey("lookUpAngle"));
            Assert.IsTrue(observations["enemy2"].ContainsKey("shoot"));
            Assert.IsTrue(observations["enemy2"].ContainsKey("energy"));
            Assert.IsTrue(observations["enemy2"].ContainsKey("weapon"));
            Assert.IsTrue(observations["enemy2"].ContainsKey("numberAttribute"));
            Assert.IsTrue(observations["enemy2"].ContainsKey("categoryAttribute"));
            Assert.IsTrue(observations["enemy2"].ContainsKey("booleanAttribute"));
        }

        [Test]
        public void CreateBrainUsingWrongTypes()
        {
            Falken.Service service = Falken.Service.Connect(
              null, null, null);
            Assert.IsNotNull(service);
            // See
            //https://docs.microsoft.com/en-us/dotnet/api/system.activator.createinstance?view=netcore-3.1
            // to understand why this exception is thrown.
            Assert.That(() => service.CreateBrain<TestBrainSpec>(_kBrainName,
                                                                 typeof(Falken.ObservationsBase),
                                                                 typeof(Falken.ActionsBase)),
                        Throws.TypeOf<TargetInvocationException>());
        }

        [Test]
        public void CreateBrainEmptyActions()
        {
            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Falken.Service service = Falken.Service.Connect(null, null, null);
                Assert.That(() => service.CreateBrain<BaseBrainSpec>(_kBrainName),
                            Throws.TypeOf<InvalidOperationException>()
                            .With.Message.EqualTo("Brain could not be created. Ensure that " +
                                                  "you have more than one attribute created " +
                                                  "for actions."));
            }
        }

        [Test]
        public void CreateBrainNullBrainSpec()
        {
            Falken.Service service = Falken.Service.Connect(null, null, null);
            Assert.IsNotNull(service);
            Assert.That(() => service.CreateBrain(_kBrainName, null),
                        Throws.TypeOf<ArgumentNullException>());
        }

        [Test]
        public void CreateBrainNullName()
        {
            Falken.Service service = Falken.Service.Connect(null, null, null);
            Assert.IsNotNull(service);
            Assert.That(() => service.CreateBrain<TestBrainSpec>(null),
                        Throws.TypeOf<ArgumentNullException>());
        }

        [Test]
        public void CreateBrainEmptyName()
        {
            Falken.Service service = Falken.Service.Connect(null, null, null);
            Assert.IsNotNull(service);
            Assert.That(() => service.CreateBrain<TestBrainSpec>(""),
                        Throws.TypeOf<ArgumentNullException>());
        }

        [Test]
        public void LoadBrain()
        {
            Falken.Service service = Falken.Service.Connect(null, null, null);
            Assert.IsNotNull(service);
            string brainId;
            // Create and destroy the brain so that when we call LoadBrain we actually load
            // it from the service.
            using (var brain = service.CreateBrain<TestBrainSpec>(_kBrainName))
            {
                brainId = brain.Id;
            }
            Falken.Brain<BaseBrainSpec> loadedBrain = service.LoadBrain<BaseBrainSpec>(brainId);

            Falken.ActionsBase actions = loadedBrain.BrainSpec.Actions;
            Assert.IsTrue(actions.Bound);
            Assert.AreEqual(7, actions.Count);
            Assert.IsTrue(actions.ContainsKey("lookUpAngle"));
            Assert.IsTrue(actions.ContainsKey("jump"));
            Assert.IsTrue(actions.ContainsKey("weapon"));
            Assert.IsTrue(actions.ContainsKey("joystick"));
            Assert.IsTrue(actions.ContainsKey("numberAttribute"));
            Assert.IsTrue(actions.ContainsKey("categoryAttribute"));
            Assert.IsTrue(actions.ContainsKey("booleanAttribute"));
            Assert.IsTrue(actions["lookUpAngle"] is Falken.Number);
            Assert.IsTrue(actions["jump"] is Falken.Boolean);
            Assert.IsTrue(actions["weapon"] is Falken.Category);
            Assert.IsTrue(actions["joystick"] is Falken.Joystick);
            Assert.IsTrue(actions["numberAttribute"] is Falken.Number);
            Assert.IsTrue(actions["categoryAttribute"] is Falken.Category);
            Assert.IsTrue(actions["booleanAttribute"] is Falken.Boolean);

            Falken.ObservationsBase observations = loadedBrain.BrainSpec.Observations;
            Assert.IsTrue(observations.Bound);
            Assert.AreEqual(2, observations.Count);
            Assert.IsTrue(observations.ContainsKey("player"));
            Assert.IsTrue(observations.ContainsKey("entity_0"));
        }

        [Test]
        public void LoadBrainWithFeeler()
        {
            Falken.Service service = Falken.Service.Connect(
              null, null, null);
            Assert.IsNotNull(service);
            Assert.DoesNotThrow(() =>
            {
                var brain = service.CreateBrain<FeelerBrainSpec>(_kBrainName);
                var loadedBrain = service.LoadBrain<FeelerBrainSpec>(brain.Id);
            });
        }

        [Test]
        public void LoadBrainWithTypes()
        {
            Falken.Service service = Falken.Service.Connect(
              null, null, null);
            Assert.IsNotNull(service);
            var brain =
              service.CreateBrain<Falken.BrainSpec<FalkenExtendedExampleObservations,
                FalkenExtendedExampleActions>>(
                  _kBrainName);
            var loadedBrain =
              service.LoadBrain<TestBrainSpec>(
                brain.Id, typeof(FalkenExtendedExampleObservations),
                typeof(FalkenExtendedExampleActions));

            FalkenExtendedExampleActions actions =
              (FalkenExtendedExampleActions)loadedBrain.BrainSpec.Actions;
            Assert.IsTrue(actions.Bound);
            Assert.AreEqual(8, actions.Count);
            Assert.IsTrue(actions.ContainsKey("lookUpAngle"));
            Assert.IsTrue(actions.ContainsKey("jump"));
            Assert.IsTrue(actions.ContainsKey("weapon"));
            Assert.IsTrue(actions.ContainsKey("joystick"));
            Assert.IsTrue(actions.ContainsKey("steering"));
            Assert.IsTrue(actions.ContainsKey("numberAttribute"));
            Assert.IsTrue(actions.ContainsKey("categoryAttribute"));
            Assert.IsTrue(actions.ContainsKey("booleanAttribute"));
            Assert.IsTrue(actions["lookUpAngle"] is Falken.Number);
            Assert.IsTrue(actions["jump"] is Falken.Boolean);
            Assert.IsTrue(actions["weapon"] is Falken.Category);
            Assert.IsTrue(actions["joystick"] is Falken.Joystick);
            Assert.IsTrue(actions["steering"] is Falken.Number);
            Assert.IsTrue(actions["numberAttribute"] is Falken.Number);
            Assert.IsTrue(actions["categoryAttribute"] is Falken.Category);
            Assert.IsTrue(actions["booleanAttribute"] is Falken.Boolean);

            FalkenExtendedExampleObservations observations =
              (FalkenExtendedExampleObservations)loadedBrain.BrainSpec.Observations;
            Assert.IsTrue(observations.Bound);
            Assert.AreEqual(3, observations.Count);
            Assert.IsTrue(observations.ContainsKey("player"));
            Assert.IsTrue(observations.ContainsKey("enemy"));
            Assert.IsTrue(observations.ContainsKey("enemy2"));
        }

        [Test]
        public void LoadGenericBrain()
        {
            Falken.Service service = Falken.Service.Connect(
              null, null, null);
            Assert.IsNotNull(service);
            Falken.Brain<TestBrainSpec> brain =
              service.CreateBrain<TestBrainSpec>(_kBrainName);
            Assert.DoesNotThrow(() =>
            {
                var loadedBrain = service.CreateBrain<FeelerBrainSpec>(_kBrainName);
            });
        }

        [Test]
        public void LoadBrainInvalidId()
        {
            Falken.Service service = Falken.Service.Connect(null, null, null);
            Assert.IsNotNull(service);
            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Assert.That(() => service.LoadBrain<TestBrainSpec>("nonexistentId"),
                            Throws.TypeOf<InvalidOperationException>());
            }
        }

        [Test]
        public void LoadBrainNullId()
        {
            Falken.Service service = Falken.Service.Connect(null, null, null);
            Assert.IsNotNull(service);
            Assert.That(() => service.LoadBrain<TestBrainSpec>(null),
                        Throws.TypeOf<ArgumentNullException>());
        }

        public sealed class OtherActionSet : Falken.ActionsBase
        {
            public bool jump = false;
        }

        [Test]
        public void LoadGenericBrainWrongActions()
        {
            Falken.Service service = Falken.Service.Connect(
              null, null, null);
            Assert.IsNotNull(service);
            Falken.Brain<TestBrainSpec> brain =
              service.CreateBrain<TestBrainSpec>(_kBrainName);
            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Assert.That(() => service.LoadBrain<Falken.BrainSpec<FalkenExampleObservations,
                                                                     OtherActionSet>>(brain.Id),
                            Throws.TypeOf<InvalidOperationException>()
                            .With.Message.EqualTo($"Could not load brain with id '{brain.Id}' " +
                                                  "because the actions or observations " +
                                                  "do not match."));
            }
        }

        public sealed class OtherObservationSet : Falken.ObservationsBase
        {
            public OtherObservationSet()
            {
                player = new SimpleExampleEntity();
            }
            public EnemyExampleEntity enemy = new EnemyExampleEntity();
            public EnemyExampleEntity anotherEnemy = new EnemyExampleEntity();
        }

        [Test]
        public void LoadGenericBrainWrongObservations()
        {
            Falken.Service service = Falken.Service.Connect(
              null, null, null);
            Assert.IsNotNull(service);
            Falken.Brain<TestBrainSpec> brain = service.CreateBrain<TestBrainSpec>(_kBrainName);
            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Assert.That(() => service.LoadBrain<Falken.BrainSpec<
                                    OtherObservationSet, FalkenExampleActions>>(brain.Id),
                            Throws.TypeOf<InvalidOperationException>()
                            .With.Message.EqualTo($"Could not load brain with id '{brain.Id}' " +
                                                  "because the actions or observations do not " +
                                                  "match."));
            }
        }

        [Test]
        public void StartSessionInvalid()
        {
            Falken.Service service = Falken.Service.Connect(
              null, null, null);
            Assert.IsNotNull(service);
            Falken.Brain<TestBrainSpec> brain = service.CreateBrain<TestBrainSpec>(_kBrainName);
            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Assert.That(() => brain.StartSession(Falken.Session.Type.Invalid,
                            _kMaxStepsPerEpisode), Throws.TypeOf<InvalidOperationException>());
            }
        }

        [Test]
        public void StartSessionInteractiveTraining()
        {
            Falken.Service service = Falken.Service.Connect(
              null, null, null);
            Assert.IsNotNull(service);
            Falken.Brain<TestBrainSpec> brain = service.CreateBrain<TestBrainSpec>(_kBrainName);
            Falken.Session session = brain.StartSession(
              Falken.Session.Type.InteractiveTraining, _kMaxStepsPerEpisode);
            Assert.IsNotNull(session);
        }

        [Test]
        public void GetSessionInfo()
        {
            Falken.Service service = Falken.Service.Connect(
              null, null, null);
            Assert.IsNotNull(service);
            Falken.Brain<TestBrainSpec> brain = service.CreateBrain<TestBrainSpec>(_kBrainName);
            Falken.Session session = brain.StartSession(
              Falken.Session.Type.InteractiveTraining, _kMaxStepsPerEpisode);
            Assert.IsNotNull(session);
            Assert.IsFalse(String.IsNullOrEmpty(session.Info));
        }

        /// <summary>
        /// This test checks the behavior of a inference session. A training session and an
        /// evaluation session needs to be executed first.
        /// </summary>
        [Test]
        public void StartSessionInference()
        {
            // Amount of episodes of the training session.
            const int kTrainEpisodes = 20;

            // Amount of episodes of the inference session.
            const int kInferenceEpisodes = 1;

            // Amount of episodes for the inferences.
            const int kMaxStepsPerEpisode = 100;

            // Connect to the Falken service and checks if the connection was successful.
            Falken.Service service = Falken.Service.Connect(
              null, null, null);
            Assert.IsNotNull(service);

            // Create a brain.
            Falken.Brain<TestTemplateBrainSpec> brain =
              service.CreateBrain<TestTemplateBrainSpec>(_kBrainName);
            Assert.IsNotNull(brain);
            Assert.IsFalse(String.IsNullOrEmpty(brain.Id));

            // This session trains the brain.
            Falken.Session trainSession = brain.StartSession(
              Falken.Session.Type.InteractiveTraining, kMaxStepsPerEpisode);
            Assert.IsNotNull(trainSession);
            TrainSession(trainSession, brain, kTrainEpisodes, kMaxStepsPerEpisode, 0.2f);
            trainSession.Stop();

            // Start a new session for executing inference.
            Falken.Session inferenceSession = brain.StartSession(
              Falken.Session.Type.Inference, kMaxStepsPerEpisode);
            Assert.IsNotNull(inferenceSession);
            RunInference(inferenceSession, brain,
              kInferenceEpisodes, kMaxStepsPerEpisode);
        }

        [Test]
        public void StartSessionEvaluation()
        {
            // Amount of episodes of the training session.
            const int kTrainEpisodes = 20;

            // Amount of episodes of the inference session.
            const int kInferenceEpisodes = 1;

            // Amount of episodes of the inference session.
            const int kEvaluationEpisodes = 10;

            // Amount of episodes for the inferences.
            const int kMaxStepsPerEpisode = 100;

            Falken.Service service = Falken.Service.Connect(
              null, null, null);
            Assert.IsNotNull(service);

            // Create and train a brain.
            string brainId;
            string trainingSnapshotId;
            using (var brain = service.CreateBrain<TestTemplateBrainSpec>(_kBrainName))
            {
                Assert.IsNotNull(brain);
                Assert.IsFalse(String.IsNullOrEmpty(brain.Id));
                brainId = brain.Id;

                // This session trains the brain.
                Falken.Session trainSession = brain.StartSession(
                  Falken.Session.Type.InteractiveTraining, kMaxStepsPerEpisode);
                Assert.IsNotNull(trainSession);
                TrainSession(trainSession, brain, kTrainEpisodes, kMaxStepsPerEpisode, 0.2f);
                trainingSnapshotId = trainSession.Stop();
                Assert.IsFalse(String.IsNullOrEmpty(trainingSnapshotId));
            }

            // Perform inference with the trained brain to calculate the average error per step.
            float baselineError;
            using (var brain = service.LoadBrain<TestTemplateBrainSpec>(brainId,
                                                                        trainingSnapshotId))
            {
                // Start a new inference session.
                Falken.Session inferenceSession = brain.StartSession(
                  Falken.Session.Type.Inference, kMaxStepsPerEpisode);
                Assert.IsNotNull(inferenceSession);
                baselineError = RunInference(inferenceSession, brain, kInferenceEpisodes,
                                             kMaxStepsPerEpisode);
                TestContext.Out.WriteLine("Inference session returned baseline average error " +
                                          $"per step of {baselineError}");
                string inferenceSnapshotId = inferenceSession.Stop();
                Assert.AreEqual(inferenceSnapshotId, trainingSnapshotId);
            }

            // Run an evaluation session using the trained brain and track the best average
            // error per step.
            float evaluationAverageError;
            string evaluationSnapshotId;
            using (var brain = service.LoadBrain<TestTemplateBrainSpec>(brainId, trainingSnapshotId))
            {
                Falken.Session evaluationSession = brain.StartSession(
                  Falken.Session.Type.Evaluation, kMaxStepsPerEpisode);
                Assert.IsNotNull(evaluationSession);
                evaluationAverageError = RunEvaluation(evaluationSession, brain, kEvaluationEpisodes,
                                                       kMaxStepsPerEpisode, baselineError);
                evaluationSnapshotId = evaluationSession.Stop();
                Assert.IsFalse(String.IsNullOrEmpty(evaluationSnapshotId));
                Assert.IsTrue(evaluationSession.Stopped);
                TestContext.Out.WriteLine("Evaluation session returned a best average error " +
                                          $"per step of {evaluationAverageError}");
            }
            // The error after evaluation session should be equal or lower than running
            // only inferenceSession.
            Assert.LessOrEqual(evaluationAverageError, baselineError);

            // Start a new inference session and make sure the average error per step is the same
            // as the best result of the evaluation session.
            using (var brain = service.LoadBrain<TestTemplateBrainSpec>(brainId,
                                                                        evaluationSnapshotId))
            {
                Falken.Session inferenceSessionPostEvaluation = brain.StartSession(
                  Falken.Session.Type.Inference, kMaxStepsPerEpisode);
                Assert.IsNotNull(inferenceSessionPostEvaluation);
                float postEvalError = RunInference(inferenceSessionPostEvaluation, brain,
                                                   kInferenceEpisodes, kMaxStepsPerEpisode);
                inferenceSessionPostEvaluation.Stop();
                // The error after evaluation session should be equal or lower than running
                // only inference Session.
                Assert.LessOrEqual(postEvalError, baselineError);
            }
        }

        [Test]
        public void GetSessionCount()
        {
            Falken.Service service = Falken.Service.Connect(
              null, null, null);
            Assert.IsNotNull(service);
            Falken.Brain<TestBrainSpec> brain =
              service.CreateBrain<TestBrainSpec>(_kBrainName);
            Assert.AreEqual(0, brain.SessionCount);
            Falken.Session session = brain.StartSession(
              Falken.Session.Type.InteractiveTraining, _kMaxStepsPerEpisode);
            Assert.AreEqual(1, brain.SessionCount);
            session = brain.StartSession(
              Falken.Session.Type.InteractiveTraining, _kMaxStepsPerEpisode);
            Assert.AreEqual(2, brain.SessionCount);
            session = brain.StartSession(
              Falken.Session.Type.InteractiveTraining, _kMaxStepsPerEpisode);
            Assert.AreEqual(3, brain.SessionCount);
            session = brain.StartSession(
              Falken.Session.Type.InteractiveTraining, _kMaxStepsPerEpisode);
            Assert.AreEqual(4, brain.SessionCount);
        }

        [Test]
        public void GetSessionById()
        {
            Falken.Service service = Falken.Service.Connect(
              null, null, null);
            Assert.IsNotNull(service);
            Falken.Brain<TestBrainSpec> brain =
              service.CreateBrain<TestBrainSpec>(_kBrainName);
            Falken.Session session = brain.StartSession(
              Falken.Session.Type.InteractiveTraining, _kMaxStepsPerEpisode);
            Falken.Session sessionById = brain.GetSession(session.Id);
            Assert.IsNotNull(sessionById);
            Assert.AreEqual(sessionById.Id, session.Id);
        }

        [Test]
        public void StopSession()
        {
            Falken.Service service = Falken.Service.Connect(
              null, null, null);
            Assert.IsNotNull(service);
            Falken.Brain<TestBrainSpec> brain = service.CreateBrain<TestBrainSpec>(_kBrainName);
            Falken.Session session = brain.StartSession(
              Falken.Session.Type.InteractiveTraining, _kMaxStepsPerEpisode);
            Assert.IsFalse(session.Stopped);
            Assert.AreEqual("", session.Stop());
            Assert.IsTrue(session.Stopped);
        }

        [Test]
        public void StartEpisode()
        {
            Falken.Service service = Falken.Service.Connect(
              null, null, null);
            Assert.IsNotNull(service);
            Falken.Brain<TestBrainSpec> brain = service.CreateBrain<TestBrainSpec>(_kBrainName);
            Falken.Session session = brain.StartSession(
              Falken.Session.Type.InteractiveTraining, _kMaxStepsPerEpisode);
            Falken.Episode episode = session.StartEpisode();
            Assert.IsNotNull(episode);
            // Should fail as the episode is empty.
            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Assert.IsFalse(episode.Complete(Falken.Episode.CompletionState.Aborted));
            }
        }

        [Test]
        public void StepEpisode()
        {
            Falken.Service service = Falken.Service.Connect(
              null, null, null);
            Assert.IsNotNull(service);
            Falken.Brain<TestBrainSpec> brain = service.CreateBrain<TestBrainSpec>(_kBrainName);
            Falken.Session session = brain.StartSession(
              Falken.Session.Type.InteractiveTraining, _kMaxStepsPerEpisode);
            Falken.Episode episode = session.StartEpisode();
            Assert.IsTrue(episode.Step());
            Assert.IsTrue(episode.Step(3.0f));
            Assert.IsFalse(episode.Step());
            Assert.IsTrue(episode.Completed);
        }

        [Test]
        public void CompleteEpisode()
        {
            Falken.Service service = Falken.Service.Connect(
              null, null, null);
            Assert.IsNotNull(service);
            Falken.Brain<TestBrainSpec> brain = service.CreateBrain<TestBrainSpec>(_kBrainName);
            Falken.Session session = brain.StartSession(
              Falken.Session.Type.InteractiveTraining, _kMaxStepsPerEpisode);
            Falken.Episode episode = session.StartEpisode();
            Assert.IsTrue(episode.Step());
            Assert.IsTrue(episode.Complete(Falken.Episode.CompletionState.Success));
            Assert.IsTrue(episode.Completed);
        }

        /// <summary>
        /// This test executes a training session and checks all the information retrieved.
        /// </summary>
        [Test]
        public void ReadSession()
        {
            // Amount of episodes of the session.
            const int kEpisodes = 5;
            // Amount of steps per episode.
            const int kStepsPerEpisode = 10;

            // Connect to the Falken service and checks if the connection was successful.
            Falken.Service service = Falken.Service.Connect(null, null, null);
            Assert.IsNotNull(service);

            // Check if a brain can be created.
            Falken.Brain<TestTemplateBrainSpec> brain =
              service.CreateBrain<TestTemplateBrainSpec>(_kBrainName);
            Assert.IsNotNull(brain);

            // Check if a training session can be created.
            Falken.Session trainingSession = brain.StartSession(
              Falken.Session.Type.InteractiveTraining, kStepsPerEpisode);
            Assert.IsNotNull(trainingSession);

            // Simulate a training session.
            TrainSession(trainingSession, brain, kEpisodes, kStepsPerEpisode);
            var trainingSessionId = trainingSession.Id;
            trainingSession.Stop();
            // After executing the session, retrieves information about it and check its status.
            Falken.Session inspectSession = brain.GetSession(trainingSessionId);
            // StartEpisode must fail after finishing the training.
            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Assert.That(() => inspectSession.StartEpisode(),
                            Throws.TypeOf<InvalidOperationException>());
            }

            Assert.IsTrue(inspectSession.Stopped);

            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Assert.AreEqual(inspectSession.Stop(), "");
            }

            Assert.AreSame(brain, inspectSession.BrainBase);
            Assert.AreEqual(trainingSessionId, inspectSession.Id);
            Assert.AreEqual(Falken.Session.Type.InteractiveTraining, inspectSession.SessionType);
            Assert.AreEqual(Falken.Session.TrainingState.Training,
                            inspectSession.SessionTrainingState);
            Assert.AreEqual(kEpisodes, inspectSession.EpisodeCount);

            // Inspect all the episodes
            for (int ep = 0; ep < kEpisodes; ++ep)
            {
                Falken.Episode episode = inspectSession.GetEpisode(ep);
                Assert.IsNotNull(episode);

                using (var ignoreErrorMessages = new IgnoreErrorMessages())
                {
                    Assert.IsFalse(episode.Step());
                    Assert.IsFalse(episode.Step(1.0f));
                }

                Assert.IsTrue(episode.Completed);

                using (var ignoreErrorMessages = new IgnoreErrorMessages())
                {
                    Assert.IsFalse(episode.Complete(Falken.Episode.CompletionState.Failure));
                }

                Assert.AreEqual(kStepsPerEpisode, episode.StepCount, _kDelta);

                // Inspect all the steps of each episode.
                for (int st = 0; st < kStepsPerEpisode; ++st)
                {
                    // Create an Expected brain to compare it agains the generated one.
                    Falken.Brain<TestTemplateBrainSpec> expectedBrain =
                      service.CreateBrain<TestTemplateBrainSpec>(_kBrainName);
                    TrainingData(expectedBrain.BrainSpec, st, kStepsPerEpisode);

                    Assert.IsTrue(episode.ReadStep(st));
                    Assert.AreEqual(episode.Reward, 0.0f, _kDelta);
                    Assert.AreEqual((
                        (TestEntity)expectedBrain.BrainSpec.Observations.player).health,
                        ((TestEntity)brain.BrainSpec.Observations.player).health);
                    Assert.AreEqual(expectedBrain.BrainSpec.Actions.speed,
                                    brain.BrainSpec.Actions.speed, _kDelta);
                }
                // Read out of range steps.
                using (var ignoreErrorMessages = new IgnoreErrorMessages())
                {
                    Assert.IsFalse(episode.ReadStep(-1));
                    Assert.IsFalse(episode.ReadStep(kStepsPerEpisode));
                }
            }
            // Try getting an out of range episode.
            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
                Assert.IsNull(inspectSession.GetEpisode(-1));
                Assert.IsNull(inspectSession.GetEpisode(kEpisodes));
            }
        }

        /// <summary>
        /// Start multiple episodes and step them simultaneously.
        /// </summary>
        [Test]
        public void TrainWithInterleavedEpisodes()
        {
            // Amount of episodes of the session.
            const int kEpisodes = 5;
            // Amount of steps per episode.
            const int kStepsPerEpisode = 10;

            // Function that generates step index based on the episode number. This allows to train
            // each episode with different data between them.
            Func<int, int, int> calculateEpisodeStepIndex =
              (int step, int episode) => { return (step + episode) % kStepsPerEpisode; };

            Falken.Service service = Falken.Service.Connect(
              null, null, null);
            Assert.IsNotNull(service);
            Falken.Brain<TestTemplateBrainSpec> brain =
              service.CreateBrain<TestTemplateBrainSpec>(_kBrainName);
            Falken.Session trainSession = brain.StartSession(
              Falken.Session.Type.InteractiveTraining, kStepsPerEpisode);

            // Create episodes.
            List<Falken.Episode> episodes = new List<Falken.Episode>();
            for (int ep = 0; ep < kEpisodes; ++ep)
            {
                episodes.Add(trainSession.StartEpisode());
                Assert.IsNotNull(episodes[ep]);
            }

            // Populate episodes by interleaving training data.
            for (int ep = 0; ep < kEpisodes; ++ep)
            {
                for (int st = 0; st < kStepsPerEpisode; ++st)
                {
                    // Train data and step.
                    TrainingData(brain.BrainSpec, calculateEpisodeStepIndex(st, ep),
                                 kStepsPerEpisode);
                    episodes[ep].Step();
                }
            }

            // Complete episodes.
            for (int ep = 0; ep < kEpisodes; ++ep)
            {
                Assert.IsTrue(episodes[ep].Complete(Falken.Episode.CompletionState.Success));
            }
            var trainingSnapshotId = trainSession.Stop();

            // Fetch session data and make sure all episodes are populated as expected.
            var inspectSession = brain.GetSession(trainSession.Id);
            for (int ep = 0; ep < kEpisodes; ++ep)
            {
                var episode = inspectSession.GetEpisode(ep);
                for (int st = 0; st < kStepsPerEpisode; ++st)
                {
                    // Create an Expected brain to compare it agains the generated one.
                    Falken.Brain<TestTemplateBrainSpec> expectedBrain =
                      service.CreateBrain<TestTemplateBrainSpec>(_kBrainName);

                    // Train data for expected episode.
                    TrainingData(expectedBrain.BrainSpec, calculateEpisodeStepIndex(st, ep),
                      kStepsPerEpisode);

                    // Get episode and compare against the expected one.
                    Assert.IsTrue(episode.ReadStep(st));
                    Assert.AreEqual(episode.Reward, 0.0f, _kDelta);
                    Assert.AreEqual(
                      ((TestEntity)expectedBrain.BrainSpec.Observations.player).health,
                      ((TestEntity)brain.BrainSpec.Observations.player).health);
                    Assert.AreEqual(expectedBrain.BrainSpec.Actions.speed,
                                    brain.BrainSpec.Actions.speed, _kDelta);
                }
            }
        }

        [Test]
        public void TestObservationsAndActionsUnsetLogs()
        {
            Falken.Service service = Falken.Service.Connect(
              null, null, null);
            Assert.IsNotNull(service);
            Falken.Brain<TestBrainSpec> brain = service.CreateBrain<TestBrainSpec>(_kBrainName);
            var actions =
              (FalkenExampleActions)brain.BrainSpec.Actions;
            var observations =
              (FalkenExampleObservations)brain.BrainSpec.Observations;
            Falken.Session session = brain.StartSession(
              Falken.Session.Type.InteractiveTraining, 5);
            Falken.Episode episode = session.StartEpisode();

            var recovered_logs = new List<String>();
            System.EventHandler<Falken.Log.MessageArgs> handler = (
                object source, Falken.Log.MessageArgs args) =>
            {
                recovered_logs.Add(args.Message);
            };
            Falken.Log.OnMessage += handler;

            var expected_logs = new List<String>() {
                "Attributes [booleanAttribute, categoryAttribute, energy, lookUpAngle," +
                    " numberAttribute, position, rotation, weapon] of entity enemy" +
                    " are not set. To fix this issue, set attributes to a valid value before" +
                    " stepping an episode.",
                "Attributes [position, rotation] of entity player are not set. To fix this" +
                    " issue, set attributes to a valid value before stepping an episode.",
                "Action data has been partly provided, but the attributes" +
                    " [booleanAttribute, categoryAttribute, joystick/x_axis, joystick/y_axis," +
                    " lookUpAngle, numberAttribute, weapon]" +
                    " have not been set to valid values. To" +
                    " fix this issue, when providing action data set all attributes to valid" +
                    " values before stepping an episode." };
            recovered_logs.Clear();
            actions.ActionsSource = Falken.ActionsBase.Source.HumanDemonstration;

            TestContext.Out.WriteLine("Stepping empty step.");

            Assert.IsTrue(episode.Step());
            Assert.That(recovered_logs, Is.EquivalentTo(expected_logs));

            expected_logs = new List<String>() {
                "Attributes [booleanAttribute, categoryAttribute, energy, numberAttribute," +
                    " position, rotation] of entity enemy" +
                    " are not set. To fix this issue, set attributes to a valid value before" +
                    " stepping an episode.",
                "Attributes [position] of entity player are not set. To fix this" +
                    " issue, set attributes to a valid value before stepping an episode.",
                "Action data has been partly provided, but the attributes" +
                    " [booleanAttribute, categoryAttribute, joystick/y_axis, lookUpAngle," +
                    " numberAttribute, weapon]" +
                    " have not been set to valid values. To" +
                    " fix this issue, when providing action data set all attributes to valid" +
                    " values before stepping an episode." };
            recovered_logs.Clear();
            actions.ActionsSource = Falken.ActionsBase.Source.HumanDemonstration;
            observations.enemy.weapon = 0;
            observations.enemy.lookUpAngle = 0.5f;
            observations.player.rotation = new Falken.RotationQuaternion();
            actions.joystick.X = 0.0f;
            TestContext.Out.WriteLine("Stepping with some values set.");
            Assert.IsTrue(episode.Step());
            Assert.That(recovered_logs, Is.EquivalentTo(expected_logs));

            expected_logs = new List<String>();
            recovered_logs.Clear();
            actions.ActionsSource = Falken.ActionsBase.Source.HumanDemonstration;
            observations.enemy.weapon = 0;
            observations.enemy.lookUpAngle = 0.5f;
            observations.enemy.energy = 3;
            observations.enemy.booleanAttribute.Value = true;
            observations.enemy.categoryAttribute.Value = 1;
            observations.enemy.numberAttribute.Value = 0.5f;

            observations.enemy.position = new Falken.PositionVector();
            observations.enemy.rotation = new Falken.RotationQuaternion();
            observations.player.position = new Falken.PositionVector();
            observations.player.rotation = new Falken.RotationQuaternion();

            actions.joystick.X = 0.0f;
            actions.joystick.Y = 0.0f;
            actions.weapon = 0;
            actions.lookUpAngle = 0.0f;
            actions.booleanAttribute.Value = true;
            actions.categoryAttribute.Value = 1;
            actions.numberAttribute.Value = 0.5f;

            TestContext.Out.WriteLine("Stepping again with all values set.");
            Assert.IsTrue(episode.Step());
            
            Assert.That(recovered_logs, Is.EquivalentTo(expected_logs));

            expected_logs = new List<String>() {
                "Attributes [booleanAttribute, categoryAttribute, energy, lookUpAngle," +
                    " numberAttribute, position, rotation, weapon] of entity enemy" +
                    " are not set. To fix this issue, set attributes to a valid value before" +
                    " stepping an episode.",
                "Attributes [position, rotation] of entity player are not set. To fix this" +
                    " issue, set attributes to a valid value before stepping an episode.",
                "Action data has been partly provided, but the attributes" +
                    " [booleanAttribute, categoryAttribute, joystick/x_axis, joystick/y_axis," +
                    " lookUpAngle, numberAttribute, weapon]" +
                    " have not been set to valid values. To" +
                    " fix this issue, when providing action data set all attributes to valid" +
                    " values before stepping an episode." };
            recovered_logs.Clear();
            actions.ActionsSource = Falken.ActionsBase.Source.HumanDemonstration;
            TestContext.Out.WriteLine("Stepping again with some values set.");
            Assert.IsTrue(episode.Step());
            Assert.That(recovered_logs, Is.EquivalentTo(expected_logs));

            Assert.IsTrue(episode.Complete(Falken.Episode.CompletionState.Success));
            Assert.IsTrue(episode.Completed);
        }

        [Test]
        public void TestActionInvalidation()
        {
            Falken.Service service = Falken.Service.Connect(
              null, null, null);
            Assert.IsNotNull(service);
            Falken.Brain<TestTemplateBrainSpec> brain =
              service.CreateBrain<TestTemplateBrainSpec>(_kBrainName);
            var actions =
              (TestActions)brain.BrainSpec.Actions;
            var observations =
              (TestObservation)brain.BrainSpec.Observations;

            Action setObservationsAndActions = () => {
              actions.speed = 6.0f;
              observations.player.position = new Falken.PositionVector();
              observations.player.rotation = new Falken.RotationQuaternion();
              ((TestEntity)observations.player).health = 1.0f;
            };
            Func<bool> anyObservationsAreInvalid = () => {
              return Single.IsNaN(((TestEntity)observations.player).health)
                  || Single.IsNaN(observations.player.position.X)
                  || Single.IsNaN(observations.player.position.Y)
                  || Single.IsNaN(observations.player.position.Z)
                  || Single.IsNaN(observations.player.rotation.X)
                  || Single.IsNaN(observations.player.rotation.Y)
                  || Single.IsNaN(observations.player.rotation.Z)
                  || Single.IsNaN(observations.player.rotation.W);
            };
            Func<bool> actionsAreInvalid = () => {
              return Single.IsNaN(actions.speed);
            };

            const int trainingEpisodes = 4;
            const int stepsPerEpisode = 2;

            var session = brain.StartSession(
              Falken.Session.Type.InteractiveTraining, stepsPerEpisode);

            TrainSession(session, brain, trainingEpisodes, stepsPerEpisode, 0.01f);

            Falken.Episode episode = session.StartEpisode();

            using (var ignoreErrorMessages = new IgnoreErrorMessages())
            {
              // human action, episodes below limit (cpp step returns true) => invalidation
              setObservationsAndActions();
              actions.ActionsSource = Falken.ActionsBase.Source.HumanDemonstration;
              Assert.IsTrue(episode.Step());
              Assert.IsTrue(actionsAreInvalid());
              Assert.IsTrue(anyObservationsAreInvalid());

              // brain action, episodes below limit (cpp step returns true) => no invalidation
              setObservationsAndActions();
              actions.ActionsSource = Falken.ActionsBase.Source.BrainAction;
              Assert.IsTrue(episode.Step());
              // we need a model
              Assert.IsTrue(actions.ActionsSource == Falken.ActionsBase.Source.BrainAction);
              Assert.IsFalse(actionsAreInvalid());
              Assert.IsTrue(anyObservationsAreInvalid());

              // human action, episodes above limit (cpp step returns false) => invalidation
              setObservationsAndActions();
              actions.ActionsSource = Falken.ActionsBase.Source.HumanDemonstration;
              Assert.IsFalse(episode.Step());
              Assert.IsTrue(actionsAreInvalid());
              Assert.IsTrue(anyObservationsAreInvalid());

              // brain action, episodes above limit (cpp step returns false) => no invalidation
              setObservationsAndActions();
              actions.ActionsSource = Falken.ActionsBase.Source.BrainAction;
              Assert.IsFalse(episode.Step());
              Assert.IsFalse(actionsAreInvalid());
              Assert.IsTrue(anyObservationsAreInvalid());

              Assert.IsTrue(episode.Completed);
            }
        }
    }
}
