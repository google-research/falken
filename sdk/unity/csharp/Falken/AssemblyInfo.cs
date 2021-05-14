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

// Assembly information for the Falken assembly.
using System.Reflection;
using System.Runtime.CompilerServices;

// Information about this assembly is defined by the following attributes.
// Change them to the values specific to your project.
[assembly: AssemblyTitle("Falken")]
[assembly: AssemblyDescription("Falken SDK")]
[assembly: AssemblyConfiguration("")]
[assembly: AssemblyCompany("Google Inc.")]
[assembly: AssemblyProduct("")]
[assembly: AssemblyCopyright("Copyright 2020")]
[assembly: AssemblyTrademark("")]
[assembly: AssemblyCulture("")]

// This intentionally does *not* track the SDK version. This makes it possible
// to replace a Falken assembly when upgrading to a new version of the SDK
// without having to recompile all dependent assemblies.
[assembly: AssemblyVersion("1.0.0.0")]

// Uses internal methods for testing purposes
[assembly: InternalsVisibleTo("Falken.Tests")]
