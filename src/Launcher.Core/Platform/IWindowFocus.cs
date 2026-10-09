namespace Launcher.Core.Platform;

/// <summary>
/// Hands the foreground to an emulator and takes it back afterwards (ARCHITECTURE.md A1, A2). Every method must be
/// called on the thread that owns <c>launcherWindow</c> (Godot's main thread). None of them does I/O or blocks.
/// </summary>
public interface IWindowFocus
{
    /// <summary>
    /// Just after the emulator starts, while the launcher still has the foreground: lets the emulator, and any
    /// process a stub launcher starts, take the foreground.
    /// </summary>
    void BeforeLaunch(nint launcherWindow, int childProcessId);

    /// <summary>True once another process's window is in the foreground (the launcher logs when the emulator took it).</summary>
    bool HasLostForeground(nint launcherWindow);

    /// <summary>After the emulator exits: restores the launcher window if it was minimised and brings it to the foreground.</summary>
    ForegroundResult AfterExit(nint launcherWindow);

    /// <summary>
    /// True while the shell keeps the launcher window hidden (cloaked) even though it's shown. Windows' full screen
    /// experience cloaks the windows behind a full-screen game, and after a boot into it, doesn't uncloak the
    /// launcher when the game ends: the screen stays black until the player switches apps.
    /// </summary>
    bool IsCloaked(nint launcherWindow);

    /// <summary>
    /// Gets the shell to show a cloaked launcher window again (a minimise and restore); the shell may take a moment,
    /// so check <see cref="IsCloaked"/> a little later.
    /// </summary>
    void Uncloak(nint launcherWindow);

    /// <summary>
    /// One line for the log: the launcher window's state (visible, minimised, cloaked, where), the foreground window,
    /// the window at the middle of the launcher's monitor, the desktop shell's window, and the windows above the
    /// launcher's. For tracking down a launcher that doesn't come back after a game.
    /// </summary>
    string Describe(nint launcherWindow);
}

/// <summary>How <see cref="IWindowFocus.AfterExit"/> got the foreground back, for the log.</summary>
public enum ForegroundResult
{
    /// <summary>Nothing to do on this platform, or there's no window (headless).</summary>
    NotSupported,

    /// <summary>The launcher was already in the foreground.</summary>
    AlreadyForeground,

    /// <summary>A plain request was allowed.</summary>
    Direct,

    /// <summary>It needed the foreground window's input queue attached to ours.</summary>
    AttachedInput,

    /// <summary>It needed a synthetic Alt key tap, which Windows counts as user input.</summary>
    AltKey,

    /// <summary>Windows refused every attempt; the taskbar button flashes instead.</summary>
    Failed,
}

/// <summary>The Linux stub, and headless runs: there's nothing to hand over.</summary>
public sealed class NullWindowFocus : IWindowFocus
{
    public static NullWindowFocus Instance { get; } = new();

    public void BeforeLaunch(nint launcherWindow, int childProcessId)
    {
    }

    public bool HasLostForeground(nint launcherWindow) => false;

    public ForegroundResult AfterExit(nint launcherWindow) => ForegroundResult.NotSupported;

    public bool IsCloaked(nint launcherWindow) => false;

    public void Uncloak(nint launcherWindow)
    {
    }

    public string Describe(nint launcherWindow) => "no window state on this platform";
}
