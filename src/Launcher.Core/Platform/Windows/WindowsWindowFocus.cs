using System.Runtime.Versioning;
using static Launcher.Core.Platform.Windows.NativeMethods;

namespace Launcher.Core.Platform.Windows;

/// <summary>
/// Works with Windows' foreground rules instead of against them. Windows only lets a process take the foreground
/// in a few cases: it's the foreground process, the foreground process allowed it, it received the last input, or
/// there's no foreground window. After a game, input went to the emulator, so a plain
/// <c>SetForegroundWindow</c> often just flashes the taskbar button. <see cref="AfterExit"/> escalates:
/// <list type="number">
/// <item>restore (which activates the window when that's allowed), then <c>SetForegroundWindow</c>;</item>
/// <item>attach to the foreground window's input queue, which shares its foreground rights, and try again;</item>
/// <item>tap Alt with <c>SendInput</c>: Windows lifts the lock after keyboard input, as it does for Alt+Tab;</item>
/// <item>flash the taskbar button until the user switches back.</item>
/// </list>
/// It never changes system settings such as the foreground lock timeout.
/// </summary>
[SupportedOSPlatform("windows")]
public sealed class WindowsWindowFocus : IWindowFocus
{
    /// <summary>
    /// Allows any process to take the foreground, not only the emulator: a stub launcher's real emulator is a
    /// grandchild with an id we don't know yet. Windows withdraws the grant at the next keyboard or mouse input.
    /// </summary>
    public void BeforeLaunch(nint launcherWindow, int childProcessId) => AllowSetForegroundWindow(AsfwAny);

    public bool HasLostForeground(nint launcherWindow)
    {
        var foreground = GetForegroundWindow();
        if (foreground == 0 || foreground == launcherWindow)
        {
            return false;
        }

        GetWindowThreadProcessId(foreground, out var processId);
        return processId != GetCurrentProcessId();
    }

    public ForegroundResult AfterExit(nint launcherWindow)
    {
        if (launcherWindow == 0)
        {
            return ForegroundResult.NotSupported;
        }

        if (GetForegroundWindow() == launcherWindow && !IsIconic(launcherWindow))
        {
            return ForegroundResult.AlreadyForeground;
        }

        if (IsIconic(launcherWindow))
        {
            ShowWindow(launcherWindow, SwRestore);
        }

        if (IsForeground(launcherWindow) || (SetForegroundWindow(launcherWindow) && IsForeground(launcherWindow)))
        {
            return ForegroundResult.Direct;
        }

        if (TryWithAttachedInput(launcherWindow))
        {
            return ForegroundResult.AttachedInput;
        }

        if (TryWithAltKey(launcherWindow))
        {
            return ForegroundResult.AltKey;
        }

        var flash = new FlashWInfo
        {
            Size = (uint)System.Runtime.InteropServices.Marshal.SizeOf<FlashWInfo>(),
            Window = launcherWindow,
            Flags = FlashWTray | FlashWTimerNoFg,
        };
        FlashWindowEx(in flash);
        return ForegroundResult.Failed;
    }

    private static bool IsForeground(nint window) => GetForegroundWindow() == window;

    private static bool TryWithAttachedInput(nint window)
    {
        var foreground = GetForegroundWindow();
        if (foreground == 0)
        {
            return false;
        }

        var foregroundThread = GetWindowThreadProcessId(foreground, out _);
        var ourThread = GetCurrentThreadId();
        if (foregroundThread == 0 || foregroundThread == ourThread || !AttachThreadInput(ourThread, foregroundThread, true))
        {
            return false;
        }

        try
        {
            BringWindowToTop(window);
            SetForegroundWindow(window);
            SetActiveWindow(window);
            SetFocus(window);
        }
        finally
        {
            AttachThreadInput(ourThread, foregroundThread, false);
        }

        return IsForeground(window);
    }

    /// <summary>
    /// Alt goes down before the request and up after it, so the other window never sees a whole Alt tap (which
    /// would open its menu bar). The key-up lands in the launcher, which ignores input just after a game.
    /// </summary>
    private static unsafe bool TryWithAltKey(nint window)
    {
        var inputs = stackalloc Input[1];
        inputs[0] = new Input { Type = InputKeyboard };
        inputs[0].Data.Keyboard.VirtualKey = VkMenu;
        if (SendInput(1, inputs, sizeof(Input)) != 1)
        {
            return false;
        }

        SetForegroundWindow(window);
        inputs[0].Data.Keyboard.Flags = KeyEventFKeyUp;
        SendInput(1, inputs, sizeof(Input));
        return IsForeground(window);
    }
}
