using System.Globalization;
using System.Runtime.Versioning;
using System.Text;
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
public sealed unsafe class WindowsWindowFocus : IWindowFocus
{
    /// <summary>How many windows above the launcher's <see cref="Describe"/> lists, and how far down the z-order it looks.</summary>
    private const int AboveListed = 6;
    private const int AboveSteps = 500;

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

    public bool IsCloaked(nint launcherWindow)
    {
        uint cloaked = 0;
        return launcherWindow != 0
            && DwmGetWindowAttribute(launcherWindow, DwmwaCloaked, &cloaked, sizeof(uint)) >= 0
            && cloaked != 0;
    }

    /// <summary>
    /// The full screen experience's shell uncloaks a window it restores from minimised (seen on the owner's machine,
    /// where <c>SwitchToThisWindow</c> didn't). Restoring also activates it, so it keeps the foreground.
    /// </summary>
    public void Uncloak(nint launcherWindow)
    {
        ShowWindow(launcherWindow, SwMinimize);
        ShowWindow(launcherWindow, SwRestore);
        SetForegroundWindow(launcherWindow);
    }

    public string Describe(nint launcherWindow)
    {
        var text = new StringBuilder();
        text.Append("ours ");
        AppendWindow(text, launcherWindow, launcherWindow);
        if (launcherWindow != 0)
        {
            text.Append(CultureInfo.InvariantCulture, $" iconic={Flag(IsIconic(launcherWindow))} zoomed={Flag(IsZoomed(launcherWindow))}");
        }

        var monitor = default(Rect);
        var info = new MonitorInfo { Size = (uint)sizeof(MonitorInfo) };
        if (launcherWindow != 0 && GetMonitorInfo(MonitorFromWindow(launcherWindow, MonitorDefaultToNearest), ref info))
        {
            monitor = info.Monitor;
            text.Append("; monitor ");
            AppendRect(text, monitor);
        }

        text.Append("; foreground ");
        AppendWindow(text, GetForegroundWindow(), launcherWindow);

        // What's actually on top in the middle of the screen, whoever has the foreground.
        var centre = new Point { X = (monitor.Left + monitor.Right) / 2, Y = (monitor.Top + monitor.Bottom) / 2 };
        text.Append("; at centre ");
        AppendWindow(text, GetAncestor(WindowFromPoint(centre), GaRoot), launcherWindow);

        // Explorer's desktop: hidden (visible=0) in the full screen experience, and none without Explorer.
        text.Append("; shell ");
        AppendWindow(text, GetShellWindow(), launcherWindow);

        // The visible windows above ours on its monitor, nearest first.
        text.Append("; above [");
        var listed = 0;
        var window = launcherWindow;
        for (var steps = 0; launcherWindow != 0 && listed < AboveListed && steps < AboveSteps; steps++)
        {
            window = GetWindow(window, GwHwndPrev);
            if (window == 0)
            {
                break;
            }

            if (!IsWindowVisible(window) || !GetWindowRect(window, out var rect) || rect.Right <= monitor.Left
                || rect.Left >= monitor.Right || rect.Bottom <= monitor.Top || rect.Top >= monitor.Bottom)
            {
                continue;
            }

            text.Append(listed == 0 ? "" : ", ");
            AppendWindow(text, window, launcherWindow);
            listed++;
        }

        text.Append(']');
        return text.ToString();
    }

    private static string Flag(bool value) => value ? "1" : "0";

    /// <summary><c>0x1234 retroarch.exe(5678) RetroArch visible=1 cloaked=0 topmost=0 0,0 1280x800</c>, or <c>none</c>.</summary>
    private static void AppendWindow(StringBuilder text, nint window, nint launcherWindow)
    {
        if (window == 0)
        {
            text.Append("none");
            return;
        }

        GetWindowThreadProcessId(window, out var processId);
        text.Append(CultureInfo.InvariantCulture, $"0x{window:X} {ProcessName(processId)}({processId}) {ClassName(window)}");
        if (window == launcherWindow)
        {
            text.Append(" [launcher]");
        }

        uint cloaked = 0;
        _ = DwmGetWindowAttribute(window, DwmwaCloaked, &cloaked, sizeof(uint));
        var topmost = (GetWindowLongPtr(window, GwlExStyle) & WsExTopmost) != 0;
        text.Append(CultureInfo.InvariantCulture, $" visible={Flag(IsWindowVisible(window))} cloaked={cloaked} topmost={Flag(topmost)} ");
        if (GetWindowRect(window, out var rect))
        {
            AppendRect(text, rect);
        }
    }

    private static void AppendRect(StringBuilder text, Rect rect) =>
        text.Append(CultureInfo.InvariantCulture, $"{rect.Left},{rect.Top} {rect.Right - rect.Left}x{rect.Bottom - rect.Top}");

    private static string ClassName(nint window)
    {
        var name = stackalloc char[256];
        var length = GetClassName(window, name, 256);
        return length > 0 ? new string(name, 0, length) : "?";
    }

    private static string ProcessName(uint processId)
    {
        var process = OpenProcess(ProcessQueryLimitedInformation, false, processId);
        if (process == 0)
        {
            return "?";
        }

        try
        {
            var path = stackalloc char[1024];
            var size = 1024u;
            return QueryFullProcessImageName(process, 0, path, ref size) ? Path.GetFileName(new string(path, 0, (int)size)) : "?";
        }
        finally
        {
            CloseHandle(process);
        }
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
