using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using static Launcher.Core.Platform.Linux.LinuxNativeMethods;

namespace Launcher.Core.Platform.Linux;

/// <summary>
/// Restart, shutdown and sleep through systemd-logind (<c>org.freedesktop.login1.Manager</c> on the system bus,
/// called with libsystemd's sd-bus), as the owner chose on 2026-11-04: the desktop's session manager isn't asked, so
/// apps are sent SIGTERM as the session ends rather than asked to close. Never interactive: where logind would ask
/// for a password ("challenge": another user logged in, say), the action isn't offered, since a password prompt over a
/// full-screen launcher driven by a pad is no way to ask. What's offered is asked once (<c>CanReboot</c>,
/// <c>CanPowerOff</c>, <c>CanSuspend</c>) on the first <see cref="Unavailable"/>, which the app calls on a worker in
/// its warm-up. Sleep returns once logind has accepted it, before the computer sleeps.
/// </summary>
[SupportedOSPlatform("linux")]
public sealed unsafe class LinuxPowerControl : IPowerControl
{
    private const string Destination = "org.freedesktop.login1";
    private const string ObjectPath = "/org/freedesktop/login1";
    private const string Interface = "org.freedesktop.login1.Manager";

    private readonly Lazy<string?[]> _unavailable = new(AskLogind);

    public string? Unavailable(PowerAction action) => _unavailable.Value[(int)action];

    public string? Request(PowerAction action)
    {
        if (Unavailable(action) is { } unavailable)
        {
            return unavailable;
        }

        var member = action switch
        {
            PowerAction.Restart => "Reboot",
            PowerAction.ShutDown => "PowerOff",
            _ => "Suspend",
        };
        var problem = WithBus(bus => Call(bus, member, interactive: false, out _));
        return problem is null ? null : $"logind couldn't {Verb(action)}: {problem}";
    }

    /// <summary>What the menu says for logind's answer to <c>CanReboot</c>, <c>CanPowerOff</c> or <c>CanSuspend</c>: null for "yes".</summary>
    internal static string? Explain(PowerAction action, string? answer) => answer switch
    {
        "yes" => null,
        "challenge" => $"Needs an administrator's password to {Verb(action)} (another user may be logged in).",
        "no" => $"This account isn't allowed to {Verb(action)} the computer.",
        "na" => $"This computer can't {Verb(action)}.",
        _ => $"Not offered: logind answered '{answer}'.",
    };

    private static string Verb(PowerAction action) => action switch
    {
        PowerAction.Restart => "restart",
        PowerAction.ShutDown => "shut down",
        _ => "sleep",
    };

    private static string?[] AskLogind()
    {
        var unavailable = new string?[3];
        var problem = WithBus(bus =>
        {
            foreach (var action in (ReadOnlySpan<PowerAction>)[PowerAction.Restart, PowerAction.ShutDown, PowerAction.Sleep])
            {
                var member = action switch
                {
                    PowerAction.Restart => "CanReboot",
                    PowerAction.ShutDown => "CanPowerOff",
                    _ => "CanSuspend",
                };
                unavailable[(int)action] = Call(bus, member, interactive: null, out var answer) is { } failed
                    ? $"logind couldn't say whether this computer can {Verb(action)}: {failed}"
                    : Explain(action, answer);
            }

            return null;
        });
        if (problem is not null)
        {
            Array.Fill(unavailable, problem);
        }

        return unavailable;
    }

    /// <summary>Runs <paramref name="call"/> on a new connection to the system bus: null, or why it failed.</summary>
    private static string? WithBus(Func<nint, string?> call)
    {
        try
        {
            var opened = SdBusOpenSystem(out var bus);
            if (opened < 0)
            {
                return $"The system bus couldn't be reached: {Marshal.GetPInvokeErrorMessage(-opened)}.";
            }

            try
            {
                return call(bus);
            }
            finally
            {
                SdBusFlushCloseUnref(bus);
            }
        }
        catch (Exception e) when (e is DllNotFoundException or EntryPointNotFoundException)
        {
            return "Not available without systemd (libsystemd wasn't found).";
        }
    }

    /// <summary>
    /// Calls a logind method: null, or why it failed. The <c>Can*</c> methods take no argument
    /// (<paramref name="interactive"/> null) and answer a string; the actions take one, <c>interactive</c>, and answer
    /// nothing.
    /// </summary>
    private static string? Call(nint bus, string member, bool? interactive, out string? answer)
    {
        answer = null;
        var result = SdBusMessageNewMethodCall(bus, out var message, Destination, ObjectPath, Interface, member);
        if (result < 0)
        {
            return Marshal.GetPInvokeErrorMessage(-result);
        }

        var error = default(SdBusError);
        nint reply = 0;
        try
        {
            if (interactive is { } flag)
            {
                var value = flag ? 1 : 0;
                result = SdBusMessageAppendBasic(message, (byte)'b', &value);
                if (result < 0)
                {
                    return Marshal.GetPInvokeErrorMessage(-result);
                }
            }

            // 0: sd-bus's default timeout (25 s).
            result = SdBusCall(bus, message, 0, &error, out reply);
            if (result < 0)
            {
                return error.Message != 0 ? Marshal.PtrToStringUTF8(error.Message) : Marshal.GetPInvokeErrorMessage(-result);
            }

            if (interactive is null)
            {
                nint text;
                result = SdBusMessageReadBasic(reply, (byte)'s', &text);
                if (result < 0)
                {
                    return Marshal.GetPInvokeErrorMessage(-result);
                }

                answer = Marshal.PtrToStringUTF8(text);
            }

            return null;
        }
        finally
        {
            SdBusErrorFree(&error);
            if (reply != 0)
            {
                SdBusMessageUnref(reply);
            }

            SdBusMessageUnref(message);
        }
    }
}
