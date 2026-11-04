using System.Runtime.Versioning;
using Launcher.Core.Platform;
using Launcher.Core.Platform.Linux;

namespace Launcher.Core.Tests.Platform;

/// <summary>The power menu on Linux: logind's answers, and asking it (never an actual restart, shutdown or sleep).</summary>
public sealed class LinuxPowerControlTests
{
    [Theory]
    [SupportedOSPlatform("linux")]
    [InlineData(PowerAction.Restart, "yes", null)]
    [InlineData(PowerAction.Sleep, "challenge", "Needs an administrator's password to sleep (another user may be logged in).")]
    [InlineData(PowerAction.ShutDown, "no", "This account isn't allowed to shut down the computer.")]
    [InlineData(PowerAction.Sleep, "na", "This computer can't sleep.")]
    [InlineData(PowerAction.Restart, "maybe", "Not offered: logind answered 'maybe'.")]
    public void Logind_answers_become_what_the_menu_says(PowerAction action, string answer, string? expected)
    {
        Assert.SkipUnless(OperatingSystem.IsLinux(), "Linux-only.");

        Assert.Equal(expected, LinuxPowerControl.Explain(action, answer));
    }

    [Fact]
    [SupportedOSPlatform("linux")]
    public void Logind_is_asked_what_each_action_can_do()
    {
        Assert.SkipUnless(OperatingSystem.IsLinux(), "Linux-only.");
        Assert.SkipUnless(Directory.Exists("/run/systemd/system"), "Needs systemd (and so logind) running.");

        var power = new LinuxPowerControl();

        // Whatever this machine allows, each answer is logind's, not a failure to reach it.
        foreach (var action in (ReadOnlySpan<PowerAction>)[PowerAction.Restart, PowerAction.ShutDown, PowerAction.Sleep])
        {
            var unavailable = power.Unavailable(action);
            Assert.True(unavailable is null || !unavailable.StartsWith("logind couldn't", StringComparison.Ordinal), unavailable);
            Assert.DoesNotContain("libsystemd", unavailable ?? string.Empty, StringComparison.Ordinal);
            Assert.DoesNotContain("system bus", unavailable ?? string.Empty, StringComparison.Ordinal);
        }
    }
}
