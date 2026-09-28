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

    /// <summary>True once another process's window is in the foreground, so the launcher can minimise without
    /// handing the foreground to some unrelated window.</summary>
    bool HasLostForeground(nint launcherWindow);

    /// <summary>Minimises the launcher without activating anything.</summary>
    void Minimise(nint launcherWindow);

    /// <summary>After the emulator exits: restores the launcher window and brings it to the foreground.</summary>
    ForegroundResult AfterExit(nint launcherWindow);
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

    public void Minimise(nint launcherWindow)
    {
    }

    public ForegroundResult AfterExit(nint launcherWindow) => ForegroundResult.NotSupported;
}
