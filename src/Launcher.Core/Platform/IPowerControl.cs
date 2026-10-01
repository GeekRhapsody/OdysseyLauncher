namespace Launcher.Core.Platform;

/// <summary>What the power menu can ask the operating system for. Quitting the app isn't one: Godot does that.</summary>
public enum PowerAction
{
    Restart,
    ShutDown,
    Sleep,
}

/// <summary>
/// Restarts, shuts down or sleeps the computer, for the power menu (View in the grids). <see cref="Request"/> can
/// block (sleep returns once the computer wakes), so it's called on a worker thread.
/// </summary>
public interface IPowerControl
{
    /// <summary>Null when <paramref name="action"/> can be asked for here; otherwise why not, for the menu to say.</summary>
    string? Unavailable(PowerAction action);

    /// <summary>
    /// Asks for <paramref name="action"/>: null once the system has accepted it, otherwise what went wrong. A restart
    /// or shutdown returns at once, and the system then closes every app; sleep returns after the computer wakes.
    /// </summary>
    string? Request(PowerAction action);
}

/// <summary>Linux, until it's worth doing: nothing is available.</summary>
public sealed class NullPowerControl : IPowerControl
{
    public static NullPowerControl Instance { get; } = new();

    public string? Unavailable(PowerAction action) => "Not available on this platform yet.";

    public string? Request(PowerAction action) => Unavailable(action);
}
