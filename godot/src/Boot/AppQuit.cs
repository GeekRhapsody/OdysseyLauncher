using System;
using Godot;

namespace Launcher.App.Boot;

/// <summary>
/// The app's own ways of quitting (the power menu, a bench or capture ending, <c>--quit-after-launch</c>) go through
/// here, so the main scene can free its GPU memory before the process ends (POC, streamed layer pool: the Deck's AMD
/// driver has bugchecked seconds after the app quit a heavy run, while it cleaned up the process's GPU memory).
/// </summary>
public static class AppQuit
{
    private static Action<int>? _handler;

    /// <summary>Main thread: who quits gracefully; null (headless, or the main scene gone) quits at once.</summary>
    public static void SetHandler(Action<int>? handler) => _handler = handler;

    /// <summary>Main thread: quits with the exit code, through the handler when there is one.</summary>
    public static void Request(SceneTree tree, int exitCode = 0)
    {
        if (_handler is { } handler)
        {
            handler(exitCode);
        }
        else
        {
            tree.Quit(exitCode);
        }
    }
}
