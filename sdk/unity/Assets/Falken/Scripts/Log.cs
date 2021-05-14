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

#if UNITY_5_3_OR_NEWER
// Use UnityEngine.CoreModule.AOT
#else
namespace AOT
{
    /// <summary>
    /// Implementation of Mono.Util.MonoPInvokeCallbackAttribute
    /// mono/src/mcs/class/System/Mono.Util/MonoPInvokeCallbackAttribute.cs
    /// In the AOT namespace for compatibility with Unity.
    /// This should be applied to methods that are called from unmanaged code so that the ahead of
    /// time compiler doesn't strip them.
    /// </summary>
    [AttributeUsage(AttributeTargets.Method)]
    public class MonoPInvokeCallbackAttribute : Attribute
    {
        /// <summary>
        /// Construct the callback attribute.
        /// </summary>
        public MonoPInvokeCallbackAttribute(Type type) {}
    }
}
#endif  // UNITY_5_3_OR_NEWER

namespace Falken
{
    /// <summary>
    /// Log level of messages.
    /// </summary>
    /// <remarks>
    /// Verbosity of log messages from Debug (most verbose, least important), to Fatal 
    /// (least verbose, most important).
    /// </remarks>
    public enum LogLevel
    {
        /// <summary>
        /// Debug message.
        /// </summary>
        Debug,
        /// <summary>
        /// Verbose message.
        /// </summary>
        Verbose,
        /// <summary>
        /// Informational message.
        /// </summary>
        Info,
        /// <summary>
        /// Warning message.
        /// </summary>
        Warning,
        /// <summary>
        /// Error message.
        /// </summary>
        Error,
        /// <summary>
        /// Fatal message.
        /// </summary>
        Fatal
    }

    /// <summary>
    /// Configures Falken logging.
    /// </summary>
    public class Log
    {
        /// <summary>
        /// Registers for log message callbacks from C/C++ on creation, and unregisters itself when
        /// disposed.
        /// </summary>
        internal class Logger : FalkenInternal.falken.SystemLogger
        {
            // Log callback handle.
            private uint callbackHandle = 0;
            // Delegate that wraps LogMessage().
            private FalkenInternal.falken.LoggerNotifier.LogMessageDelegate logMessageDelegate;
            // Logger singleton.
            private static Logger defaultInstance = null;

            /// <summary>
            /// Register LogMessage as a log callback for the C/C++ layer.
            /// </summary>
            public Logger() : base()
            {
                // Throw C# exceptions instead of aborting the application when a fatal
                // error occurs.
                set_abort_on_fatal_error(false);
                // Call LogMessage when a message is logged.
                logMessageDelegate = LogMessage;
                callbackHandle = GetLoggerNotifier().AddLogCallback(logMessageDelegate,
                                                                    IntPtr.Zero);
                AppDomain.CurrentDomain.DomainUnload += (object sender, EventArgs e) => {
                    Dispose(false);
                };
            }

            /// <summary>
            /// Finalize the logger.
            /// </summary>
            ~Logger()
            {
                Dispose(false);
            }

            /// <summary>
            /// Unregister the logger from the C/C++ layer.
            /// </summary>
            protected override void Dispose(bool disposing)
            {
                if (callbackHandle > 0)
                {
                    GetLoggerNotifier().RemoveLogCallback(callbackHandle);
                    set_abort_on_fatal_error(true);
                    callbackHandle = 0;
                }
                base.Dispose(disposing);
            }

            /// <summary>
            /// Log a message from C/C++.
            /// </summary>
            /// <param name="logLevel">Log level of the message.</param>
            /// <param name="message">Message to log.</param>
            /// <param name="context">Context of the logger (unused).</param>
            [AOT.MonoPInvokeCallback(
                 typeof(FalkenInternal.falken.LoggerNotifier.LogMessageDelegate))]
            private static void LogMessage(
                FalkenInternal.falken.LogLevel logLevel, string message,
                System.IntPtr context)
            {
                // Explicitly keep a reference to logger to prevent GC.
                var logger = DefaultInstance;  
                var loggerBase = logger.GetLoggerBase();
                if (loggerBase != null && logLevel >= loggerBase.log_level())
                {
#if UNITY_5_3_OR_NEWER
                    switch (logLevel)
                    {
                        case FalkenInternal.falken.LogLevel.kLogLevelDebug:
                        case FalkenInternal.falken.LogLevel.kLogLevelVerbose:
                        case FalkenInternal.falken.LogLevel.kLogLevelInfo:
                            UnityEngine.Debug.Log(message);
                            break;
                        case FalkenInternal.falken.LogLevel.kLogLevelWarning:
                            UnityEngine.Debug.LogWarning(message);
                            break;
                        case FalkenInternal.falken.LogLevel.kLogLevelError:
                        case FalkenInternal.falken.LogLevel.kLogLevelFatal:
                            UnityEngine.Debug.LogError(message);
                            break;
                    }
#else
          System.Console.WriteLine(message);
#endif  // UNITY_5_3_OR_NEWER
                }

                Exception logMessageException = null;
                try
                {
                    Falken.Log.NotifyLoggedMessage(logLevel, message);
                }
                catch (Exception exception)
                {
                    // Exceptions can't be thrown in this context as this callback is called
                    // from unmanaged code so instead set the exception as pending on this thread 
                    // if a fatal error didn't occur.
                    logMessageException = exception;
                }

                if (!FalkenInternal.falken_modulePINVOKE.SWIGPendingException.Pending)
                {
                    if (logLevel == FalkenInternal.falken.LogLevel.kLogLevelFatal)
                    {
                        FalkenInternal.falken_modulePINVOKE.SWIGPendingException.Set(
                            new ApplicationException(message));
                    }
                    else if (logMessageException != null)
                    {
                        FalkenInternal.falken_modulePINVOKE.SWIGPendingException.Set(
                            logMessageException);
                    }
                }

            }

            /// <summary>
            /// Get the logger.
            /// </summary>
            internal static Logger DefaultInstance
            {
                get
                {
                    lock (typeof(Logger))
                    {
                        if (defaultInstance == null)
                        {
                            // The P/Invoke module creates a logger on construction so firstly
                            // force construction of the module by creating a SystemLogger proxy.
                            using (var systemLogger = new FalkenInternal.falken.SystemLogger())
                            {
                                // If the P/Invoke module constructor is called, defaultInstance
                                // will be set.
                                if (defaultInstance == null)
                                {
                                    defaultInstance = new Logger();
                                }
                            }
                        }
                        return defaultInstance;
                    }
                }
            }
        }

        /// <summary>
        /// Initialize the log class.
        /// </summary>
        static Log()
        {
            // Create the logger.
            var logger = Logger.DefaultInstance;
        }

        /// <summary>
        /// Arguments passed to a log event.
        /// </summary>
        public class MessageArgs : System.EventArgs
        {
            /// <summary>
            /// Log level of the message.
            /// </summary>
            public LogLevel LogLevel
            {
                get; set;
            }

            /// <summary>
            /// Log message.
            /// </summary>
            public string Message
            {
                get; set;
            }
        }

        /// <summary>
        /// Event that is notified when messages are logged.
        /// </summary>
        public static event System.EventHandler<MessageArgs> OnMessage;

        /// <summary>
        /// Set / get the log level.
        /// </summary>
        /// <remarks>
        /// All log message below or at the specified log level will be logged.
        /// </remarks>
        public static LogLevel Level
        {
            set
            {
                // Explicitly keep a reference to logger to prevent GC.
                var logger = Logger.DefaultInstance;
                var loggerBase = logger?.GetLoggerBase();
                if (loggerBase != null)
                {
                    loggerBase.set_log_level(ToInternalLogLevel(value));
                }
            }

            get
            {
                // Explicitly keep a reference to logger to prevent GC.
                var logger = Logger.DefaultInstance;
                var loggerBase = logger?.GetLoggerBase();
                return loggerBase != null ? FromInternalLogLevel(loggerBase.log_level()) :
                                            LogLevel.Info;
            }
        }

        /// <summary>
        /// Set / get the log filename.
        /// </summary>
        public static string Filename
        {
            set
            {
                var logger = Logger.DefaultInstance;
                if (logger != null)
                {
                    logger.file_logger().set_filename(value);
                }
            }

            get
            {
                var logger = Logger.DefaultInstance;
                return logger != null ? logger.file_logger().filename() : null;
            }
        }

        /// <summary>
        /// Notify event listeners of a logged message.
        /// </summary>
        /// <param name="logLevel">Internal log level.</param>
        /// <param name="message">Message to log.</param>
        private static void NotifyLoggedMessage(FalkenInternal.falken.LogLevel logLevel,
                                                string message)
        {
            var handler = OnMessage;
            if (handler != null)
            {
                handler(null,
                        new MessageArgs()
                        {
                            LogLevel = FromInternalLogLevel(logLevel),
                            Message = message
                        });
            }
        }

        /// <summary>
        /// Convert from an internal LogLevel to public LogLevel enum.
        /// </summary>
        /// <param name="logLevel">Internal log level to convert.</param>
        /// <returns>Public log level.</returns>
        internal static LogLevel FromInternalLogLevel(FalkenInternal.falken.LogLevel logLevel)
        {
            switch (logLevel)
            {
                case FalkenInternal.falken.LogLevel.kLogLevelDebug:
                    return LogLevel.Debug;
                case FalkenInternal.falken.LogLevel.kLogLevelVerbose:
                    return LogLevel.Verbose;
                case FalkenInternal.falken.LogLevel.kLogLevelInfo:
                    return LogLevel.Info;
                case FalkenInternal.falken.LogLevel.kLogLevelWarning:
                    return LogLevel.Warning;
                case FalkenInternal.falken.LogLevel.kLogLevelError:
                    return LogLevel.Error;
                case FalkenInternal.falken.LogLevel.kLogLevelFatal:
                    return LogLevel.Fatal;
            }
            return LogLevel.Debug;
        }

        /// <summary>
        /// Convert from a public to internal LogLevel.
        /// </summary>
        /// <param name="logLevel">Public log level to convert.</param>
        /// <returns>Internal log level.</returns>
        internal static FalkenInternal.falken.LogLevel ToInternalLogLevel(LogLevel logLevel)
        {
            switch (logLevel)
            {
                case LogLevel.Debug:
                    return FalkenInternal.falken.LogLevel.kLogLevelDebug;
                case LogLevel.Verbose:
                    return FalkenInternal.falken.LogLevel.kLogLevelVerbose;
                case LogLevel.Info:
                    return FalkenInternal.falken.LogLevel.kLogLevelInfo;
                case LogLevel.Warning:
                    return FalkenInternal.falken.LogLevel.kLogLevelWarning;
                case LogLevel.Error:
                    return FalkenInternal.falken.LogLevel.kLogLevelError;
                case LogLevel.Fatal:
                    return FalkenInternal.falken.LogLevel.kLogLevelFatal;
            }
            return FalkenInternal.falken.LogLevel.kLogLevelDebug;
        }

        /// <summary>
        /// Log a message.
        /// </summary>
        /// <param name="logLevel">Log level of the message.</param>
        /// <param name="message">Message to log.</param>
        internal static void LogMessage(LogLevel logLevel, string message)
        {
            // Explicitly keep a reference to logger to prevent GC.
            var logger = Logger.DefaultInstance;
            var loggerBase = logger?.GetLoggerBase();
            if (loggerBase != null)
            {
                loggerBase.Log(ToInternalLogLevel(logLevel), message);
            }
            // If an exception was set on this thread, raise it.
            if (FalkenInternal.falken_modulePINVOKE.SWIGPendingException.Pending)
            {
                throw FalkenInternal.falken_modulePINVOKE.SWIGPendingException.Retrieve();
            }
        }

        /// <summary>
        /// Log a debug message.
        /// </summary>
        /// <param name="message">Message to log.</param>
        internal static void Debug(string message)
        {
            LogMessage(LogLevel.Debug, message);
        }

        /// <summary>
        /// Log a verbose message.
        /// </summary>
        /// <param name="message">Message to log.</param>
        internal static void Verbose(string message)
        {
            LogMessage(LogLevel.Verbose, message);
        }

        /// <summary>
        /// Log an info message.
        /// </summary>
        /// <param name="message">Message to log.</param>
        internal static void Info(string message)
        {
            LogMessage(LogLevel.Info, message);
        }

        /// <summary>
        /// Log a warning message.
        /// </summary>
        /// <param name="message">Message to log.</param>
        internal static void Warning(string message)
        {
            LogMessage(LogLevel.Warning, message);
        }

        /// <summary>
        /// Log an error message.
        /// </summary>
        /// <param name="message">Message to log.</param>
        internal static void Error(string message)
        {
            LogMessage(LogLevel.Error, message);
        }

        /// <summary>
        /// Log a fatal message.
        /// </summary>
        /// <param name="message">Message to log.</param>
        internal static void Fatal(string message)
        {
            LogMessage(LogLevel.Fatal, message);
        }
    }
}
