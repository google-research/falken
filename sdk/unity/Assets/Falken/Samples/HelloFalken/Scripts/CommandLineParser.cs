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

﻿using System;
﻿using System.Collections;
using System.Collections.Generic;
using UnityEngine;

// Class for parsing data from the command line or a string specified during
// class construction.
//
// For example, we can parse sessionType, brain, snapshot, episode, so one can
// specify in the command line or the Unity Editor commandLineArguments:
//
//  -sessionType EVALUATION -brain 8c1ec42b-77f1-42ba-9ca7-074323adfdd7 \
//  -snapshot 1ea671e1-87fb-4982-8259-261cf7bb1ad0 episode 10
//
// to run an evaluation session with the specified brain ID and snapshot ID for
// 10 episodes.
public class CommandLineParser
{
    private string commandLineArguments = "";

    public CommandLineParser(string commandLineArgs)
    {
        commandLineArguments = commandLineArgs;
    }

    private string[] GetCommandLineArgs()
    {
        string[] args;
        if (!String.IsNullOrEmpty(commandLineArguments))
        {
            args = commandLineArguments.Split(" \t".ToCharArray());
        }
        else
        {
            args = Environment.GetCommandLineArgs();
        }
        return args;
    }

    private string GetArg(string argName, string defaultValue = null)
    {
        string[] args = GetCommandLineArgs();
        for (int i = 0; i < args.Length; i++)
        {
            bool matchesName = (args[i] == argName) ||
                                (args[i] == "--" + argName) ||
                                (args[i] == "-" + argName);
            if (matchesName && args.Length > i + 1)
            {
                Debug.Log("Command line argument " + argName +
                            " found with value " + args[i + 1]);
                return args[i + 1].Trim();
            }
        }
        return defaultValue;
    }

    // Specify the session type (Inference, Evaluation, InteractiveTraining)
    // from command line by passing "--sessionType INFERENCE" or the such.
    public Falken.Session.Type SessionType
    {
        get
        {
            switch (GetArg("sessionType"))
            {
                case "INFERENCE":
                    return Falken.Session.Type.Inference;
                case "EVALUATION":
                    return Falken.Session.Type.Evaluation;
                default:
                    return Falken.Session.Type.InteractiveTraining;
            }
        }
    }

    public string BrainId
    {
        get
        {
            return GetArg("brain");
        }
    }

    public string SnapshotId
    {
        get
        {
            return GetArg("snapshot");
        }
    }

    public int EpisodesRequested
    {
        get
        {
            if (int.TryParse(GetArg("episodes"), out var numEpisodesRequested))
            {
                return numEpisodesRequested;
            }
            return 0;
        }
    }
}
