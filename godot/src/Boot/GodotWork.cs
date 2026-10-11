using System;
using System.Diagnostics;
using System.Threading;

namespace Launcher.App.Boot;

/// <summary>
/// Background work that calls into Godot (a model parsed and converted, a video decoded into images, a thumbnail made),
/// counted so the app can wait for it as it quits. The engine shuts down right after the scene tree goes, and a worker
/// still calling into it then brings the process down (an access violation in the interop, at any of its calls).
/// <para>
/// A job calls <see cref="TryEnter"/> before its first Godot call and <see cref="Exit"/> after its last; once the app
/// is quitting, <see cref="TryEnter"/> refuses, so a job queued but not started never begins. A long-lived worker (a
/// video's decoding thread) holds it for its whole run and stops when it sees <see cref="Quitting"/>. As the app quits,
/// <c>Main</c>'s <c>_ExitTree</c> calls <see cref="Quit"/>, which waits for the jobs still running.
/// </para>
/// </summary>
public static class GodotWork
{
    private static readonly object Gate = new();
    private static int _running;
    private static volatile bool _quitting;

    /// <summary>True once the app has started quitting: a long-lived worker stops.</summary>
    public static bool Quitting => _quitting;

    /// <summary>Any thread: true if the job may call into Godot (and must <see cref="Exit"/>); false once the app is quitting.</summary>
    public static bool TryEnter()
    {
        lock (Gate)
        {
            if (_quitting)
            {
                return false;
            }

            _running++;
            return true;
        }
    }

    /// <summary>Any thread: the job is done with Godot.</summary>
    public static void Exit()
    {
        lock (Gate)
        {
            _running--;
            if (_running == 0)
            {
                Monitor.PulseAll(Gate);
            }
        }
    }

    /// <summary>
    /// Main thread, as the app quits: refuses new jobs and waits up to <paramref name="timeout"/> for the running ones.
    /// Returns how many were still running when it gave up (0 when all finished).
    /// </summary>
    public static int Quit(TimeSpan timeout)
    {
        var clock = Stopwatch.StartNew();
        lock (Gate)
        {
            _quitting = true;
            while (_running > 0)
            {
                var left = timeout - clock.Elapsed;
                if (left <= TimeSpan.Zero)
                {
                    return _running;
                }

                Monitor.Wait(Gate, left);
            }

            return 0;
        }
    }
}
